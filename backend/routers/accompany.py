from datetime import UTC, datetime
from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from crud import accompany as crud
from database import get_db
from models.accompany import Notification
from routers.operation_log import write_log
from schemas.accompany import (
    AdviceActionRequest,
    AdviceGenerateRequest,
    AdviceResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ItineraryCreate,
    ItineraryResponse,
    ItineraryUpdate,
    LocationResponse,
    LocationUpdate,
    MemoCreate,
    MemoResponse,
    MemoUpdate,
    NotificationResponse,
)
from services import accompany_service as service
from services.ai_gateway import AuditRejectedError
from utils.dify_client import DifyError

router = APIRouter(prefix="/api", tags=["Hikari Atlas"])


def _not_found(exc: Exception) -> NoReturn:
    raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/memos", response_model=MemoResponse)
def create_memo(
    data: MemoCreate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return service.create_memo(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/trips/{trip_id}/memos", response_model=list[MemoResponse])
def list_memos(
    trip_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return crud.list_memos(db, trip_id)


@router.patch("/memos/{memo_id}", response_model=MemoResponse)
def update_memo(
    memo_id: int,
    data: MemoUpdate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return service.update_memo(db, memo_id, data)
    except LookupError as exc:
        _not_found(exc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/memos/{memo_id}", status_code=204)
def delete_memo(
    memo_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        service.delete_memo(db, memo_id)
    except LookupError as exc:
        _not_found(exc)


@router.post("/itineraries", response_model=ItineraryResponse)
def create_itinerary(
    data: ItineraryCreate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return service.create_itinerary(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/trips/{trip_id}/itineraries", response_model=list[ItineraryResponse])
def list_itineraries(
    trip_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return service.list_itineraries(db, trip_id)


@router.patch("/itineraries/{itinerary_id}", response_model=ItineraryResponse)
def update_itinerary(
    itinerary_id: int,
    data: ItineraryUpdate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return service.update_itinerary(db, itinerary_id, data)
    except LookupError as exc:
        _not_found(exc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/itineraries/{itinerary_id}", status_code=204)
def delete_itinerary(
    itinerary_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        service.delete_itinerary(db, itinerary_id)
    except LookupError as exc:
        _not_found(exc)


@router.post("/ai-advice/generate", response_model=AdviceResponse)
def generate_advice(
    data: AdviceGenerateRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return service.advice_response(service.generate_advice(db, data))
    except AuditRejectedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DifyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/trips/{trip_id}/ai-advice", response_model=list[AdviceResponse])
def list_advice(
    trip_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return [service.advice_response(x) for x in crud.list_advice(db, trip_id)]


@router.post("/ai-advice/{advice_id}/action", response_model=AdviceResponse)
def act(
    advice_id: int,
    data: AdviceActionRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return service.advice_response(
            service.act_on_advice(
                db,
                advice_id,
                data.action,
                data.user_id,
                data.additional_requirement,
                data.selected_itinerary_ids,
            )
        )
    except LookupError as exc:
        _not_found(exc)
    except AuditRejectedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DifyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/chat/messages", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        result = service.chat(db, data)
        write_log(current_user_id, "对话", data.message)
        return result
    except LookupError as exc:
        _not_found(exc)
    except AuditRejectedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DifyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/chat/sessions/{session_id}", response_model=ChatHistoryResponse)
def chat_history(
    session_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return service.chat_history(db, session_id, current_user_id)
    except LookupError as exc:
        _not_found(exc)


@router.get("/trips/{trip_id}/chat", response_model=ChatHistoryResponse)
def trip_chat_history(
    trip_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return service.chat_history_by_trip(db, trip_id, current_user_id)
    except LookupError as exc:
        _not_found(exc)


@router.put("/locations", response_model=LocationResponse)
def update_location(
    data: LocationUpdate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return service.upsert_location(
        db, data.model_copy(update={"user_id": current_user_id})
    )


@router.get("/locations", response_model=LocationResponse)
def current_location(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    row = service.get_location(db, current_user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="location not found")
    return row


@router.get("/notifications", response_model=list[NotificationResponse])
def notifications(
    user_id: int,
    unread_only: bool = Query(default=True),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return crud.list_notifications(db, user_id, unread_only)


@router.post(
    "/notifications/{notification_id}/read", response_model=NotificationResponse
)
def mark_notification_read(
    notification_id: int,
    user_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    row = (
        db.query(Notification)
        .filter(
            Notification.notification_id == notification_id,
            Notification.user_id == user_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="notification not found")
    row.read_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(row)
    return row
