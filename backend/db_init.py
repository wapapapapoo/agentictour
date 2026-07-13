"""应用启动时自动执行 sql/ 目录下所有 SQL 文件（幂等）。"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import text

from database import SessionLocal, engine

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _sql_files() -> list[Path]:
    if not SQL_DIR.is_dir():
        return []
    # 建表脚本优先，测试数据靠后
    tables: list[Path] = []
    seeds: list[Path] = []
    for p in sorted(SQL_DIR.glob("*.sql")):
        if p.name == "basic_test_data.sql":
            seeds.append(p)
        else:
            tables.append(p)
    return tables + seeds


def run_init_sql() -> None:
    files = _sql_files()
    if not files:
        return

    with engine.connect() as conn:
        for filepath in files:
            raw = filepath.read_text(encoding="utf-8")
            # 按分号拆成多条语句
            statements = [s.strip() for s in raw.split(";") if s.strip()]
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                except Exception as exc:
                    print(f"[db_init] skip ({filepath.name}): {exc}")
        conn.commit()
