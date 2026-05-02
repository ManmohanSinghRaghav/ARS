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
    # ── Database & Auth ──
    # Managed securely via Firebase natively

    # ── LLM defaults (overridable per-user via settings API) ──
    # ── LLM API Keys (used for prefix resolution) ──
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    CLAUDE_API_KEY: str = ""

    # ── Local / Self-hosted LLM Backends ──
    LLM_BACKEND: str = "gemini"       # default: gemini | ollama | mlx
    MLX_MODEL: str = "mlx-community/Mistral-7B-Instruct-v0.3-4bit"  # macOS only
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_URL: str = ""
    
    # ── Dynamic Model Categories ──
    DEFAULT_HEAVY_MODEL: str = "gemini/gemini-3.1-flash-lite-preview"
    DEFAULT_HEAVY_RPM: int = 15
    DEFAULT_HEAVY_TPM: int = 30000
    DEFAULT_HEAVY_FALLBACK_MODEL: str = "gemini/gemini-3.1-flash-lite-preview"
    DEFAULT_HEAVY_FALLBACK_RPM: int = 15
    DEFAULT_HEAVY_FALLBACK_TPM: int = 30000

    DEFAULT_LIGHT_MODEL: str = "gemini/gemini-3.1-flash-lite-preview"
    DEFAULT_LIGHT_RPM: int = 15
    DEFAULT_LIGHT_TPM: int = 30000
    DEFAULT_LIGHT_FALLBACK_MODEL: str = "gemini/gemini-3.1-flash-lite-preview"
    DEFAULT_LIGHT_FALLBACK_RPM: int = 15
    DEFAULT_LIGHT_FALLBACK_TPM: int = 30000
    TAVILY_API_KEY: str = ""
    EXECUTION_ENABLED: bool = True
    MODAL_TOKEN_ID: str = ""
    MODAL_TOKEN_SECRET: str = ""

    # ── Secrets at rest ──
    # Server secret used to encrypt per-user API keys stored in Firestore.
    # If unset, encryption is disabled and encrypted values cannot be decrypted.
    SETTINGS_ENCRYPTION_KEY: str = ""

    # ── Firebase Storage ──
    FIREBASE_STORAGE_BUCKET: str = ""

    # ── Cache (Redis) ──
    REDIS_URL: str = ""

    # ── Vector Store & RAG (ChromaDB) ──
    CHROMA_ENABLED: bool = False
    CHROMA_HOST: str = "https://api.trychroma.com"
    CHROMA_PORT: int = 443
    CHROMA_API_KEY: str = ""
    CHROMA_TENANT: str = "d5a06c2e-49d9-4efa-8357-69a2110af4ca"
    CHROMA_DATABASE: str = "ARS"

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
