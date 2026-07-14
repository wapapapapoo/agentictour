from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from database import Base


class PlanKnowledgeMapping(Base):
    __tablename__ = "plan_knowledge_mappings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    plan_id = Column(
        BigInteger,
        ForeignKey("trip_plan_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_id = Column(
        BigInteger,
        ForeignKey("trip_plan_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(String(64), nullable=False)
    dataset_id = Column(String(100), nullable=False)
    document_id = Column(String(100), nullable=True)
    document_name = Column(String(255), nullable=False)
    batch = Column(String(100), nullable=True)
    humanized_text = Column(Text, nullable=False)
    indexing_status = Column(String(50), nullable=False, default="waiting")
    created_at = Column(DateTime, server_default=func.now())
