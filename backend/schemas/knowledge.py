from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanKnowledgeRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    dataset_id: str = Field(
        default="",
        max_length=100,
        description="知识库ID，留空则取环境变量 DIFY_KNOWLEDGE_DATASET_ID",
    )
    chunk_size: int = Field(
        default=4000, ge=1, le=4000, description="分块大小(token数)，最大4000"
    )


class PlanKnowledgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    version_id: int
    humanized_text: str
    dataset_id: str
    document_name: str
    document_id: Optional[str] = None
    batch: Optional[str] = None
    indexing_status: Optional[str] = None
    created_at: datetime

class KnowledgeSearchRequest(BaseModel):
    dataset_id: str = Field(
        default="",
        max_length=100,
        description="知识库ID，留空则取环境变量 DIFY_KNOWLEDGE_DATASET_ID",
    )
    query: str


class KnowledgeSearchResult(BaseModel):
    chunk_content: str
    score: float
    document_id: str
    plan_id: Optional[int] = None
    plan_title: Optional[str] = None


class KnowledgeSearchResponse(BaseModel):
    results: list[KnowledgeSearchResult]


class TraceKnowledgeResponse(BaseModel):
    plan_id: int
    version_id: int
    title: Optional[str] = None
    origin_city: str
    destination_city: str
    start_date: str
    end_date: str
    document_id: str
    document_name: str
    indexing_status: str
    created_at: datetime
