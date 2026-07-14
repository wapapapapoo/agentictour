"""Debug routes — only when DEBUG=true."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from services import preference_service

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.post("/analyze-preferences")
def analyze_preferences(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    if not DEBUG:
        raise HTTPException(status_code=404)
    return preference_service.analyze_user_preferences(db, current_user_id)


@router.get("/recommend/{user_id}")
def recommend_by_prototypes(
    user_id: int,
    top_k: int = Query(default=5, ge=1, le=20),
    page: int = Query(default=0, ge=0),
    page_size: int = Query(default=50, ge=10, le=200),
    db: Session = Depends(get_db),
) -> Any:
    if not DEBUG:
        raise HTTPException(status_code=404)
    return preference_service.recommend_by_prototypes(db, user_id, top_k, page, page_size)
