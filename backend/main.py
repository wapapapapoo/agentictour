"""AgenticTour API — LLM-powered travel planning, companion, and blog."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents import companion_chat, generate_blog, plan_travel
from models import (
    BlogGenerateRequest,
    CompanionChatRequest,
    CompanionResponse,
    TravelPlan,
    TravelPlanRequest,
)

load_dotenv()

app = FastAPI(
    title="AgenticTour",
    description="LLM驱动的智能旅行规划与陪伴",
    version="0.2.0",
    debug=os.getenv("DEBUG", "false").lower() == "true",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

plans_db: dict[str, TravelPlan] = {}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AgenticTour API 🧳", "docs": "/docs"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/plan")
def create_travel_plan(request: TravelPlanRequest) -> TravelPlan:
    """生成旅行计划 — 多Agent协作 + LLM"""
    plan = plan_travel(request)
    plans_db[plan.id] = plan
    return plan


@app.get("/api/plan")
def list_plans() -> list[dict[str, Any]]:
    return [
        {
            "id": p.id,
            "created_at": p.created_at.isoformat(),
            "destination": p.request.destination,
            "dates": f"{p.request.start_date} ~ {p.request.end_date}",
            "style": p.request.style,
            "overview": p.overview[:100] + "...",
        }
        for p in plans_db.values()
    ]


@app.get("/api/plan/{plan_id}")
def get_plan(plan_id: str) -> TravelPlan:
    if plan_id not in plans_db:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plans_db[plan_id]


@app.post("/api/companion/chat")
def chat_with_companion(request: CompanionChatRequest) -> CompanionResponse:
    plan = plans_db.get(request.plan_id) if request.plan_id else None
    ctx: dict[str, Any] = dict(request.context)
    if plan:
        ctx["destination"] = plan.request.destination
    result = companion_chat(request.message, ctx)
    return CompanionResponse(**result)


@app.post("/api/blog/generate")
def create_blog_post(request: BlogGenerateRequest) -> dict[str, Any]:
    if request.plan_id not in plans_db:
        raise HTTPException(status_code=404, detail="Plan not found")
    return generate_blog(plans_db[request.plan_id], request.tone, request.focus)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )
