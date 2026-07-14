from typing import Any, TypeVar

from sqlalchemy.orm import Session

from models.accompany import AIAdvice, ItineraryItem, Memo, Notification

ModelT = TypeVar("ModelT")


def create(db: Session, model: type[ModelT], values: dict[str, Any]) -> ModelT:
    row = model(**values)
    db.add(row)
    db.flush()
    return row


def get_or_none(
    db: Session, model: type[ModelT], pk_name: str, pk: int
) -> ModelT | None:
    return db.query(model).filter(getattr(model, pk_name) == pk).first()


def list_memos(db: Session, trip_id: int) -> list[Memo]:
    return (
        db.query(Memo).filter(Memo.trip_id == trip_id).order_by(Memo.created_at).all()
    )


def list_itineraries(db: Session, trip_id: int) -> list[ItineraryItem]:
    return (
        db.query(ItineraryItem)
        .filter(ItineraryItem.trip_id == trip_id)
        .order_by(ItineraryItem.start_time)
        .all()
    )


def list_advice(db: Session, trip_id: int) -> list[AIAdvice]:
    return (
        db.query(AIAdvice)
        .filter(AIAdvice.trip_id == trip_id)
        .order_by(AIAdvice.created_at.desc())
        .all()
    )


def list_notifications(
    db: Session, user_id: int, unread_only: bool = True
) -> list[Notification]:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    return query.order_by(Notification.created_at.desc()).all()


def update(row: Any, values: dict[str, Any]) -> Any:
    for key, value in values.items():
        setattr(row, key, value)
    return row


def delete(db: Session, row: Any) -> None:
    db.delete(row)
