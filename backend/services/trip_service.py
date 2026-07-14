from sqlalchemy.orm import Session

from models.trip import Trip
from schemas.trip import TripCreate, TripUpdate


def create_trip(db: Session, data: TripCreate) -> Trip:
    trip = Trip(**data.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def get_trip(db: Session, trip_id: int) -> Trip | None:
    return db.query(Trip).filter(Trip.id == trip_id).first()


def list_trips(db: Session, user_id: int | None = None) -> list[Trip]:
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
    db.commit()
    db.refresh(trip)
    return trip
