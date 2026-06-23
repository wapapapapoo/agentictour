"""Pydantic models for AgenticTour API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class TravelPlanRequest(BaseModel):
    destination: str = Field(..., description="目的地", examples=["东京"])
    departure_city: str = Field(default="北京", description="出发城市")
    start_date: date = Field(..., description="出发日期")
    end_date: date = Field(..., description="返回日期")
    budget: float = Field(default=10000, description="预算（元）")
    travelers: int = Field(default=1, ge=1, le=20, description="人数")
    style: str = Field(
        default="balanced",
        description="风格: leisure|adventure|foodie|culture|shopping|balanced|luxury",
    )
    interests: list[str] = Field(default_factory=list, description="兴趣标签")
    special_requirements: str = Field(default="", description="特殊需求")


class CompanionChatRequest(BaseModel):
    plan_id: str | None = Field(default=None)
    message: str = Field(...)
    context: dict[str, Any] = Field(default_factory=dict)


class BlogGenerateRequest(BaseModel):
    plan_id: str
    tone: str = Field(default="casual")
    focus: str = Field(default="highlights")
    include_photos: bool = Field(default=True)


class DayPlan(BaseModel):
    day: int
    date: date
    theme: str
    activities: list[dict[str, Any]]
    meals: list[dict[str, Any]]
    transportation: str
    notes: str


class TravelPlan(BaseModel):
    id: str
    created_at: datetime
    request: TravelPlanRequest
    overview: str
    weather_forecast: list[dict[str, Any]]
    days: list[DayPlan]
    budget_breakdown: dict[str, float]
    tips: list[str]
    recommended_attractions: list[dict[str, Any]]
    recommended_hotels: list[dict[str, Any]]
    agent_log: list[str]


class CompanionResponse(BaseModel):
    reply: str
    suggestions: list[str]
    relevant_info: dict[str, Any]
    agent_emoji: str = "🤖"
