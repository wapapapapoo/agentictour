from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.trip import Trip

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    itinerary_id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    trip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    place_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    itinerary_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="play"
    )
    reminder_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_initial: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    trip: Mapped[Trip] = relationship("Trip", back_populates="itinerary_items")


class Memo(Base):
    __tablename__ = "memos"

    memo_id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    trip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    memo_text: Mapped[str] = mapped_column(Text, nullable=False)
    reminder_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    trip: Mapped[Trip] = relationship("Trip", back_populates="memos")


class AIAdvice(Base):
    __tablename__ = "ai_advice"

    advice_id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    trip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    advice_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="recommendation"
    )
    parent_advice_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ai_advice.advice_id", ondelete="SET NULL"),
        nullable=True,
    )
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    advice_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_itinerary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    audit_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    audit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_stopped: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    trip: Mapped[Trip] = relationship("Trip", back_populates="advice")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    trip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    advice_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ai_advice.advice_id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )
    trip: Mapped[Trip] = relationship("Trip", back_populates="notifications")


class AgentJobState(Base):
    __tablename__ = "agent_job_states"

    job_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserLocation(Base):
    __tablename__ = "user_locations"

    user_id: Mapped[int] = mapped_column(
        ID_TYPE,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    place_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    trip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    conversation_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, default=lambda: str(uuid4())
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    trip: Mapped[Trip] = relationship("Trip", back_populates="chat_session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id: Mapped[int] = mapped_column(
        ID_TYPE, primary_key=True, autoincrement=True
    )
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_order: Mapped[int] = mapped_column(Integer, nullable=False)
    audit_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pass"
    )
    audit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
