"""
LLM dispatch — routes calls to MLX or Ollama based on configuration.
"""

import platform
import traceback
from typing import Optional


# Module-level cache for MLX model/tokenizer
_mlx_model = None
_mlx_tokenizer = None


def _get_effective_config(user_settings: Optional[dict] = None, server_settings: Optional[dict] = None) -> dict:
    """
    Merge user settings with server defaults.
    Returns dict with keys: llm_backend, mlx_model, ollama_model, ollama_url
    """
    from app.config import get_settings
    s = server_settings or {}
    defaults = get_settings()

    llm_backend = (user_settings or {}).get("llm_backend") or s.get("llm_backend") or defaults.LLM_BACKEND
    if not llm_backend:
        llm_backend = "mlx" if platform.system() == "Darwin" else "ollama"

    return {
        "llm_backend": llm_backend.lower(),
        "mlx_model": (user_settings or {}).get("mlx_model") or defaults.MLX_MODEL,
        "ollama_model": (user_settings or {}).get("ollama_model") or defaults.OLLAMA_MODEL,
        "ollama_url": (user_settings or {}).get("ollama_url") or defaults.OLLAMA_URL,
    }


def boot_mlx(model_name: str):
    """Load MLX model + tokenizer (macOS only). Cached at module level."""
    global _mlx_model, _mlx_tokenizer
    if _mlx_model is not None:
        return _mlx_model, _mlx_tokenizer
    from mlx_lm import load as mlx_load
    print(f"[Model] Loading {model_name} via MLX ...")
    _mlx_model, _mlx_tokenizer = mlx_load(model_name)
    print("[Model] Ready.")
    return _mlx_model, _mlx_tokenizer


def check_ollama(url: str, model_name: str):
    """Verify Ollama is reachable and model is available."""
    import requests
    try:
        resp = requests.get(f"{url}/api/tags", timeout=10)
        resp.raise_for_status()
        available = [m["name"] for m in resp.json().get("models", [])]
        if model_name not in available:
            match = [n for n in available if model_name.split(":")[0] in n]
            if not match:
                print(f"[WARN] Model '{model_name}' not found in Ollama. Available: {available}")
            else:
                print(f"[Model] Using closest match: {match[0]}")
        else:
            print(f"[Model] Ollama model '{model_name}' available.")
    except Exception as e:
        print(f"[WARN] Cannot reach Ollama at {url}: {e}")
    print(f"[Model] Backend = Ollama @ {url}  model = {model_name}")


def llm(messages: list, max_tokens: int = 800, config: Optional[dict] = None) -> str:
    """
    Single entry point for all LLM calls.
    config: dict with llm_backend, mlx_model, ollama_model, ollama_url
    """
    cfg = config or _get_effective_config()
    backend = cfg["llm_backend"]

    if backend == "mlx":
        from mlx_lm import generate as mlx_generate
        model, tokenizer = boot_mlx(cfg["mlx_model"])
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        return mlx_generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens)
    else:  # ollama
        import requests
        payload = {
            "model": cfg["ollama_model"],
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        resp = requests.post(f"{cfg['ollama_url']}/api/chat", json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


def safe_llm(messages: list, max_tokens: int = 800, fallback: str = "", config: Optional[dict] = None) -> str:
    """Wrapper around llm() that catches errors and returns fallback on failure."""
    try:
        return llm(messages, max_tokens, config=config)
    except Exception as e:
        print(f"  ✗ LLM call failed: {e}")
        traceback.print_exc()
        return fallback or f"LLM_ERROR: {e}"
