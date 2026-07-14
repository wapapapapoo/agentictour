"""用户偏好分析：解析点赞日志，从 Dify pgvector 查向量，聚类存原型."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
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


def _parse_liked_plan_ids(log_path: str) -> tuple[list[int], list[str]]:
    """返回 (plan_ids, raw_lines) 方便调试."""
    try:
        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return [], []
    plan_ids: set[int] = set()
    liked_lines: list[str] = []
    for line in lines:
        if "点赞" in line:
            liked_lines.append(line.strip())
            m = re.search(r"plan_id:(\d+)", line)
            if m:
                plan_ids.add(int(m.group(1)))
    return list(plan_ids), liked_lines


def _decode_embedding(raw: bytes) -> list[float] | None:
    """尝试多种偏移/格式解码，返回第一个无 NaN 的结果."""
    candidates: list[tuple[int, str, list[float]]] = []
    total = len(raw)

    # 试不同偏移 skip 0,2,4,6,8,10,12
    for skip in [0, 2, 4, 6, 8, 10, 12]:
        body = raw[skip:]
        if len(body) % 4 == 0 and len(body) > 0:
            arr = np.frombuffer(body, dtype=np.float32)
            candidates.append((skip, "f32", arr.tolist()))
    # 试 float16 (skip 0)
    if total % 2 == 0:
        arr = np.frombuffer(raw, dtype=np.float16).astype(np.float32)
        candidates.append((0, "f16", arr.tolist()))

    for skip, fmt, vals in candidates:
        if vals and not any(math.isnan(v) for v in vals):
            return vals
    # 都没完美结果，返回第一个有效的（可能含 NaN）
    for skip, fmt, vals in candidates:
        if vals:
            return vals
    return None


def analyze_user_preferences(db: Session, user_id: int) -> dict:
    debug: dict = {"steps": []}

    # Step 1: 读日志
    log_path = _today_log_path(user_id)
    plan_ids, liked_lines = _parse_liked_plan_ids(log_path)
    debug["steps"].append({
        "step": 1, "action": "read_log",
        "log_path": log_path,
        "log_exists": bool(liked_lines) or os.path.exists(log_path),
        "liked_lines": liked_lines,
        "plan_ids": plan_ids,
    })
    if not plan_ids:
        debug["message"] = "no likes today"
        debug["prototypes"] = 0
        return debug

    # Step 2: 查 document_id
    mappings = (
        db.query(PlanKnowledgeMapping.document_id, PlanKnowledgeMapping.plan_id)
        .filter(
            PlanKnowledgeMapping.plan_id.in_(plan_ids),
            PlanKnowledgeMapping.document_id.isnot(None),
        )
        .all()
    )
    doc_ids = [m.document_id for m in mappings if m.document_id]
    plan_doc_map = {m.plan_id: m.document_id for m in mappings if m.document_id}
    debug["steps"].append({
        "step": 2, "action": "lookup_docs",
        "mapping_count": len(mappings),
        "doc_ids": doc_ids,
        "plan_doc_map": {str(k): v for k, v in plan_doc_map.items()},
    })
    if not doc_ids:
        debug["message"] = "no linked dify documents found in plan_knowledge_mappings"
        debug["prototypes"] = 0
        return debug

    # Step 3: 从 Dify pgvector 查向量
    import psycopg2
    try:
        conn = psycopg2.connect(DIFY_DB)
    except Exception as e:
        debug["message"] = f"cannot connect to Dify PostgreSQL: {e}"
        debug["prototypes"] = 0
        return debug

    vectors: list[list[float]] = []
    segment_details: list[dict] = []
    hash_hits: dict[str, int] = {"index_node_hash": 0, "sha256": 0, "miss": 0}
    try:
        cur = conn.cursor()
        for doc_id in doc_ids:
            cur.execute(
                "SELECT id, content, index_node_hash, position FROM document_segments "
                "WHERE document_id = %s ORDER BY position",
                (doc_id,),
            )
            segs = cur.fetchall()
            for seg_id, content, node_hash, pos in segs:
                emb_bytes = None
                source = "miss"
                # 先试 index_node_hash
                if node_hash:
                    cur.execute("SELECT embedding FROM embeddings WHERE hash = %s", (node_hash,))
                    row = cur.fetchone()
                    if row:
                        emb_bytes = bytes(row[0])
                        source = "index_node_hash"
                # fallback: sha256(content)
                if emb_bytes is None:
                    ch = hashlib.sha256(content.encode()).hexdigest()
                    cur.execute("SELECT embedding FROM embeddings WHERE hash = %s", (ch,))
                    row = cur.fetchone()
                    if row:
                        emb_bytes = bytes(row[0])
                        source = "sha256"
                hash_hits[source] += 1

                seg_info = {
                    "seg_id": str(seg_id),
                    "doc_id": str(doc_id),
                    "position": pos,
                    "content_len": len(content),
                    "content_preview": content[:80],
                    "node_hash": node_hash,
                    "hash_source": source,
                }
                if emb_bytes is not None:
                    floats = _decode_embedding(emb_bytes)
                    if floats is not None:
                        vectors.append(floats)
                        seg_info["vector_dim"] = len(floats)
                        seg_info["vector_preview"] = floats[:5]
                    else:
                        seg_info["decode_error"] = f"raw_len={len(emb_bytes)}"
                segment_details.append(seg_info)
        cur.close()
    finally:
        conn.close()

    debug["steps"].append({
        "step": 3, "action": "fetch_vectors",
        "segments_total": len(segment_details),
        "vectors_found": len(vectors),
        "hash_hits": hash_hits,
        "segment_details": segment_details,
    })
    if len(vectors) < 2:
        debug["message"] = f"need >=2 vectors for clustering, got {len(vectors)}"
        debug["prototypes"] = 0
        return debug

    # Step 4: K-means 聚类
    arr = np.array(vectors)
    n = arr.shape[0]
    mx = min(10, n)
    inertias = []
    for k in range(1, mx + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(arr)
        inertias.append(float(km.inertia_))

    if len(inertias) < 3:
        best_k = 2 if len(inertias) >= 2 and inertias[1] < inertias[0] * 0.6 else 1
    else:
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
        best_k = max(2, min(best_k, mx))

    km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = km.fit_predict(arr)
    cluster_counts = [int((labels == c).sum()) for c in range(best_k)]

    debug["steps"].append({
        "step": 4, "action": "cluster",
        "vector_count": n,
        "vector_dim": int(arr.shape[1]),
        "inertias": inertias,
        "best_k": best_k,
        "cluster_sizes": cluster_counts,
        "centroids_preview": [[float(v) for v in km.cluster_centers_[c][:5]] for c in range(best_k)],
    })

    # Step 5: 存原型
    db.query(UserPreferencePrototype).filter(
        UserPreferencePrototype.user_id == user_id
    ).delete()
    for cid in range(best_k):
        centroid = [float(v) for v in km.cluster_centers_[cid]]
        db.add(UserPreferencePrototype(
            user_id=user_id,
            vector=json.dumps(centroid, ensure_ascii=False),
        ))
    db.commit()

    debug["message"] = f"ok: k={best_k}, {n} vectors, {len(doc_ids)} docs, {best_k} prototypes saved"
    debug["prototypes"] = best_k
    return debug
