from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "pong"}


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_history_route_uses_integer_session_id() -> None:
    schema = client.get("/openapi.json").json()

    assert "/api/chat/conversations/{conversation_id}" not in schema["paths"]
    operation = schema["paths"]["/api/chat/sessions/{session_id}"]["get"]
    session_parameter = next(
        parameter
        for parameter in operation["parameters"]
        if parameter["name"] == "session_id"
    )
    assert session_parameter["schema"]["type"] == "integer"
