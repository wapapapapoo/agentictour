from typing import Any, Dict

import httpx

from travel_mcp.configs import settings


async def amap_weather(adcode: str, extensions: str = "base") -> Dict[str, Any]:
    """
    查询高德天气。

    参数:
    - adcode: 城市/区县 adcode，例如上海 310000、北京 110000
    - extensions:
        - base: 实况天气
        - all: 未来天气预报
    """

    url = f"{settings.AMAP_BASE_URL}/v3/weather/weatherInfo"

    params = {
        "key": settings.AMAP_KEY,
        "city": adcode,
        "extensions": extensions,
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
            "tool": "amap_weather",
            "error": f"Failed to request AMap weather API: {str(e)}",
        }

    if str(data.get("status")) != "1":
        return {
            "ok": False,
            "tool": "amap_weather",
            "info": data.get("info"),
            "infocode": data.get("infocode"),
            "raw": data,
        }

    if extensions == "base":
        lives = data.get("lives", [])
        return {
            "ok": True,
            "tool": "amap_weather",
            "mode": "base",
            "adcode": adcode,
            "weather": lives[0] if lives else {},
            "raw": data,
        }

    forecasts = data.get("forecasts", [])
    return {
        "ok": True,
        "tool": "amap_weather",
        "mode": "forecast",
        "adcode": adcode,
        "forecast": forecasts[0] if forecasts else {},
        "raw": data,
    }
