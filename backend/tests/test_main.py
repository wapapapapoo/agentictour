"""Tests for AgenticTour API."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "AgenticTour" in r.json()["message"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_travel_plan():
    payload = {
        "destination": "tokyo",
        "departure_city": "北京",
        "start_date": str(date.today() + timedelta(days=30)),
        "end_date": str(date.today() + timedelta(days=32)),
        "budget": 8000,
        "travelers": 1,
        "style": "foodie",
        "interests": ["美食"],
    }
    r = client.post("/api/plan", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert len(data["days"]) == 3
    assert len(data["agent_log"]) >= 4
    assert "budget_breakdown" in data
    return data["id"]


def test_list_plans():
    test_create_travel_plan()
    r = client.get("/api/plan")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_plan():
    pid = test_create_travel_plan()
    r = client.get(f"/api/plan/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid


def test_plan_not_found():
    r = client.get("/api/plan/nonexistent")
    assert r.status_code == 404


def test_companion_chat():
    r = client.post("/api/companion/chat", json={"message": "附近有好吃的吗"})
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data
    assert len(data["suggestions"]) > 0


def test_companion_chat_with_plan():
    pid = test_create_travel_plan()
    r = client.post("/api/companion/chat", json={"plan_id": pid, "message": "天气"})
    assert r.status_code == 200
    assert "reply" in r.json()


def test_blog_generate():
    pid = test_create_travel_plan()
    r = client.post("/api/blog/generate", json={
        "plan_id": pid, "tone": "casual", "focus": "food",
    })
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert len(data["suggested_hashtags"]) > 0


def test_blog_plan_not_found():
    r = client.post("/api/blog/generate", json={
        "plan_id": "nope", "tone": "casual", "focus": "highlights",
    })
    assert r.status_code == 404
