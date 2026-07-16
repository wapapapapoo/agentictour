from typing import Any, Dict

import httpx

from travel_mcp.configs import settings


async def _amap_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        response = await client.get(
            f"{settings.AMAP_BASE_URL}{path}",
            params={**params, "key": settings.AMAP_KEY, "output": "json"},
        )
        response.raise_for_status()
        data = response.json()
    if str(data.get("status")) != "1":
        raise RuntimeError(data.get("info") or "AMap request failed")
    return data


async def amap_reverse_geocode(
    longitude: float,
    latitude: float,
    coordinate_system: str = "gps",
) -> Dict[str, Any]:
    """Resolve coordinates to an AMap address and adcode."""
    try:
        amap_longitude, amap_latitude = longitude, latitude
        if coordinate_system.lower() in {"gps", "wgs84"}:
            converted = await _amap_get(
                "/v3/assistant/coordinate/convert",
                {"locations": f"{longitude},{latitude}", "coordsys": "gps"},
            )
            amap_longitude, amap_latitude = (
                float(value)
                for value in str(converted.get("locations") or "").split(",", 1)
            )
        reverse = await _amap_get(
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
        city = component.get("city")
        if not isinstance(city, str) or not city:
            city = component.get("province") or ""
        return {
            "ok": True,
            "tool": "amap_reverse_geocode",
            "coordinate": {
                "longitude": amap_longitude,
                "latitude": amap_latitude,
                "coordinate_system": "gcj02",
            },
            "adcode": str(component.get("adcode") or ""),
            "formatted_address": regeocode.get("formatted_address") or "",
            "place_name": nearest_poi.get("name")
            or regeocode.get("formatted_address")
            or "",
            "province": component.get("province") or "",
            "city": city,
            "district": component.get("district") or "",
            "township": component.get("township") or "",
            "nearest_poi": nearest_poi.get("name") or "",
        }
    except Exception as exc:
        return {"ok": False, "tool": "amap_reverse_geocode", "error": str(exc)}
