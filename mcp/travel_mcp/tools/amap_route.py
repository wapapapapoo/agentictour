from typing import Any, Dict, List, Mapping

import httpx

from travel_mcp.configs import settings


async def amap_walking_route(
    origin: str,
    destination: str,
    isindoor: int = 0,
) -> Dict[str, Any]:
    """
    查询步行路线。

    参数:
    - origin: 起点经纬度，格式：经度,纬度
    - destination: 终点经纬度，格式：经度,纬度
    - isindoor: 是否需要室内算路，0 不需要，1 需要
    """

    url = f"{settings.AMAP_BASE_URL}/v5/direction/walking"

    params: Mapping[str, str | int] = {
        "key": settings.AMAP_KEY,
        "origin": origin,
        "destination": destination,
        "isindoor": isindoor,
        "show_fields": "cost,navi",
        "output": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return {
            "ok": False,
            "tool": "amap_walking_route",
            "error": f"Failed to request AMap walking route API: {str(e)}",
        }

    if str(data.get("status")) != "1":
        return {
            "ok": False,
            "tool": "amap_walking_route",
            "info": data.get("info"),
            "infocode": data.get("infocode"),
            "raw": data,
        }

    route = data.get("route", {})
    paths = route.get("paths", [])

    if not paths:
        return {
            "ok": True,
            "tool": "amap_walking_route",
            "origin": origin,
            "destination": destination,
            "has_route": False,
            "message": "No walking route found",
            "raw": data,
        }

    first_path = paths[0]

    steps: List[Dict[str, Any]] = []
    for step in first_path.get("steps", [])[:10]:
        steps.append(
            {
                "instruction": step.get("instruction"),
                "road_name": step.get("road_name"),
                "distance": step.get("step_distance") or step.get("distance"),
                "orientation": step.get("orientation"),
            }
        )

    return {
        "ok": True,
        "tool": "amap_walking_route",
        "origin": origin,
        "destination": destination,
        "has_route": True,
        "distance_meter": first_path.get("distance"),
        "duration_second": first_path.get("cost", {}).get("duration"),
        "steps": steps,
        "raw": data,
    }
