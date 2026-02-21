from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_admin_user, get_approver_or_admin
from app.models.user import User
from app.schemas.booking import BookingCreateRequest, ApproveRequest, RejectRequest, CancelRequest
from app.schemas.common import success_response, paginated_response
from app.services.booking_service import booking_service

router = APIRouter(prefix="/bookings")


@router.get("", summary="List bookings (role-filtered)")
def list_bookings(
    page:         int            = Query(1, ge=1),
    limit:        int            = Query(20, ge=1, le=100),
    status:       Optional[str]  = Query(None),
    resourceId:   Optional[int]  = Query(None),
    resourceType: Optional[str]  = Query(None, description="VEHICLE | ROOM"),
    userId:       Optional[int]  = Query(None, description="Admin/Approver only"),
    startDate:    Optional[str]  = Query(None, description="ISO 8601 date filter"),
    endDate:      Optional[str]  = Query(None),
    db:           Session        = Depends(get_db),
    current_user: User           = Depends(get_current_user),
):
    data, total = booking_service.list_bookings(
        db, current_user, page, limit,
        status, resourceId, resourceType, startDate, endDate, userId,
    )
    return paginated_response("Bookings retrieved successfully", data, total, page, limit)


@router.get("/{booking_id}", summary="Get booking detail")
def get_booking(
    booking_id: int,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_current_user),
):
    data = booking_service.get_booking(db, booking_id, current_user)
    return success_response("Booking retrieved", data)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create booking")
def create_booking(
    body: BookingCreateRequest,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = booking_service.create_booking(db, body, current_user)
    return success_response("Booking created successfully", data)


@router.patch("/{booking_id}/cancel", summary="Cancel booking (PENDING only)")
def cancel_booking(
    booking_id: int,
    body:       CancelRequest = CancelRequest(),
    db:         Session       = Depends(get_db),
    current_user: User        = Depends(get_current_user),
):
    data = booking_service.cancel_booking(db, booking_id, current_user)
    return success_response("Booking cancelled", data)


@router.post("/{booking_id}/approve", summary="Approve booking (Approver/Admin)")
def approve_booking(
    booking_id: int,
    body:       ApproveRequest,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_approver_or_admin),
):
    data = booking_service.approve_booking(db, booking_id, body, current_user)
    return success_response("Booking approved successfully", data)


@router.post("/{booking_id}/reject", summary="Reject booking (Approver/Admin)")
def reject_booking(
    booking_id: int,
    body:       RejectRequest,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_approver_or_admin),
):
    data = booking_service.reject_booking(db, booking_id, body, current_user)
    return success_response("Booking rejected", data)


@router.patch("/{booking_id}/start", summary="Mark booking as ONGOING (Admin)")
def start_booking(
    booking_id: int,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    data = booking_service.start_booking(db, booking_id, current_user)
    return success_response("Booking started (ONGOING)", data)


@router.patch("/{booking_id}/complete", summary="Mark booking as COMPLETED (Admin)")
def complete_booking(
    booking_id: int,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    data = booking_service.complete_booking(db, booking_id, current_user)
    return success_response("Booking completed", data)


@router.get("/{booking_id}/approval-log", summary="Get approval history (Approver/Admin)")
def get_approval_log(
    booking_id: int,
    db:         Session = Depends(get_db),
    _:          User    = Depends(get_approver_or_admin),
):
    data = booking_service.get_approval_log(db, booking_id)
    return success_response("Approval log retrieved", data)
