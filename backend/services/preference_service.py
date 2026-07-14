"""用户偏好分析：解析点赞日志，从 Dify pgvector 查向量，聚类存原型."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import struct
from datetime import datetime, timezone

import numpy as np
from sklearn.cluster import KMeans

from database import Session
from models.knowledge import PlanKnowledgeMapping, UserPreferencePrototype
from routers.operation_log import LOG_DIR

DIFY_DB = os.getenv("DIFY_DB_URL", "postgresql://postgres:difyai123456@host.docker.internal:5432/dify")


def _today_log_path(user_id: int) -> str:
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    return str(LOG_DIR / f"{user_id}_{today}.txt")


def _parse_liked_plan_ids(log_path: str) -> list[int]:
    try:
        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []
    plan_ids: set[int] = set()
    for line in lines:
        if "点赞" in line:
            m = re.search(r"plan_id:(\d+)", line)
            if m:
                plan_ids.add(int(m.group(1)))
    return list(plan_ids)


def _fetch_vectors(db: Session, plan_ids: list[int]) -> list[list[float]]:
    """从 Dify pgvector: document_segments JOIN embeddings ON hash(content)."""
    import psycopg2

    mappings = (
        db.query(PlanKnowledgeMapping.document_id)
        .filter(
            PlanKnowledgeMapping.plan_id.in_(plan_ids),
            PlanKnowledgeMapping.document_id.isnot(None),
        )
        .all()
    )
    doc_ids = [m.document_id for m in mappings if m.document_id]
    if not doc_ids:
        return []

    conn = psycopg2.connect(DIFY_DB)
    vectors: list[list[float]] = []
    try:
        cur = conn.cursor()
        for doc_id in doc_ids:
            cur.execute(
                "SELECT content, index_node_hash FROM document_segments "
                "WHERE document_id = %s ORDER BY position",
                (doc_id,),
            )
            segments = cur.fetchall()
            for content, node_hash in segments:
                emb_bytes = _lookup_embedding(cur, content, node_hash)
                if emb_bytes is not None:
                    floats = struct.unpack(f"<{len(emb_bytes)//4}f", emb_bytes)
                    vectors.append(list(floats))
        cur.close()
    finally:
        conn.close()
    return vectors


def _lookup_embedding(cur, content: str, node_hash) -> bytes | None:
    # 先试 index_node_hash 匹配 embeddings.hash
    if node_hash:
        cur.execute(
            "SELECT embedding FROM embeddings WHERE hash = %s",
            (node_hash,),
        )
        row = cur.fetchone()
        if row:
            return bytes(row[0])

    # fallback: sha256(content) 匹配
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    cur.execute(
        "SELECT embedding FROM embeddings WHERE hash = %s",
        (content_hash,),
    )
    row = cur.fetchone()
    if row:
        return bytes(row[0])

    return None


def _elbow_k(vectors: np.ndarray) -> int:
    n = vectors.shape[0]
    if n < 2:
        return 1
    mx = min(10, n)
    inertias = []
    for k in range(1, mx + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(vectors)
        inertias.append(float(km.inertia_))
    if len(inertias) < 3:
        return 2 if len(inertias) >= 2 and inertias[1] < inertias[0] * 0.6 else 1
    best_k, best = 2, -1.0
    for i in range(1, len(inertias) - 1):
        x0, y0 = 1, inertias[0]
        xi, yi = i + 1, inertias[i]
        xn, yn = mx, inertias[-1]
        num = abs((xn - x0) * (yi - y0) - (xi - x0) * (yn - y0))
        den = math.sqrt((xn - x0) ** 2 + (yn - y0) ** 2)
        if den > 0 and num / den > best:
            best = num / den
            best_k = i + 1
    return max(2, min(best_k, mx))


def analyze_user_preferences(db: Session, user_id: int) -> dict:
    log_path = _today_log_path(user_id)
    plan_ids = _parse_liked_plan_ids(log_path)
    if not plan_ids:
        return {"message": "no likes today", "prototypes": 0}

    vectors_list = _fetch_vectors(db, plan_ids)
    if len(vectors_list) < 2:
        return {"message": f"need >=2 vectors, got {len(vectors_list)}", "prototypes": 0}

    vectors = np.array(vectors_list)
    k = _elbow_k(vectors)
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(vectors)

    db.query(UserPreferencePrototype).filter(
        UserPreferencePrototype.user_id == user_id
    ).delete()

    for cid in range(k):
        centroid = [float(v) for v in km.cluster_centers_[cid]]
        db.add(UserPreferencePrototype(
            user_id=user_id,
            vector=json.dumps(centroid, ensure_ascii=False),
        ))
    db.commit()
    return {"message": f"k={k}, {len(vectors_list)} vectors from {len(plan_ids)} plans", "prototypes": k}
