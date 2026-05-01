"""
Pydantic schemas for user LLM settings.
"""

from pydantic import BaseModel
from typing import Optional


class SettingsUpdate(BaseModel):
    llm_backend: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None  # Model selection for Gemini
    groq_api_key: Optional[str] = None
    mlx_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_url: Optional[str] = None
    tavily_api_key: Optional[str] = None
    execution_enabled: Optional[bool] = None
    
    # Dynamic Models - Heavy Reasoning
    heavy_model: Optional[str] = None
    heavy_rpm: Optional[int] = None
    heavy_tpm: Optional[int] = None
    heavy_fallback_model: Optional[str] = None
    heavy_fallback_rpm: Optional[int] = None
    heavy_fallback_tpm: Optional[int] = None

    # Dynamic Models - Light Fast Processing
    light_model: Optional[str] = None
    light_rpm: Optional[int] = None
    light_tpm: Optional[int] = None
    light_fallback_model: Optional[str] = None
    light_fallback_rpm: Optional[int] = None
    light_fallback_tpm: Optional[int] = None


class SettingsResponse(BaseModel):
    llm_backend: str
    gemini_api_key_set: bool
    gemini_model: str  # Default Gemini model
    groq_api_key_set: bool
    mlx_model: str
    openai_api_key_set: bool
    claude_api_key_set: bool
    ollama_model: str
    ollama_url: str
    tavily_api_key_set: bool  # masked — only shows whether a key is configured
    execution_enabled: bool
    
    # Dynamic Models - Heavy Reasoning
    heavy_model: Optional[str] = None
    heavy_rpm: Optional[int] = None
    heavy_tpm: Optional[int] = None
    heavy_fallback_model: Optional[str] = None
    heavy_fallback_rpm: Optional[int] = None
    heavy_fallback_tpm: Optional[int] = None

    # Dynamic Models - Light Fast Processing
    light_model: Optional[str] = None
    light_rpm: Optional[int] = None
    light_tpm: Optional[int] = None
    light_fallback_model: Optional[str] = None
    light_fallback_rpm: Optional[int] = None
    light_fallback_tpm: Optional[int] = None

    model_config = {"from_attributes": True}
