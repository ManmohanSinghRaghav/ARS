"""
Settings router — per-user LLM configuration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.settings import UserSettings
from app.schemas.config import SettingsUpdate, SettingsResponse
from app.auth.dependencies import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _get_or_create_settings(user: User, db: Session) -> UserSettings:
    """Get user settings row, creating one if it doesn't exist."""
    us = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    if not us:
        us = UserSettings(user_id=user.id)
        db.add(us)
        db.commit()
        db.refresh(us)
    return us


@router.get("", response_model=SettingsResponse)
def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's LLM settings (with server defaults as fallback)."""
    defaults = get_settings()
    us = _get_or_create_settings(current_user, db)

    return SettingsResponse(
        llm_backend=us.llm_backend or defaults.LLM_BACKEND or "ollama",
        mlx_model=us.mlx_model or defaults.MLX_MODEL,
        ollama_model=us.ollama_model or defaults.OLLAMA_MODEL,
        ollama_url=us.ollama_url or defaults.OLLAMA_URL,
        tavily_api_key_set=bool(us.tavily_api_key or defaults.TAVILY_API_KEY),
    )


@router.put("", response_model=SettingsResponse)
def update_user_settings(
    payload: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's LLM settings."""
    defaults = get_settings()
    us = _get_or_create_settings(current_user, db)

    if payload.llm_backend is not None:
        if payload.llm_backend not in ("mlx", "ollama", ""):
            raise HTTPException(status_code=400, detail="llm_backend must be 'mlx', 'ollama', or '' (server default)")
        us.llm_backend = payload.llm_backend
    if payload.mlx_model is not None:
        us.mlx_model = payload.mlx_model
    if payload.ollama_model is not None:
        us.ollama_model = payload.ollama_model
    if payload.ollama_url is not None:
        us.ollama_url = payload.ollama_url
    if payload.tavily_api_key is not None:
        us.tavily_api_key = payload.tavily_api_key

    db.commit()
    db.refresh(us)

    return SettingsResponse(
        llm_backend=us.llm_backend or defaults.LLM_BACKEND or "ollama",
        mlx_model=us.mlx_model or defaults.MLX_MODEL,
        ollama_model=us.ollama_model or defaults.OLLAMA_MODEL,
        ollama_url=us.ollama_url or defaults.OLLAMA_URL,
        tavily_api_key_set=bool(us.tavily_api_key or defaults.TAVILY_API_KEY),
    )
