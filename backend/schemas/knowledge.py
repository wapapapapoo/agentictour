from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PlanKnowledgeRequest(BaseModel):
    user_id: str = Field(..., max_length=64)
    dataset_id: str = Field(..., max_length=100)


class PlanKnowledgeResponse(BaseModel):
    plan_id: int
    version_id: int
    humanized_text: str
    dataset_id: str
    document_name: str
    document_id: Optional[str] = None
    batch: Optional[str] = None
    indexing_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
