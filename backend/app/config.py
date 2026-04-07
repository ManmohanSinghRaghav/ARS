"""
Application configuration via pydantic-settings.
Reads from environment variables / .env file.
All paths are resolved relative to the backend/ directory
so the server works regardless of the working directory.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Resolve the backend/ directory (parent of app/)
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # ── Database ──
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'ars.db'}"

    # ── JWT ──
    SECRET_KEY: str = "change-me-in-production-use-a-random-64-char-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── LLM defaults (overridable per-user via settings API) ──
    LLM_BACKEND: str = ""
    MLX_MODEL: str = "mlx-community/Qwen2.5-3B-Instruct-bf16"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_URL: str = "http://localhost:11434"
    TAVILY_API_KEY: str = ""

    # ── Outputs ──
    OUTPUTS_DIR: str = str(BACKEND_DIR / "outputs")

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {
        "env_file": str(BACKEND_DIR.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
