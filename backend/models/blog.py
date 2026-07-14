from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class BlogMaterial(Base):
    __tablename__ = "blog_materials"
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    people_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    itinerary_text: Mapped[str] = mapped_column(Text, nullable=False)
    food_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    feeling_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    generations: Mapped[list[BlogGeneration]] = relationship(
        "BlogGeneration",
        back_populates="material",
        cascade="all, delete-orphan",
    )
    photos: Mapped[list[BlogPhoto]] = relationship(
        "BlogPhoto",
        back_populates="material",
        cascade="all, delete-orphan",
    )


class BlogPhoto(Base):
    __tablename__ = "blog_photos"
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    material_id: Mapped[int] = mapped_column(
        ID_TYPE,
        ForeignKey("blog_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )

    material: Mapped[BlogMaterial] = relationship(
        "BlogMaterial", back_populates="photos"
    )


class BlogGeneration(Base):
    __tablename__ = "blog_generations"
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    material_id: Mapped[int] = mapped_column(
        ID_TYPE,
        ForeignKey("blog_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    writing_style: Mapped[str] = mapped_column(String(50), nullable=False)

    generated_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generated_content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), index=True
    )

    material: Mapped[BlogMaterial] = relationship(
        "BlogMaterial", back_populates="generations"
    )
