from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from models import Trip  # noqa: F401 - load the complete model graph
from routers.trip import router


def test_trip_api_create_list_get_and_update() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    app = FastAPI()
    app.include_router(router)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    try:
        created = client.post(
            "/api/trips",
            json={
                "user_id": 42,
                "title": "上海三日游",
                "origin_city": "杭州",
                "destination_city": "上海",
                "start_date": "2026-07-20",
                "end_date": "2026-07-22",
            },
        )
        assert created.status_code == 201
        trip_id = created.json()["id"]

        listed = client.get("/api/trips", params={"user_id": 42})
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [trip_id]

        fetched = client.get(f"/api/trips/{trip_id}")
        assert fetched.status_code == 200
        assert fetched.json()["user_id"] == 42

        updated = client.patch(
            f"/api/trips/{trip_id}",
            json={"status": "ongoing"},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "ongoing"
    finally:
        session.close()
        Base.metadata.drop_all(engine)
