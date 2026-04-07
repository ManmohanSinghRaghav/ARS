"""
LLM Factory — Yields standard LangChain BaseChatModel instances for CrewAI compatibility.
"""

from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel

def _get_effective_config(user_settings: Optional[dict] = None) -> dict:
    from app.config import get_settings
    defaults = get_settings()
    llm_backend = (user_settings or {}).get("llm_backend") or defaults.LLM_BACKEND or "ollama"

    return {
        "llm_backend": llm_backend.lower(),
        "mlx_model": (user_settings or {}).get("mlx_model") or defaults.MLX_MODEL,
        "ollama_model": (user_settings or {}).get("ollama_model") or defaults.OLLAMA_MODEL,
        "ollama_url": (user_settings or {}).get("ollama_url") or defaults.OLLAMA_URL,
    }

def get_llm(user_settings: Optional[dict] = None) -> BaseChatModel:
    """Returns a Langchain ChatModel compatible instance based on settings."""
    cfg = _get_effective_config(user_settings)
    backend = cfg["llm_backend"]

    if backend == "mlx":
        # Note: If running locally on a mac, langchain_community provides ChatMLX
        from langchain_community.chat_models.mlx import ChatMLX
        return ChatMLX(model=cfg["mlx_model"])
    
    # Default to Ollama
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=cfg["ollama_model"],
        base_url=cfg["ollama_url"],
        temperature=0.7,
    )
