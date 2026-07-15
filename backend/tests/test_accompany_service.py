import json
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base
from models.accompany import (
    AIAdvice,
    ChatMessage,
    ChatSession,
    ItineraryItem,
    UserLocation,
)
from models.trip import Trip
from schemas.accompany import (
    AdviceGenerateRequest,
    ChatRequest,
    ItineraryCreate,
    LocationResponse,
    LocationUpdate,
    MemoCreate,
)
from services import accompany_service, ai_gateway
from services.ai_gateway import AuditedOutput


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(
        Trip(
            id=1,
            user_id=1,
            title="测试旅行",
            origin_city="杭州",
            destination_city="上海",
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 22),
            timezone="Asia/Shanghai",
            status="planned",
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _item(start: datetime, end: datetime, **kwargs) -> ItineraryCreate:
    return ItineraryCreate(
        trip_id=1,
        title=kwargs.pop("title", "行程"),
        place_name="地点",
        start_time=start,
        end_time=end,
        **kwargs,
    )


def _audited_output(
    content: str = "ok", main_response: dict | None = None
) -> AuditedOutput:
    return AuditedOutput(
        content=content,
        passed=True,
        reason=None,
        main_response=main_response or {},
        audit_response={},
        audit_count=1,
    )


def test_accompany_request_models_use_city_adcode_without_manual_contexts() -> None:
    assert "city_adcode" in AdviceGenerateRequest.model_fields
    assert "city_adcode" in ChatRequest.model_fields
    assert "city_adcode" in LocationUpdate.model_fields
    for model in (AdviceGenerateRequest, ChatRequest, LocationUpdate):
        assert "city" not in model.model_fields
        assert "location_context" not in model.model_fields
    assert "current_itinerary" not in AdviceGenerateRequest.model_fields
    assert "nearby_context" not in ChatRequest.model_fields


def test_user_flows_send_only_agent_owned_context(monkeypatch, db: Session) -> None:
    calls = []

    def fake_hikari(**kwargs):
        calls.append(kwargs)
        return _audited_output()

    monkeypatch.setattr(accompany_service, "run_hikari_once_audited", fake_hikari)

    accompany_service.generate_advice(
        db,
        AdviceGenerateRequest(
            trip_id=1,
            user_id=1,
            reason="The attraction is closed",
            city_adcode="310115",
            latitude=31.22,
            longitude=121.55,
            location_name="Pudong",
        ),
    )
    accompany_service.chat(
        db,
        ChatRequest(
            trip_id=1,
            user_id=1,
            message="Recommend somewhere nearby",
            city_adcode="310115",
            latitude=31.22,
            longitude=121.55,
            location_name="Pudong",
        ),
    )

    advice_keys = {
        "user_query",
        "trigger_type",
        "tour_id",
        "city_adcode",
        "latitude",
        "longitude",
        "location_name",
    }
    chat_keys = advice_keys | {"conversation_id", "conversation_history"}
    assert [set(call["inputs"]) for call in calls] == [advice_keys, chat_keys]
    assert all(call["inputs"]["city_adcode"] == "310115" for call in calls)
    stored = db.query(UserLocation).filter(UserLocation.user_id == 1).one()
    assert stored.city == "310115"
    assert LocationResponse.model_validate(stored).city_adcode == "310115"


def test_chat_uses_session_id_and_database_history(monkeypatch, db: Session) -> None:
    calls = []

    def fake_hikari(**kwargs):
        calls.append(kwargs)
        return _audited_output(content=f"<think>hidden</think>reply-{len(calls)}")

    monkeypatch.setattr(accompany_service, "run_hikari_once_audited", fake_hikari)

    first = accompany_service.chat(
        db, ChatRequest(trip_id=1, user_id=1, message="first question")
    )
    second = accompany_service.chat(
        db, ChatRequest(trip_id=1, user_id=1, message="second question")
    )

    assert first["session_id"] == second["session_id"]
    assert "conversation_id" not in first
    assert "conversation_id" not in second
    assert calls[0]["inputs"]["conversation_history"] == "[]"
    assert json.loads(calls[1]["inputs"]["conversation_history"]) == [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "reply-1"},
    ]
    assert calls[0]["inputs"]["conversation_id"] == str(first["session_id"])
    assert calls[1]["inputs"]["conversation_id"] == str(second["session_id"])

    session = db.query(ChatSession).one()
    assert session.session_id == first["session_id"]
    assert not hasattr(session, "conversation_id")
    assert [row.message_order for row in db.query(ChatMessage).all()] == [1, 2, 3, 4]


def _stored_history(db: Session, *contents: tuple[str, str]) -> ChatSession:
    session = ChatSession(trip_id=1, user_id=1, title="history test")
    db.add(session)
    db.flush()
    for order, (sender_type, content) in enumerate(contents, start=1):
        db.add(
            ChatMessage(
                session_id=session.session_id,
                sender_type=sender_type,
                content=content,
                message_order=order,
            )
        )
    db.commit()
    return session


def test_chat_history_strips_think_blocks_without_changing_stored_message(
    monkeypatch, db: Session
) -> None:
    monkeypatch.setenv("HIKARI_CHAT_HISTORY_MAX_MESSAGES", "10")
    monkeypatch.setenv("HIKARI_CHAT_HISTORY_MAX_CHARS", "1000")
    raw = "<think>private\nreasoning</think>visible<think>more</think> answer"
    session = _stored_history(db, ("user", "question"), ("ai", raw))

    history = accompany_service._chat_history(db, session.session_id)

    assert history == [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "visible answer"},
    ]
    stored_ai_message = (
        db.query(ChatMessage).filter(ChatMessage.sender_type == "ai").one()
    )
    assert stored_ai_message.content == raw


def test_chat_history_keeps_latest_configured_number_of_messages(
    monkeypatch, db: Session
) -> None:
    monkeypatch.setenv("HIKARI_CHAT_HISTORY_MAX_MESSAGES", "2")
    monkeypatch.setenv("HIKARI_CHAT_HISTORY_MAX_CHARS", "1000")
    session = _stored_history(
        db,
        ("user", "old question"),
        ("ai", "old answer"),
        ("user", "new question"),
        ("ai", "new answer"),
    )

    assert accompany_service._chat_history(db, session.session_id) == [
        {"role": "user", "content": "new question"},
        {"role": "assistant", "content": "new answer"},
    ]


def test_chat_history_respects_character_budget_from_newest_message(
    monkeypatch, db: Session
) -> None:
    monkeypatch.setenv("HIKARI_CHAT_HISTORY_MAX_MESSAGES", "10")
    monkeypatch.setenv("HIKARI_CHAT_HISTORY_MAX_CHARS", "8")
    session = _stored_history(db, ("user", "older"), ("ai", "abcdefghijk"))

    assert accompany_service._chat_history(db, session.session_id) == [
        {"role": "assistant", "content": "defghijk"}
    ]


def test_chat_history_rejects_invalid_context_limit(monkeypatch, db: Session) -> None:
    monkeypatch.setenv("HIKARI_CHAT_HISTORY_MAX_MESSAGES", "invalid")
    session = _stored_history(db, ("user", "question"))

    with pytest.raises(ValueError, match="HIKARI_CHAT_HISTORY_MAX_MESSAGES"):
        accompany_service._chat_history(db, session.session_id)


def test_list_chat_messages_reads_local_database_in_message_order(
    monkeypatch, db: Session
) -> None:
    monkeypatch.setattr(
        accompany_service,
        "run_hikari_once_audited",
        lambda **_kwargs: _audited_output("local reply"),
    )
    result = accompany_service.chat(
        db, ChatRequest(trip_id=1, user_id=1, message="local question")
    )

    messages = accompany_service.list_chat_messages(db, result["session_id"])

    assert [message.sender_type for message in messages] == ["user", "ai"]
    assert [message.content for message in messages] == [
        "local question",
        "local reply",
    ]
    history = accompany_service.chat_history(db, result["session_id"], 1)
    assert history["messages"] == messages
    with pytest.raises(LookupError, match="chat session not found"):
        accompany_service.chat_history(db, result["session_id"], 2)


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
            trip_id=1,
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
        db, MemoCreate(trip_id=1, memo_text="带证件", reminder_time=local_time)
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
        trip_id=1,
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

    result = accompany_service.act_on_advice(db, advice.advice_id, "accept", 1, "")

    assert result.result == "accepted"
    inserted = db.query(ItineraryItem).one()
    assert inserted.title == "咖啡馆休息"
    assert inserted.is_initial is True


def test_revise_advice_stores_one_combined_input(db: Session, monkeypatch) -> None:
    old = AIAdvice(
        trip_id=1,
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
            trip_id=data.trip_id,
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
        db, old.advice_id, "revise", 1, "不要安排博物馆"
    )

    assert captured["reason"] == (
        "原输入：景点临时闭馆\n原建议：建议改去博物馆\n用户新要求：不要安排博物馆"
    )
    assert new.input_text == captured["reason"]
    assert new.parent_advice_id == old.advice_id
