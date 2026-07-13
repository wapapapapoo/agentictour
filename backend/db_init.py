"""应用启动时自动执行 sql/ 目录下所有 SQL 文件（幂等）。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from database import engine

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def run_init_sql() -> None:
    if not SQL_DIR.is_dir():
        return

    files = sorted(SQL_DIR.glob("*.sql"))
    if not files:
        return

    with engine.connect() as conn:
        for filepath in files:
            raw = filepath.read_text(encoding="utf-8")
            statements = [s.strip() for s in raw.split(";") if s.strip()]
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                except Exception as exc:
                    print(f"[db_init] skip ({filepath.name}): {exc}")
        conn.commit()
