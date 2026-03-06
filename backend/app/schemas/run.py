"""
Pydantic schemas for research runs.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RunCreate(BaseModel):
    topic: str


class RunResponse(BaseModel):
    id: int
    user_id: int
    topic: str
    status: str
    hypothesis: str
    generated_code: str
    execution_output: str
    paper_markdown: str
    summary_json: dict
    error_message: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RunListItem(BaseModel):
    id: int
    topic: str
    status: str
    paper_word_count: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
