from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.trip import Trip


class TripPlanRequest(Base):
    __tablename__ = "trip_plan_requests"
    __table_args__ = (
        UniqueConstraint("trip_id", name="uk_trip_plan_request_trip"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    trip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", onupdate="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False, default="create"
    )

    origin_city: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[str] = mapped_column(String(20), nullable=False)
    end_date: Mapped[str] = mapped_column(String(20), nullable=False)
    people_count: Mapped[str] = mapped_column(String(20), nullable=False)
    budget_total: Mapped[str] = mapped_column(String(50), nullable=False)
    interests: Mapped[str] = mapped_column(Text, nullable=False)
    hotel_level: Mapped[str] = mapped_column(String(100), nullable=False)
    transport_preference: Mapped[str] = mapped_column(String(100), nullable=False)
    pace: Mapped[str] = mapped_column(String(50), nullable=False)
    special_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list[TripPlanVersion]] = relationship(
        "TripPlanVersion",
        back_populates="request",
        cascade="all, delete-orphan",
    )
    trip: Mapped[Trip] = relationship("Trip", back_populates="plan_request")


class TripPlanVersion(Base):
    __tablename__ = "trip_plan_versions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trip_plan_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", onupdate="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_request: Mapped[str | None] = mapped_column(Text, nullable=True)

    workflow_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )

    request: Mapped[TripPlanRequest] = relationship(
        "TripPlanRequest", back_populates="versions"
    )
