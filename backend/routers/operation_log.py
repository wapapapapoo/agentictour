from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(os.getenv("OPERATION_LOG_DIR", "/app/logs"))


def write_log(user_id: int, category: str, content: str) -> None:
    now = datetime.now(timezone.utc).astimezone()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")

    safe_content = content[:1024]
    line = f"[{timestamp}] {category} | {safe_content}\n"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}_{date_str}.txt"
    filepath = LOG_DIR / filename

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line)
