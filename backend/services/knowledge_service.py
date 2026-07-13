"""将人话行程上传至 Dify 知识库，并通过元数据记录来源."""

from __future__ import annotations

import re
from typing import Any

import requests
from sqlalchemy.orm import Session

from models.knowledge import PlanKnowledgeMapping
from models.trip_plan import TripPlanRequest
from schemas.knowledge import PlanKnowledgeRequest
from schemas.trip_plan import PlanHumanizeRequest
from services.trip_plan_service import (
    _loads_json,
    get_latest_version,
    get_plan,
    humanize_plan,
)
import os

from utils import dify_knowledge_client as kb_client
from utils.dify_client import DifyError, DifyRequestError


def _dataset_id(requested: str) -> str:
    return requested or os.getenv("DIFY_KNOWLEDGE_DATASET_ID", "").strip()

_METADATA_PLAN_ID = "plan_id"
_METADATA_VERSION_ID = "version_id"


def _ensure_metadata_fields(dataset_id: str) -> dict[str, str]:
    """确保知识库中存在 plan_id / version_id 两个元数据字段，返回 {name: id}."""
    try:
        existing = kb_client.list_metadata_fields(dataset_id)
    except requests.RequestException as exc:
        raise DifyRequestError(f"list metadata fields failed: {exc}") from exc

    field_map: dict[str, str] = {}
    for f in existing.get("doc_metadata", []):
        field_map[f["name"]] = f["id"]

    for field_name in (_METADATA_PLAN_ID, _METADATA_VERSION_ID):
        if field_name not in field_map:
            try:
                created = kb_client.create_metadata_field(
                    dataset_id=dataset_id,
                    name=field_name,
                    field_type="string",
                )
            except requests.RequestException as exc:
                raise DifyRequestError(
                    f"create metadata field '{field_name}' failed: {exc}"
                ) from exc
            field_map[field_name] = created["id"]

    return field_map


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

    # 去重
    existing = (
        db.query(PlanKnowledgeMapping)
        .filter(
            PlanKnowledgeMapping.plan_id == plan_id,
            PlanKnowledgeMapping.version_id == version.id,
        )
        .first()
    )
    if existing is not None:
        return _mapping_to_response(existing)

    # 确保知识库有元数据字段
    ds_id = _dataset_id(ds_id)
    if not ds_id:
        raise RuntimeError("dataset_id 未配置，请设置 DIFY_KNOWLEDGE_DATASET_ID 环境变量或传入 dataset_id")
    field_map = _ensure_metadata_fields(ds_id)

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

    # 2) 上传文档
    doc_name = _pick_doc_name(title, plan)
    try:
        result = kb_client.create_document_by_text(
            dataset_id=ds_id,
            name=doc_name,
            text=humanized_text,
            chunk_size=data.chunk_size,
        )
    except requests.RequestException as exc:
        raise DifyRequestError(f"create document failed: {exc}") from exc

    doc_id = result["document"]["id"]
    batch = result.get("batch")

    # 3) 写入元数据：来源计划的 plan_id / version_id
    try:
        kb_client.update_document_metadata(
            dataset_id=ds_id,
            operation_data=[{
                "document_id": doc_id,
                "metadata_list": [
                    {"id": field_map[_METADATA_PLAN_ID], "name": _METADATA_PLAN_ID, "value": str(plan_id)},
                    {"id": field_map[_METADATA_VERSION_ID], "name": _METADATA_VERSION_ID, "value": str(version.id)},
                ],
            }],
        )
    except requests.RequestException as exc:
        raise DifyRequestError(f"set document metadata failed: {exc}") from exc

    # 4) 存本地映射
    mapping = PlanKnowledgeMapping(
        plan_id=plan.id,
        version_id=version.id,
        user_id=data.user_id,
        dataset_id=ds_id,
        document_id=doc_id,
        document_name=doc_name,
        batch=batch,
        humanized_text=humanized_text,
        indexing_status="waiting",
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return _mapping_to_response(mapping)


def _mapping_to_response(mapping: PlanKnowledgeMapping) -> dict[str, Any]:
    return {
        "plan_id": mapping.plan_id,
        "version_id": mapping.version_id,
        "humanized_text": mapping.humanized_text,
        "dataset_id": mapping.dataset_id,
        "document_name": mapping.document_name,
        "document_id": mapping.document_id,
        "batch": mapping.batch,
        "indexing_status": mapping.indexing_status,
        "created_at": mapping.created_at,
    }


def trace_by_document_id(
    db: Session,
    document_id: str,
) -> dict[str, Any] | None:
    mapping = (
        db.query(PlanKnowledgeMapping)
        .filter(PlanKnowledgeMapping.document_id == document_id)
        .first()
    )
    if mapping is None:
        return None

    plan = get_plan(db, mapping.plan_id)
    if plan is None:
        return None

    version = get_latest_version(db, mapping.plan_id)
    plan_obj = _loads_json(version.plan_json) if version and version.plan_json else {}
    title = plan_obj.get("title") if isinstance(plan_obj, dict) else None

    return {
        "plan_id": plan.id,
        "version_id": mapping.version_id,
        "title": title,
        "origin_city": plan.origin_city,
        "destination_city": plan.destination_city,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "document_id": mapping.document_id or "",
        "document_name": mapping.document_name,
        "indexing_status": mapping.indexing_status,
        "created_at": mapping.created_at,
    }


def search_knowledge(
    db: Session,
    data: Any,  # KnowledgeSearchRequest
) -> dict[str, Any]:
    ds_id = _dataset_id(data.dataset_id)
    if not ds_id:
        raise RuntimeError("dataset_id 未配置")
    try:
        resp = kb_client.retrieve_chunks(
            dataset_id=ds_id,
            query=data.query,
        )
    except requests.RequestException as exc:
        raise DifyRequestError(f"retrieve failed: {exc}") from exc

    results: list[dict[str, Any]] = []
    for record in resp.get("records", []):
        segment = record.get("segment", record)
        doc_id = segment.get("document_id", "")
        chunk = segment.get("content", "")

        # 查映射
        mapping = (
            db.query(PlanKnowledgeMapping)
            .filter(PlanKnowledgeMapping.document_id == doc_id)
            .first()
        )

        plan_id = mapping.plan_id if mapping else None
        title = None
        if plan_id:
            plan = get_plan(db, plan_id)
            if plan:
                version = get_latest_version(db, plan_id)
                if version and version.plan_json:
                    obj = _loads_json(version.plan_json)
                    if isinstance(obj, dict):
                        title = obj.get("title")

        results.append({
            "chunk_content": chunk,
            "score": record.get("score", 0.0),
            "document_id": doc_id,
            "plan_id": plan_id,
            "plan_title": title,
        })

    return {"results": results}


def _pick_doc_name(title: str | None, plan: TripPlanRequest) -> str:
    base = (title or "行程").strip()
    safe = re.sub(r"[\\/:*?\"<>|]", "_", base)
    return f"{safe} - {plan.destination_city} {plan.start_date}"
