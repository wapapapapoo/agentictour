from typing import Any, Dict

from fastmcp import FastMCP

from travel_mcp.configs import check_settings, settings
from travel_mcp.tools.amap_poi import amap_nearby_search as amap_nearby_search_func
from travel_mcp.tools.amap_route import amap_walking_route as amap_walking_route_func
from travel_mcp.tools.amap_weather import amap_weather as amap_weather_func
from travel_mcp.tools.knowledge_search import (
    list_knowledge_bases as list_knowledge_bases_func,
    search_knowledge as search_knowledge_func,
)

check_settings()

mcp = FastMCP("ai-travel-amap-mcp")


@mcp.tool
async def amap_weather(adcode: str, extensions: str = "base") -> Dict[str, Any]:
    """
    查询指定城市或区县的天气。

    适用场景：
    - 用户问今天/现在天气
    - 用户问是否需要带伞
    - 用户问穿衣建议
    - 系统自动生成行前提醒

    参数：
    - adcode: 高德行政区编码，例如上海 310000，北京 110000
    - extensions: base 表示实况天气，all 表示天气预报
    """
    return await amap_weather_func(adcode=adcode, extensions=extensions)


@mcp.tool
async def amap_nearby_search(
    location: str,
    keywords: str = "",
    types: str = "",
    radius: int = 1000,
    page_size: int = 10,
    page_num: int = 1,
) -> Dict[str, Any]:
    """
    查询当前位置附近的地点。

    适用场景：
    - 用户想找附近餐厅
    - 用户想找咖啡店
    - 用户想找休息点
    - 用户想找厕所、商场、景点等

    参数：
    - location: 经纬度，格式为 经度,纬度，例如 116.397428,39.90923
    - keywords: 搜索关键词，例如 餐厅、咖啡、厕所、商场
    - types: 高德 POI 类型编码，可为空
    - radius: 搜索半径，单位米
    - page_size: 返回数量
    - page_num: 页码
    """
    return await amap_nearby_search_func(
        location=location,
        keywords=keywords,
        types=types,
        radius=radius,
        page_size=page_size,
        page_num=page_num,
    )


@mcp.tool
async def amap_walking_route(
    origin: str,
    destination: str,
    isindoor: int = 0,
) -> Dict[str, Any]:
    """
    查询两个地点之间的步行路线。

    适用场景：
    - 用户问怎么走
    - 用户问步行多久
    - 用户问是否来得及
    - 系统判断附近地点是否适合作为推荐

    参数：
    - origin: 起点经纬度，格式为 经度,纬度
    - destination: 终点经纬度，格式为 经度,纬度
    - isindoor: 是否室内算路，0 不需要，1 需要
    """
    return await amap_walking_route_func(
        origin=origin,
        destination=destination,
        isindoor=isindoor,
    )


@mcp.tool
async def list_knowledge_bases() -> Dict[str, Any]:
    """
    列出 Dify 中所有可用的知识库，返回每个知识库的 ID、名称、描述和文档数。

    模型应先调用此工具获取可用知识库清单，根据 description 判断哪个知识库适合用户的查询意图，
    然后用返回的 id 调用 search_knowledge。
    """
    return await list_knowledge_bases_func()


@mcp.tool
async def search_knowledge(dataset_id: str, query: str) -> Dict[str, Any]:
    """
    在指定的 Dify 知识库中检索文档片段。

    适用场景：
    - 用户询问旅行攻略、美食推荐、行程安排等信息
    - 需要从已有知识库中查找相关内容

    参数：
    - dataset_id: 知识库 ID（由 list_knowledge_bases 返回）
    - query: 搜索关键词或问题
    """
    return await search_knowledge_func(dataset_id=dataset_id, query=query)


if __name__ == "__main__":
    # Dify 接 MCP 时一般用 HTTP 地址，例如：
    # http://服务器IP:8001/mcp
    mcp.run(
        transport="streamable-http",
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        path=settings.MCP_PATH,
    )