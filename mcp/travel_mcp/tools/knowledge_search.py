"""Dify 知识库检索工具."""

from typing import Any

import httpx

from travel_mcp.configs import settings


async def list_knowledge_bases() -> dict[str, Any]:
    """列出 Dify 中所有可用的知识库。"""
    url = f"{settings.DIFY_KNOWLEDGE_URL}/datasets"
    headers = {"Authorization": f"Bearer {settings.DIFY_KNOWLEDGE_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            resp = await client.get(
                url, headers=headers, params={"page": 1, "limit": 50}
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    bases = []
    for ds in data.get("data", []):
        bases.append({
            "id": ds.get("id"),
            "name": ds.get("name"),
            "description": ds.get("description", ""),
            "document_count": ds.get("document_count", 0),
            "embedding_model": ds.get("embedding_model"),
        })

    return {"ok": True, "knowledge_bases": bases}


async def search_knowledge(dataset_id: str, query: str) -> dict[str, Any]:
    """在指定知识库中检索。"""
    url = f"{settings.DIFY_KNOWLEDGE_URL}/datasets/{dataset_id}/retrieve"
    headers = {
        "Authorization": f"Bearer {settings.DIFY_KNOWLEDGE_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json={"query": query})
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    results = []
    for record in data.get("records", []):
        seg = record.get("segment", record)
        results.append({
            "content": seg.get("content", ""),
            "score": record.get("score", 0),
            "document_id": seg.get("document_id", ""),
            "document_name": seg.get("document", {}).get("name", ""),
        })

    return {"ok": True, "query": query, "results": results}
