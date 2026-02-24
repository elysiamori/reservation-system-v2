from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_admin_user, get_admin_or_driver
from app.models.user import User
from app.models.role import RoleName
from app.schemas.fuel_expense import FuelExpenseCreateRequest, FuelExpenseUpdateRequest
from app.schemas.common import success_response, paginated_response
from app.services.fuel_service import fuel_service
from app.utils.exceptions import ForbiddenException

router = APIRouter(prefix="/fuel-expenses")


@router.get("", summary="List fuel expenses (Admin or own Driver)")
def list_expenses(
    page:      int            = Query(1, ge=1),
    limit:     int            = Query(20, ge=1, le=100),
    vehicleId: Optional[int]  = Query(None),
    driverId:  Optional[int]  = Query(None),
    fuelType:  Optional[str]  = Query(None, description="BBM | LISTRIK"),
    startDate: Optional[str]  = Query(None),
    endDate:   Optional[str]  = Query(None),
    db:        Session        = Depends(get_db),
    current_user: User        = Depends(get_admin_or_driver),
):
    data, total = fuel_service.list_expenses(
        db, current_user, page, limit, vehicleId, driverId, startDate, endDate, fuelType
    )
    return paginated_response("Fuel expenses retrieved", data, total, page, limit)


@router.get("/{expense_id}", summary="Get fuel expense detail")
def get_expense(
    expense_id: int,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_or_driver),
):
    return success_response("Fuel expense retrieved",
                            fuel_service.get_expense(db, expense_id, current_user))


@router.post("", status_code=status.HTTP_201_CREATED,
             summary="Submit fuel expense — BBM or Listrik (Driver)")
def create_expense(
    body: FuelExpenseCreateRequest,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != RoleName.DRIVER:
        raise ForbiddenException("Only DRIVER can submit fuel expenses")
    return success_response("Fuel expense submitted successfully",
                            fuel_service.create_expense(db, body, current_user))


@router.put("/{expense_id}", summary="Update fuel expense (Admin)")
def update_expense(
    expense_id: int,
    body:       FuelExpenseUpdateRequest,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    return success_response("Fuel expense updated",
                            fuel_service.update_expense(db, expense_id, body, current_user))


@router.delete("/{expense_id}", summary="Delete fuel expense (Admin)")
def delete_expense(
    expense_id: int,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(get_admin_user),
):
    fuel_service.delete_expense(db, expense_id, current_user)
    return success_response("Fuel expense deleted", None)
