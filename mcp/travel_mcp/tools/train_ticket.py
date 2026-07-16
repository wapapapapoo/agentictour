from typing import Any

from fastmcp import Client

from travel_mcp.configs import settings


async def train_ticket_query(
    date: str,
    from_station: str,
    to_station: str,
    train_filter_flags: str = "",
    earliest_start_time: int = 0,
    latest_start_time: int = 24,
    sort_flag: str = "startTime",
    limited_num: int = 10,
) -> dict[str, Any]:
    """Query Joooook/12306-mcp and return its official 12306 result."""
    arguments = {
        "date": date,
        "fromStation": from_station,
        "toStation": to_station,
        "trainFilterFlags": train_filter_flags,
        "earliestStartTime": earliest_start_time,
        "latestStartTime": latest_start_time,
        "sortFlag": sort_flag,
        "sortReverse": False,
        "limitedNum": limited_num,
        "format": "text",
    }
    try:
        async with Client(settings.TRAIN_MCP_URL) as client:
            result = await client.call_tool(
                "get-tickets",
                arguments,
                timeout=settings.HTTP_TIMEOUT,
                raise_on_error=False,
            )
    except Exception as exc:
        return {
            "ok": False,
            "source": "Joooook/12306-mcp",
            "error": f"12306 MCP 连接失败：{exc}",
        }
    texts = [
        block.text
        for block in result.content
        if hasattr(block, "text") and isinstance(block.text, str)
    ]
    text = "\n".join(texts).strip()
    if result.is_error or text.startswith("Error:"):
        return {
            "ok": False,
            "source": "Joooook/12306-mcp",
            "error": text or "12306 查询失败",
        }
    return {
        "ok": True,
        "source": "Joooook/12306-mcp（12306 实时查询）",
        "query": arguments,
        "tickets": text,
    }
