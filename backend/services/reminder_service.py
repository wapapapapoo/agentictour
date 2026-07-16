import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from crud.accompany import create
from models.accompany import (
    AgentJobState,
    AIAdvice,
    ChatMessage,
    ChatSession,
    ItineraryItem,
    Memo,
    Notification,
    UserLocation,
)
from models.trip import Trip
from services.accompany_service import (
    authoritative_itinerary_context,
    sync_itinerary_statuses,
)
from services.ai_gateway import AuditRejectedError, run_hikari_once_audited
from services.trip_service import sync_trip_statuses
from utils.trip_time import trip_local_iso, trip_route_context, trip_time_context

logger = logging.getLogger(__name__)


def _trip_context(trip: Trip | None) -> str:
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


def _location_inputs(db: Session, user_id: int) -> dict[str, str | float]:
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


PROMPTS = {
    "initial_start": (
        "这是当天初始行程提醒，请用温暖的起床/出发语气提醒用户，"
        "并概括今天的第一个安排。"
    ),
    "memo": "这是用户设置了时间的备忘录提醒，请清楚、简短地提醒用户备忘内容。",
    "next_itinerary": (
        "这是下个行程提醒，请说明下一安排、地点和时间，并给出必要的出发提示。"
    ),
}


def _emit(
    db: Session, trip_id: int, user_id: int, category: str, detail: str
) -> Notification:
    original = f"{PROMPTS[category]}\n{detail}"
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    audited = run_hikari_once_audited(
        user=str(user_id),
        original_input=original,
        inputs={
            "user_query": original,
            "trigger_type": "system_auto_remind",
            "tour_id": trip_id,
            "trip_context": _trip_context(trip),
            "backend_itinerary_context": authoritative_itinerary_context(
                db, trip_id
            ),
            **_location_inputs(db, user_id),
        },
    )
    if not audited.passed:
        raise AuditRejectedError(audited.reason)
    return create(
        db,
        Notification,
        {
            "trip_id": trip_id,
            "user_id": user_id,
            "category": category,
            "content": audited.content,
        },
    )


def _agent_check(
    db: Session,
    trip: Trip,
    trigger_type: str,
    detail: str,
) -> AIAdvice | None:
    if trigger_type == "system_auto_check":
        # Due-reminder checks and the hourly job can run at almost the same time.
        # Serialize them per trip and reuse the open adjustment instead of sending
        # two notifications for the same unresolved incident.
        db.query(Trip.id).filter(Trip.id == trip.id).with_for_update().one()
        open_adjustment = (
            db.query(AIAdvice)
            .filter(
                AIAdvice.trip_id == trip.id,
                AIAdvice.advice_type.in_(("itinerary_replan", "replan")),
                AIAdvice.result.in_(("pending", "revising")),
                AIAdvice.audit_status == "pass",
            )
            .order_by(AIAdvice.created_at.desc(), AIAdvice.advice_id.desc())
            .first()
        )
        if open_adjustment is not None:
            return open_adjustment
    audited = run_hikari_once_audited(
        user=str(trip.user_id),
        original_input=detail,
        inputs={
            "user_query": detail,
            "trigger_type": trigger_type,
            "tour_id": trip.id,
            "trip_context": _trip_context(trip),
            "backend_itinerary_context": authoritative_itinerary_context(
                db, trip.id
            ),
            **_location_inputs(db, trip.user_id),
        },
    )
    if not audited.passed:
        logger.warning(
            "automatic agent output rejected by audit: trip_id=%s trigger=%s reason=%s",
            trip.id,
            trigger_type,
            audited.reason,
        )
        return None
    decision = (
        "chat_recommendation"
        if trigger_type == "system_auto_advice"
        else _auto_check_decision(audited)
    )
    category = {
        "chat_recommendation": "proactive_recommendation",
        "itinerary_replan": "itinerary_replan",
    }.get(decision, "itinerary_check")
    result = {
        "false": "not_required",
        "chat_recommendation": "delivered",
        "itinerary_replan": "pending",
    }[decision]
    conflict_ids = (
        _auto_conflict_ids(db, trip, audited)
        if decision == "itinerary_replan"
        else []
    )
    advice = create(
        db,
        AIAdvice,
        {
            "trip_id": trip.id,
            "advice_type": category,
            "input_text": detail,
            "reason_text": audited.content
            if decision == "itinerary_replan"
            else detail,
            "advice_text": audited.content,
            "proposed_itinerary_json": json.dumps(
                {"conflicting_itinerary_ids": conflict_ids}, ensure_ascii=False
            )
            if decision == "itinerary_replan"
            else None,
            "result": result,
            "audit_status": "pass",
            "audit_reason": None,
        },
    )
    db.flush()
    if decision == "itinerary_replan":
        create(
            db,
            Notification,
            {
                "trip_id": trip.id,
                "user_id": trip.user_id,
                "advice_id": advice.advice_id,
                "category": category,
                "content": audited.content,
            },
        )
    elif decision == "chat_recommendation":
        _append_chat_recommendation(db, trip, audited.content, advice)
    return advice


def _append_chat_recommendation(
    db: Session, trip: Trip, content: str, advice: AIAdvice
) -> ChatMessage:
    db.query(Trip.id).filter(Trip.id == trip.id).with_for_update().one()
    session = (
        db.query(ChatSession)
        .filter(ChatSession.trip_id == trip.id)
        .with_for_update()
        .first()
    )
    if session is None:
        session = create(
            db,
            ChatSession,
            {
                "trip_id": trip.id,
                "user_id": trip.user_id,
                "title": "Hikari 主动推荐",
            },
        )
    message_order = (
        db.query(func.max(ChatMessage.message_order))
        .filter(ChatMessage.session_id == session.session_id)
        .scalar()
        or 0
    ) + 1
    message = create(
        db,
        ChatMessage,
        {
            "session_id": session.session_id,
            "sender_type": "ai",
            "content": content,
            "message_order": message_order,
            "audit_status": advice.audit_status,
            "audit_reason": advice.audit_reason,
        },
    )
    session.last_message_at = datetime.now(UTC).replace(tzinfo=None)
    return message


AUTO_CHECK_DECISIONS = {"false", "chat_recommendation", "itinerary_replan"}


def _decision_from(value: object) -> str | None:
    if isinstance(value, bool):
        return "false" if value is False else None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in AUTO_CHECK_DECISIONS:
            return normalized
    if isinstance(value, dict):
        for key in ("decision", "recommendation_type", "result", "need_notify"):
            if key in value:
                nested_decision = _decision_from(value[key])
                if nested_decision is not None:
                    return nested_decision
    return None


def _auto_check_decision(audited: object) -> str:
    main_response = getattr(audited, "main_response", {})
    outputs = (
        main_response.get("data", {}).get("outputs", {})
        if isinstance(main_response, dict)
        else {}
    )
    for source in (outputs, getattr(audited, "structured_output", None)):
        decision = _decision_from(source)
        if decision is not None:
            return decision
    content = getattr(audited, "content", "")
    try:
        parsed_content = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        parsed_content = content
    decision = _decision_from(parsed_content)
    # Unknown or malformed output must not create an unsolicited notification.
    return "false" if decision is None else decision


def _auto_conflict_ids(db: Session, trip: Trip, audited: object) -> list[int]:
    main_response = getattr(audited, "main_response", {})
    outputs = (
        main_response.get("data", {}).get("outputs", {})
        if isinstance(main_response, dict)
        else {}
    )
    raw = outputs.get("conflicting_itinerary_ids", [])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = []
    if not isinstance(raw, list):
        return []
    requested = {
        value
        for value in raw
        if isinstance(value, int) and not isinstance(value, bool)
    }
    if not requested:
        return []
    eligible = (
        db.query(ItineraryItem.itinerary_id)
        .filter(
            ItineraryItem.trip_id == trip.id,
            ItineraryItem.status == "pending",
            ItineraryItem.itinerary_id.in_(requested),
        )
        .all()
    )
    return sorted(row[0] for row in eligible)


def scan_due_reminders(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC).replace(tzinfo=None)
    sync_trip_statuses(db, now=now, commit=False)
    sync_itinerary_statuses(db, now=now, commit=False)
    count = 0
    due_memos = (
        db.query(Memo)
        .filter(
            Memo.reminder_time.isnot(None),
            Memo.reminder_time <= now,
            Memo.reminded_at.is_(None),
        )
        .all()
    )
    for memo in due_memos:
        try:
            with db.begin_nested():
                trip = (
                    db.query(Trip)
                    .filter(
                        Trip.id == memo.trip_id,
                        Trip.status == "ongoing",
                    )
                    .first()
                )
                if trip:
                    _emit(db, memo.trip_id, trip.user_id, "memo", memo.memo_text)
                    memo.reminded_at = now
                    count += 1
        except Exception:
            logger.exception("memo reminder failed: memo_id=%s", memo.memo_id)

    due_items = (
        db.query(ItineraryItem)
        .filter(
            ItineraryItem.reminder_time <= now,
            ItineraryItem.reminded_at.is_(None),
            ItineraryItem.status == "pending",
        )
        .all()
    )
    for item in due_items:
        try:
            with db.begin_nested():
                trip = (
                    db.query(Trip)
                    .filter(
                        Trip.id == item.trip_id,
                        Trip.status == "ongoing",
                    )
                    .first()
                )
                if not trip:
                    continue
                category = "initial_start" if item.is_initial else "next_itinerary"
                detail = (
                    f"{item.title}，地点：{item.place_name}，"
                    f"开始：{trip_local_iso(item.start_time, trip.timezone)} "
                    f"（{trip.timezone or 'Asia/Shanghai'}）"
                )
                if item.is_initial:
                    unscheduled = (
                        db.query(Memo)
                        .filter(
                            Memo.trip_id == item.trip_id,
                            Memo.reminder_time.is_(None),
                            Memo.reminded_at.is_(None),
                        )
                        .all()
                    )
                    if unscheduled:
                        detail += "\n同时提醒备忘：" + "；".join(
                            m.memo_text for m in unscheduled
                        )
                        for memo in unscheduled:
                            memo.reminded_at = now
                _emit(db, item.trip_id, trip.user_id, category, detail)
                _agent_check(
                    db,
                    trip,
                    "system_auto_check",
                    f"行程提醒触发的实时信息检查：{detail}",
                )
                item.reminded_at = now
                count += 1
        except Exception:
            logger.exception(
                "itinerary reminder failed: itinerary_id=%s", item.itinerary_id
            )
    db.commit()
    return count


def run_periodic_agent_jobs(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC).replace(tzinfo=None)
    sync_trip_statuses(db, now=now, commit=False)
    sync_itinerary_statuses(db, now=now, commit=False)
    executed = 0
    jobs = (("hourly_itinerary_check", timedelta(hours=1), "system_auto_check"),)
    for job_name, interval, trigger in jobs:
        state = (
            db.query(AgentJobState).filter(AgentJobState.job_name == job_name).first()
        )
        if (
            state is not None
            and state.last_run_at
            and now - state.last_run_at < interval
        ):
            continue
        trips = (
            db.query(Trip)
            .join(ItineraryItem, ItineraryItem.trip_id == Trip.id)
            .filter(
                Trip.status == "ongoing",
                ItineraryItem.status == "pending",
                ItineraryItem.end_time >= now,
            )
            .distinct()
            .all()
        )
        for trip in trips:
            detail = (
                "每小时统一主动巡检：请在无需提示、聊天主动推荐、日程重推荐"
                "三种结果中选择一种。"
            )
            try:
                with db.begin_nested():
                    _agent_check(db, trip, trigger, detail)
                    executed += 1
            except Exception:
                logger.exception(
                    "periodic agent job failed: job=%s trip_id=%s",
                    job_name,
                    trip.id,
                )
        if state is None:
            state = AgentJobState(job_name=job_name)
            db.add(state)
        state.last_run_at = now
    db.commit()
    return executed
