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
    鏌ヨ闄勮繎 POI銆?

    鍙傛暟:
    - location: 涓績鐐圭粡绾害锛屾牸寮忥細缁忓害,绾害锛屼緥濡?116.397428,39.90923
    - keywords: 鎼滅储鍏抽敭璇嶏紝渚嬪 椁愬巺銆佸挅鍟°€佸帟鎵€銆佸晢鍦?
    - types: 楂樺痉 POI 绫诲瀷缂栫爜锛屽彲閫?
    - radius: 鎼滅储鍗婂緞锛屽崟浣嶇背
    - page_size: 杩斿洖鏁伴噺锛屽缓璁?5~20
    - page_num: 椤电爜
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
