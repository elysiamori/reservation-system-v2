from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_admin_user
from app.models.user import User
from app.schemas.room import RoomCreateRequest, RoomUpdateRequest, RoomStatusRequest
from app.schemas.common import success_response, paginated_response
from app.services.room_service import room_service

router = APIRouter(prefix="/rooms")


@router.get("", summary="List rooms (paginated)")
def list_rooms(
    page:        int           = Query(1, ge=1),
    limit:       int           = Query(20, ge=1, le=100),
    search:      Optional[str] = Query(None),
    status:      Optional[str] = Query(None, description="AVAILABLE | MAINTENANCE | INACTIVE"),
    minCapacity: Optional[int] = Query(None, ge=1),
    db:          Session       = Depends(get_db),
    _:           User          = Depends(get_current_user),
):
    data, total = room_service.list_rooms(db, page, limit, search, status, minCapacity)
    return paginated_response("Rooms retrieved successfully", data, total, page, limit)


@router.get("/{room_id}", summary="Get room by ID")
def get_room(room_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return success_response("Room retrieved", room_service.get_room(db, room_id))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create room (Admin)")
def create_room(
    body: RoomCreateRequest,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = room_service.create_room(db, body, current_user.id)
    return success_response("Room created successfully", data)


@router.put("/{room_id}", summary="Update room (Admin)")
def update_room(
    room_id: int,
    body:    RoomUpdateRequest,
    db:      Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = room_service.update_room(db, room_id, body, current_user.id)
    return success_response("Room updated successfully", data)


@router.patch("/{room_id}/status", summary="Change room status (Admin)")
def update_status(
    room_id: int,
    body:    RoomStatusRequest,
    db:      Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = room_service.update_status(db, room_id, body, current_user.id)
    return success_response("Room status updated", data)


@router.delete("/{room_id}", summary="Delete room (Admin)")
def delete_room(
    room_id: int,
    db:      Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    room_service.delete_room(db, room_id, current_user.id)
    return success_response("Room deleted successfully", None)
