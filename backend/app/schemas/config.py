"""
Pydantic schemas for user LLM settings.
"""

from pydantic import BaseModel
from typing import Optional


class SettingsUpdate(BaseModel):
    llm_backend: Optional[str] = None
    mlx_model: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_url: Optional[str] = None
    tavily_api_key: Optional[str] = None


class SettingsResponse(BaseModel):
    llm_backend: str
    mlx_model: str
    ollama_model: str
    ollama_url: str
    tavily_api_key_set: bool  # masked — only shows whether a key is configured

    model_config = {"from_attributes": True}
