from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TripStatus = Literal["planned", "ongoing", "completed", "cancelled"]


class TripCreate(BaseModel):
    user_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=100)
    origin_city: str = Field(min_length=1, max_length=100)
    destination_city: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=64)
    status: TripStatus = "planned"

    @model_validator(mode="after")
    def validate_date_range(self) -> TripCreate:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TripUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    origin_city: str | None = Field(default=None, min_length=1, max_length=100)
    destination_city: str | None = Field(default=None, min_length=1, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    status: TripStatus | None = None

    @model_validator(mode="after")
    def validate_complete_date_range(self) -> TripUpdate:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must be on or after start_date")
        return self


class TripResponse(BaseModel):
    id: int
    user_id: int
    title: str
    origin_city: str
    destination_city: str
    start_date: date
    end_date: date
    timezone: str
    status: TripStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
