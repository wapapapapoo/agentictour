"""Dify Knowledge API 客户端."""

from __future__ import annotations

import os
from typing import Any

from utils.dify_client import DifyClient


def _base_url() -> str:
    return (
        os.getenv("DIFY_KNOWLEDGE_URL")
        or "http://host.docker.internal:3000/v1"
    ).rstrip("/")


def _api_key() -> str:
    return (
        os.getenv("DIFY_KNOWLEDGE_API_KEY")
        or os.getenv("DIFY_HUMANIZE_API_KEY")
        or os.getenv("DIFY_TRIP_PLAN_API_KEY")
        or os.getenv("DIFY_API_KEY")
        or ""
    ).strip()


def create_document_by_text(
    *,
    dataset_id: str,
    name: str,
    text: str,
    indexing_technique: str = "high_quality",
) -> dict[str, Any]:
    url = f"{_base_url()}/datasets/{dataset_id}/documents"
    client = DifyClient(api_key=_api_key(), url=url)
    return client.post_json({
        "name": name,
        "text": text,
        "indexing_technique": indexing_technique,
    })


def get_indexing_status(
    dataset_id: str,
    batch: str,
) -> dict[str, Any]:
    url = f"{_base_url()}/datasets/{dataset_id}/documents/{batch}/indexing-status"
    client = DifyClient(api_key=_api_key(), url=url)
    return client.post_json({})
