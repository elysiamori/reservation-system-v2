from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_admin_user
from app.models.user import User
from app.schemas.maintenance import MaintenanceCreateRequest, MaintenanceUpdateRequest
from app.schemas.common import success_response, paginated_response
from app.services.maintenance_service import maintenance_service

router = APIRouter(prefix="/maintenance")


@router.get("", summary="List maintenance records (Admin)")
def list_records(
    page:         int            = Query(1, ge=1),
    limit:        int            = Query(20, ge=1, le=100),
    resourceId:   Optional[int]  = Query(None),
    resourceType: Optional[str]  = Query(None, description="VEHICLE | ROOM"),
    ongoing:      Optional[bool] = Query(None, description="True=ongoing only, False=completed only"),
    db:           Session        = Depends(get_db),
    _:            User           = Depends(get_admin_user),
):
    data, total = maintenance_service.list_records(db, page, limit, resourceId, resourceType, ongoing)
    return paginated_response("Maintenance records retrieved", data, total, page, limit)


@router.get("/{record_id}", summary="Get maintenance record (Admin)")
def get_record(record_id: int, db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    return success_response("Record retrieved", maintenance_service.get_record(db, record_id))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create maintenance record (Admin)")
def create_record(
    body: MaintenanceCreateRequest,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = maintenance_service.create_record(db, body, current_user.id)
    return success_response("Maintenance record created. Resource status set to MAINTENANCE.", data)


@router.put("/{record_id}", summary="Update maintenance record (Admin)")
def update_record(
    record_id: int,
    body:      MaintenanceUpdateRequest,
    db:        Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = maintenance_service.update_record(db, record_id, body, current_user.id)
    return success_response("Maintenance record updated", data)


@router.delete("/{record_id}", summary="Delete maintenance record (Admin)")
def delete_record(
    record_id: int,
    db:        Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    maintenance_service.delete_record(db, record_id, current_user.id)
    return success_response("Maintenance record deleted", None)
