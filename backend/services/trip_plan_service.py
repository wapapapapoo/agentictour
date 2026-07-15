from __future__ import annotations

import json
import logging
import os
import re
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from models.trip import Trip
from models.trip_plan import TripPlanRequest, TripPlanVersion
from models.user import User
from schemas.trip_plan import (
    TripPlanGenerateRequest,
    TripPlanReviseRequest,
)
from services.trip_service import ensure_trip_dates_available
from utils import dify_knowledge_client
from utils.dify_client import DifyClient, DifyError, DifyResponseError

DEFAULT_EMPTY_PLAN = {
    "title": "行程计划生成失败",
    "summary": "Dify 未返回可用的 plan_json。",
    "days": [],
    "budget": {},
    "warnings": ["请检查 Dify 工作流输出变量是否包含 plan_json。"],
    "route_summary": {},
}


def _get_username(db: Session, user_id: int) -> str:
    user = db.query(User).filter(User.user_id == user_id).first()
    return user.username if user else str(user_id)


def _get_or_create_trip(
    db: Session, data: TripPlanGenerateRequest, user_id: int
) -> int:
    if data.trip_id > 0 and db.get(Trip, data.trip_id) is not None:
        return data.trip_id
    try:
        start_date = date.fromisoformat(data.start_date)
        end_date = date.fromisoformat(data.end_date)
    except ValueError as exc:
        raise ValueError("trip plan dates must use YYYY-MM-DD format") from exc
    ensure_trip_dates_available(
        db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
    trip = Trip(
        user_id=user_id,
        title=f"{data.destination_city} {data.start_date} ~ {data.end_date}",
        origin_city=data.origin_city,
        destination_city=data.destination_city,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(trip)
    db.flush()
    return trip.id


def create_plan(
    db: Session, data: TripPlanGenerateRequest, user_id: int
) -> TripPlanRequest:
    trip_id = _get_or_create_trip(db, data, user_id)
    existing = (
        db.query(TripPlanRequest)
        .filter(TripPlanRequest.trip_id == trip_id)
        .first()
    )
    if existing is not None:
        raise ValueError("trip already has a plan request")

    request = TripPlanRequest(
        trip_id=trip_id,
        user_id=user_id,
        action="create",
        origin_city=data.origin_city,
        destination_city=data.destination_city,
        start_date=data.start_date,
        end_date=data.end_date,
        people_count=data.people_count,
        budget_total=data.budget_total,
        interests=data.interests,
        hotel_level=data.hotel_level,
        transport_preference=data.transport_preference,
        pace=data.pace,
        special_requirements=data.special_requirements,
    )
    db.add(request)
    db.flush()

    username = _get_username(db, user_id)
    response = _run_trip_plan_workflow(data, username)
    version = _build_version(
        request_id=request.id,
        user_id=user_id,
        version_no=1,
        revision_request=data.revision_request,
        workflow_response=response,
    )
    db.add(version)
    db.commit()
    db.refresh(request)
    return request


def revise_plan(
    db: Session,
    plan_id: int,
    data: TripPlanReviseRequest,
    user_id: int,
) -> TripPlanRequest:
    request = get_plan(db, plan_id)
    if request is None:
        raise LookupError("trip plan not found")

    latest_version = get_latest_version(db, plan_id)
    if latest_version is None:
        raise LookupError("trip plan version not found")

    generate_request = TripPlanGenerateRequest(
        trip_id=request.trip_id,
        action="revise",
        origin_city=request.origin_city,
        destination_city=request.destination_city,
        start_date=request.start_date,
        end_date=request.end_date,
        people_count=request.people_count,
        budget_total=request.budget_total,
        interests=request.interests,
        hotel_level=request.hotel_level,
        transport_preference=request.transport_preference,
        pace=request.pace,
        special_requirements=request.special_requirements or "",
        previous_plan_json=latest_version.plan_json,
        revision_request=data.revision_request,
    )

    response = _run_trip_plan_workflow(
        generate_request, _get_username(db, user_id)
    )
    next_version_no = latest_version.version_no + 1
    version = _build_version(
        request_id=request.id,
        user_id=user_id,
        version_no=next_version_no,
        revision_request=data.revision_request,
        workflow_response=response,
    )
    db.add(version)
    db.commit()
    db.refresh(request)
    return request


def get_plan(db: Session, plan_id: int) -> TripPlanRequest | None:
    return db.query(TripPlanRequest).filter(TripPlanRequest.id == plan_id).first()


def get_latest_version(db: Session, plan_id: int) -> TripPlanVersion | None:
    return (
        db.query(TripPlanVersion)
        .filter(TripPlanVersion.request_id == plan_id)
        .order_by(TripPlanVersion.version_no.desc())
        .first()
    )


def list_plans(db: Session, user_id: int | None = None) -> list[dict[str, Any]]:
    query = db.query(TripPlanRequest).order_by(TripPlanRequest.created_at.desc())
    if user_id:
        query = query.filter(TripPlanRequest.user_id == user_id)

    items: list[dict[str, Any]] = []
    for request in query.all():
        latest_version = get_latest_version(db, request.id)
        plan_json = _loads_json(latest_version.plan_json) if latest_version else {}
        title = plan_json.get("title") if isinstance(plan_json, dict) else None
        items.append(
            {
                "id": request.id,
                "trip_id": request.trip_id,
                "user_id": request.user_id,
                "origin_city": request.origin_city,
                "destination_city": request.destination_city,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "version_no": latest_version.version_no if latest_version else None,
                "title": title,
                "created_at": request.created_at,
                "updated_at": request.updated_at,
            }
        )
    return items


def humanize_plan(
    db: Session,
    plan_id: int,
    user_id: int,
) -> dict[str, Any]:
    request = get_plan(db, plan_id)
    if request is None:
        raise LookupError("trip plan not found")

    latest_version = get_latest_version(db, plan_id)
    if latest_version is None or not latest_version.plan_json:
        raise LookupError("trip plan version not found or plan_json is empty")

    plan_json = latest_version.plan_json

    original_prompt = (
        f"出发地：{request.origin_city}\n"
        f"目的地：{request.destination_city}\n"
        f"出发日期：{request.start_date}\n"
        f"结束日期：{request.end_date}\n"
        f"人数：{request.people_count}\n"
        f"预算：{request.budget_total}\n"
        f"兴趣：{request.interests}\n"
        f"住宿标准：{request.hotel_level}\n"
        f"交通偏好：{request.transport_preference}\n"
        f"旅游节奏：{request.pace}"
    )
    if request.special_requirements:
        original_prompt += f"\n特殊要求：{request.special_requirements}"

    client = DifyClient(
        api_key=os.getenv("DIFY_HUMANIZE_API_KEY") or os.getenv("DIFY_API_KEY"),
        url=os.getenv("DIFY_HUMANIZE_URL") or os.getenv("DIFY_URL"),
        timeout=float(os.getenv("DIFY_TIMEOUT", "600")),
    )
    try:
        response = client.run_workflow(
            user=_get_username(db, user_id),
            inputs={
                "input_json": plan_json,
                "original_user_prompt": original_prompt,
            },
        )
    except DifyError:
        raise

    outputs = response.get("data", {}).get("outputs", {})
    natural_language = (
        outputs.get("reply")
        or outputs.get("text")
        or outputs.get("result")
        or ""
    )
    if isinstance(natural_language, dict):
        natural_language = json.dumps(natural_language, ensure_ascii=False)

    plan_obj = _loads_json(plan_json)
    title = plan_obj.get("title") if isinstance(plan_obj, dict) else None

    return {
        "plan_id": plan_id,
        "title": title,
        "natural_language": natural_language,
    }


def delete_plan(db: Session, plan_id: int) -> bool:
    request = get_plan(db, plan_id)
    if request is None:
        return False

    # 先删 Dify 知识库文档
    from models.knowledge import PlanKnowledgeMapping
    logger = logging.getLogger(__name__)
    mappings = (
        db.query(PlanKnowledgeMapping)
        .filter(PlanKnowledgeMapping.plan_id == plan_id)
        .all()
    )
    for m in mappings:
        if m.document_id and m.dataset_id:
            try:
                dify_knowledge_client.delete_document(
                    dataset_id=m.dataset_id,
                    document_id=m.document_id,
                )
            except Exception as e:
                logger.warning(
                    "failed to delete dify document %s: %s", m.document_id, e
                )

    db.delete(request)
    db.commit()
    return True


def to_response(request: TripPlanRequest) -> dict[str, Any]:
    latest_version = max(
        request.versions,
        key=lambda version: version.version_no,
        default=None,
    )
    return {
        "id": request.id,
        "trip_id": request.trip_id,
        "user_id": request.user_id,
        "action": request.action,
        "origin_city": request.origin_city,
        "destination_city": request.destination_city,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "people_count": request.people_count,
        "budget_total": request.budget_total,
        "interests": request.interests,
        "hotel_level": request.hotel_level,
        "transport_preference": request.transport_preference,
        "pace": request.pace,
        "special_requirements": request.special_requirements,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
        "latest_version": _version_to_response(latest_version)
        if latest_version is not None
        else None,
    }


def _run_trip_plan_workflow(
    data: TripPlanGenerateRequest, username: str
) -> dict[str, Any]:
    client = DifyClient(
        api_key=os.getenv("DIFY_TRIP_PLAN_API_KEY") or os.getenv("DIFY_API_KEY"),
        url=os.getenv("DIFY_TRIP_PLAN_URL") or os.getenv("DIFY_URL"),
        timeout=float(os.getenv("DIFY_TIMEOUT", "600")),
    )
    try:
        return client.run_workflow(
            user=username,
            inputs=_to_dify_inputs(data, username),
        )
    except DifyError:
        raise


def _to_dify_inputs(data: TripPlanGenerateRequest, username: str) -> dict[str, str]:
    return {
        "action": data.action,
        "user_id": username,
        "origin_city": data.origin_city,
        "destination_city": data.destination_city,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "people_count": data.people_count,
        "budget_total": data.budget_total,
        "interests": data.interests,
        "hotel_level": data.hotel_level,
        "transport_preference": data.transport_preference,
        "pace": data.pace,
        "special_requirements": data.special_requirements,
        "previous_plan_json": data.previous_plan_json,
        "revision_request": data.revision_request,
    }


def _build_version(
    *,
    request_id: int,
    user_id: int,
    version_no: int,
    revision_request: str,
    workflow_response: dict[str, Any],
) -> TripPlanVersion:
    plan_json = _extract_plan_json(workflow_response)
    return TripPlanVersion(
        request_id=request_id,
        user_id=user_id,
        version_no=version_no,
        revision_request=revision_request,
        workflow_run_id=workflow_response.get("workflow_run_id")
        or workflow_response.get("workflow_run_id".replace("_", "-")),
        task_id=workflow_response.get("task_id"),
        plan_json=json.dumps(plan_json, ensure_ascii=False),
        raw_response_json=json.dumps(workflow_response, ensure_ascii=False),
    )


def _extract_plan_json(workflow_response: dict[str, Any]) -> Any:
    outputs = workflow_response.get("data", {}).get("outputs", {})
    if not isinstance(outputs, dict):
        raise DifyResponseError("Dify workflow outputs must be an object.")

    value = (
        outputs.get("plan_json")
        or outputs.get("result")
        or outputs.get("answer")
        or DEFAULT_EMPTY_PLAN
    )
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return DEFAULT_EMPTY_PLAN
        return _loads_json(stripped)

    return value


def _loads_json(value: str) -> Any:
    stripped = value.strip()
    # 去掉 think 标签
    stripped = re.sub(r"</?think>", "", stripped, flags=re.IGNORECASE).strip()
    # 如果文本中嵌有 JSON，提取从第一个 { 到最后一个 }
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        stripped = match.group(0)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {
            "title": "行程计划",
            "summary": value,
            "days": [],
            "budget": {},
            "warnings": ["Dify 返回了文本内容，后端已包装为基础 JSON。"],
            "route_summary": {},
        }


def _version_to_response(version: TripPlanVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "request_id": version.request_id,
        "user_id": version.user_id,
        "version_no": version.version_no,
        "revision_request": version.revision_request,
        "workflow_run_id": version.workflow_run_id,
        "task_id": version.task_id,
        "plan_json": _loads_json(version.plan_json),
        "created_at": version.created_at,
    }
