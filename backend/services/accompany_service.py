from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime, time, timedelta, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func
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
from models.trip import Trip
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
from services.ai_gateway import AuditRejectedError, run_hikari_once_audited
from utils.trip_time import trip_local_iso, trip_route_context, trip_time_context

logger = logging.getLogger(__name__)

CHAT_HISTORY_MAX_MESSAGES_DEFAULT = 20
CHAT_HISTORY_MAX_CHARS_DEFAULT = 12000
CHANGE_PENDING_STATUS = "change_pending"
THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think\s*>", re.IGNORECASE | re.DOTALL)


def _trip_context(db: Session, trip_id: int) -> str:
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        return "{}"
    return json.dumps(
        {
            "trip_id": trip.id,
            "title": trip.title,
            "origin_city": trip.origin_city,
            "destination_city": trip.destination_city,
            **trip_route_context(trip.origin_city, trip.destination_city),
            "start_date": trip.start_date.isoformat(),
            "end_date": trip.end_date.isoformat(),
            **trip_time_context(trip.timezone),
            "status": trip.status,
        },
        ensure_ascii=False,
    )


def authoritative_itinerary_context(db: Session, trip_id: int) -> str:
    """Serialize the current DB state separately from conversational history."""
    sync_itinerary_statuses(db, trip_id=trip_id, commit=False)
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        return "{}"
    now = datetime.now(UTC).replace(tzinfo=None)

    def serialize(row: ItineraryItem) -> dict[str, Any]:
        if row.status == "cancelled":
            lifecycle = "cancelled"
        elif row.status == "done":
            lifecycle = "completed"
        elif row.status == CHANGE_PENDING_STATUS:
            lifecycle = CHANGE_PENDING_STATUS
        elif row.start_time <= now < row.end_time:
            lifecycle = "ongoing"
        else:
            lifecycle = "upcoming"
        return {
            "itinerary_id": row.itinerary_id,
            "title": row.title,
            "place_name": row.place_name,
            "start_time": trip_local_iso(row.start_time, trip.timezone),
            "end_time": trip_local_iso(row.end_time, trip.timezone),
            "itinerary_type": row.itinerary_type,
            "reminder_time": trip_local_iso(row.reminder_time, trip.timezone)
            if row.reminder_time
            else None,
            "is_initial": row.is_initial,
            "status": row.status,
            "lifecycle_status": lifecycle,
        }

    rows = crud.list_itineraries(db, trip_id)
    items = [serialize(row) for row in rows]
    payload = {
        "source": "agentictour_backend_database",
        "authority": "current_database_state",
        "trip_id": trip_id,
        "timezone": trip.timezone,
        "generated_at": trip_time_context(trip.timezone)["current_time_local"],
        "absence_means_deleted": True,
        "active_items": [item for item in items if item["status"] == "pending"],
        "change_pending_items": [
            item for item in items if item["status"] == CHANGE_PENDING_STATUS
        ],
        "completed_items": [item for item in items if item["status"] == "done"],
        "cancelled_items": [item for item in items if item["status"] == "cancelled"],
    }
    return json.dumps(payload, ensure_ascii=False)


def upsert_location(db: Session, data: LocationUpdate) -> UserLocation:
    resolved: dict[str, Any] = {}
    try:
        from services.amap_location_service import resolve_browser_location

        resolved = resolve_browser_location(data.latitude, data.longitude)
    except Exception as exc:
        logger.warning("location enrichment failed for user %s: %s", data.user_id, exc)
    row = db.query(UserLocation).filter(UserLocation.user_id == data.user_id).first()
    values = {
        "latitude": resolved.get("latitude", data.latitude),
        "longitude": resolved.get("longitude", data.longitude),
        "city": resolved.get("city_adcode") or data.city_adcode or None,
        "place_name": resolved.get("place_name") or data.place_name or None,
        "location_context": json.dumps(
            resolved.get("location_context")
            or {
                "provider": "browser",
                "coordinate_system": "wgs84",
                "resolution_status": "unavailable",
            },
            ensure_ascii=False,
        ),
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


def get_location(db: Session, user_id: int) -> UserLocation | None:
    return db.query(UserLocation).filter(UserLocation.user_id == user_id).first()


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
    _validate_reminder_in_trip(db, data.trip_id, values.get("reminder_time"))
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
    _validate_reminder_in_trip(
        db, row.trip_id, values.get("reminder_time", row.reminder_time)
    )
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
            ItineraryItem.status != "cancelled",
        )
        .order_by(ItineraryItem.end_time.desc())
        .first()
    )


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _trip_utc_window(trip: Trip) -> tuple[datetime, datetime]:
    try:
        resolved_tz: tzinfo = ZoneInfo(trip.timezone or "Asia/Shanghai")
    except ZoneInfoNotFoundError:
        resolved_tz = timezone(timedelta(hours=8))
    start = datetime.combine(trip.start_date, time.min, tzinfo=resolved_tz)
    end = datetime.combine(
        trip.end_date + timedelta(days=1), time.min, tzinfo=resolved_tz
    )
    return _utc_naive(start), _utc_naive(end)


def _validate_reminder_in_trip(
    db: Session, trip_id: int, reminder_time: datetime | None
) -> None:
    if reminder_time is None:
        return
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise ValueError("trip not found")
    start, end = _trip_utc_window(trip)
    reminder = _utc_naive(reminder_time)
    if reminder < start or reminder >= end:
        raise ValueError("reminder_time must be within the trip date range")


def _validate_itinerary_in_trip(
    db: Session, trip_id: int, start_time: datetime, end_time: datetime
) -> None:
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise ValueError("trip not found")
    trip_start, trip_end = _trip_utc_window(trip)
    start = _utc_naive(start_time)
    end = _utc_naive(end_time)
    if start < trip_start or end > trip_end:
        raise ValueError("itinerary time must be within the trip date range")


def sync_itinerary_statuses(
    db: Session,
    *,
    trip_id: int | None = None,
    now: datetime | None = None,
    commit: bool = False,
) -> int:
    effective_now = _utc_naive(now or datetime.now(UTC))
    query = db.query(ItineraryItem).filter(
        ItineraryItem.status == "pending",
        ItineraryItem.end_time <= effective_now,
    )
    if trip_id is not None:
        query = query.filter(ItineraryItem.trip_id == trip_id)
    rows = query.all()
    for row in rows:
        row.status = "done"
    if rows:
        if commit:
            db.commit()
        else:
            db.flush()
    return len(rows)


def list_itineraries(db: Session, trip_id: int) -> list[ItineraryItem]:
    sync_itinerary_statuses(db, trip_id=trip_id, commit=True)
    return crud.list_itineraries(db, trip_id)


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
            ItineraryItem.status != "cancelled",
        )
        .order_by(ItineraryItem.start_time, ItineraryItem.itinerary_id)
        .all()
    )
    for index, item in enumerate(items):
        was_initial = bool(item.is_initial)
        item.is_initial = index == 0
        if index == 0:
            if item.reminder_time is None:
                item.reminder_time = item.start_time
            if item.reminder_time > item.start_time:
                raise ValueError(
                    "reminder_time must not be later than itinerary start_time"
                )
            _validate_reminder_in_trip(db, trip_id, item.reminder_time)
            continue
        previous = items[index - 1]
        if was_initial or item.reminder_time is None:
            item.reminder_time = _default_from_previous(previous)
        if item.reminder_time > item.start_time:
            raise ValueError(
                "reminder_time must not be later than itinerary start_time"
            )
        _validate_reminder_in_trip(db, trip_id, item.reminder_time)


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
            ItineraryItem.status != "cancelled",
        )
        .first()
        is not None
    )
    if data.is_initial or not day_has_item:
        values["is_initial"] = True
        if values["reminder_time"] is None:
            values["reminder_time"] = data.start_time
    elif data.itinerary_type == "play" and data.reminder_time is None:
        values["reminder_time"] = _default_play_reminder(db, data)
    if (
        values["reminder_time"] is not None
        and values["reminder_time"] > data.start_time
    ):
        raise ValueError("reminder_time must not be later than itinerary start_time")
    _validate_itinerary_in_trip(db, data.trip_id, data.start_time, data.end_time)
    _validate_reminder_in_trip(db, data.trip_id, values["reminder_time"])
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
    reminder_was_supplied = "reminder_time" in values
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
    if initial and reminder is None:
        values["reminder_time"] = start
        reminder = start
    elif kind == "transit" and reminder is None:
        raise ValueError("transit itinerary requires reminder_time")
    if reminder is not None and reminder > start:
        if "start_time" in values and not reminder_was_supplied:
            values["reminder_time"] = start
            reminder = start
        else:
            raise ValueError(
                "reminder_time must not be later than itinerary start_time"
            )
    _validate_itinerary_in_trip(db, row.trip_id, start, end)
    _validate_reminder_in_trip(
        db, row.trip_id, values.get("reminder_time", row.reminder_time)
    )
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


def _stored_location_inputs(db: Session, user_id: int) -> dict[str, str | float]:
    location = db.query(UserLocation).filter(UserLocation.user_id == user_id).first()
    if location is None:
        return {
            "city_adcode": "",
            "latitude": "",
            "longitude": "",
            "location_name": "",
        }
    return {
        "city_adcode": location.city or "",
        "latitude": location.latitude,
        "longitude": location.longitude,
        "location_name": location.place_name or "",
    }


def _advice_revision_context(db: Session, row: AIAdvice) -> str:
    """Build a bounded, oldest-to-newest recommendation history for the agent."""
    max_versions = _history_limit("HIKARI_ADVICE_HISTORY_MAX_VERSIONS", 10)
    max_chars = _history_limit("HIKARI_ADVICE_HISTORY_MAX_CHARS", 12000)
    chain: list[AIAdvice] = []
    seen: set[int] = set()
    current: AIAdvice | None = row

    while current is not None and len(chain) < max_versions:
        if current.advice_id in seen:
            break
        seen.add(current.advice_id)
        chain.append(current)
        if current.parent_advice_id is None:
            break
        current = (
            db.query(AIAdvice)
            .filter(
                AIAdvice.advice_id == current.parent_advice_id,
                AIAdvice.trip_id == row.trip_id,
            )
            .first()
        )

    entries: list[str] = []
    remaining = max_chars
    for advice in chain:
        payload = {
            "advice_id": advice.advice_id,
            "parent_advice_id": advice.parent_advice_id,
            "advice_type": advice.advice_type,
            "input_text": advice.input_text,
            "reason_text": advice.reason_text,
            "advice_text": advice.advice_text,
            "proposed_itinerary": _json_or_none(advice.proposed_itinerary_json or ""),
            "result": advice.result,
        }
        serialized = json.dumps(payload, ensure_ascii=False, default=str)
        if len(serialized) > remaining:
            if not entries:
                entries.append(serialized[:remaining])
            break
        entries.append(serialized)
        remaining -= len(serialized)

    entries.reverse()
    return "\n".join(entries)


def _workflow_outputs(audited: Any) -> dict[str, Any]:
    response = getattr(audited, "main_response", {})
    if not isinstance(response, dict):
        return {}
    outputs = response.get("data", {}).get("outputs", {})
    return outputs if isinstance(outputs, dict) else {}


def _replan_payload(audited: Any) -> dict[str, Any] | None:
    outputs = _workflow_outputs(audited)
    structured = audited.structured_output
    raw_items = outputs.get("itinerary_items", structured)
    raw_cancelled = outputs.get("cancelled_itinerary_ids", [])
    if isinstance(structured, dict):
        raw_items = outputs.get("itinerary_items", structured.get("itinerary_items"))
        raw_cancelled = outputs.get(
            "cancelled_itinerary_ids",
            structured.get("cancelled_itinerary_ids", []),
        )
    if isinstance(raw_items, str):
        raw_items = _json_or_none(raw_items)
    if isinstance(raw_cancelled, str):
        raw_cancelled = _json_or_none(raw_cancelled)

    parsed_content = _json_or_none(audited.content)
    if isinstance(parsed_content, dict):
        if raw_items is None:
            raw_items = parsed_content.get("itinerary_items")
        if not raw_cancelled:
            raw_cancelled = parsed_content.get("cancelled_itinerary_ids", [])
    elif raw_items is None and isinstance(parsed_content, list):
        raw_items = parsed_content

    items = raw_items if isinstance(raw_items, list) else []
    cancelled = raw_cancelled if isinstance(raw_cancelled, list) else []
    if not items and not cancelled:
        return None
    return {
        "cancelled_itinerary_ids": cancelled,
        "itinerary_items": items,
    }


def _pending_scope_ids(
    db: Session, trip_id: int, requested_ids: list[int] | None
) -> list[int]:
    return _scope_ids(db, trip_id, requested_ids, ("pending",))


def _scope_ids(
    db: Session,
    trip_id: int,
    requested_ids: list[int] | None,
    statuses: tuple[str, ...],
) -> list[int]:
    selected = sorted(
        {
            value
            for value in (requested_ids or [])
            if isinstance(value, int) and not isinstance(value, bool)
        }
    )
    if not selected:
        return []
    return sorted(
        row[0]
        for row in db.query(ItineraryItem.itinerary_id)
        .filter(
            ItineraryItem.trip_id == trip_id,
            ItineraryItem.status.in_(statuses),
            ItineraryItem.itinerary_id.in_(selected),
        )
        .all()
    )


def _eligible_selected_ids(
    db: Session,
    trip_id: int,
    requested_ids: list[int] | None,
    *,
    change_pending_ids: list[int] | None = None,
) -> list[int]:
    raw = requested_ids or []
    if any(not isinstance(value, int) or isinstance(value, bool) for value in raw):
        raise ValueError("selected itinerary ids must be integers")
    requested = sorted(set(raw))
    allowed_change = set(change_pending_ids or [])
    rows = (
        db.query(ItineraryItem.itinerary_id, ItineraryItem.status)
        .filter(
            ItineraryItem.trip_id == trip_id,
            ItineraryItem.itinerary_id.in_(requested),
        )
        .all()
    )
    eligible = sorted(
        itinerary_id
        for itinerary_id, status in rows
        if status == "pending"
        or (status == CHANGE_PENDING_STATUS and itinerary_id in allowed_change)
    )
    if eligible != requested:
        raise ValueError(
            "selected itineraries must be pending items from the current trip; "
            "only system-locked items may be change_pending"
        )
    return eligible


def _advice_scope_ids(row: AIAdvice) -> tuple[list[int], list[int]]:
    proposed = _json_or_none(row.proposed_itinerary_json or "")
    if not isinstance(proposed, dict):
        return [], []

    def ids(key: str) -> list[int]:
        values = proposed.get(key, [])
        if not isinstance(values, list):
            return []
        return sorted(
            {
                value
                for value in values
                if isinstance(value, int) and not isinstance(value, bool)
            }
        )

    locked = ids("locked_itinerary_ids") or ids("conflicting_itinerary_ids")
    selected = ids("selected_itinerary_ids") or ids("cancelled_itinerary_ids")
    return sorted(set(selected) | set(locked)), locked


def _attach_and_validate_replan_scope(
    proposed: dict[str, Any] | None,
    selected_ids: list[int],
    locked_ids: list[int],
    *,
    trip: Trip,
    original: str,
    location_name: str,
    has_pending_transit: bool,
) -> dict[str, Any] | None:
    if proposed is None:
        return None
    cancelled = proposed.get("cancelled_itinerary_ids", [])
    cancelled_ids = {
        value
        for value in cancelled
        if isinstance(value, int) and not isinstance(value, bool)
    }
    unselected = cancelled_ids - set(selected_ids)
    if unselected:
        raise AuditRejectedError(
            "候选方案试图修改未勾选的日程，请重新选择冲突项后再生成。"
        )
    proposed["selected_itinerary_ids"] = selected_ids
    proposed["locked_itinerary_ids"] = locked_ids
    _validate_cross_city_candidate(
        proposed,
        trip=trip,
        original=original,
        location_name=location_name,
        has_pending_transit=has_pending_transit,
    )
    return proposed


def _city_key(value: str) -> str:
    return re.sub(r"[\s省市区县]+$", "", value.strip())


def _validate_cross_city_candidate(
    proposed: dict[str, Any],
    *,
    trip: Trip,
    original: str,
    location_name: str,
    has_pending_transit: bool,
) -> None:
    """Reject a passed-but-directionally-wrong generic future-day candidate."""
    if _city_key(trip.origin_city) == _city_key(trip.destination_city):
        return
    if not re.search(r"明天|第二天|次日|后天", original):
        return
    origin = re.escape(_city_key(trip.origin_city))
    if re.search(rf"(?:留在|待在|在){origin}.*(?:游|玩|逛|安排)", original):
        return
    items = proposed.get("itinerary_items", [])
    if not isinstance(items, list):
        return
    destination = _city_key(trip.destination_city)
    for item in items:
        if not isinstance(item, dict) or item.get("itinerary_type") != "play":
            continue
        city_name = item.get("city_name")
        if not isinstance(city_name, str) or not city_name.strip():
            raise AuditRejectedError(
                "跨城候选日程缺少 city_name，无法确认游览活动是否位于旅游目的地。"
            )
        if _city_key(city_name) != destination:
            raise AuditRejectedError(
                f"候选方案把游览活动安排在 {city_name}，但当前旅游目的地是 "
                f"{trip.destination_city}。"
            )
    user_at_origin = _city_key(trip.origin_city) in _city_key(location_name)
    if (
        user_at_origin
        and any(
            isinstance(item, dict) and item.get("itinerary_type") == "play"
            for item in items
        )
        and not any(
            isinstance(item, dict) and item.get("itinerary_type") == "transit"
            for item in items
        )
        and not has_pending_transit
    ):
        raise AuditRejectedError(
            "用户仍在出发城市，跨城候选方案必须先提供到旅游目的地的交通日程。"
        )


def _generate_replan(
    db: Session,
    *,
    trip_id: int,
    user_id: int,
    original: str,
    reason: str,
    trigger_type: str,
    location_inputs: dict[str, Any],
    selected_itinerary_ids: list[int] | None = None,
    locked_itinerary_ids: list[int] | None = None,
    parent_advice_id: int | None = None,
    commit: bool = True,
) -> AIAdvice:
    sync_itinerary_statuses(db, trip_id=trip_id, commit=False)
    locked_request = sorted(set(locked_itinerary_ids or []))
    locked_ids = _eligible_selected_ids(
        db,
        trip_id,
        locked_request,
        change_pending_ids=locked_request,
    )
    selected_ids = _eligible_selected_ids(
        db,
        trip_id,
        sorted(set(selected_itinerary_ids or []) | set(locked_ids)),
        change_pending_ids=locked_ids,
    )
    audited = run_hikari_once_audited(
        user=_get_username(db, user_id),
        original_input=original,
        inputs={
            "user_query": original,
            "trigger_type": trigger_type,
            "tour_id": trip_id,
            "trip_context": _trip_context(db, trip_id),
            "backend_itinerary_context": authoritative_itinerary_context(db, trip_id),
            "selected_itinerary_ids": json.dumps(selected_ids),
            "locked_itinerary_ids": json.dumps(locked_ids),
            **location_inputs,
        },
    )
    if not audited.passed:
        raise AuditRejectedError(audited.reason)
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise LookupError("trip not found")
    proposed = _attach_and_validate_replan_scope(
        _replan_payload(audited),
        selected_ids,
        locked_ids,
        trip=trip,
        original=original,
        location_name=str(location_inputs.get("location_name") or ""),
        has_pending_transit=db.query(ItineraryItem.itinerary_id)
        .filter(
            ItineraryItem.trip_id == trip_id,
            ItineraryItem.itinerary_type == "transit",
            ItineraryItem.status == "pending",
        )
        .first()
        is not None,
    )
    row = crud.create(
        db,
        AIAdvice,
        {
            "trip_id": trip_id,
            "advice_type": "replan",
            "parent_advice_id": parent_advice_id,
            "input_text": original,
            "reason_text": reason,
            "advice_text": audited.content,
            "proposed_itinerary_json": json.dumps(proposed, ensure_ascii=False)
            if proposed
            else None,
            "audit_status": "pass",
            "audit_reason": None,
        },
    )
    if commit:
        db.commit()
        db.refresh(row)
    return row


def generate_advice(db: Session, data: AdviceGenerateRequest) -> AIAdvice:
    _save_request_location(db, data)
    original = data.reason + (
        f"；补充要求：{data.additional_requirement}"
        if data.additional_requirement
        else ""
    )
    return _generate_replan(
        db,
        trip_id=data.trip_id,
        user_id=data.user_id,
        original=original,
        reason=data.reason,
        trigger_type="user_accident",
        selected_itinerary_ids=data.selected_itinerary_ids,
        location_inputs={
            "city_adcode": data.city_adcode,
            "latitude": data.latitude if data.latitude is not None else "",
            "longitude": data.longitude if data.longitude is not None else "",
            "location_name": data.location_name,
        },
    )


def _apply_replan(db: Session, row: AIAdvice) -> None:
    if row.audit_status == "failed":
        raise ValueError("failed-audit itinerary changes cannot be applied")
    proposed = _json_or_none(row.proposed_itinerary_json or "")
    if isinstance(proposed, list):
        cancelled_ids: list[Any] = []
        new_items = proposed
    elif isinstance(proposed, dict):
        cancelled_ids = proposed.get("cancelled_itinerary_ids", [])
        new_items = (
            proposed.get("itinerary_items")
            or proposed.get("items")
            or proposed.get("itinerary")
            or []
        )
    else:
        raise ValueError("advice has no structured itinerary changes to accept")
    if not isinstance(cancelled_ids, list) or not isinstance(new_items, list):
        raise ValueError("structured itinerary changes have invalid list fields")
    if not cancelled_ids and not new_items:
        raise ValueError("advice has no structured itinerary changes to accept")

    normalized_ids: list[int] = []
    for itinerary_id in cancelled_ids:
        if isinstance(itinerary_id, bool):
            raise ValueError("cancelled itinerary ids must be integers")
        try:
            normalized_ids.append(int(itinerary_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("cancelled itinerary ids must be integers") from exc
    if len(set(normalized_ids)) != len(normalized_ids):
        raise ValueError("cancelled itinerary ids must not contain duplicates")

    cancelled_days: list[datetime] = []
    if normalized_ids:
        rows = (
            db.query(ItineraryItem)
            .filter(
                ItineraryItem.trip_id == row.trip_id,
                ItineraryItem.itinerary_id.in_(normalized_ids),
            )
            .all()
        )
        if len(rows) != len(normalized_ids):
            raise ValueError("some cancelled itineraries do not belong to this trip")
        for itinerary in rows:
            if itinerary.status not in ("pending", CHANGE_PENDING_STATUS):
                raise ValueError(
                    "only pending or change_pending itineraries can be "
                    "cancelled by replan"
                )
            itinerary.status = "cancelled"
            cancelled_days.append(itinerary.start_time)
        db.flush()

    for item in new_items:
        if not isinstance(item, dict):
            raise ValueError("each proposed itinerary item must be an object")
        payload = dict(item)
        payload["trip_id"] = row.trip_id
        create_itinerary(db, ItineraryCreate.model_validate(payload), commit=False)

    for day in cancelled_days:
        _recalculate_day(db, row.trip_id, day)


def _automatic_root(db: Session, row: AIAdvice) -> AIAdvice | None:
    current = row
    seen: set[int] = set()
    while True:
        if current.advice_id in seen:
            return None
        seen.add(current.advice_id)
        if current.advice_type == "itinerary_replan":
            return current
        if current.parent_advice_id is None:
            return None
        parent = crud.get_or_none(db, AIAdvice, "advice_id", current.parent_advice_id)
        if parent is None:
            return None
        current = parent


def _automatic_chain(db: Session, root: AIAdvice) -> list[AIAdvice]:
    rows = db.query(AIAdvice).filter(AIAdvice.trip_id == root.trip_id).all()
    by_id = {item.advice_id: item for item in rows}

    def belongs(item: AIAdvice) -> bool:
        current = item
        seen: set[int] = set()
        while current.parent_advice_id is not None:
            if current.advice_id in seen:
                return False
            seen.add(current.advice_id)
            if current.parent_advice_id == root.advice_id:
                return True
            parent = by_id.get(current.parent_advice_id)
            if parent is None:
                return False
            current = parent
        return item.advice_id == root.advice_id

    return [item for item in rows if belongs(item)]


def _automatic_conflict_ids(root: AIAdvice) -> list[int]:
    proposed = _json_or_none(root.proposed_itinerary_json or "")
    if not isinstance(proposed, dict):
        return []
    values = proposed.get("conflicting_itinerary_ids", [])
    if not isinstance(values, list):
        return []
    return sorted(
        {
            value
            for value in values
            if isinstance(value, int) and not isinstance(value, bool)
        }
    )


def _resolve_automatic_adjustment(
    db: Session,
    row: AIAdvice,
    *,
    result: str,
    itinerary_status: str,
) -> AIAdvice:
    root = _automatic_root(db, row)
    if root is None:
        raise ValueError("this advice is not part of an automatic adjustment")
    conflict_ids = _automatic_conflict_ids(root)
    affected = []
    if conflict_ids:
        affected = (
            db.query(ItineraryItem)
            .filter(
                ItineraryItem.trip_id == root.trip_id,
                ItineraryItem.itinerary_id.in_(conflict_ids),
                ItineraryItem.status == CHANGE_PENDING_STATUS,
            )
            .all()
        )
        for itinerary in affected:
            itinerary.status = itinerary_status
    for item in _automatic_chain(db, root):
        item.result = result
        item.generation_stopped = True
    if itinerary_status == "cancelled":
        for day in {item.start_time for item in affected}:
            _recalculate_day(db, root.trip_id, day)
    db.commit()
    db.refresh(row)
    return row


def _finish_automatic_acceptance(db: Session, row: AIAdvice) -> None:
    root = _automatic_root(db, row)
    if root is None:
        return
    conflict_ids = _automatic_conflict_ids(root)
    if conflict_ids:
        (
            db.query(ItineraryItem)
            .filter(
                ItineraryItem.trip_id == root.trip_id,
                ItineraryItem.itinerary_id.in_(conflict_ids),
                ItineraryItem.status == CHANGE_PENDING_STATUS,
            )
            .update({ItineraryItem.status: "pending"}, synchronize_session=False)
        )
    for item in _automatic_chain(db, root):
        item.result = (
            "accepted"
            if item.advice_id in (root.advice_id, row.advice_id)
            else "superseded"
        )
        item.generation_stopped = True


def act_on_advice(
    db: Session,
    advice_id: int,
    action: str,
    user_id: int,
    additional: str,
    selected_itinerary_ids: list[int] | None = None,
) -> AIAdvice:
    row = crud.get_or_none(db, AIAdvice, "advice_id", advice_id)
    if row is None:
        raise LookupError("advice not found")
    automatic_root = _automatic_root(db, row)
    if action == "reject" and automatic_root is not None:
        action = "keep_original"
    if action == "keep_original":
        return _resolve_automatic_adjustment(
            db, row, result="kept", itinerary_status="pending"
        )
    if action == "cancel_original":
        return _resolve_automatic_adjustment(
            db, row, result="cancelled_original", itinerary_status="cancelled"
        )
    if row.generation_stopped and action == "revise":
        raise ValueError("advice generation has been stopped")
    if action == "accept":
        try:
            if row.advice_type == "itinerary_replan":
                incident = row.reason_text or row.advice_text
                stored_selected, locked_ids = _advice_scope_ids(row)
                stored_selected = _scope_ids(
                    db,
                    row.trip_id,
                    stored_selected,
                    ("pending", CHANGE_PENDING_STATUS),
                )
                locked_ids = _scope_ids(
                    db,
                    row.trip_id,
                    locked_ids,
                    ("pending", CHANGE_PENDING_STATUS),
                )
                selected_ids = sorted(
                    set(stored_selected)
                    | set(selected_itinerary_ids or [])
                    | set(locked_ids)
                )
                agent_input = (
                    "系统自动检查发现了以下突发状况，用户已经明确同意生成行程"
                    "调整方案。请像处理用户主动提出的行程修改请求一样，结合当前"
                    "行程、时间、位置和实时信息，生成最小且可执行的候选调整。"
                    "这里只生成候选方案，必须等待用户再次采纳后才能修改数据库；"
                    "不要把这段内部指令原样回复给用户。\n"
                    f"突发状况：{incident}"
                )
                if additional:
                    agent_input += f"\n用户补充要求：{additional}"
                generated = _generate_replan(
                    db,
                    trip_id=row.trip_id,
                    user_id=user_id,
                    original=agent_input,
                    reason=incident,
                    trigger_type="system_auto_accident",
                    location_inputs=_stored_location_inputs(db, user_id),
                    selected_itinerary_ids=selected_ids,
                    locked_itinerary_ids=locked_ids,
                    parent_advice_id=row.advice_id,
                    commit=False,
                )
                db.commit()
                db.refresh(generated)
                return generated
            _apply_replan(db, row)
            _finish_automatic_acceptance(db, row)
        except Exception:
            db.rollback()
            raise
        row.result = "accepted"
    elif action == "reject":
        row.result, row.generation_stopped = "rejected", True
    else:
        row.result = "revising"
        stored_selected, locked_ids = _advice_scope_ids(row)
        statuses = (
            ("pending", CHANGE_PENDING_STATUS)
            if automatic_root is not None
            else ("pending",)
        )
        stored_selected = _scope_ids(db, row.trip_id, stored_selected, statuses)
        locked_ids = _scope_ids(db, row.trip_id, locked_ids, statuses)
        selected_ids = sorted(
            set(stored_selected) | set(selected_itinerary_ids or []) | set(locked_ids)
        )
        revision_context = _advice_revision_context(db, row)
        combined_input = (
            "这是对已有候选方案的进一步修改。以下版本历史由后端从 "
            "ai_advice 按 parent_advice_id 读取，并按旧到新排列。请保留仍然"
            "有效的约束，以当前用户的新要求为最高优先级；不要恢复已经被后续"
            "版本否定的内容，也不要声称已经修改数据库。\n"
            f"推荐版本历史：\n{revision_context}\n"
            f"当前用户新要求：{additional}"
        )
        generated = _generate_replan(
            db,
            trip_id=row.trip_id,
            user_id=user_id,
            original=combined_input,
            reason=additional or row.reason_text or "进一步修改候选方案",
            trigger_type="user_accident",
            location_inputs=_stored_location_inputs(db, user_id),
            selected_itinerary_ids=selected_ids,
            locked_itinerary_ids=locked_ids,
            parent_advice_id=row.advice_id,
            commit=False,
        )
        generated.reason_text = None
        db.commit()
        db.refresh(generated)
        return generated
    db.commit()
    db.refresh(row)
    return row


def chat(db: Session, data: ChatRequest) -> dict[str, Any]:
    _save_request_location(db, data)
    trip = (
        db.query(Trip)
        .filter(Trip.id == data.trip_id, Trip.user_id == data.user_id)
        .with_for_update()
        .first()
    )
    if trip is None:
        raise LookupError("trip not found")
    session = (
        db.query(ChatSession)
        .filter(ChatSession.trip_id == data.trip_id)
        .with_for_update()
        .first()
    )
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
        db.query(func.max(ChatMessage.message_order))
        .filter(ChatMessage.session_id == session.session_id)
        .scalar()
        or 0
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
            "trip_context": _trip_context(db, data.trip_id),
            "backend_itinerary_context": authoritative_itinerary_context(
                db, data.trip_id
            ),
            "conversation_history": json.dumps(history, ensure_ascii=False),
            "city_adcode": data.city_adcode,
            "latitude": data.latitude if data.latitude is not None else "",
            "longitude": data.longitude if data.longitude is not None else "",
            "location_name": data.location_name,
        },
    )
    if not audited.passed:
        session.last_message_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
        db.refresh(user_msg)
        raise AuditRejectedError(audited.reason)
    ai_msg = crud.create(
        db,
        ChatMessage,
        {
            "session_id": session.session_id,
            "sender_type": "ai",
            "content": audited.content,
            "message_order": order + 2,
            "audit_status": "pass",
            "audit_reason": None,
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


def chat_history_by_trip(db: Session, trip_id: int, user_id: int) -> dict[str, Any]:
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.trip_id == trip_id,
            ChatSession.user_id == user_id,
        )
        .first()
    )
    if session is None:
        raise LookupError("chat session not found")
    return chat_history(db, session.session_id, user_id)
