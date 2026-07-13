import os

from dotenv import load_dotenv
from fastapi import FastAPI

from routers.blog import router as blog_router
from routers.knowledge import router as knowledge_router
from routers.trip_plan import router as trip_plan_router

# 加载 .env 文件
load_dotenv()

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )
