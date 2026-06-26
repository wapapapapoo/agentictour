from typing import Any, Dict, List, Mapping

import httpx

from travel_mcp.configs import settings


async def amap_nearby_search(
    location: str,
    keywords: str = "",
    types: str = "",
    radius: int = 1000,
    page_size: int = 10,
    page_num: int = 1,
) -> Dict[str, Any]:
    """
    查询附近 POI。

    参数:
    - location: 中心点经纬度，格式：经度,纬度，例如 116.397428,39.90923
    - keywords: 搜索关键词，例如 餐厅、咖啡、厕所、商场
    - types: 高德 POI 类型编码，可选
    - radius: 搜索半径，单位米
    - page_size: 返回数量，建议 5~20
    - page_num: 页码
    """

    url = f"{settings.AMAP_BASE_URL}/v5/place/around"

    params: Mapping[str, str | int] = {
        "key": settings.AMAP_KEY,
        "location": location,
        "keywords": keywords,
        "types": types,
        "radius": radius,
        "page_size": page_size,
        "page_num": page_num,
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
            "tool": "amap_nearby_search",
            "error": f"Failed to request AMap POI API: {str(e)}",
        }

    if str(data.get("status")) != "1":
        return {
            "ok": False,
            "tool": "amap_nearby_search",
            "info": data.get("info"),
            "infocode": data.get("infocode"),
            "raw": data,
        }

    pois = data.get("pois", [])

    simplified_pois: List[Dict[str, Any]] = []
    for poi in pois:
        simplified_pois.append(
            {
                "id": poi.get("id"),
                "name": poi.get("name"),
                "type": poi.get("type"),
                "address": poi.get("address"),
                "location": poi.get("location"),
                "distance": poi.get("distance"),
                "tel": poi.get("tel"),
                "business_area": poi.get("business_area"),
                "cityname": poi.get("cityname"),
                "adname": poi.get("adname"),
            }
        )

    return {
        "ok": True,
        "tool": "amap_nearby_search",
        "location": location,
        "keywords": keywords,
        "types": types,
        "radius": radius,
        "count": len(simplified_pois),
        "pois": simplified_pois,
    }
