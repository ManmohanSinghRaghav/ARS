"""
UserSettings ORM model — per-user LLM configuration.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    llm_backend = Column(String(20), default="")       # "mlx" | "ollama" | "" (use server default)
    mlx_model = Column(String(255), default="")
    ollama_model = Column(String(255), default="")
    ollama_url = Column(String(500), default="")
    tavily_api_key = Column(String(255), default="")

    # Relationships
    user = relationship("User", back_populates="settings")
