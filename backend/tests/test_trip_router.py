from datetime import date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from auth import get_current_user
from database import Base, get_db
from models import ItineraryItem, Memo, Trip, User  # noqa: F401 - load complete graph
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
    session.add_all(
        [
            User(user_id=42, username="test-user-42", password_hash="test"),
            User(user_id=43, username="test-user-43", password_hash="test"),
        ]
    )
    session.commit()
    app = FastAPI()
    app.include_router(router)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: 42
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

        memo = Memo(trip_id=trip_id, memo_text="带充电宝")
        itinerary = ItineraryItem(
            trip_id=trip_id,
            title="入住酒店",
            place_name="沈阳站附近",
            start_time=datetime(2026, 7, 20, 20, 0),
            end_time=datetime(2026, 7, 20, 21, 0),
        )
        session.add_all([memo, itinerary])
        session.commit()
        memo_id = memo.memo_id
        itinerary_id = itinerary.itinerary_id

        other_trip = Trip(
            user_id=43,
            title="其他用户的计划",
            origin_city="北京",
            destination_city="天津",
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 21),
            status="planned",
        )
        session.add(other_trip)
        session.commit()
        assert client.delete(f"/api/trips/{other_trip.id}").status_code == 404
        assert session.get(Trip, other_trip.id) is not None

        deleted = client.delete(f"/api/trips/{trip_id}")
        assert deleted.status_code == 204
        assert session.get(Memo, memo_id) is None
        assert session.get(ItineraryItem, itinerary_id) is None
        assert client.get(f"/api/trips/{trip_id}").status_code == 404
        assert client.get("/api/trips", params={"user_id": 42}).json() == []
    finally:
        session.close()
        Base.metadata.drop_all(engine)
