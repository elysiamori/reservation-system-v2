from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_admin_user, get_admin_or_driver
from app.models.user import User
from app.schemas.booking import (
    BookingCreateRequest, ApproveRequest, RejectRequest, CancelRequest,
    AssignVehicleRequest, DriverRatingCreateRequest,
)
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
    userId:       Optional[int]  = Query(None, description="Admin only"),
    startDate:    Optional[str]  = Query(None),
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
    return success_response("Booking retrieved", booking_service.get_booking(db, booking_id, current_user))


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
    return success_response("Booking cancelled", booking_service.cancel_booking(db, booking_id, current_user))


@router.post("/{booking_id}/approve", summary="Approve booking (Admin only)")
def approve_booking(
    booking_id: int,
    body:       ApproveRequest,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    return success_response("Booking approved successfully",
                            booking_service.approve_booking(db, booking_id, body, current_user))


@router.post("/{booking_id}/reject", summary="Reject booking (Admin only)")
def reject_booking(
    booking_id: int,
    body:       RejectRequest,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    return success_response("Booking rejected",
                            booking_service.reject_booking(db, booking_id, body, current_user))


@router.post("/{booking_id}/assign-vehicle", summary="Assign vehicle & driver to approved booking (Admin)")
def assign_vehicle(
    booking_id: int,
    body:       AssignVehicleRequest,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    return success_response("Vehicle and driver assigned",
                            booking_service.assign_vehicle(db, booking_id, body, current_user))


@router.patch("/{booking_id}/start", summary="Start trip — mark ONGOING (Driver or Admin)")
def start_booking(
    booking_id: int,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_or_driver),
):
    return success_response("Booking started (ONGOING)",
                            booking_service.start_booking(db, booking_id, current_user))


@router.patch("/{booking_id}/complete", summary="Complete booking (Admin)")
def complete_booking(
    booking_id: int,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    return success_response("Booking completed",
                            booking_service.complete_booking(db, booking_id, current_user))


@router.post("/{booking_id}/rate-driver",
             status_code=status.HTTP_201_CREATED,
             summary="Rate driver for completed vehicle booking (Employee/User)")
def rate_driver(
    booking_id: int,
    body:       DriverRatingCreateRequest,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_current_user),
):
    return success_response("Driver rated successfully",
                            booking_service.rate_driver(db, booking_id, body, current_user))


@router.get("/drivers/{driver_id}/ratings", summary="Get driver ratings & average score")
def get_driver_ratings(
    driver_id: int,
    db:        Session = Depends(get_db),
    _:         User    = Depends(get_admin_user),
):
    return success_response("Driver ratings retrieved",
                            booking_service.get_driver_ratings(db, driver_id))


@router.get("/{booking_id}/approval-log", summary="Get approval history (Admin)")
def get_approval_log(
    booking_id: int,
    db:         Session = Depends(get_db),
    _:          User    = Depends(get_admin_user),
):
    return success_response("Approval log retrieved", booking_service.get_approval_log(db, booking_id))
