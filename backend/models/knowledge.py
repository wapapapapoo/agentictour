from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class PlanKnowledgeMapping(Base):
    __tablename__ = "plan_knowledge_mappings"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trip_plan_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trip_plan_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    document_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    batch: Mapped[str | None] = mapped_column(String(100), nullable=True)
    humanized_text: Mapped[str] = mapped_column(Text, nullable=False)
    indexing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="waiting"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )
