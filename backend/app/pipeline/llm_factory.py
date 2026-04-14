"""
LLM Factory — Yields standard LangChain BaseChatModel instances for CrewAI compatibility.
"""

from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel

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

def get_llm(user_settings: Optional[dict] = None) -> BaseChatModel:
    """Legacy get_llm, default to Reasoning tier."""
    return get_tier_llm("reasoning", user_settings)

def get_tier_llm(tier: str, user_settings: Optional[dict] = None) -> BaseChatModel:
    """
    Returns a Langchain ChatModel compatible instance based on the topological tier.
    Tiers:
      - reasoning: gemini-3.1-pro-preview
      - extraction: gemini-3.1-flash-lite-preview
      - critic: muse-spark-thinking (mocked to gemini-pro if unavailable)
      - router: llama-3.1-8b via Groq
    """
    cfg = _get_effective_config(user_settings)
    backend = cfg["llm_backend"]

    if backend == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_groq import ChatGroq

        gemini_key = cfg.get("gemini_api_key") or None
        groq_key = cfg.get("groq_api_key") or None

        if tier == "reasoning":
            return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7, google_api_key=gemini_key)  # Using 1.5-pro as stable fallback for preview
        elif tier == "extraction":
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1, google_api_key=gemini_key)  # Using 1.5-flash as stable fallback
        elif tier == "router":
            return ChatGroq(model="llama3-8b-8192", temperature=0.0, groq_api_key=groq_key)
        elif tier == "critic":
            return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.2, google_api_key=gemini_key)  # Muse-spark fallback

    if backend == "mlx":
        from langchain_community.chat_models.mlx import ChatMLX
        return ChatMLX(model=cfg["mlx_model"])
    
    # Default to Ollama if all else fails
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=cfg["ollama_model"],
        base_url=cfg["ollama_url"],
        temperature=0.7,
    )
