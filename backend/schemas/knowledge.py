from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PlanKnowledgeRequest(BaseModel):
    user_id: str = Field(..., max_length=64)
    dataset_id: str = Field(..., max_length=100)
    chunk_size: int = Field(default=4000, ge=1, le=4000, description="分块大小(token数)，最大4000")


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
