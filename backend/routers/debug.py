"""Debug routes — only when DEBUG=true."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
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
