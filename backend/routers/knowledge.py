from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.knowledge import PlanKnowledgeRequest, PlanKnowledgeResponse
from services import knowledge_service
from utils.dify_client import DifyError

router = APIRouter(prefix="/api/trip-plans", tags=["知识库同步"])


@router.post("/{plan_id}/knowledge", response_model=PlanKnowledgeResponse)
def sync_plan_to_knowledge(
    plan_id: int,
    data: PlanKnowledgeRequest,
    db: Session = Depends(get_db),
):
    try:
        return knowledge_service.create_knowledge(db, plan_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DifyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
