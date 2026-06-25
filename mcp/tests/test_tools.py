import asyncio
from types import TracebackType
from typing import Any, Awaitable, ClassVar

import pytest

from travel_mcp.tools import amap_poi, amap_route, amap_weather


class FakeResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._data


class FakeAsyncClient:
    response_data: ClassVar[dict[str, Any]] = {}
    requests: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def get(self, url: str, params: dict[str, Any]) -> FakeResponse:
        self.__class__.requests.append(
            {"url": url, "params": params, "timeout": self.timeout}
        )
        return FakeResponse(self.__class__.response_data)


def run_tool(result: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    return asyncio.run(result)


def install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
    response_data: dict[str, Any],
) -> None:
    FakeAsyncClient.response_data = response_data
    FakeAsyncClient.requests = []
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(module.settings, "AMAP_KEY", "test-key")
    monkeypatch.setattr(module.settings, "HTTP_TIMEOUT", 3)


def test_amap_weather_returns_current_weather(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_client(
        monkeypatch,
        amap_weather,
        {
            "status": "1",
            "lives": [{"city": "Shanghai", "weather": "Sunny"}],
        },
    )

    result = run_tool(amap_weather.amap_weather("310000"))

    assert result["ok"] is True
    assert result["mode"] == "base"
    assert result["weather"] == {"city": "Shanghai", "weather": "Sunny"}
    request = FakeAsyncClient.requests[0]
    assert request["url"].endswith("/v3/weather/weatherInfo")
    assert request["params"]["key"] == "test-key"
    assert request["params"]["city"] == "310000"
    assert request["timeout"] == 3


def test_amap_weather_returns_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_response = {
        "status": "0",
        "info": "INVALID_USER_KEY",
        "infocode": "10001",
    }
    install_fake_client(monkeypatch, amap_weather, api_response)

    result = run_tool(amap_weather.amap_weather("310000"))

    assert result["ok"] is False
    assert result["tool"] == "amap_weather"
    assert result["info"] == "INVALID_USER_KEY"
    assert result["raw"] == api_response


def test_amap_nearby_search_simplifies_pois(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_client(
        monkeypatch,
        amap_poi,
        {
            "status": "1",
            "pois": [
                {
                    "id": "poi-1",
                    "name": "Coffee Bar",
                    "type": "Food",
                    "address": "Road 1",
                    "location": "121.1,31.2",
                    "distance": "120",
                    "tel": "123",
                    "business_area": "Center",
                    "cityname": "Shanghai",
                    "adname": "Pudong",
                    "unused": "ignored",
                }
            ],
        },
    )

    result = run_tool(
        amap_poi.amap_nearby_search(
            location="121.0,31.0",
            keywords="coffee",
            radius=500,
            page_size=5,
        )
    )

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["pois"] == [
        {
            "id": "poi-1",
            "name": "Coffee Bar",
            "type": "Food",
            "address": "Road 1",
            "location": "121.1,31.2",
            "distance": "120",
            "tel": "123",
            "business_area": "Center",
            "cityname": "Shanghai",
            "adname": "Pudong",
        }
    ]
    request = FakeAsyncClient.requests[0]
    assert request["url"].endswith("/v5/place/around")
    assert request["params"]["keywords"] == "coffee"
    assert request["params"]["radius"] == 500
    assert request["params"]["page_size"] == 5


def test_amap_walking_route_returns_first_path_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_client(
        monkeypatch,
        amap_route,
        {
            "status": "1",
            "route": {
                "paths": [
                    {
                        "distance": "800",
                        "cost": {"duration": "600"},
                        "steps": [
                            {
                                "instruction": f"step {index}",
                                "road_name": f"road {index}",
                                "step_distance": str(index),
                                "orientation": "east",
                            }
                            for index in range(12)
                        ],
                    }
                ]
            },
        },
    )

    result = run_tool(
        amap_route.amap_walking_route(
            origin="121.0,31.0",
            destination="121.1,31.1",
        )
    )

    assert result["ok"] is True
    assert result["has_route"] is True
    assert result["distance_meter"] == "800"
    assert result["duration_second"] == "600"
    assert len(result["steps"]) == 10
    assert result["steps"][0] == {
        "instruction": "step 0",
        "road_name": "road 0",
        "distance": "0",
        "orientation": "east",
    }
    request = FakeAsyncClient.requests[0]
    assert request["url"].endswith("/v5/direction/walking")
    assert request["params"]["show_fields"] == "cost,navi"
