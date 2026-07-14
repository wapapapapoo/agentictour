from typing import Any

from sqlalchemy.orm import Session

from models.accompany import AIAdvice, ItineraryItem, Memo, Notification


def create(db: Session, model: Any, values: dict[str, Any]) -> Any:
    row = model(**values)
    db.add(row)
    db.flush()
    return row


def get_or_none(db: Session, model: Any, pk_name: str, pk: int) -> Any:
    return db.query(model).filter(getattr(model, pk_name) == pk).first()  # type: ignore[no-any-return]


def list_memos(db: Session, trip_id: int) -> list[Memo]:
    return (  # type: ignore[no-any-return]
        db.query(Memo).filter(Memo.trip_id == trip_id).order_by(Memo.created_at).all()
    )


def list_itineraries(db: Session, trip_id: int) -> list[ItineraryItem]:  # type: ignore[no-any-return]
    return (
        db.query(ItineraryItem)
        .filter(ItineraryItem.trip_id == trip_id)
        .order_by(ItineraryItem.start_time)
        .all()
    )


def list_advice(db: Session, trip_id: int) -> list[AIAdvice]:  # type: ignore[no-any-return]
    return (
        db.query(AIAdvice)
        .filter(AIAdvice.trip_id == trip_id)
        .order_by(AIAdvice.created_at.desc())
        .all()
    )


def list_notifications(  # type: ignore[no-any-return]
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
