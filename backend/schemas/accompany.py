from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class MemoCreate(BaseModel):
    trip_id: int
    memo_text: str = Field(min_length=1)
    reminder_time: datetime | None = None


class MemoUpdate(BaseModel):
    memo_text: str | None = Field(default=None, min_length=1)
    reminder_time: datetime | None = None


class MemoResponse(MemoCreate):
    memo_id: int
    reminded_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    model_config = {"from_attributes": True}


class ItineraryCreate(BaseModel):
    trip_id: int
    title: str = Field(min_length=1, max_length=100)
    place_name: str = Field(min_length=1, max_length=100)
    start_time: datetime
    end_time: datetime
    itinerary_type: Literal["transit", "play"] = "play"
    reminder_time: datetime | None = None
    is_initial: bool = False
    status: Literal["pending", "done", "cancelled"] = "pending"

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        if self.itinerary_type == "transit" and self.reminder_time is None:
            raise ValueError("transit itinerary requires reminder_time")
        return self


class ItineraryUpdate(BaseModel):
    title: str | None = None
    place_name: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    itinerary_type: Literal["transit", "play"] | None = None
    reminder_time: datetime | None = None
    is_initial: bool | None = None
    status: Literal["pending", "done", "cancelled"] | None = None


class ItineraryResponse(ItineraryCreate):
    itinerary_id: int
    reminded_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    model_config = {"from_attributes": True}


class AdviceGenerateRequest(BaseModel):
    trip_id: int
    user_id: int = Field(gt=0)
    reason: str = Field(min_length=1)
    city: str = ""
    current_itinerary: Any = None
    additional_requirement: str = ""
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_name: str = ""
    location_context: str = ""


class AdviceActionRequest(BaseModel):
    action: Literal["accept", "reject", "revise"]
    user_id: int = Field(gt=0)
    additional_requirement: str = ""


class AdviceResponse(BaseModel):
    advice_id: int
    trip_id: int
    advice_type: str
    parent_advice_id: int | None
    input_text: str | None
    reason_text: str | None
    advice_text: str
    proposed_itinerary: Any = None
    result: str
    audit_status: str
    audit_reason: str | None
    generation_stopped: bool
    created_at: datetime


class NotificationResponse(BaseModel):
    notification_id: int
    trip_id: int
    user_id: int
    advice_id: int | None
    category: str
    content: str
    read_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    trip_id: int
    user_id: int = Field(gt=0)
    message: str = Field(min_length=1)
    city: str = ""
    nearby_context: str = ""
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_name: str = ""


class LocationUpdate(BaseModel):
    user_id: int = Field(gt=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    city: str = Field(default="", max_length=100)
    place_name: str = Field(default="", max_length=200)
    location_context: str = ""


class LocationResponse(LocationUpdate):
    updated_at: datetime
    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    session_id: int
    user_message_id: int
    ai_message_id: int
    reply: str
    audit_status: str
    audit_reason: str | None
    conversation_id: str | None = None
