import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models.knowledge import PlanLike
from routers.operation_log import write_log
from schemas.operation_log import PlanLikeRequest, PlanLikeResponse
from schemas.trip_plan import (
    PlanHumanizeRequest,
    PlanHumanizeResponse,
    TripPlanGenerateRequest,
    TripPlanListItem,
    TripPlanResponse,
    TripPlanReviseRequest,
)
from services import trip_plan_service
from utils.dify_client import DifyError

router = APIRouter(prefix="/api/trip-plans", tags=["行前旅行计划制定"])


@router.post("/generate", response_model=TripPlanResponse)
def generate_trip_plan(
    data: TripPlanGenerateRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        plan = trip_plan_service.create_plan(db, data, current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DifyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    write_log(current_user_id, "生成", f"目的地:{data.destination_city} 兴趣:{data.interests}")
    return trip_plan_service.to_response(plan)


@router.post("/{plan_id}/revise", response_model=TripPlanResponse)
def revise_trip_plan(
    plan_id: int,
    data: TripPlanReviseRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        plan = trip_plan_service.revise_plan(db, plan_id, data, current_user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DifyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return trip_plan_service.to_response(plan)


@router.get("", response_model=list[TripPlanListItem])
def list_trip_plans(
    user_id: int | None = Query(default=None, gt=0),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return trip_plan_service.list_plans(db, user_id or current_user_id)


@router.get("/{plan_id}", response_model=TripPlanResponse)
def get_trip_plan(
    plan_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    plan = trip_plan_service.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="trip plan not found")
    return trip_plan_service.to_response(plan)


@router.delete("/{plan_id}")
def delete_trip_plan(
    plan_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    ok = trip_plan_service.delete_plan(db, plan_id)
    if not ok:
        raise HTTPException(status_code=404, detail="trip plan not found")
    return {"message": "删除成功"}


@router.post("/{plan_id}/humanize", response_model=PlanHumanizeResponse)
def humanize_trip_plan(
    plan_id: int,
    data: PlanHumanizeRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return trip_plan_service.humanize_plan(db, plan_id, current_user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DifyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{plan_id}/like", response_model=PlanLikeResponse)
def like_trip_plan(
    plan_id: int,
    data: PlanLikeRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    plan = trip_plan_service.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="trip plan not found")

    like = PlanLike(
        user_id=current_user_id,
        plan_id=plan_id,
        chunk_ids=json.dumps(data.chunk_ids, ensure_ascii=False),
    )
    db.add(like)
    db.commit()
    db.refresh(like)

    write_log(
        current_user_id,
        "点赞",
        f"plan_id:{plan_id} chunks:{','.join(data.chunk_ids)}",
    )

    return PlanLikeResponse(
        id=like.id,
        user_id=like.user_id,
        plan_id=like.plan_id,
        chunk_ids=data.chunk_ids,
        created_at=like.created_at.isoformat() if like.created_at else "",
    )
