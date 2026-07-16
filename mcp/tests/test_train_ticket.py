import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from travel_mcp.tools import train_ticket


class FakeClient:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def call_tool(
        self, name: str, arguments: dict[str, Any], **_kwargs: Any
    ) -> Any:
        self.__class__.calls.append((name, arguments))
        return SimpleNamespace(
            content=[SimpleNamespace(text="G123 09:30-12:10")],
            is_error=False,
        )


def test_train_ticket_query_proxies_joooook_12306_mcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeClient.calls = []
    monkeypatch.setattr(train_ticket, "_train_client", FakeClient())

    result = asyncio.run(
        train_ticket.train_ticket_query(
            date="2026-07-17",
            from_station="天津",
            to_station="沈阳",
            train_filter_flags="G",
            earliest_start_time=8,
            latest_start_time=12,
        )
    )

    assert result["ok"] is True
    assert result["tickets"] == "G123 09:30-12:10"
    assert FakeClient.calls[0][0] == "get-tickets"
    assert FakeClient.calls[0][1]["fromStation"] == "天津"
    assert FakeClient.calls[0][1]["toStation"] == "沈阳"


def test_travel_mcp_exposes_train_ticket_on_main_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AMAP_KEY", "test-key")

    from travel_mcp.server import mcp

    tool_names = {tool.name for tool in asyncio.run(mcp.list_tools())}

    assert "train_ticket_query" in tool_names
