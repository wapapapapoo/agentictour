from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TripPlanGenerateRequest(BaseModel):
    action: str = Field(default="create", max_length=20)
    user_id: str = Field(..., max_length=64)
    origin_city: str = Field(..., max_length=100)
    destination_city: str = Field(..., max_length=100)
    start_date: str = Field(..., max_length=20)
    end_date: str = Field(..., max_length=20)
    people_count: str = Field(..., max_length=20)
    budget_total: str = Field(..., max_length=50)
    interests: str
    hotel_level: str = Field(..., max_length=100)
    transport_preference: str = Field(..., max_length=100)
    pace: str = Field(..., max_length=50)
    special_requirements: str = ""
    previous_plan_json: str = ""
    revision_request: str = ""


class PlanHumanizeRequest(BaseModel):
    user_id: str = Field(..., max_length=64)


class PlanHumanizeResponse(BaseModel):
    plan_id: int
    title: Optional[str] = None
    natural_language: str


class TripPlanReviseRequest(BaseModel):
    user_id: str = Field(..., max_length=64)
    revision_request: str


class TripPlanVersionResponse(BaseModel):
    id: int
    request_id: int
    user_id: str
    version_no: int
    revision_request: Optional[str]
    workflow_run_id: Optional[str]
    task_id: Optional[str]
    plan_json: Any
    created_at: datetime

    class Config:
        from_attributes = True


class TripPlanResponse(BaseModel):
    id: int
    user_id: str
    action: str
    origin_city: str
    destination_city: str
    start_date: str
    end_date: str
    people_count: str
    budget_total: str
    interests: str
    hotel_level: str
    transport_preference: str
    pace: str
    special_requirements: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    latest_version: Optional[TripPlanVersionResponse]

    class Config:
        from_attributes = True


class TripPlanListItem(BaseModel):
    id: int
    user_id: str
    origin_city: str
    destination_city: str
    start_date: str
    end_date: str
    version_no: Optional[int]
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
