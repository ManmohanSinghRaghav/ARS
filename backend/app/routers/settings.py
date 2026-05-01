"""
Settings router — per-user LLM configuration using Firestore.
"""

from fastapi import APIRouter, Depends, HTTPException
from firebase_admin.firestore import client as FirestoreClient

from app.database import get_db
from app.auth.dependencies import User, get_current_user
from app.schemas.config import SettingsUpdate, SettingsResponse
from app.config import get_settings
from app.security.crypto import encrypt_str

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _get_or_create_settings(user: User, db) -> dict:
    """Get user settings from Firestore or return an empty dict."""
    doc_ref = db.collection("user_settings").document(user.id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {}


@router.get("", response_model=SettingsResponse)
def get_user_settings(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get the current user's LLM settings (with server defaults as fallback)."""
    defaults = get_settings()
    us = _get_or_create_settings(current_user, db)

    return SettingsResponse(
        llm_backend=us.get("llm_backend") or "gemini",
        gemini_api_key_set=bool(us.get("gemini_api_key") or defaults.GEMINI_API_KEY),
        gemini_model=us.get("gemini_model") or "gemini/gemini-2.0-flash",
        groq_api_key_set=bool(us.get("groq_api_key") or defaults.GROQ_API_KEY),
        openai_api_key_set=bool(us.get("openai_api_key") or defaults.OPENAI_API_KEY),
        claude_api_key_set=bool(us.get("claude_api_key") or defaults.CLAUDE_API_KEY),
        mlx_model=us.get("mlx_model") or getattr(defaults, "MLX_MODEL", ""),
        ollama_model=us.get("ollama_model") or getattr(defaults, "OLLAMA_MODEL", "llama3"),
        ollama_url=us.get("ollama_url") or getattr(defaults, "OLLAMA_URL", "http://localhost:11434"),
        tavily_api_key_set=bool(us.get("tavily_api_key") or defaults.TAVILY_API_KEY),
        heavy_model=us.get("heavy_model") or defaults.DEFAULT_HEAVY_MODEL,
        heavy_rpm=us.get("heavy_rpm") or defaults.DEFAULT_HEAVY_RPM,
        heavy_tpm=us.get("heavy_tpm") or defaults.DEFAULT_HEAVY_TPM,
        heavy_fallback_model=us.get("heavy_fallback_model") or defaults.DEFAULT_HEAVY_FALLBACK_MODEL,
        heavy_fallback_rpm=us.get("heavy_fallback_rpm") or defaults.DEFAULT_HEAVY_FALLBACK_RPM,
        heavy_fallback_tpm=us.get("heavy_fallback_tpm") or defaults.DEFAULT_HEAVY_FALLBACK_TPM,
        light_model=us.get("light_model") or defaults.DEFAULT_LIGHT_MODEL,
        light_rpm=us.get("light_rpm") or defaults.DEFAULT_LIGHT_RPM,
        light_tpm=us.get("light_tpm") or defaults.DEFAULT_LIGHT_TPM,
        light_fallback_model=us.get("light_fallback_model") or defaults.DEFAULT_LIGHT_FALLBACK_MODEL,
        light_fallback_rpm=us.get("light_fallback_rpm") or defaults.DEFAULT_LIGHT_FALLBACK_RPM,
        light_fallback_tpm=us.get("light_fallback_tpm") or defaults.DEFAULT_LIGHT_FALLBACK_TPM,
        execution_enabled=us.get("execution_enabled") if us.get("execution_enabled") is not None else defaults.EXECUTION_ENABLED,
    )


@router.put("", response_model=SettingsResponse)
def update_user_settings(
    payload: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update the current user's LLM settings."""
    defaults = get_settings()
    doc_ref = db.collection("user_settings").document(current_user.id)
    us = _get_or_create_settings(current_user, db)

    if payload.llm_backend is not None:
        if payload.llm_backend not in ("mlx", "ollama", "gemini", ""):
            raise HTTPException(status_code=400, detail="llm_backend must be 'mlx', 'ollama', 'gemini', or ''")
        us["llm_backend"] = payload.llm_backend
    if payload.gemini_api_key is not None:
        us["gemini_api_key"] = encrypt_str(payload.gemini_api_key)
    if payload.gemini_model is not None:
        us["gemini_model"] = payload.gemini_model
    if payload.groq_api_key is not None:
        us["groq_api_key"] = encrypt_str(payload.groq_api_key)
    if payload.openai_api_key is not None:
        us["openai_api_key"] = encrypt_str(payload.openai_api_key)
    if payload.claude_api_key is not None:
        us["claude_api_key"] = encrypt_str(payload.claude_api_key)
    if payload.mlx_model is not None:
        us["mlx_model"] = payload.mlx_model
    if payload.ollama_model is not None:
        us["ollama_model"] = payload.ollama_model
    if payload.ollama_url is not None:
        us["ollama_url"] = payload.ollama_url
    if payload.tavily_api_key is not None:
        us["tavily_api_key"] = encrypt_str(payload.tavily_api_key)
        
    for field in [
        "heavy_model", "heavy_rpm", "heavy_tpm", 
        "heavy_fallback_model", "heavy_fallback_rpm", "heavy_fallback_tpm",
        "light_model", "light_rpm", "light_tpm", 
        "light_fallback_model", "light_fallback_rpm", "light_fallback_tpm"
    ]:
        val = getattr(payload, field, None)
        if val is not None:
            us[field] = val
            
    if payload.execution_enabled is not None:
        us["execution_enabled"] = payload.execution_enabled

    doc_ref.set(us, merge=True)

    return SettingsResponse(
        llm_backend=us.get("llm_backend") or "gemini",
        gemini_api_key_set=bool(us.get("gemini_api_key") or defaults.GEMINI_API_KEY),
        gemini_model=us.get("gemini_model") or "gemini/gemini-2.0-flash",
        groq_api_key_set=bool(us.get("groq_api_key") or defaults.GROQ_API_KEY),
        openai_api_key_set=bool(us.get("openai_api_key") or defaults.OPENAI_API_KEY),
        claude_api_key_set=bool(us.get("claude_api_key") or defaults.CLAUDE_API_KEY),
        mlx_model=us.get("mlx_model") or getattr(defaults, "MLX_MODEL", ""),
        ollama_model=us.get("ollama_model") or getattr(defaults, "OLLAMA_MODEL", "llama3"),
        ollama_url=us.get("ollama_url") or getattr(defaults, "OLLAMA_URL", "http://localhost:11434"),
        tavily_api_key_set=bool(us.get("tavily_api_key") or defaults.TAVILY_API_KEY),
        heavy_model=us.get("heavy_model") or defaults.DEFAULT_HEAVY_MODEL,
        heavy_rpm=us.get("heavy_rpm") or defaults.DEFAULT_HEAVY_RPM,
        heavy_tpm=us.get("heavy_tpm") or defaults.DEFAULT_HEAVY_TPM,
        heavy_fallback_model=us.get("heavy_fallback_model") or defaults.DEFAULT_HEAVY_FALLBACK_MODEL,
        heavy_fallback_rpm=us.get("heavy_fallback_rpm") or defaults.DEFAULT_HEAVY_FALLBACK_RPM,
        heavy_fallback_tpm=us.get("heavy_fallback_tpm") or defaults.DEFAULT_HEAVY_FALLBACK_TPM,
        light_model=us.get("light_model") or defaults.DEFAULT_LIGHT_MODEL,
        light_rpm=us.get("light_rpm") or defaults.DEFAULT_LIGHT_RPM,
        light_tpm=us.get("light_tpm") or defaults.DEFAULT_LIGHT_TPM,
        light_fallback_model=us.get("light_fallback_model") or defaults.DEFAULT_LIGHT_FALLBACK_MODEL,
        light_fallback_rpm=us.get("light_fallback_rpm") or defaults.DEFAULT_LIGHT_FALLBACK_RPM,
        light_fallback_tpm=us.get("light_fallback_tpm") or defaults.DEFAULT_LIGHT_FALLBACK_TPM,
        execution_enabled=us.get("execution_enabled") if us.get("execution_enabled") is not None else defaults.EXECUTION_ENABLED,
    )
