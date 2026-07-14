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
        if "点赞" in line and "取消点赞" not in line:
            liked_lines.append(line.strip())
            m = re.search(r"plan_id:(\d+)", line)
            if m:
                plan_ids.add(int(m.group(1)))
        elif "取消点赞" in line:
            liked_lines.append(line.strip())
            m = re.search(r"plan_id:(\d+)", line)
            if m:
                # 取消点赞从集合中移除
                plan_ids.discard(int(m.group(1)))
    return list(plan_ids), liked_lines


def _decode_embedding(raw: bytes) -> list[float]:
    """Dify 用 pickle.dumps(list) 存 bytea."""
    import pickle
    arr = pickle.loads(raw)
    if isinstance(arr, np.ndarray):
        return arr.astype(np.float32).flatten().tolist()
    if isinstance(arr, list):
        return [float(v) for v in arr]
    raise ValueError(f"unexpected type: {type(arr)}")


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
                    seg_info["raw_len"] = len(emb_bytes)
                    try:
                        floats = _decode_embedding(emb_bytes)
                        vectors.append(floats)
                        seg_info["vector_dim"] = len(floats)
                        seg_info["vector_preview"] = floats[:5]
                    except Exception as e:
                        seg_info["decode_error"] = str(e)
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
        count = int((labels == cid).sum())
        db.add(UserPreferencePrototype(
            user_id=user_id,
            vector=json.dumps(centroid, ensure_ascii=False),
            chunk_count=count,
        ))
    db.commit()

    debug["message"] = f"ok: k={best_k}, {n} vectors, {len(doc_ids)} docs, {best_k} prototypes saved"
    debug["prototypes"] = best_k
    return debug


def recommend_by_prototypes(db: Session, user_id: int, top_k: int, page: int, page_size: int) -> dict:
    import random

    prototypes = (
        db.query(UserPreferencePrototype)
        .filter(UserPreferencePrototype.user_id == user_id)
        .order_by(UserPreferencePrototype.chunk_count.desc())
        .limit(5)
        .all()
    )
    if not prototypes:
        return {"results": []}

    centroids = np.array([json.loads(p.vector) for p in prototypes])

    import psycopg2
    import pickle
    conn = psycopg2.connect(DIFY_DB)
    raw = []  # (content, doc_id, score)
    offset = page * page_size
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ds.content, ds.document_id, e.embedding "
            "FROM document_segments ds "
            "JOIN embeddings e ON e.hash = ds.index_node_hash "
            "WHERE ds.status = 'completed' AND e.embedding IS NOT NULL "
            "ORDER BY ds.created_at DESC "
            "LIMIT %s OFFSET %s",
            (page_size, offset),
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    if not rows:
        return {"results": []}

    contents = []
    doc_ids = []
    vec_list = []
    for content, doc_id, emb_bytes in rows:
        arr = pickle.loads(bytes(emb_bytes))
        if isinstance(arr, list) and len(arr) > 0:
            contents.append(content)
            doc_ids.append(doc_id)
            vec_list.append([float(v) for v in arr])

    if not vec_list:
        return {"results": []}

    all_vecs = np.array(vec_list)
    cn = centroids / (np.linalg.norm(centroids, axis=1, keepdims=True) + 1e-10)
    an = all_vecs / (np.linalg.norm(all_vecs, axis=1, keepdims=True) + 1e-10)
    sim = cn @ an.T  # (n_centroids, n_chunks)

    # 每个簇取 top_k，收集 (content, doc_id, score)
    seen_doc_ids: set[str] = set()
    raw = []
    for i in range(len(prototypes)):
        scores = sim[i]
        top_idx = np.argsort(scores)[::-1]
        taken = 0
        for idx in top_idx:
            if taken >= top_k:
                break
            did = doc_ids[idx]
            if did in seen_doc_ids:
                continue  # 去重：同一个 doc 不跨簇重复出现
            seen_doc_ids.add(did)
            raw.append({
                "chunk_content": contents[idx],
                "score": float(scores[idx]),
                "document_id": did,
            })
            taken += 1

    if not raw:
        return {"results": []}

    # 按 (plan_id, version_id) 合并，同搜索接口
    from models.knowledge import PlanKnowledgeMapping, PlanLike
    from services.trip_plan_service import _loads_json, get_plan, get_latest_version

    # 反查 mapping
    all_doc_ids = [r["document_id"] for r in raw]
    mappings = {
        m.document_id: m
        for m in db.query(PlanKnowledgeMapping)
        .filter(PlanKnowledgeMapping.document_id.in_(all_doc_ids))
        .all()
    }

    groups: dict[tuple, dict] = {}
    for r in raw:
        m = mappings.get(r["document_id"])
        if m is None:
            continue
        key = (m.plan_id, m.version_id)
        if key in groups:
            g = groups[key]
            g["chunk_content"] += "\n---\n" + r["chunk_content"]
            g["_scores"].append(r["score"])
        else:
            title = None
            plan = get_plan(db, m.plan_id)
            if plan:
                version = get_latest_version(db, m.plan_id)
                if version and version.plan_json:
                    obj = _loads_json(version.plan_json)
                    if isinstance(obj, dict):
                        title = obj.get("title")
            groups[key] = {
                "chunk_content": r["chunk_content"],
                "score": r["score"],
                "document_id": r["document_id"],
                "plan_id": m.plan_id,
                "plan_title": title,
                "_scores": [r["score"]],
            }

    # 点赞计数 + 当前用户是否点过
    all_pids = [g["plan_id"] for g in groups.values() if g["plan_id"] is not None]
    like_counts: dict[int, int] = {}
    user_liked: set[int] = set()
    if all_pids:
        for pid, uid in db.query(PlanLike.plan_id, PlanLike.user_id).filter(PlanLike.plan_id.in_(all_pids)).all():
            like_counts[pid] = like_counts.get(pid, 0) + 1
            if uid == user_id:
                user_liked.add(pid)

    results = []
    for g in groups.values():
        scores = g.pop("_scores")
        if len(scores) > 1:
            g["score"] = math.log(sum(math.exp(s) for s in scores))
        g["like_count"] = like_counts.get(g["plan_id"], 0)
        g["is_liked"] = g["plan_id"] in user_liked
        results.append(g)

    random.shuffle(results)
    return {
        "results": results,
        "page": page,
        "has_more": len(rows) == page_size,
    }
