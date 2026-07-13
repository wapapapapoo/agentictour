import httpx
import asyncio

async def call(sid, method, params=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    async with httpx.AsyncClient() as c:
        r = await c.post(
            "http://localhost:8001/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": sid,
            },
            json=body,
        )
        return r.text

async def main():
    async with httpx.AsyncClient() as c:
        r = await c.get("http://localhost:8001/mcp", headers={"Accept": "text/event-stream"})
        sid = r.headers["mcp-session-id"]
        print("session:", sid)

    print("=== tools/list ===")
    print(await call(sid, "tools/list"))

    print("=== list_knowledge_bases ===")
    print(await call(sid, "tools/call", {"name": "list_knowledge_bases", "arguments": {}}))

    print("=== search_knowledge ===")
    print(await call(sid, "tools/call", {"name": "search_knowledge", "arguments": {"dataset_id": "396ae5ec-72b1-464e-b6a0-129567810feb", "query": "上海美食"}}))

asyncio.run(main())
