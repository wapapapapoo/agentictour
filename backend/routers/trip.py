from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models.trip import Trip
from schemas.trip import TripCreate, TripResponse, TripUpdate
from services import trip_service

router = APIRouter(prefix="/api/trips", tags=["Trips"])


@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(
    data: TripCreate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Trip:
    return trip_service.create_trip(db, data)


@router.get("", response_model=list[TripResponse])
def list_trips(
    user_id: int | None = Query(default=None, gt=0),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Trip]:
    return trip_service.list_trips(db, user_id)


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Trip:
    trip = trip_service.get_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")
    return trip


@router.patch("/{trip_id}", response_model=TripResponse)
def update_trip(
    trip_id: int,
    data: TripUpdate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Trip:
    try:
        return trip_service.update_trip(db, trip_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(
    trip_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        trip_service.delete_trip(db, trip_id, current_user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
