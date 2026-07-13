"""Dify Knowledge API 客户端 — 依照官方 OpenAPI 文档."""

from __future__ import annotations

import os
from typing import Any

import requests


def _base_url() -> str:
    return (
        os.getenv("DIFY_KNOWLEDGE_URL")
        or "http://host.docker.internal:3000/v1"
    ).rstrip("/")


def _api_key() -> str:
    return (
        os.getenv("DIFY_KNOWLEDGE_API_KEY")
        or ""
    ).strip()


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


def _timeout() -> float:
    return float(os.getenv("DIFY_TIMEOUT", "60"))


# ---- Documents ----

def create_document_by_text(
    *,
    dataset_id: str,
    name: str,
    text: str,
    indexing_technique: str = "high_quality",
    chunk_size: int = 4000,
    doc_form: str = "text_model",
) -> dict[str, Any]:
    url = f"{_base_url()}/datasets/{dataset_id}/document/create-by-text"
    payload: dict[str, Any] = {
        "name": name,
        "text": text,
        "indexing_technique": indexing_technique,
        "doc_form": doc_form,
        "process_rule": {
            "mode": "automatic",
        },
    }
    resp = requests.post(url, headers=_headers(), json=payload, timeout=_timeout())
    if resp.status_code >= 400:
        raise requests.HTTPError(
            f"{resp.status_code} {resp.reason}: {resp.text[:500]}",
            response=resp,
        )
    return resp.json()


def get_indexing_status(
    dataset_id: str,
    batch: str,
) -> dict[str, Any]:
    url = f"{_base_url()}/datasets/{dataset_id}/documents/{batch}/indexing-status"
    resp = requests.get(url, headers=_headers(), timeout=_timeout())
    resp.raise_for_status()
    return resp.json()


# ---- Metadata ----

def create_metadata_field(
    *,
    dataset_id: str,
    name: str,
    field_type: str,  # "string" | "number" | "time"
) -> dict[str, Any]:
    url = f"{_base_url()}/datasets/{dataset_id}/metadata"
    resp = requests.post(
        url,
        headers=_headers(),
        json={"name": name, "type": field_type},
        timeout=_timeout(),
    )
    resp.raise_for_status()
    return resp.json()


def list_metadata_fields(dataset_id: str) -> dict[str, Any]:
    url = f"{_base_url()}/datasets/{dataset_id}/metadata"
    resp = requests.get(url, headers=_headers(), timeout=_timeout())
    resp.raise_for_status()
    return resp.json()


def update_document_metadata(
    *,
    dataset_id: str,
    operation_data: list[dict[str, Any]],
) -> dict[str, Any]:
    url = f"{_base_url()}/datasets/{dataset_id}/documents/metadata"
    resp = requests.post(
        url,
        headers=_headers(),
        json={"operation_data": operation_data},
        timeout=_timeout(),
    )
    resp.raise_for_status()
    return resp.json()
