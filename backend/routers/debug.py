"""Debug routes — only when DEBUG=true."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services import preference_service
from routers.operation_log import LOG_DIR

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

router = APIRouter(prefix="/debug", tags=["Debug"])


def _scan_log_users(date_str: str) -> tuple[list[int], list[str]]:
    """扫描日志目录，返回 (user_ids, all_txt_files)."""
    if not LOG_DIR.exists():
        return [], []
    user_ids: set[int] = set()
    all_files: list[str] = []
    for path in sorted(LOG_DIR.iterdir()):
        if not path.is_file():
            continue
        name = path.name
        if not name.endswith(".txt"):
            continue
        all_files.append(name)
        stem = name[:-4]
        parts = stem.rsplit("_", 3)
        if len(parts) < 4:
            continue
        file_date = "-".join(parts[1:4])
        if file_date == date_str:
            try:
                user_ids.add(int(parts[0]))
            except ValueError:
                continue
    return sorted(user_ids), all_files


@router.get("/analyze-preferences")
def analyze_preferences(
    db: Session = Depends(get_db),
    date: str | None = Query(default=None, description="日期 yyyy-mm-dd，默认今天"),
    user_id: int | None = Query(default=None, description="指定用户 ID，不传则跑全部"),
) -> Any:
    if not DEBUG:
        raise HTTPException(status_code=404)

    date_str = date or datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

    user_ids, all_files = _scan_log_users(date_str)

    if user_id is not None:
        user_ids = [user_id]

    if not user_ids:
        return {
            "message": f"no log files found for {date_str}",
            "prototypes": 0,
            "log_dir": str(LOG_DIR),
            "log_dir_exists": LOG_DIR.exists(),
            "files_in_dir": all_files,
        }

    results: list[dict] = []
    for uid in user_ids:
        result = preference_service.analyze_user_preferences_for_date(db, uid, date_str)
        result["user_id"] = uid
        results.append(result)

    return {
        "date": date_str,
        "users_scanned": len(results),
        "total_prototypes": sum(r.get("prototypes", 0) for r in results),
        "results": results,
    }
