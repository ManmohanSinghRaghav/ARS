"""app.pipeline.llm_factory

CrewAI expects `Agent.llm` to be a string or a CrewAI BaseLLM.

This factory returns CrewAI-native `LLM` instances (Gemini-only) using the per-run
API key passed in via `user_settings`.
"""

from __future__ import annotations

from typing import Optional

from crewai import LLM
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import time
import threading

class ModelGovernor:
    """Proactive rate limiter to prevent 429s by waiting before calls."""
    def __init__(self):
        self.request_history = []
        self.token_history = []
        self.lock = threading.Lock()
        self.min_call_gap = 3.0  # 3s breathing space between consecutive calls
        self.last_call_time = 0.0

    def _clean_history(self):
        now = time.time()
        self.request_history = [t for t in self.request_history if now - t < 60]
        self.token_history = [e for e in self.token_history if now - e['time'] < 60]

    def wait_if_needed(self, estimated_tokens: int, rpm_limit: int, tpm_limit: int):
        if not rpm_limit or not tpm_limit:
            return
        with self.lock:
            while True:
                self._clean_history()
                now = time.time()
                # Absolute gap between any two calls to this provider
                gap = now - self.last_call_time
                if gap < self.min_call_gap:
                    wait_time = self.min_call_gap - gap
                    time.sleep(wait_time)
                    continue
                # RPM check
                if len(self.request_history) >= rpm_limit:
                    sleep_time = 60 - (time.time() - self.request_history[0])
                    if sleep_time > 0:
                        print(f"[Governor] RPM Limit ({rpm_limit}) reached. Throttling for {sleep_time:.1f}s...")
                        time.sleep(max(1.0, sleep_time))
                    continue
                # TPM check
                current_tpm = sum(e['tokens'] for e in self.token_history)
                if current_tpm + estimated_tokens > tpm_limit:
                    sleep_time = 60 - (time.time() - self.token_history[0]['time'])
                    if sleep_time > 0:
                        print(f"[Governor] TPM Limit ({tpm_limit}) reached. Waiting {sleep_time:.1f}s...")
                        time.sleep(max(1.0, sleep_time))
                    continue
                # Passed all checks
                self.last_call_time = time.time()
                self.request_history.append(self.last_call_time)
                self.token_history.append({'time': self.last_call_time, 'tokens': estimated_tokens})
                break


# Per-provider governor registry — each provider tracks its own RPM/TPM independently.
# This prevents Gemini calls from consuming Groq's quota and vice versa.
_governors: dict[str, ModelGovernor] = {}
_governors_lock = threading.Lock()

def _get_governor(provider: str) -> ModelGovernor:
    """Return (and lazily create) the per-provider governor."""
    with _governors_lock:
        if provider not in _governors:
            _governors[provider] = ModelGovernor()
        return _governors[provider]


def _provider_from_model(model_name: str) -> str:
    """Resolve provider key from the model name prefix."""
    m = (model_name or "").lower()
    if m.startswith("groq"):
        return "groq"
    if m.startswith("gemini"):
        return "gemini"
    if m.startswith("openai"):
        return "openai"
    if m.startswith("anthropic") or m.startswith("claude"):
        return "anthropic"
    return "default"


def estimate_tokens(text: str) -> int:
    """Rule of thumb: 1 token ≈ 4 chars + 2000 token pessimistic output buffer."""
    input_tokens = len(str(text)) // 4
    return input_tokens + 2000 
import crewai

def _patch_crewai_llm():
    """
    Monkey-patches crewai.LLM.call to add global rate-limiting and 503 handling.
    This ensures all agents, even those using internally created LLMs, are protected.
    """
    original_call = crewai.LLM.call

    @retry(
        wait=wait_exponential(multiplier=3, min=10, max=120),
        stop=stop_after_attempt(8),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def wrapped_call(self, prompt=None, *args, **kwargs):
        content = prompt or kwargs.get("prompt", "")
        tokens = estimate_tokens(content)

        # 1. Proactive Rate Limiting (RPM/TPM)
        provider = _provider_from_model(self.model)
        gov = _get_governor(provider)
        rpm = getattr(self, "rpm", None)
        tpm = getattr(self, "tpm", None)
        gov.wait_if_needed(tokens, rpm, tpm)

        try:
            return original_call(self, content, *args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            
            # 503 / High Demand
            if "503" in err_str or "high demand" in err_str or "unavailable" in err_str or "overloaded" in err_str:
                print(f"[LLM] {self.model} experiencing high demand (503). Waiting 20s for recovery...")
                try:
                    from app.pipeline.runtime_context import get_run_id
                    from app.pipeline.progress import add_step
                    rid = get_run_id()
                    if rid:
                        add_step(rid, 0, 15, f"System Retry: High demand on {self.model} (503). Waiting 20s...", status="running", detail=str(e), is_internal=True)
                except Exception:
                    pass
                time.sleep(20) # User requested longer waits
                raise e
            
            # 429 / Rate Limit
            if "429" in err_str or "rate limit" in err_str:
                print(f"[LLM] Rate limit hit (429) on {self.model}. Cooldown 15s...")
                try:
                    from app.pipeline.runtime_context import get_run_id
                    from app.pipeline.progress import add_step
                    rid = get_run_id()
                    if rid:
                        add_step(rid, 0, 15, f"System Retry: Rate limit (429) on {self.model}. Cooldown 15s...", status="running", detail=str(e), is_internal=True)
                except Exception:
                    pass
                time.sleep(15)
                raise e
                
            raise e

    # Apply the patch
    crewai.LLM.call = wrapped_call
    print("[LLM Factory] Global CrewAI LLM patch applied.")

# Initialize the patch on module load
_patch_crewai_llm()

def _get_effective_config(user_settings: Optional[dict] = None) -> dict:
    from app.config import get_settings
    defaults = get_settings()
    return {
        "gemini_api_key": (user_settings or {}).get("gemini_api_key") or defaults.GEMINI_API_KEY,
        "gemini_model": (user_settings or {}).get("gemini_model") or "gemini-3.1-flash-lite-preview",
        "groq_api_key": (user_settings or {}).get("groq_api_key") or defaults.GROQ_API_KEY,
        "openai_api_key": (user_settings or {}).get("openai_api_key") or defaults.OPENAI_API_KEY,
        "claude_api_key": (user_settings or {}).get("claude_api_key") or defaults.CLAUDE_API_KEY,
        
        "heavy_model": (user_settings or {}).get("heavy_model") or defaults.DEFAULT_HEAVY_MODEL,
        "heavy_rpm": (user_settings or {}).get("heavy_rpm") or defaults.DEFAULT_HEAVY_RPM,
        "heavy_tpm": (user_settings or {}).get("heavy_tpm") or defaults.DEFAULT_HEAVY_TPM,
        "heavy_fallback_model": (user_settings or {}).get("heavy_fallback_model") or defaults.DEFAULT_HEAVY_FALLBACK_MODEL,
        "heavy_fallback_rpm": (user_settings or {}).get("heavy_fallback_rpm") or defaults.DEFAULT_HEAVY_FALLBACK_RPM,
        "heavy_fallback_tpm": (user_settings or {}).get("heavy_fallback_tpm") or defaults.DEFAULT_HEAVY_FALLBACK_TPM,

        "light_model": (user_settings or {}).get("light_model") or defaults.DEFAULT_LIGHT_MODEL,
        "light_rpm": (user_settings or {}).get("light_rpm") or defaults.DEFAULT_LIGHT_RPM,
        "light_tpm": (user_settings or {}).get("light_tpm") or defaults.DEFAULT_LIGHT_TPM,
        "light_fallback_model": (user_settings or {}).get("light_fallback_model") or defaults.DEFAULT_LIGHT_FALLBACK_MODEL,
        "light_fallback_rpm": (user_settings or {}).get("light_fallback_rpm") or defaults.DEFAULT_LIGHT_FALLBACK_RPM,
        "light_fallback_tpm": (user_settings or {}).get("light_fallback_tpm") or defaults.DEFAULT_LIGHT_FALLBACK_TPM,
    }

def get_llm(user_settings: Optional[dict] = None) -> LLM:
    """Legacy get_llm, default to Reasoning tier."""
    return get_tier_llm("reasoning", user_settings)

def get_tier_llm(tier: str, user_settings: Optional[dict] = None) -> LLM:
    """
    Returns a CrewAI `LLM` instance configured with dynamic heavy or light models.
    """
    cfg = _get_effective_config(user_settings)
    
    # Helper to resolve API keys based on the model prefix
    def _resolve_key(model_name: str) -> str:
        model_name = model_name.lower()
        if model_name.startswith("gemini"):
            return cfg.get("gemini_api_key", "").strip()
        if model_name.startswith("groq"):
            return cfg.get("groq_api_key", "").strip()
        if model_name.startswith("openai"):
            return cfg.get("openai_api_key", "").strip()
        if model_name.startswith("anthropic") or model_name.startswith("claude"):
            return cfg.get("claude_api_key", "").strip()
        # Fallback to gemini if undefined
        return cfg.get("gemini_api_key", "").strip()
        
    if tier in ["reasoning", "critic"]:
        main_model = cfg["heavy_model"]
        return LLM(
            model=main_model, 
            temperature=0.7 if tier == "reasoning" else 0.2, 
            api_key=_resolve_key(main_model),
            base_url=None, # Auto-resolved by model prefix
            rpm=cfg["heavy_rpm"],
            tpm=cfg["heavy_tpm"]
        )
    
    if tier == "extraction":
        main_model = cfg["light_model"]
        return LLM(
            model=main_model, 
            temperature=0.1, 
            api_key=_resolve_key(main_model),
            rpm=cfg["light_rpm"],
            tpm=cfg["light_tpm"]
        )

    # Backward-compatible default
    main_model = cfg["heavy_model"]
    return LLM(
        model=main_model, 
        temperature=0.0, 
        api_key=_resolve_key(main_model),
        rpm=cfg["heavy_rpm"],
        tpm=cfg["heavy_tpm"]
    )

