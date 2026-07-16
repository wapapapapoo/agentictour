from __future__ import annotations

import os
from typing import Any

import httpx

AMAP_BASE_URL = os.getenv("AMAP_BASE_URL", "https://restapi.amap.com").rstrip("/")
AMAP_KEY = os.getenv("AMAP_KEY", "")
AMAP_TIMEOUT = float(os.getenv("AMAP_TIMEOUT", "10"))


def _request(path: str, params: dict[str, Any]) -> dict[str, Any]:
    if not AMAP_KEY:
        raise RuntimeError("AMAP_KEY is not configured")
    response = httpx.get(
        f"{AMAP_BASE_URL}{path}",
        params={**params, "key": AMAP_KEY, "output": "json"},
        timeout=AMAP_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if str(payload.get("status")) != "1":
        raise RuntimeError(payload.get("info") or "AMap request failed")
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
    place_name = str(nearest_poi.get("name") or formatted_address)
    city = component.get("city")
    if not isinstance(city, str) or not city:
        city = component.get("province") or ""
    return {
        "latitude": amap_latitude,
        "longitude": amap_longitude,
        "city_adcode": str(component.get("adcode") or ""),
        "place_name": place_name,
        "location_context": {
            "provider": "amap",
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
