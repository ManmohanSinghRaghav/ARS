"""app.pipeline.llm_factory

CrewAI expects `Agent.llm` to be a string or a CrewAI BaseLLM.

This factory returns CrewAI-native `LLM` instances (Gemini-only) using the per-run
API key passed in via `user_settings`.
"""

from __future__ import annotations

from typing import Optional

from crewai import LLM
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

class RetryingLLM(LLM):
    """CrewAI LLM wrapper that adds exponential backoff for API limits (e.g. 429)."""
    
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def call(self, *args, **kwargs):
        return super().call(*args, **kwargs)

def _get_effective_config(user_settings: Optional[dict] = None) -> dict:
    from app.config import get_settings
    defaults = get_settings()
    llm_backend = (user_settings or {}).get("llm_backend") or defaults.LLM_BACKEND or "gemini"

    return {
        "llm_backend": llm_backend.lower(),
        "gemini_api_key": (user_settings or {}).get("gemini_api_key") or defaults.GEMINI_API_KEY,
        "groq_api_key": (user_settings or {}).get("groq_api_key") or defaults.GROQ_API_KEY,
        "mlx_model": (user_settings or {}).get("mlx_model") or defaults.MLX_MODEL,
        "ollama_model": (user_settings or {}).get("ollama_model") or defaults.OLLAMA_MODEL,
        "ollama_url": (user_settings or {}).get("ollama_url") or defaults.OLLAMA_URL,
    }

def get_llm(user_settings: Optional[dict] = None) -> LLM:
    """Legacy get_llm, default to Reasoning tier."""
    return get_tier_llm("reasoning", user_settings)

def get_tier_llm(tier: str, user_settings: Optional[dict] = None) -> LLM:
    """
    Returns a CrewAI `LLM` instance. Offloads Extraction and Critic to Groq if key is present.
    """
    cfg = _get_effective_config(user_settings)
    backend = cfg["llm_backend"]

    if backend != "gemini":
         raise ValueError(
            f"Unsupported llm_backend '{backend}'. This server build supports Gemini+Groq for CrewAI runs."
        )

    gemini_key = (cfg.get("gemini_api_key") or "").strip()
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY is missing. Set it in server config or user settings.")
        
    groq_key = (cfg.get("groq_api_key") or "").strip()

    if tier == "reasoning":
        return RetryingLLM(model="gemini-1.5-pro", temperature=0.7, api_key=gemini_key)
    
    if tier == "extraction":
        if groq_key:
            return RetryingLLM(model="groq/llama3-8b-8192", temperature=0.1, api_key=groq_key)
        return RetryingLLM(model="gemini-1.5-flash", temperature=0.1, api_key=gemini_key)
        
    if tier == "critic":
        if groq_key:
            return RetryingLLM(model="groq/llama3-8b-8192", temperature=0.2, api_key=groq_key)
        return RetryingLLM(model="gemini-1.5-pro", temperature=0.2, api_key=gemini_key)

    # Backward-compatible default for any unexpected tier.
    return RetryingLLM(model="gemini-1.5-flash", temperature=0.0, api_key=gemini_key)
