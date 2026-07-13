import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from crud.accompany import create
from models.accompany import (
    AgentJobState,
    AIAdvice,
    ItineraryItem,
    Memo,
    Notification,
    UserLocation,
)
from models.trip_plan import TripPlanRequest
from services.ai_gateway import run_hikari_once_audited

logger = logging.getLogger(__name__)


def _location_inputs(db: Session, user_id: str) -> dict[str, str | float]:
    location = (
        db.query(UserLocation).filter(UserLocation.user_id == user_id).first()
    )
    if location is None:
        return {
            "latitude": "",
            "longitude": "",
            "location_name": "",
            "location_context": "",
        }
    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "location_name": location.place_name or "",
        "location_context": location.location_context or "",
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
    db: Session, tour_id: int, user_id: str, category: str, detail: str
) -> AIAdvice:
    original = f"{PROMPTS[category]}\n{detail}"
    audited = run_hikari_once_audited(
        user=user_id,
        original_input=original,
        inputs={
            "user_query": original,
            "trigger_type": "system_auto_remind",
            "tour_id": tour_id,
            "city": "",
            **_location_inputs(db, user_id),
        },
    )
    advice = create(
        db,
        AIAdvice,
        {
            "tour_id": tour_id,
            "advice_type": category,
            "reason_text": detail,
            "advice_text": audited.content,
            "result": "pending",
            "audit_status": "pass" if audited.passed else "failed",
            "audit_reason": audited.reason,
        },
    )
    db.flush()
    create(
        db,
        Notification,
        {
            "tour_id": tour_id,
            "user_id": user_id,
            "advice_id": advice.advice_id,
            "category": category,
            "content": audited.content,
        },
    )
    return advice


def _agent_check(
    db: Session,
    plan: TripPlanRequest,
    trigger_type: str,
    detail: str,
) -> AIAdvice:
    audited = run_hikari_once_audited(
        user=plan.user_id,
        original_input=detail,
        inputs={
            "user_query": detail,
            "trigger_type": trigger_type,
            "tour_id": plan.id,
            "city": plan.destination_city,
            **_location_inputs(db, plan.user_id),
        },
    )
    category = (
        "proactive_recommendation"
        if trigger_type == "system_auto_advice"
        else "itinerary_check"
    )
    advice = create(
        db,
        AIAdvice,
        {
            "tour_id": plan.id,
            "advice_type": category,
            "input_text": detail,
            "reason_text": detail,
            "advice_text": audited.content,
            "result": "pending",
            "audit_status": "pass" if audited.passed else "failed",
            "audit_reason": audited.reason,
        },
    )
    db.flush()
    create(
        db,
        Notification,
        {
            "tour_id": plan.id,
            "user_id": plan.user_id,
            "advice_id": advice.advice_id,
            "category": category,
            "content": audited.content,
        },
    )
    return advice


def scan_due_reminders(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC).replace(tzinfo=None)
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
                plan = (
                    db.query(TripPlanRequest)
                    .filter(TripPlanRequest.id == memo.tour_id)
                    .first()
                )
                if plan:
                    _emit(db, memo.tour_id, plan.user_id, "memo", memo.memo_text)
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
                plan = (
                    db.query(TripPlanRequest)
                    .filter(TripPlanRequest.id == item.tour_id)
                    .first()
                )
                if not plan:
                    continue
                category = "initial_start" if item.is_initial else "next_itinerary"
                detail = (
                    f"{item.title}，地点：{item.place_name}，"
                    f"开始：{item.start_time.isoformat()}"
                )
                if item.is_initial:
                    unscheduled = (
                        db.query(Memo)
                        .filter(
                            Memo.tour_id == item.tour_id,
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
                _emit(db, item.tour_id, plan.user_id, category, detail)
                _agent_check(
                    db,
                    plan,
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
    executed = 0
    jobs = (
        ("hourly_itinerary_check", timedelta(hours=1), "system_auto_check"),
        ("three_hour_proactive", timedelta(hours=3), "system_auto_advice"),
    )
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
        plans = (
            db.query(TripPlanRequest)
            .join(ItineraryItem, ItineraryItem.tour_id == TripPlanRequest.id)
            .filter(
                ItineraryItem.status == "pending",
                ItineraryItem.end_time >= now,
            )
            .distinct()
            .all()
        )
        for plan in plans:
            detail = (
                "每小时行程外部信息巡检，请判断未来行程是否需要变化。"
                if trigger == "system_auto_check"
                else "每3小时主动陪伴推荐，请结合当前时间推荐休息、吃饭或落脚地点。"
            )
            try:
                with db.begin_nested():
                    _agent_check(db, plan, trigger, detail)
                    executed += 1
            except Exception:
                logger.exception(
                    "periodic agent job failed: job=%s tour_id=%s",
                    job_name,
                    plan.id,
                )
        if state is None:
            state = AgentJobState(job_name=job_name)
            db.add(state)
        state.last_run_at = now
    db.commit()
    return executed
