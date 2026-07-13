import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from routers.accompany import router as accompany_router
from routers.blog import router as blog_router
from routers.knowledge import router as knowledge_router
from routers.trip_plan import router as trip_plan_router
from scheduler import reminder_loop

# 加载 .env 文件
load_dotenv()

from db_init import run_init_sql
run_init_sql()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(reminder_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=os.getenv("APP_NAME", "My FastAPI App"),
    debug=os.getenv("DEBUG", "false").lower() == "true",
    lifespan=lifespan,
)

app.include_router(blog_router)
app.include_router(knowledge_router)
app.include_router(trip_plan_router)
app.include_router(accompany_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "pong"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/debug/db")
def debug_db():
    from sqlalchemy import text
    from database import engine, DATABASE_URL
    safe = DATABASE_URL.rsplit("@", 1)[-1] if "@" in DATABASE_URL else DATABASE_URL
    with engine.connect() as c:
        tables = [r[0] for r in c.execute(text("SHOW TABLES"))]
    return {"host": safe, "tables": tables}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )
