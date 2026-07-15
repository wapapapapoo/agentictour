from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from routers.operation_log import write_log
from schemas.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    PlanKnowledgeRequest,
    PlanKnowledgeResponse,
    TraceKnowledgeResponse,
)
from services import knowledge_service, preference_service
from utils.dify_client import DifyError, DifyRequestError

router = APIRouter(prefix="/api/trip-plans", tags=["知识库同步"])


@router.post("/{plan_id}/knowledge", response_model=PlanKnowledgeResponse)
def sync_plan_to_knowledge(
    plan_id: int,
    data: PlanKnowledgeRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return knowledge_service.create_knowledge(db, plan_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DifyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/knowledge/trace", response_model=TraceKnowledgeResponse)
def trace_from_document_id(
    document_id: str = Query(..., min_length=1),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    result = knowledge_service.trace_by_document_id(db, document_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"no plan found for document_id={document_id}",
        )
    return result


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    data: KnowledgeSearchRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        result = knowledge_service.search_knowledge(db, data, current_user_id)
        write_log(current_user_id, "搜索", f"关键词:{data.query}")
        return result
    except DifyRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recommend/{user_id}")
def recommend_feed(
    user_id: int,
    top_k: int = Query(default=5, ge=1, le=20),
    page: int = Query(default=0, ge=0),
    page_size: int = Query(default=20, ge=10, le=200),
    db: Session = Depends(get_db),
) -> Any:
    return preference_service.recommend_by_prototypes(db, user_id, top_k, page, page_size)


@router.get("/trending")
def trending(
    db: Session = Depends(get_db),
) -> Any:
    return preference_service.trending(db)
