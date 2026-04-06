"""
Settings router — per-user LLM configuration using Firestore.
"""

from fastapi import APIRouter, Depends, HTTPException
from firebase_admin.firestore import client as FirestoreClient

from app.database import get_db
from app.auth.dependencies import User, get_current_user
from app.schemas.config import SettingsUpdate, SettingsResponse
from app.config import get_settings

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
        llm_backend=us.get("llm_backend") or defaults.LLM_BACKEND or "ollama",
        mlx_model=us.get("mlx_model") or defaults.MLX_MODEL,
        ollama_model=us.get("ollama_model") or defaults.OLLAMA_MODEL,
        ollama_url=us.get("ollama_url") or defaults.OLLAMA_URL,
        tavily_api_key_set=bool(us.get("tavily_api_key") or defaults.TAVILY_API_KEY),
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
        if payload.llm_backend not in ("mlx", "ollama", ""):
            raise HTTPException(status_code=400, detail="llm_backend must be 'mlx', 'ollama', or ''")
        us["llm_backend"] = payload.llm_backend
    if payload.mlx_model is not None:
        us["mlx_model"] = payload.mlx_model
    if payload.ollama_model is not None:
        us["ollama_model"] = payload.ollama_model
    if payload.ollama_url is not None:
        us["ollama_url"] = payload.ollama_url
    if payload.tavily_api_key is not None:
        us["tavily_api_key"] = payload.tavily_api_key

    doc_ref.set(us, merge=True)

    return SettingsResponse(
        llm_backend=us.get("llm_backend") or defaults.LLM_BACKEND or "ollama",
        mlx_model=us.get("mlx_model") or defaults.MLX_MODEL,
        ollama_model=us.get("ollama_model") or defaults.OLLAMA_MODEL,
        ollama_url=us.get("ollama_url") or defaults.OLLAMA_URL,
        tavily_api_key_set=bool(us.get("tavily_api_key") or defaults.TAVILY_API_KEY),
    )
