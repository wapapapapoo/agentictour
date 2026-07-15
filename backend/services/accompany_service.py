from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from crud import accompany as crud
from models.accompany import (
    AIAdvice,
    ChatMessage,
    ChatSession,
    ItineraryItem,
    Memo,
    UserLocation,
)
from models.user import User
from schemas.accompany import (
    AdviceGenerateRequest,
    ChatRequest,
    ItineraryCreate,
    ItineraryUpdate,
    LocationUpdate,
    MemoCreate,
    MemoUpdate,
)
from services.ai_gateway import run_hikari_once_audited

CHAT_HISTORY_MAX_MESSAGES_DEFAULT = 20
CHAT_HISTORY_MAX_CHARS_DEFAULT = 12000
THINK_BLOCK_RE = re.compile(
    r"<think\b[^>]*>.*?</think\s*>", re.IGNORECASE | re.DOTALL
)


def upsert_location(db: Session, data: LocationUpdate) -> UserLocation:
    row = db.query(UserLocation).filter(UserLocation.user_id == data.user_id).first()
    values = {
        "latitude": data.latitude,
        "longitude": data.longitude,
        "city": data.city_adcode or None,
        "place_name": data.place_name or None,
        "updated_at": datetime.now(UTC).replace(tzinfo=None),
    }
    if row is None:
        row = UserLocation(user_id=data.user_id, **values)
        db.add(row)
    else:
        crud.update(row, values)
    db.commit()
    db.refresh(row)
    return row


def _save_request_location(db: Session, data: Any) -> None:
    if data.latitude is None or data.longitude is None:
        return
    upsert_location(
        db,
        LocationUpdate(
            user_id=data.user_id,
            latitude=data.latitude,
            longitude=data.longitude,
            city_adcode=data.city_adcode,
            place_name=data.location_name,
        ),
    )


def create_memo(db: Session, data: MemoCreate) -> Memo:
    values = data.model_dump()
    if data.reminder_time is not None:
        values["reminder_time"] = _utc_naive(data.reminder_time)
    row = crud.create(db, Memo, values)
    db.commit()
    db.refresh(row)
    return row


def update_memo(db: Session, memo_id: int, data: MemoUpdate) -> Memo:
    row = crud.get_or_none(db, Memo, "memo_id", memo_id)
    if row is None:
        raise LookupError("memo not found")
    values = data.model_dump(exclude_unset=True)
    if values.get("reminder_time") is not None:
        values["reminder_time"] = _utc_naive(values["reminder_time"])
    crud.update(row, values)
    db.commit()
    db.refresh(row)
    return row


def delete_memo(db: Session, memo_id: int) -> None:
    row = crud.get_or_none(db, Memo, "memo_id", memo_id)
    if row is None:
        raise LookupError("memo not found")
    crud.delete(db, row)
    db.commit()


def _previous_itinerary(db: Session, data: ItineraryCreate) -> ItineraryItem | None:
    return (
        db.query(ItineraryItem)
        .filter(
            ItineraryItem.trip_id == data.trip_id,
            ItineraryItem.end_time <= data.start_time,
        )
        .order_by(ItineraryItem.end_time.desc())
        .first()
    )


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _default_from_previous(previous: ItineraryItem) -> datetime:
    duration = previous.end_time - previous.start_time
    if duration >= timedelta(minutes=20):
        return previous.end_time - timedelta(minutes=20)
    if duration >= timedelta(minutes=5):
        return previous.end_time - timedelta(minutes=5)
    return previous.end_time


def _default_play_reminder(db: Session, data: ItineraryCreate) -> datetime:
    previous = _previous_itinerary(db, data)
    if previous is None:
        return data.start_time
    candidate = _default_from_previous(previous)
    return min(max(candidate, previous.start_time), previous.end_time)


def _recalculate_day(db: Session, trip_id: int, day: datetime) -> None:
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    items = (
        db.query(ItineraryItem)
        .filter(
            ItineraryItem.trip_id == trip_id,
            ItineraryItem.start_time >= day_start,
            ItineraryItem.start_time < day_end,
        )
        .order_by(ItineraryItem.start_time, ItineraryItem.itinerary_id)
        .all()
    )
    for index, item in enumerate(items):
        was_initial = bool(item.is_initial)
        item.is_initial = index == 0
        if index == 0:
            item.reminder_time = item.start_time
            continue
        previous = items[index - 1]
        if was_initial or item.reminder_time is None:
            item.reminder_time = _default_from_previous(previous)
        if not (previous.start_time <= item.reminder_time <= previous.end_time):
            raise ValueError(
                "reminder_time must be within the previous itinerary start and end time"
            )


def create_itinerary(
    db: Session, data: ItineraryCreate, *, commit: bool = True
) -> ItineraryItem:
    values = data.model_dump()
    values["start_time"] = _utc_naive(data.start_time)
    values["end_time"] = _utc_naive(data.end_time)
    if data.reminder_time is not None:
        values["reminder_time"] = _utc_naive(data.reminder_time)
    data = ItineraryCreate.model_validate(values)
    day_start = data.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    day_has_item = (
        db.query(ItineraryItem)
        .filter(
            ItineraryItem.trip_id == data.trip_id,
            ItineraryItem.start_time >= day_start,
            ItineraryItem.start_time < day_end,
        )
        .first()
        is not None
    )
    if data.is_initial or not day_has_item:
        values["is_initial"] = True
        values["reminder_time"] = data.start_time
    elif data.itinerary_type == "play" and data.reminder_time is None:
        values["reminder_time"] = _default_play_reminder(db, data)
    previous = _previous_itinerary(db, data)
    if (
        not values["is_initial"]
        and previous
        and values["reminder_time"] is not None
        and not (previous.start_time <= values["reminder_time"] <= previous.end_time)
    ):
        raise ValueError(
            "reminder_time must be within the previous itinerary start and end time"
        )
    row = crud.create(db, ItineraryItem, values)
    _recalculate_day(db, data.trip_id, data.start_time)
    if commit:
        db.commit()
        db.refresh(row)
    return row


def update_itinerary(
    db: Session, itinerary_id: int, data: ItineraryUpdate
) -> ItineraryItem:
    row = crud.get_or_none(db, ItineraryItem, "itinerary_id", itinerary_id)
    if row is None:
        raise LookupError("itinerary not found")
    values = data.model_dump(exclude_unset=True)
    for field in ("start_time", "end_time", "reminder_time"):
        if values.get(field) is not None:
            values[field] = _utc_naive(values[field])
    old_day = row.start_time
    start, end = (
        values.get("start_time", row.start_time),
        values.get("end_time", row.end_time),
    )
    kind = values.get("itinerary_type", row.itinerary_type)
    reminder = values.get("reminder_time", row.reminder_time)
    initial = values.get("is_initial", row.is_initial)
    if end <= start:
        raise ValueError("end_time must be later than start_time")
    if initial:
        values["reminder_time"] = start
    elif kind == "transit" and reminder is None:
        raise ValueError("transit itinerary requires reminder_time")
    crud.update(row, values)
    db.flush()
    _recalculate_day(db, row.trip_id, old_day)
    if row.start_time.date() != old_day.date():
        _recalculate_day(db, row.trip_id, row.start_time)
    db.commit()
    db.refresh(row)
    return row


def delete_itinerary(db: Session, itinerary_id: int) -> None:
    row = crud.get_or_none(db, ItineraryItem, "itinerary_id", itinerary_id)
    if row is None:
        raise LookupError("itinerary not found")
    day, trip_id = row.start_time, row.trip_id
    crud.delete(db, row)
    db.flush()
    _recalculate_day(db, trip_id, day)
    db.commit()


def _json_or_none(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def advice_response(row: AIAdvice) -> dict[str, Any]:
    return {
        "advice_id": row.advice_id,
        "trip_id": row.trip_id,
        "advice_type": row.advice_type,
        "parent_advice_id": row.parent_advice_id,
        "input_text": row.input_text,
        "reason_text": row.reason_text,
        "advice_text": row.advice_text,
        "proposed_itinerary": _json_or_none(row.proposed_itinerary_json)
        if row.proposed_itinerary_json
        else None,
        "result": row.result,
        "audit_status": row.audit_status,
        "audit_reason": row.audit_reason,
        "generation_stopped": row.generation_stopped,
        "created_at": row.created_at,
    }


def _get_username(db: Session, user_id: int) -> str:
    user = db.query(User).filter(User.user_id == user_id).first()
    return user.username if user else str(user_id)


def generate_advice(db: Session, data: AdviceGenerateRequest) -> AIAdvice:
    _save_request_location(db, data)
    original = data.reason + (
        f"；补充要求：{data.additional_requirement}"
        if data.additional_requirement
        else ""
    )
    audited = run_hikari_once_audited(
        user=_get_username(db, data.user_id),
        original_input=original,
        inputs={
            "user_query": original,
            "trigger_type": "user_accident",
            "tour_id": data.trip_id,
            "city_adcode": data.city_adcode,
            "latitude": data.latitude if data.latitude is not None else "",
            "longitude": data.longitude if data.longitude is not None else "",
            "location_name": data.location_name,
        },
    )
    proposed = audited.structured_output
    if isinstance(proposed, str):
        proposed = _json_or_none(proposed)
    if proposed is None:
        proposed = _json_or_none(audited.content)
    row = crud.create(
        db,
        AIAdvice,
        {
            "trip_id": data.trip_id,
            "advice_type": "replan",
            "input_text": original,
            "reason_text": data.reason,
            "advice_text": audited.content,
            "proposed_itinerary_json": json.dumps(proposed, ensure_ascii=False)
            if proposed
            else None,
            "audit_status": "pass" if audited.passed else "failed",
            "audit_reason": audited.reason,
        },
    )
    db.commit()
    db.refresh(row)
    return row


def act_on_advice(
    db: Session, advice_id: int, action: str, user_id: int, additional: str
) -> AIAdvice:
    row = crud.get_or_none(db, AIAdvice, "advice_id", advice_id)
    if row is None:
        raise LookupError("advice not found")
    if row.generation_stopped and action == "revise":
        raise ValueError("advice generation has been stopped")
    if action == "accept":
        proposed = _json_or_none(row.proposed_itinerary_json or "")
        if isinstance(proposed, dict):
            proposed = (
                proposed.get("items")
                or proposed.get("itinerary_items")
                or proposed.get("itinerary")
            )
        if not isinstance(proposed, list) or not proposed:
            raise ValueError("advice has no structured itinerary items to accept")
        try:
            for item in proposed:
                if not isinstance(item, dict):
                    raise ValueError("each proposed itinerary item must be an object")
                payload = dict(item)
                payload["trip_id"] = row.trip_id
                create_itinerary(
                    db, ItineraryCreate.model_validate(payload), commit=False
                )
        except Exception:
            db.rollback()
            raise
        row.result = "accepted"
    elif action == "reject":
        row.result, row.generation_stopped = "rejected", True
    else:
        row.result = "revising"
        combined_input = (
            f"原输入：{row.input_text or row.reason_text or ''}\n"
            f"原建议：{row.advice_text}\n"
            f"用户新要求：{additional}"
        )
        generated = generate_advice(
            db,
            AdviceGenerateRequest(
                trip_id=row.trip_id,
                user_id=user_id,
                reason=combined_input,
            ),
        )
        generated.parent_advice_id = row.advice_id
        generated.reason_text = None
        db.commit()
        db.refresh(generated)
        return generated
    db.commit()
    db.refresh(row)
    return row


def chat(db: Session, data: ChatRequest) -> dict[str, Any]:
    _save_request_location(db, data)
    session = db.query(ChatSession).filter(ChatSession.trip_id == data.trip_id).first()
    if session is None:
        session = crud.create(
            db,
            ChatSession,
            {
                "trip_id": data.trip_id,
                "user_id": data.user_id,
                "title": data.message[:100],
            },
        )
    history = _chat_history(db, session.session_id)
    order = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.session_id)
        .count()
    )
    user_msg = crud.create(
        db,
        ChatMessage,
        {
            "session_id": session.session_id,
            "sender_type": "user",
            "content": data.message,
            "message_order": order + 1,
        },
    )
    audited = run_hikari_once_audited(
        user=_get_username(db, data.user_id),
        original_input=data.message,
        inputs={
            "user_query": data.message,
            "trigger_type": "user_input",
            "tour_id": data.trip_id,
            "conversation_id": str(session.session_id),
            "conversation_history": json.dumps(history, ensure_ascii=False),
            "city_adcode": data.city_adcode,
            "latitude": data.latitude if data.latitude is not None else "",
            "longitude": data.longitude if data.longitude is not None else "",
            "location_name": data.location_name,
        },
    )
    ai_msg = crud.create(
        db,
        ChatMessage,
        {
            "session_id": session.session_id,
            "sender_type": "ai",
            "content": audited.content,
            "message_order": order + 2,
            "audit_status": "pass" if audited.passed else "failed",
            "audit_reason": audited.reason,
        },
    )
    session.last_message_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(user_msg)
    db.refresh(ai_msg)
    return {
        "session_id": session.session_id,
        "user_message_id": user_msg.message_id,
        "ai_message_id": ai_msg.message_id,
        "reply": ai_msg.content,
        "audit_status": ai_msg.audit_status,
        "audit_reason": ai_msg.audit_reason,
    }


def _history_limit(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _history_content(message: ChatMessage) -> str:
    content = message.content
    if message.sender_type == "ai":
        content = THINK_BLOCK_RE.sub("", content)
    return content.strip()


def _chat_history(db: Session, session_id: int) -> list[dict[str, str]]:
    max_messages = _history_limit(
        "HIKARI_CHAT_HISTORY_MAX_MESSAGES", CHAT_HISTORY_MAX_MESSAGES_DEFAULT
    )
    max_chars = _history_limit(
        "HIKARI_CHAT_HISTORY_MAX_CHARS", CHAT_HISTORY_MAX_CHARS_DEFAULT
    )
    if max_messages == 0 or max_chars == 0:
        return []
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.message_order.desc(), ChatMessage.message_id.desc())
        .limit(max_messages)
        .all()
    )
    role_by_sender = {"ai": "assistant", "user": "user", "system": "system"}
    history: list[dict[str, str]] = []
    remaining_chars = max_chars
    for message in messages:
        content = _history_content(message)
        if not content:
            continue
        if len(content) > remaining_chars:
            content = content[-remaining_chars:]
        history.append(
            {
                "role": role_by_sender.get(message.sender_type, message.sender_type),
                "content": content,
            }
        )
        remaining_chars -= len(content)
        if remaining_chars == 0:
            break
    history.reverse()
    return history


def list_chat_messages(db: Session, session_id: int) -> list[ChatMessage]:
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if session is None:
        raise LookupError("chat session not found")
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.session_id)
        .order_by(ChatMessage.message_order, ChatMessage.message_id)
        .all()
    )


def chat_history(db: Session, session_id: int, user_id: int) -> dict[str, Any]:
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user_id,
        )
        .first()
    )
    if session is None:
        raise LookupError("chat session not found")
    return {
        "session_id": session.session_id,
        "trip_id": session.trip_id,
        "user_id": session.user_id,
        "title": session.title,
        "status": session.status,
        "messages": list_chat_messages(db, session_id),
    }
