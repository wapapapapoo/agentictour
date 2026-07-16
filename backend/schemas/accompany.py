from datetime import datetime
from typing import Any, Literal, Self

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
    status: Literal["pending", "change_pending", "done", "cancelled"] = "pending"

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        if self.reminder_time is not None and self.reminder_time > self.start_time:
            raise ValueError(
                "reminder_time must not be later than itinerary start_time"
            )
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
    status: Literal["pending", "change_pending", "done", "cancelled"] | None = None


class ItineraryResponse(BaseModel):
    """Read model for persisted itinerary rows.

    Creation constraints intentionally do not run here.  Older rows can predate
    the current reminder rules; rejecting those rows during response
    serialization turns an otherwise valid list request into HTTP 500.
    """

    trip_id: int
    title: str
    place_name: str
    start_time: datetime
    end_time: datetime
    itinerary_type: str
    reminder_time: datetime | None
    is_initial: bool
    status: str
    itinerary_id: int
    reminded_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    model_config = {"from_attributes": True}


class AdviceGenerateRequest(BaseModel):
    trip_id: int
    user_id: int = Field(gt=0)
    reason: str = Field(min_length=1)
    city_adcode: str = ""
    additional_requirement: str = ""
    selected_itinerary_ids: list[int] = Field(default_factory=list)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_name: str = ""


class AdviceActionRequest(BaseModel):
    action: Literal[
        "accept",
        "reject",
        "revise",
        "keep_original",
        "cancel_original",
    ]
    user_id: int = Field(gt=0)
    additional_requirement: str = ""
    selected_itinerary_ids: list[int] = Field(default_factory=list)


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
    city_adcode: str = ""
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_name: str = ""


class LocationUpdate(BaseModel):
    user_id: int = Field(gt=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    city_adcode: str = Field(default="", max_length=100)
    place_name: str = Field(default="", max_length=200)


class LocationResponse(BaseModel):
    user_id: int
    latitude: float
    longitude: float
    city_adcode: str = Field(default="", validation_alias="city")
    place_name: str = ""
    updated_at: datetime
    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    session_id: int
    user_message_id: int
    ai_message_id: int
    reply: str
    audit_status: str
    audit_reason: str | None


class ChatMessageResponse(BaseModel):
    message_id: int
    session_id: int
    sender_type: str
    content: str
    message_order: int
    audit_status: str
    audit_reason: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    session_id: int
    trip_id: int
    user_id: int
    title: str | None
    status: str
    messages: list[ChatMessageResponse]
