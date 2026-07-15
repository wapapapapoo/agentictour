from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from models.trip import Trip
from schemas.trip import TripCreate, TripUpdate


def ensure_trip_dates_available(
    db: Session,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
    exclude_trip_id: int | None = None,
) -> None:
    query = db.query(Trip).filter(
        Trip.user_id == user_id,
        Trip.status != "cancelled",
        Trip.start_date <= end_date,
        Trip.end_date >= start_date,
    )
    if exclude_trip_id is not None:
        query = query.filter(Trip.id != exclude_trip_id)
    conflict = query.order_by(Trip.start_date, Trip.id).with_for_update().first()
    if conflict is not None:
        raise ValueError(
            "trip date range overlaps another plan: "
            f"{conflict.title} ({conflict.start_date} - {conflict.end_date})"
        )


def _trip_status_at(trip: Trip, now: datetime) -> str:
    if trip.status == "cancelled":
        return "cancelled"
    try:
        resolved_tz: tzinfo = ZoneInfo(trip.timezone or "Asia/Shanghai")
    except ZoneInfoNotFoundError:
        resolved_tz = timezone(timedelta(hours=8))
    aware_now = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    today = aware_now.astimezone(resolved_tz).date()
    if today < trip.start_date:
        return "planned"
    if today > trip.end_date:
        return "completed"
    return "ongoing"


def sync_trip_statuses(
    db: Session,
    *,
    user_id: int | None = None,
    now: datetime | None = None,
    commit: bool = False,
) -> int:
    query = db.query(Trip).filter(Trip.status != "cancelled")
    if user_id is not None:
        query = query.filter(Trip.user_id == user_id)
    changed = 0
    effective_now = now or datetime.now(UTC)
    for trip in query.all():
        status = _trip_status_at(trip, effective_now)
        if trip.status != status:
            trip.status = status
            changed += 1
    if changed:
        if commit:
            db.commit()
        else:
            db.flush()
    return changed


def create_trip(db: Session, data: TripCreate) -> Trip:
    if data.status != "cancelled":
        ensure_trip_dates_available(
            db,
            user_id=data.user_id,
            start_date=data.start_date,
            end_date=data.end_date,
        )
    trip = Trip(**data.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def get_trip(db: Session, trip_id: int) -> Trip | None:
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is not None and trip.status != "cancelled":
        status = _trip_status_at(trip, datetime.now(UTC))
        if trip.status != status:
            trip.status = status
            db.commit()
            db.refresh(trip)
    return trip


def list_trips(db: Session, user_id: int | None = None) -> list[Trip]:
    sync_trip_statuses(db, user_id=user_id, commit=True)
    query = db.query(Trip)
    if user_id is not None:
        query = query.filter(Trip.user_id == user_id)
    return query.order_by(Trip.start_date.desc(), Trip.id.desc()).all()


def update_trip(db: Session, trip_id: int, data: TripUpdate) -> Trip:
    trip = get_trip(db, trip_id)
    if trip is None:
        raise LookupError("trip not found")

    values = data.model_dump(exclude_unset=True)
    start_date = values.get("start_date", trip.start_date)
    end_date = values.get("end_date", trip.end_date)
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    status = values.get("status", trip.status)
    if status != "cancelled":
        ensure_trip_dates_available(
            db,
            user_id=trip.user_id,
            start_date=start_date,
            end_date=end_date,
            exclude_trip_id=trip.id,
        )

    for key, value in values.items():
        setattr(trip, key, value)
    if trip.status == "planned":
        trip.status = _trip_status_at(trip, datetime.now(UTC))
    db.commit()
    db.refresh(trip)
    return trip


def delete_trip(db: Session, trip_id: int, user_id: int) -> None:
    trip = (
        db.query(Trip)
        .filter(Trip.id == trip_id, Trip.user_id == user_id)
        .first()
    )
    if trip is None:
        raise LookupError("trip not found")
    db.delete(trip)
    db.commit()
