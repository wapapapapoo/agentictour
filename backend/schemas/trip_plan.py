from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.accompany import ItineraryResponse


class TripPlanGenerateRequest(BaseModel):
    trip_id: int = Field(default=0, ge=0)
    action: str = Field(default="create", max_length=20)
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
    pass


class PlanHumanizeResponse(BaseModel):
    plan_id: int
    title: Optional[str] = None
    natural_language: str


class TripPlanReviseRequest(BaseModel):
    revision_request: str


class TripPlanVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    user_id: int
    version_no: int
    revision_request: Optional[str]
    workflow_run_id: Optional[str]
    task_id: Optional[str]
    plan_json: Any
    created_at: datetime

class TripPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    user_id: int
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

class TripPlanListItem(BaseModel):
    id: int
    trip_id: int
    user_id: int
    origin_city: str
    destination_city: str
    start_date: str
    end_date: str
    version_no: Optional[int]
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class TripPlanItinerarySyncResponse(BaseModel):
    """Result of importing a generated plan into the companion itinerary."""

    created_count: int
    itinerary_items: list[ItineraryResponse]
