from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_admin_user
from app.models.user import User
from app.schemas.driver import DriverCreateRequest, DriverUpdateRequest, AssignVehicleRequest
from app.schemas.common import success_response, paginated_response
from app.services.driver_service import driver_service

router = APIRouter(prefix="/drivers")


@router.get("", summary="List all drivers (Admin)")
def list_drivers(
    page:     int            = Query(1, ge=1),
    limit:    int            = Query(20, ge=1, le=100),
    isActive: Optional[bool] = Query(None),
    db:       Session        = Depends(get_db),
    _:        User           = Depends(get_admin_user),
):
    data, total = driver_service.list_drivers(db, page, limit, isActive)
    return paginated_response("Drivers retrieved successfully", data, total, page, limit)


@router.get("/{driver_id}", summary="Get driver by ID (Admin)")
def get_driver(driver_id: int, db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    return success_response("Driver retrieved", driver_service.get_driver(db, driver_id))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Register user as driver (Admin)")
def create_driver(
    body: DriverCreateRequest,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = driver_service.create_driver(db, body, current_user.id)
    return success_response("Driver registered successfully", data)


@router.put("/{driver_id}", summary="Update driver info (Admin)")
def update_driver(
    driver_id: int,
    body:      DriverUpdateRequest,
    db:        Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = driver_service.update_driver(db, driver_id, body, current_user.id)
    return success_response("Driver updated successfully", data)


@router.patch("/{driver_id}/toggle-active", summary="Activate/deactivate driver (Admin)")
def toggle_active(
    driver_id: int,
    db:        Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = driver_service.toggle_active(db, driver_id, current_user.id)
    label = "activated" if data["isActive"] else "deactivated"
    return success_response(f"Driver {label} successfully", data)


@router.post("/{driver_id}/assign", summary="Assign driver to vehicle (Admin)")
def assign_vehicle(
    driver_id: int,
    body:      AssignVehicleRequest,
    db:        Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = driver_service.assign_vehicle(db, driver_id, body, current_user.id)
    return success_response("Driver assigned to vehicle", data)


@router.patch("/{driver_id}/release", summary="Release driver from vehicle (Admin)")
def release_vehicle(
    driver_id: int,
    db:        Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = driver_service.release_vehicle(db, driver_id, current_user.id)
    return success_response("Driver released from vehicle", data)


@router.get("/{driver_id}/assignments", summary="Get driver assignment history (Admin)")
def get_assignments(
    driver_id: int,
    page:      int = Query(1, ge=1),
    limit:     int = Query(20, ge=1, le=100),
    db:        Session = Depends(get_db),
    _:         User    = Depends(get_admin_user),
):
    data, total = driver_service.get_assignments(db, driver_id, page, limit)
    return paginated_response("Assignment history retrieved", data, total, page, limit)
