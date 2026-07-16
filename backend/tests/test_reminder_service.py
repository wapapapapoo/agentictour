import json
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base
from models.accompany import (
    AIAdvice,
    ChatMessage,
    ItineraryItem,
    Memo,
    Notification,
    UserLocation,
)
from models.trip import Trip
from models.user import User
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
    session.add(User(user_id=1, username="test-user-1", password_hash="test"))
    session.commit()
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


def _agent_decision_output(
    decision: str, conflicting_itinerary_ids: list[int] | None = None
) -> AuditedOutput:
    return AuditedOutput(
        content="check result",
        passed=True,
        reason=None,
        main_response={
            "data": {"outputs": {
                "reply": "check result",
                "decision": decision,
                "conflicting_itinerary_ids": conflicting_itinerary_ids or [],
            }}
        },
        audit_response={},
        audit_count=1,
    )


def _rejected_output() -> AuditedOutput:
    return AuditedOutput(
        content="不应保存的审核失败回复",
        passed=False,
        reason="自动检查未通过审核",
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
    db.add(
        UserLocation(
            user_id=trip.user_id,
            latitude=31.22,
            longitude=121.55,
            city="310115",
            place_name="Pudong",
            location_context="legacy context must not be sent",
            updated_at=datetime.now(UTC).replace(tzinfo=None),
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
    trip_context = json.loads(calls[0]["inputs"]["trip_context"])
    assert trip_context["destination_city"] == "上海"
    assert trip_context["display_timezone"] == "Asia/Shanghai"
    assert trip_context["database_timezone"] == "UTC"
    assert trip_context["current_time_local"].endswith("+08:00")
    assert calls[0]["inputs"]["city_adcode"] == "310115"
    snapshot = json.loads(calls[0]["inputs"]["backend_itinerary_context"])
    assert snapshot["authority"] == "current_database_state"
    assert snapshot["trip_id"] == trip.id
    assert "city" not in calls[0]["inputs"]
    assert "location_context" not in calls[0]["inputs"]
    assert db.query(AIAdvice).count() == 0
    notification = db.query(Notification).one()
    assert notification.trip_id == trip.id
    assert notification.advice_id is None
    assert notification.category == "memo"


def test_itinerary_reminder_sends_trip_local_time_to_dify(
    db: Session, monkeypatch
) -> None:
    trip = _trip()
    db.add(trip)
    db.flush()
    db.add(
        ItineraryItem(
            trip_id=trip.id,
            title="参观博物馆",
            place_name="上海博物馆",
            start_time=datetime(2026, 7, 20, 7, 30),
            end_time=datetime(2026, 7, 20, 9, 30),
            reminder_time=datetime(2026, 7, 20, 7, 0),
            itinerary_type="play",
            status="pending",
            is_initial=False,
        )
    )
    db.commit()
    calls = []

    def fake_hikari(**kwargs):
        calls.append(kwargs)
        return _audited_output()

    monkeypatch.setattr(reminder_service, "run_hikari_once_audited", fake_hikari)

    assert reminder_service.scan_due_reminders(
        db, now=datetime(2026, 7, 20, 7, 1)
    ) == 1

    assert "开始：2026-07-20T15:30+08:00 （Asia/Shanghai）" in calls[0][
        "original_input"
    ]
    assert "2026-07-20T07:30" not in calls[0]["original_input"]


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


@pytest.mark.parametrize("trigger_type", ["system_auto_check", "system_auto_advice"])
def test_agent_jobs_use_latest_frontend_adcode(
    db: Session, monkeypatch, trigger_type: str
) -> None:
    trip = _trip()
    db.add(trip)
    db.flush()
    db.add(
        UserLocation(
            user_id=trip.user_id,
            latitude=31.22,
            longitude=121.55,
            city="310115",
            place_name="Pudong",
            updated_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    db.commit()
    calls = []

    def fake_hikari(**kwargs):
        calls.append(kwargs)
        return _audited_output()

    monkeypatch.setattr(reminder_service, "run_hikari_once_audited", fake_hikari)

    reminder_service._agent_check(db, trip, trigger_type, "check current conditions")

    inputs = calls[0]["inputs"]
    assert inputs["city_adcode"] == "310115"
    assert json.loads(inputs["trip_context"])["destination_city"] == "上海"
    assert "city" not in inputs
    assert "location_context" not in inputs


def test_system_auto_check_false_does_not_notify(db: Session, monkeypatch) -> None:
    trip = _trip()
    db.add(trip)
    db.commit()
    monkeypatch.setattr(
        reminder_service,
        "run_hikari_once_audited",
        lambda **_kwargs: _agent_decision_output("false"),
    )

    advice = reminder_service._agent_check(
        db, trip, "system_auto_check", "check current conditions"
    )
    db.commit()

    assert advice.result == "not_required"
    assert db.query(AIAdvice).count() == 1
    assert db.query(Notification).count() == 0


def test_failed_audit_auto_check_is_not_persisted(
    db: Session, monkeypatch
) -> None:
    trip = _trip()
    db.add(trip)
    db.commit()
    monkeypatch.setattr(
        reminder_service,
        "run_hikari_once_audited",
        lambda **_kwargs: _rejected_output(),
    )

    advice = reminder_service._agent_check(
        db, trip, "system_auto_check", "check current conditions"
    )
    db.commit()

    assert advice is None
    assert db.query(AIAdvice).count() == 0
    notification = db.query(Notification).one()
    assert notification.advice_id is None
    assert notification.category == "agent_audit_failed"
    assert "审核" in notification.content
    assert db.query(ChatMessage).count() == 0


def test_planned_trip_does_not_emit_due_reminders(db: Session, monkeypatch) -> None:
    trip = _trip(status="planned")
    db.add(trip)
    db.flush()
    db.add(
        Memo(
            trip_id=trip.id,
            memo_text="计划尚未开始，不应提醒",
            reminder_time=datetime(2026, 7, 19, 23, 0),
        )
    )
    db.commit()

    monkeypatch.setattr(
        reminder_service,
        "run_hikari_once_audited",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("planned trip must not call Hikari")
        ),
    )

    assert reminder_service.scan_due_reminders(
        db, now=datetime(2026, 7, 19, 23, 1)
    ) == 0


@pytest.mark.parametrize(
    ("decision", "category", "result", "notification_count", "message_count"),
    [
        ("chat_recommendation", "proactive_recommendation", "delivered", 0, 1),
        ("itinerary_replan", "itinerary_replan", "pending", 1, 0),
    ],
)
def test_system_auto_check_routes_action_to_chat_or_notification(
    db: Session,
    monkeypatch,
    decision: str,
    category: str,
    result: str,
    notification_count: int,
    message_count: int,
) -> None:
    trip = _trip()
    db.add(trip)
    db.commit()
    monkeypatch.setattr(
        reminder_service,
        "run_hikari_once_audited",
        lambda **_kwargs: _agent_decision_output(decision),
    )

    advice = reminder_service._agent_check(
        db, trip, "system_auto_check", "check current conditions"
    )
    db.commit()

    assert advice.result == result
    assert advice.advice_type == category
    assert db.query(Notification).count() == notification_count
    assert db.query(ChatMessage).count() == message_count
    if notification_count:
        notification = db.query(Notification).one()
        assert notification.advice_id == advice.advice_id
        assert notification.category == category


def test_system_auto_check_reuses_open_adjustment_without_duplicate_notification(
    db: Session, monkeypatch
) -> None:
    trip = _trip()
    db.add(trip)
    db.commit()
    calls = 0

    def run_agent(**_kwargs):
        nonlocal calls
        calls += 1
        return _agent_decision_output("itinerary_replan")

    monkeypatch.setattr(reminder_service, "run_hikari_once_audited", run_agent)

    first = reminder_service._agent_check(
        db, trip, "system_auto_check", "due reminder check"
    )
    second = reminder_service._agent_check(
        db, trip, "system_auto_check", "hourly check"
    )
    db.commit()

    assert first is not None
    assert second is not None
    assert second.advice_id == first.advice_id
    assert calls == 1
    assert db.query(Notification).count() == 1


def test_auto_replan_persists_pending_conflict_ids(db: Session, monkeypatch) -> None:
    trip = _trip()
    db.add(trip)
    db.commit()
    itinerary = ItineraryItem(
        trip_id=trip.id,
        title="夜游",
        place_name="河畔",
        start_time=datetime(2026, 7, 20, 20),
        end_time=datetime(2026, 7, 20, 22),
        itinerary_type="play",
        status="pending",
    )
    completed = ItineraryItem(
        trip_id=trip.id,
        title="已完成项目",
        place_name="旧地点",
        start_time=datetime(2026, 7, 20, 8),
        end_time=datetime(2026, 7, 20, 9),
        itinerary_type="play",
        status="done",
    )
    db.add_all([itinerary, completed])
    db.commit()
    monkeypatch.setattr(
        reminder_service,
        "run_hikari_once_audited",
        lambda **_kwargs: _agent_decision_output(
            "itinerary_replan", [itinerary.itinerary_id, completed.itinerary_id]
        ),
    )

    advice = reminder_service._agent_check(
        db, trip, "system_auto_check", "check current conditions"
    )
    db.commit()

    proposed = json.loads(advice.proposed_itinerary_json)
    assert proposed["conflicting_itinerary_ids"] == [itinerary.itinerary_id]
    db.refresh(itinerary)
    db.refresh(completed)
    assert itinerary.status == "change_pending"
    assert completed.status == "done"


def test_change_pending_itinerary_is_not_sent_to_periodic_agent_again(
    db: Session, monkeypatch
) -> None:
    trip = _trip()
    db.add(trip)
    db.flush()
    db.add(
        ItineraryItem(
            trip_id=trip.id,
            title="等待用户确认的行程",
            place_name="河畔",
            start_time=datetime(2026, 7, 20, 20),
            end_time=datetime(2026, 7, 20, 22),
            itinerary_type="play",
            status="change_pending",
        )
    )
    db.commit()
    monkeypatch.setattr(
        reminder_service,
        "run_hikari_once_audited",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("change_pending itinerary must not be sent to Dify")
        ),
    )

    executed = reminder_service.run_periodic_agent_jobs(
        db, now=datetime(2026, 7, 20, 10)
    )

    assert executed == 0
