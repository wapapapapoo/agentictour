from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class BlogMaterialCreate(BaseModel):
    user_id: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    destination: str = Field(..., max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    people_count: Optional[int] = None

    itinerary_text: str
    food_text: Optional[str] = None
    photo_text: Optional[str] = None
    expense_text: Optional[str] = None
    feeling_text: Optional[str] = None


class BlogMaterialResponse(BaseModel):
    id: int
    user_id: str
    title: str
    destination: str
    start_date: Optional[date]
    end_date: Optional[date]
    people_count: Optional[int]
    itinerary_text: str
    food_text: Optional[str]
    photo_text: Optional[str]
    expense_text: Optional[str]
    feeling_text: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class BlogGenerateRequest(BaseModel):
    material_id: int
    user_id: str
    content_type: str = Field(..., description="blog/social_post/title_tags")
    writing_style: str = Field(..., description="guide/story/casual/promotion")


class BlogGenerationResponse(BaseModel):
    id: int
    material_id: int
    user_id: str
    content_type: str
    writing_style: str
    generated_title: Optional[str]
    generated_content: str
    tags: Optional[str]
    risk_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BlogGenerationListItem(BaseModel):
    id: int
    material_id: int
    material_title: Optional[str]
    destination: Optional[str]
    content_type: str
    writing_style: str
    generated_title: Optional[str]
    created_at: datetime