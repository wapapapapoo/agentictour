from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class TripPlanRequest(Base):
    __tablename__ = "trip_plan_requests"
    __table_args__ = (
        UniqueConstraint("trip_id", name="uk_trip_plan_request_trip"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", onupdate="CASCADE"),
        nullable=False,
    )
    action = Column(String(20), nullable=False, default="create")

    origin_city = Column(String(100), nullable=False)
    destination_city = Column(String(100), nullable=False)
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    people_count = Column(String(20), nullable=False)
    budget_total = Column(String(50), nullable=False)
    interests = Column(Text, nullable=False)
    hotel_level = Column(String(100), nullable=False)
    transport_preference = Column(String(100), nullable=False)
    pace = Column(String(50), nullable=False)
    special_requirements = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    versions = relationship(
        "TripPlanVersion",
        back_populates="request",
        cascade="all, delete-orphan",
    )
    trip = relationship("Trip", back_populates="plan_request")


class TripPlanVersion(Base):
    __tablename__ = "trip_plan_versions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(
        BigInteger,
        ForeignKey("trip_plan_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", onupdate="CASCADE"),
        nullable=False,
    )
    version_no = Column(Integer, nullable=False)
    revision_request = Column(Text, nullable=True)

    workflow_run_id = Column(String(100), nullable=True)
    task_id = Column(String(100), nullable=True)
    plan_json = Column(Text, nullable=False)
    raw_response_json = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    request = relationship("TripPlanRequest", back_populates="versions")
