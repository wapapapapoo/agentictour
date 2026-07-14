from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base
from models.accompany import AIAdvice, Memo, Notification
from models.trip import Trip
from services import reminder_service
from services.ai_gateway import AuditedOutput


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


def _trip(status: str = "ongoing") -> Trip:
    return Trip(
        user_id=1,
        title="上海三日游",
        origin_city="杭州",
        destination_city="上海",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
        timezone="Asia/Shanghai",
        status=status,
    )


def _audited_output() -> AuditedOutput:
    return AuditedOutput(
        content="记得带证件",
        passed=True,
        reason=None,
        main_response={},
        audit_response={},
        audit_count=1,
    )


def test_due_reminder_uses_trip_as_context_and_keeps_dify_tour_key(
    db: Session, monkeypatch
) -> None:
    trip = _trip()
    db.add(trip)
    db.flush()
    db.add(
        Memo(
            trip_id=trip.id,
            memo_text="带证件",
            reminder_time=datetime(2026, 7, 20, 7, 0),
        )
    )
    db.commit()
    calls = []

    def fake_hikari(**kwargs):
        calls.append(kwargs)
        return _audited_output()

    monkeypatch.setattr(reminder_service, "run_hikari_once_audited", fake_hikari)

    count = reminder_service.scan_due_reminders(
        db,
        now=datetime(2026, 7, 20, 7, 1),
    )

    assert count == 1
    assert calls[0]["user"] == str(trip.user_id)
    assert calls[0]["inputs"]["tour_id"] == trip.id
    assert db.query(AIAdvice).one().trip_id == trip.id
    assert db.query(Notification).one().trip_id == trip.id


def test_cancelled_trip_does_not_emit_due_reminders(db: Session, monkeypatch) -> None:
    trip = _trip(status="cancelled")
    db.add(trip)
    db.flush()
    db.add(
        Memo(
            trip_id=trip.id,
            memo_text="这条不应发送",
            reminder_time=datetime(2026, 7, 20, 7, 0),
        )
    )
    db.commit()

    def unexpected_hikari(**_kwargs):
        raise AssertionError("cancelled trip must not call Hikari")

    monkeypatch.setattr(
        reminder_service,
        "run_hikari_once_audited",
        unexpected_hikari,
    )

    assert (
        reminder_service.scan_due_reminders(
            db,
            now=datetime(2026, 7, 20, 7, 1),
        )
        == 0
    )
