from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base
from models.accompany import AIAdvice, ItineraryItem
from schemas.accompany import ItineraryCreate, MemoCreate
from services import accompany_service, ai_gateway


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _item(start: datetime, end: datetime, **kwargs) -> ItineraryCreate:
    return ItineraryCreate(
        tour_id=1,
        title=kwargs.pop("title", "行程"),
        place_name="地点",
        start_time=start,
        end_time=end,
        **kwargs,
    )


def test_first_item_each_day_is_initial_and_reminds_at_start(db: Session) -> None:
    first = accompany_service.create_itinerary(
        db, _item(datetime(2026, 7, 20, 8), datetime(2026, 7, 20, 9))
    )
    next_day = accompany_service.create_itinerary(
        db, _item(datetime(2026, 7, 21, 9), datetime(2026, 7, 21, 10))
    )
    assert first.is_initial is True
    assert first.reminder_time == first.start_time
    assert next_day.is_initial is True
    assert next_day.reminder_time == next_day.start_time


def test_play_reminder_uses_previous_end_minus_twenty_minutes(db: Session) -> None:
    accompany_service.create_itinerary(
        db, _item(datetime(2026, 7, 20, 8), datetime(2026, 7, 20, 9))
    )
    second = accompany_service.create_itinerary(
        db, _item(datetime(2026, 7, 20, 10), datetime(2026, 7, 20, 11))
    )
    assert second.reminder_time == datetime(2026, 7, 20, 8, 40)


def test_short_previous_item_uses_five_minutes_or_end(db: Session) -> None:
    start = datetime(2026, 7, 20, 8)
    db.add(
        ItineraryItem(
            tour_id=1,
            title="短行程",
            place_name="地点",
            start_time=start,
            end_time=start + timedelta(minutes=10),
            itinerary_type="play",
            reminder_time=start,
            is_initial=True,
        )
    )
    db.commit()
    second = accompany_service.create_itinerary(
        db, _item(datetime(2026, 7, 20, 9), datetime(2026, 7, 20, 10))
    )
    assert second.reminder_time == start + timedelta(minutes=5)


def test_transit_requires_reminder() -> None:
    with pytest.raises(ValueError, match="requires reminder_time"):
        _item(
            datetime(2026, 7, 20, 8),
            datetime(2026, 7, 20, 9),
            itinerary_type="transit",
        )


def test_gateway_retries_and_audits_at_most_twice(monkeypatch) -> None:
    calls = {"main": 0, "audit": 0}

    class Main:
        def run_workflow(self, **_kwargs):
            calls["main"] += 1
            return {"data": {"outputs": {"reply": "原回答"}}}

    class Audit:
        def run_workflow(self, **_kwargs):
            calls["audit"] += 1
            return {"data": {"outputs": {"result": False, "reply": "修正回答"}}}

    monkeypatch.setattr(ai_gateway, "_main_client", lambda: Main())
    monkeypatch.setattr(ai_gateway, "_audit_client", lambda: Audit())
    result = ai_gateway.run_hikari_once_audited(
        user="u1", inputs={"user_query": "问题"}, original_input="问题"
    )
    assert result.content == "修正回答"
    assert result.passed is False
    assert result.audit_count == 2
    assert calls == {"main": 2, "audit": 2}


def test_gateway_stops_after_first_successful_audit(monkeypatch) -> None:
    calls = {"main": 0, "audit": 0}

    class Main:
        def run_workflow(self, **_kwargs):
            calls["main"] += 1
            return {"data": {"outputs": {"reply": "合格回答"}}}

    class Audit:
        def run_workflow(self, **_kwargs):
            calls["audit"] += 1
            return {"data": {"outputs": {"result": True, "reply": ""}}}

    monkeypatch.setattr(ai_gateway, "_main_client", lambda: Main())
    monkeypatch.setattr(ai_gateway, "_audit_client", lambda: Audit())
    result = ai_gateway.run_hikari_audited(
        user="u1", inputs={"user_query": "问题"}, original_input="问题"
    )
    assert result.content == "合格回答"
    assert result.audit_count == 1
    assert calls == {"main": 1, "audit": 1}


def test_memo_reminder_is_stored_as_utc(db: Session) -> None:
    local_time = datetime(2026, 7, 20, 8, tzinfo=timezone(timedelta(hours=8)))
    memo = accompany_service.create_memo(
        db, MemoCreate(tour_id=1, memo_text="带证件", reminder_time=local_time)
    )
    assert memo.reminder_time == datetime(2026, 7, 20, 0, tzinfo=None)


def test_earlier_insert_reassigns_initial_item(db: Session) -> None:
    later = accompany_service.create_itinerary(
        db, _item(datetime(2026, 7, 20, 10), datetime(2026, 7, 20, 11))
    )
    earlier = accompany_service.create_itinerary(
        db, _item(datetime(2026, 7, 20, 8), datetime(2026, 7, 20, 9))
    )
    db.refresh(later)
    assert earlier.is_initial is True
    assert later.is_initial is False
    assert later.reminder_time == datetime(2026, 7, 20, 8, 40)


def test_update_reorders_initial_and_validates_reminder(db: Session) -> None:
    first = accompany_service.create_itinerary(
        db, _item(datetime(2026, 7, 20, 8), datetime(2026, 7, 20, 9))
    )
    second = accompany_service.create_itinerary(
        db, _item(datetime(2026, 7, 20, 10), datetime(2026, 7, 20, 11))
    )
    from schemas.accompany import ItineraryUpdate

    accompany_service.update_itinerary(
        db,
        second.itinerary_id,
        ItineraryUpdate(
            start_time=datetime(2026, 7, 20, 6),
            end_time=datetime(2026, 7, 20, 7),
        ),
    )
    db.refresh(first)
    db.refresh(second)
    assert second.is_initial is True
    assert first.is_initial is False
    assert first.reminder_time == datetime(2026, 7, 20, 6, 40)


def test_accept_advice_inserts_structured_itinerary(db: Session) -> None:
    advice = AIAdvice(
        tour_id=1,
        advice_type="replan",
        advice_text="推荐替代行程",
        proposed_itinerary_json=(
            '[{"title":"咖啡馆休息","place_name":"Hikari Cafe",'
            '"start_time":"2026-07-20T14:00:00",'
            '"end_time":"2026-07-20T15:00:00","itinerary_type":"play"}]'
        ),
    )
    db.add(advice)
    db.commit()
    db.refresh(advice)

    result = accompany_service.act_on_advice(db, advice.advice_id, "accept", "u1", "")

    assert result.result == "accepted"
    inserted = db.query(ItineraryItem).one()
    assert inserted.title == "咖啡馆休息"
    assert inserted.is_initial is True


def test_revise_advice_stores_one_combined_input(db: Session, monkeypatch) -> None:
    old = AIAdvice(
        tour_id=1,
        advice_type="replan",
        input_text="景点临时闭馆",
        reason_text="景点临时闭馆",
        advice_text="建议改去博物馆",
    )
    db.add(old)
    db.commit()
    db.refresh(old)
    captured = {}

    def fake_generate(session, data):
        captured["reason"] = data.reason
        generated = AIAdvice(
            tour_id=data.tour_id,
            advice_type="replan",
            input_text=data.reason,
            reason_text=data.reason,
            advice_text="新版建议",
        )
        session.add(generated)
        session.commit()
        session.refresh(generated)
        return generated

    monkeypatch.setattr(accompany_service, "generate_advice", fake_generate)
    new = accompany_service.act_on_advice(
        db, old.advice_id, "revise", "u1", "不要安排博物馆"
    )

    assert captured["reason"] == (
        "原输入：景点临时闭馆\n原建议：建议改去博物馆\n用户新要求：不要安排博物馆"
    )
    assert new.input_text == captured["reason"]
    assert new.parent_advice_id == old.advice_id
