"""将人话行程上传至 Dify 知识库."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from models.knowledge import PlanKnowledgeMapping
from models.trip_plan import TripPlanRequest
from schemas.knowledge import PlanKnowledgeRequest
from services.trip_plan_service import (
    _loads_json,
    get_latest_version,
    get_plan,
    humanize_plan,
)
from schemas.trip_plan import PlanHumanizeRequest
from utils import dify_knowledge_client as kb_client


def create_knowledge(
    db: Session,
    plan_id: int,
    data: PlanKnowledgeRequest,
) -> dict[str, Any]:
    plan = get_plan(db, plan_id)
    if plan is None:
        raise LookupError("trip plan not found")

    version = get_latest_version(db, plan_id)
    if version is None or not version.plan_json:
        raise LookupError("trip plan version empty")

    # 去重：同一 plan_id + version_id 只上传一次
    existing = (
        db.query(PlanKnowledgeMapping)
        .filter(
            PlanKnowledgeMapping.plan_id == plan_id,
            PlanKnowledgeMapping.version_id == version.id,
        )
        .first()
    )
    if existing is not None:
        return {
            "plan_id": plan.id,
            "version_id": version.id,
            "humanized_text": existing.humanized_text,
            "dataset_id": existing.dataset_id,
            "document_name": existing.document_name,
            "document_id": existing.document_id,
            "batch": existing.batch,
            "indexing_status": existing.indexing_status,
            "created_at": existing.created_at,
        }

    plan_obj = _loads_json(version.plan_json)
    title = (
        plan_obj.get("title")
        if isinstance(plan_obj, dict)
        else "行程计划"
    )

    # 1) 生成人话
    humanized = humanize_plan(
        db=db,
        plan_id=plan_id,
        data=PlanHumanizeRequest(user_id=data.user_id),
    )

    humanized_text = humanized["natural_language"]
    if not humanized_text:
        raise RuntimeError("说人话工作流返回了空内容")

    # 2) 上传到 Dify 知识库
    doc_name = _pick_doc_name(title, plan)
    result = kb_client.create_document_by_text(
        dataset_id=data.dataset_id,
        name=doc_name,
        text=humanized_text,
        chunk_size=data.chunk_size,
    )
    doc_id = result.get("document", {}).get("id") or result.get("id")
    batch = result.get("batch")

    # 3) 存映射
    mapping = PlanKnowledgeMapping(
        plan_id=plan.id,
        version_id=version.id,
        user_id=data.user_id,
        dataset_id=data.dataset_id,
        document_id=doc_id,
        document_name=doc_name,
        batch=batch,
        humanized_text=humanized_text,
        indexing_status="completed",
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return {
        "plan_id": plan.id,
        "version_id": version.id,
        "humanized_text": humanized_text,
        "dataset_id": data.dataset_id,
        "document_name": doc_name,
        "document_id": doc_id,
        "batch": batch,
        "indexing_status": mapping.indexing_status,
        "created_at": mapping.created_at,
    }


def _pick_doc_name(title: str | None, plan: TripPlanRequest) -> str:
    base = (title or "行程").strip()
    safe = re.sub(r"[\\/:*?\"<>|]", "_", base)
    return f"{safe} - {plan.destination_city} {plan.start_date}"
