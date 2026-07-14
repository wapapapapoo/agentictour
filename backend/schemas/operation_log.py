from __future__ import annotations

from pydantic import BaseModel, Field


class PlanLikeRequest(BaseModel):
    chunk_ids: list[str] = Field(..., min_length=1)


class PlanLikeResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    chunk_ids: list[str]
    created_at: str
