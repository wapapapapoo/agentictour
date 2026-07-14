from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

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

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    title = Column(String(100), nullable=False)
    origin_city = Column(String(100), nullable=False)
    destination_city = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    timezone = Column(String(64), nullable=False, default="Asia/Shanghai")
    status = Column(String(20), nullable=False, default="planned")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    itinerary_items = relationship(
        "ItineraryItem",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    advice = relationship(
        "AIAdvice",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    memos = relationship(
        "Memo",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chat_session = relationship(
        "ChatSession",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    notifications = relationship(
        "Notification",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
