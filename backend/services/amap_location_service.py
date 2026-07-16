from __future__ import annotations

import os
from typing import Any

import httpx


def _request(path: str, params: dict[str, Any]) -> dict[str, Any]:
    # Read at request time so process managers and container runtime injection
    # are not affected by Python module import order.
    key = os.getenv("AMAP_KEY", "").strip()
    base_url = (
        os.getenv("AMAP_BASE_URL", "https://restapi.amap.com").strip().rstrip("/")
    )
    timeout = float(os.getenv("AMAP_TIMEOUT", "10").strip())
    if not key:
        raise RuntimeError("后端未配置 AMAP_KEY")
    try:
        response = httpx.get(
            f"{base_url}{path}",
            params={**params, "key": key, "output": "json"},
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"高德服务返回 HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise RuntimeError("后端无法连接高德服务") from exc
    payload = response.json()
    if str(payload.get("status")) != "1":
        info = payload.get("info") or "未知错误"
        infocode = payload.get("infocode") or ""
        raise RuntimeError(f"高德解析失败：{info}（{infocode}）")
    return payload


def resolve_browser_location(latitude: float, longitude: float) -> dict[str, Any]:
    """Convert browser WGS84 coordinates to GCJ-02 and resolve the address."""
    converted = _request(
        "/v3/assistant/coordinate/convert",
        {"locations": f"{longitude},{latitude}", "coordsys": "gps"},
    )
    location_text = str(converted.get("locations") or "").split(";")[0]
    try:
        amap_longitude, amap_latitude = (
            float(value) for value in location_text.split(",", maxsplit=1)
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError("AMap returned invalid converted coordinates") from exc

    reverse = _request(
        "/v3/geocode/regeo",
        {
            "location": f"{amap_longitude},{amap_latitude}",
            "extensions": "all",
            "radius": 1000,
        },
    )
    regeocode = reverse.get("regeocode") or {}
    component = regeocode.get("addressComponent") or {}
    pois = regeocode.get("pois") or []
    nearest_poi = pois[0] if pois else {}
    formatted_address = str(regeocode.get("formatted_address") or "")
    adcode = str(component.get("adcode") or "")
    if not formatted_address or not adcode:
        raise RuntimeError("高德未返回可用的地址或城市编码")
    place_name = str(nearest_poi.get("name") or formatted_address)
    city = component.get("city")
    if not isinstance(city, str) or not city:
        city = component.get("province") or ""
    return {
        "latitude": amap_latitude,
        "longitude": amap_longitude,
        "city_adcode": adcode,
        "place_name": place_name,
        "location_context": {
            "provider": "amap",
            "resolution_status": "resolved",
            "source_coordinate_system": "wgs84",
            "source_latitude": latitude,
            "source_longitude": longitude,
            "coordinate_system": "gcj02",
            "formatted_address": formatted_address,
            "province": component.get("province") or "",
            "city": city,
            "district": component.get("district") or "",
            "township": component.get("township") or "",
            "nearest_poi": nearest_poi.get("name") or "",
        },
    }
