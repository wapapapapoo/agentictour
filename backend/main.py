import os

from dotenv import load_dotenv
from fastapi import FastAPI

from routers.blog import router as blog_router
from routers.knowledge import router as knowledge_router
from routers.trip_plan import router as trip_plan_router

# 加载 .env 文件
load_dotenv()

from db_init import run_init_sql
run_init_sql()

app = FastAPI(
    title=os.getenv("APP_NAME", "My FastAPI App"),
    debug=os.getenv("DEBUG", "false").lower() == "true",
)

app.include_router(blog_router)
app.include_router(knowledge_router)
app.include_router(trip_plan_router)

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
