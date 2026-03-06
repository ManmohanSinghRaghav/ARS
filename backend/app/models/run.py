"""
ResearchRun ORM model — stores each pipeline execution and its results.
"""

import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(500), nullable=False)
    status = Column(String(20), default="pending")  # pending | running | completed | failed
    hypothesis = Column(Text, default="")
    generated_code = Column(Text, default="")
    execution_output = Column(Text, default="")
    paper_markdown = Column(Text, default="")
    summary_json = Column(JSON, default=dict)
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="runs")
