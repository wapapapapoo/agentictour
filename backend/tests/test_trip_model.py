from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import BigInteger, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base
from models.accompany import (
    AIAdvice,
    ChatSession,
    ItineraryItem,
    Memo,
    Notification,
    UserLocation,
)
from models.trip import Trip
from schemas.trip import TripCreate, TripUpdate
from services import trip_service


@pytest.fixture
def db() -> Session:
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
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _trip_data(**overrides) -> TripCreate:
    values = {
        "user_id": 1,
        "title": "上海三日游",
        "origin_city": "杭州",
        "destination_city": "上海",
        "start_date": date(2026, 7, 20),
        "end_date": date(2026, 7, 22),
        "timezone": "Asia/Shanghai",
        "status": "planned",
    }
    values.update(overrides)
    return TripCreate(**values)


def test_companion_foreign_keys_target_trips() -> None:
    for model in (ItineraryItem, AIAdvice, Memo, ChatSession, Notification):
        assert hasattr(model, "trip_id")
        assert not hasattr(model, "tour_id")
        foreign_keys = model.__table__.c.trip_id.foreign_keys
        assert {fk.target_fullname for fk in foreign_keys} == {"trips.id"}


def test_trip_domain_user_ids_are_bigint() -> None:
    for model in (Trip, ChatSession, Notification, UserLocation):
        assert isinstance(model.__table__.c.user_id.type, BigInteger)

    assert TripCreate.model_fields["user_id"].annotation is int


def test_trip_create_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError, match="end_date"):
        _trip_data(
            start_date=date(2026, 7, 22),
            end_date=date(2026, 7, 20),
        )


def test_trip_service_crud_and_status_transition(db: Session) -> None:
    created = trip_service.create_trip(db, _trip_data())

    assert created.id is not None
    assert trip_service.get_trip(db, created.id) is created
    assert trip_service.list_trips(db, user_id=2) == []
    assert trip_service.list_trips(db, user_id=1) == [created]

    updated = trip_service.update_trip(
        db,
        created.id,
        TripUpdate(status="ongoing", title="上海舒适三日游"),
    )
    assert updated.status == "ongoing"
    assert updated.title == "上海舒适三日游"


def test_trip_service_rejects_partial_update_with_inverted_dates(db: Session) -> None:
    created = trip_service.create_trip(db, _trip_data())

    with pytest.raises(ValueError, match="end_date"):
        trip_service.update_trip(
            db,
            created.id,
            TripUpdate(start_date=date(2026, 7, 23)),
        )


def test_deleting_trip_cascades_to_companion_rows(db: Session) -> None:
    trip = trip_service.create_trip(db, _trip_data())
    db.add(
        Memo(
            trip_id=trip.id,
            memo_text="带证件",
        )
    )
    db.commit()

    db.delete(trip)
    db.commit()

    assert db.query(Memo).count() == 0
    assert db.query(Trip).count() == 0


def test_fresh_companion_schema_references_trips_only() -> None:
    sql_dir = Path(__file__).resolve().parents[1] / "sql"
    trips_sql = (sql_dir / "03a_trips_table.sql").read_text(encoding="utf-8")
    companion_sql = (sql_dir / "04_accompany_tables.sql").read_text(
        encoding="utf-8"
    )

    assert "CREATE TABLE IF NOT EXISTS trips" in trips_sql
    assert "user_id BIGINT NOT NULL" in trips_sql
    assert companion_sql.count("user_id BIGINT") == 3
    assert companion_sql.count("REFERENCES trips(id)") == 5
    assert "REFERENCES trip_plan_requests(id)" not in companion_sql
    assert "tour_id" not in companion_sql
