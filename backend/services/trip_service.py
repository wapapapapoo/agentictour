from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from models.trip import Trip
from schemas.trip import TripCreate, TripUpdate


def _trip_status_at(trip: Trip, now: datetime) -> str:
    if trip.status == "cancelled":
        return "cancelled"
    try:
        tzinfo = ZoneInfo(trip.timezone or "Asia/Shanghai")
    except ZoneInfoNotFoundError:
        tzinfo = timezone(timedelta(hours=8))
    aware_now = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    today = aware_now.astimezone(tzinfo).date()
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
