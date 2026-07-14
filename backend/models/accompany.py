from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    itinerary_id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(100), nullable=False)
    place_name = Column(String(100), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    itinerary_type = Column(String(20), nullable=False, default="play")
    reminder_time = Column(DateTime, nullable=True)
    is_initial = Column(Boolean, nullable=False, default=False)
    reminded_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    trip = relationship("Trip", back_populates="itinerary_items")


class Memo(Base):
    __tablename__ = "memos"

    memo_id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    memo_text = Column(Text, nullable=False)
    reminder_time = Column(DateTime, nullable=True)
    reminded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    trip = relationship("Trip", back_populates="memos")


class AIAdvice(Base):
    __tablename__ = "ai_advice"

    advice_id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    advice_type = Column(String(30), nullable=False, default="recommendation")
    parent_advice_id = Column(
        BigInteger,
        ForeignKey("ai_advice.advice_id", ondelete="SET NULL"),
        nullable=True,
    )
    input_text = Column(Text, nullable=True)
    reason_text = Column(Text, nullable=True)
    advice_text = Column(Text, nullable=False)
    proposed_itinerary_json = Column(Text, nullable=True)
    result = Column(String(20), nullable=False, default="pending")
    audit_status = Column(String(20), nullable=False, default="pending")
    audit_reason = Column(Text, nullable=True)
    generation_stopped = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    trip = relationship("Trip", back_populates="advice")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    advice_id = Column(
        BigInteger,
        ForeignKey("ai_advice.advice_id", ondelete="SET NULL"),
        nullable=True,
    )
    category = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    trip = relationship("Trip", back_populates="notifications")


class AgentJobState(Base):
    __tablename__ = "agent_job_states"

    job_name = Column(String(50), primary_key=True)
    last_run_at = Column(DateTime, nullable=True)


class UserLocation(Base):
    __tablename__ = "user_locations"

    user_id = Column(
        ID_TYPE,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    city = Column(String(100), nullable=True)
    place_name = Column(String(200), nullable=True)
    location_context = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    title = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    dify_conversation_id = Column(String(100), nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    trip = relationship("Trip", back_populates="chat_session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    session_id = Column(
        BigInteger,
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    message_order = Column(Integer, nullable=False)
    audit_status = Column(String(20), nullable=False, default="pass")
    audit_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
