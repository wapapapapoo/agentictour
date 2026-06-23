"""DeepSeek LLM client for AgenticTour.

Uses OpenAI-compatible API to call DeepSeek.
API key is read from DS_API env var.
"""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DS_API = os.getenv("DS_API", "")
_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not DS_API:
            raise RuntimeError(
                "DS_API not set in .env"
            )
        _client = OpenAI(api_key=DS_API, base_url="https://api.deepseek.com")
    return _client


def chat(
    system: str,
    user: str,
    *,
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: dict[str, str] | None = None,
) -> str:
    """Single-turn chat with DeepSeek. Returns the model's text response."""
    client = get_client()
    kwargs: dict[str, Any] = dict(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    # Only pass response_format if the model supports it
    # deepseek-chat supports {"type": "json_object"}
    if response_format:
        kwargs["response_format"] = response_format

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat_json(
    system: str,
    user: str,
    *,
    model: str = "deepseek-chat",
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> Any:
    """Chat with DeepSeek and parse response as JSON."""
    text = chat(
        system=system,
        user=user,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        # Remove ```json ... ``` wrapper
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)
