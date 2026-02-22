from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_admin_user
from app.models.user import User
from app.schemas.vehicle import (
    VehicleCreateRequest, VehicleUpdateRequest,
    VehicleStatusRequest, CategoryCreateRequest,
)
from app.schemas.common import success_response, paginated_response
from app.services.vehicle_service import vehicle_service

router = APIRouter(prefix="/vehicles")


@router.get("", summary="List vehicles (paginated)")
def list_vehicles(
    page:       int           = Query(1, ge=1),
    limit:      int           = Query(20, ge=1, le=100),
    search:     Optional[str] = Query(None),
    categoryId: Optional[int] = Query(None),
    status:     Optional[str] = Query(None, description="AVAILABLE | MAINTENANCE | INACTIVE"),
    db:         Session       = Depends(get_db),
    # _:          User          = Depends(get_current_user),
):
    data, total = vehicle_service.list_vehicles(db, page, limit, search, categoryId, status)
    return paginated_response("Vehicles retrieved successfully", data, total, page, limit)


@router.get("/categories", summary="List vehicle categories")
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return success_response("Categories retrieved", vehicle_service.list_categories(db))


@router.get("/{vehicle_id}", summary="Get vehicle by ID")
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return success_response("Vehicle retrieved", vehicle_service.get_vehicle(db, vehicle_id))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create vehicle (Admin)")
def create_vehicle(
    body: VehicleCreateRequest,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = vehicle_service.create_vehicle(db, body, current_user.id)
    return success_response("Vehicle created successfully", data)


@router.post("/categories", status_code=status.HTTP_201_CREATED, summary="Create vehicle category (Admin)")
def create_category(
    body: CategoryCreateRequest,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = vehicle_service.create_category(db, body, current_user.id)
    return success_response("Category created successfully", data)


@router.put("/{vehicle_id}", summary="Update vehicle (Admin)")
def update_vehicle(
    vehicle_id: int,
    body:       VehicleUpdateRequest,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    data = vehicle_service.update_vehicle(db, vehicle_id, body, current_user.id)
    return success_response("Vehicle updated successfully", data)


@router.patch("/{vehicle_id}/status", summary="Change vehicle status (Admin)")
def update_status(
    vehicle_id: int,
    body:       VehicleStatusRequest,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    data = vehicle_service.update_status(db, vehicle_id, body, current_user.id)
    return success_response("Vehicle status updated", data)


@router.delete("/{vehicle_id}", summary="Delete vehicle (Admin)")
def delete_vehicle(
    vehicle_id: int,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    vehicle_service.delete_vehicle(db, vehicle_id, current_user.id)
    return success_response("Vehicle deleted successfully", None)


@router.delete("/categories/{category_id}", summary="Delete vehicle category (Admin)")
def delete_category(
    category_id: int,
    db:          Session = Depends(get_db),
    current_user: User   = Depends(get_admin_user),
):
    vehicle_service.delete_category(db, category_id, current_user.id)
    return success_response("Category deleted successfully", None)
