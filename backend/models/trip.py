from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.accompany import (
        AIAdvice,
        ChatSession,
        ItineraryItem,
        Memo,
        Notification,
    )
    from models.trip_plan import TripPlanRequest

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Trip(Base):
    """Stable aggregate root for all travel-companion data."""

    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="chk_trip_date_range"),
        CheckConstraint(
            "status IN ('planned', 'ongoing', 'completed', 'cancelled')",
            name="chk_trip_status",
        ),
        Index("idx_trips_user_status", "user_id", "status"),
        Index("idx_trips_dates", "start_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", onupdate="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_city: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Shanghai"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="planned"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    itinerary_items: Mapped[list[ItineraryItem]] = relationship(
        "ItineraryItem",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    advice: Mapped[list[AIAdvice]] = relationship(
        "AIAdvice",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    memos: Mapped[list[Memo]] = relationship(
        "Memo",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chat_session: Mapped[ChatSession | None] = relationship(
        "ChatSession",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    plan_request: Mapped[TripPlanRequest | None] = relationship(
        "TripPlanRequest",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
        single_parent=True,
    )
