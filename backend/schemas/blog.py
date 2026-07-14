from datetime import date, datetime
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BlogContentType(StrEnum):
    BLOG = "blog"
    SOCIAL_POST = "social_post"
    TITLE_TAGS = "title_tags"


class BlogWritingStyle(StrEnum):
    GUIDE = "guide"
    STORY = "story"
    CASUAL = "casual"
    PROMOTION = "promotion"


class BlogBaseModel(BaseModel):
    @field_validator(
        "title",
        "destination",
        "itinerary_text",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def required_text_must_not_be_blank(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        value = value.strip()
        if not value:
            raise ValueError("field must not be blank")
        return value

    @field_validator(
        "food_text",
        "photo_text",
        "expense_text",
        "feeling_text",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def optional_text_blank_to_none(cls, value: Any) -> Any:
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        value = value.strip()
        return value or None


class BlogMaterialCreate(BlogBaseModel):
    user_id: int = Field(..., gt=0)
    title: str = Field(..., max_length=255)
    destination: str = Field(..., max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    people_count: Optional[int] = Field(default=None, gt=0)

    itinerary_text: str
    food_text: Optional[str] = None
    photo_text: Optional[str] = None
    expense_text: Optional[str] = None
    feeling_text: Optional[str] = None

    @model_validator(mode="after")
    def end_date_must_not_be_before_start_date(self) -> "BlogMaterialCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class BlogMaterialResponse(BaseModel):
    id: int
    user_id: int
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

    model_config = ConfigDict(from_attributes=True)


class BlogPhotoResponse(BaseModel):
    id: int
    material_id: int
    user_id: int
    original_filename: str
    content_type: str
    file_size: int
    file_url: str
    created_at: datetime


class BlogGenerateRequest(BlogBaseModel):
    material_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)
    content_type: BlogContentType = Field(
        ..., description="blog/social_post/title_tags"
    )
    writing_style: BlogWritingStyle = Field(
        ..., description="guide/story/casual/promotion"
    )


class BlogGenerationResponse(BaseModel):
    id: int
    material_id: int
    user_id: int
    content_type: str
    writing_style: str
    generated_title: Optional[str]
    generated_content: str
    tags: Optional[str]
    risk_note: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlogGenerationListItem(BaseModel):
    id: int
    material_id: int
    material_title: Optional[str]
    destination: Optional[str]
    content_type: str
    writing_style: str
    generated_title: Optional[str]
    created_at: datetime
