from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.fuel_expense import FuelExpense
from app.models.driver import Driver
from app.models.driver_assignment import DriverAssignment
from app.models.vehicle import Vehicle
from app.models.role import RoleName
from app.models.user import User
from app.schemas.fuel_expense import FuelExpenseCreateRequest, FuelExpenseUpdateRequest
from app.utils.audit import log_action
from app.utils.exceptions import (
    NotFoundException, ForbiddenException, DriverNotAssignedException
)


def _serialize(fe: FuelExpense) -> dict:
    return {
        "id": fe.id,
        "driver": {
            "id":   fe.driver.id,
            "name": fe.driver.user.name,
        },
        "vehicle": {
            "id":          fe.vehicle.id,
            "plateNumber": fe.vehicle.plateNumber,
            "brand":       fe.vehicle.brand,
            "model":       fe.vehicle.model,
        },
        "bookingId":     fe.bookingId,
        "liter":         float(fe.liter),
        "pricePerLiter": float(fe.pricePerLiter),
        "totalAmount":   float(fe.totalAmount),
        "odometerBefore": fe.odometerBefore,
        "odometerAfter":  fe.odometerAfter,
        "distanceKm":    fe.odometerAfter - fe.odometerBefore,
        "note":          fe.note,
        "createdAt":     fe.createdAt.isoformat(),
    }


class FuelExpenseService:

    def list_expenses(
        self, db: Session, current_user: User,
        page: int, limit: int,
        vehicle_id: int | None, driver_id: int | None,
        start_date: str | None, end_date: str | None,
    ) -> tuple[list[dict], int]:
        q = db.query(FuelExpense)

        # Driver can only see own expenses
        if current_user.role.name == RoleName.DRIVER:
            driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
            if not driver: return [], 0
            q = q.filter(FuelExpense.driverId == driver.id)
        elif driver_id:
            q = q.filter(FuelExpense.driverId == driver_id)

        if vehicle_id:  q = q.filter(FuelExpense.vehicleId == vehicle_id)
        if start_date:  q = q.filter(FuelExpense.createdAt >= start_date)
        if end_date:    q = q.filter(FuelExpense.createdAt <= end_date)

        total = q.count()
        items = q.order_by(FuelExpense.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()
        return [_serialize(fe) for fe in items], total

    def get_expense(self, db: Session, expense_id: int, current_user: User) -> dict:
        fe = db.query(FuelExpense).filter(FuelExpense.id == expense_id).first()
        if not fe: raise NotFoundException("Fuel expense")
        if current_user.role.name == RoleName.DRIVER:
            driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
            if not driver or fe.driverId != driver.id:
                raise ForbiddenException("You can only view your own fuel expenses")
        return _serialize(fe)

    def create_expense(self, db: Session, data: FuelExpenseCreateRequest, current_user: User) -> dict:
        # Resolve driver
        driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
        if not driver: raise NotFoundException("Driver profile for current user")

        # Must have active assignment
        assignment = db.query(DriverAssignment).filter(
            DriverAssignment.driverId == driver.id,
            DriverAssignment.releasedAt == None,
        ).first()
        if not assignment: raise DriverNotAssignedException()

        # Must submit for assigned vehicle
        if assignment.vehicleId != data.vehicleId:
            raise ForbiddenException("You can only submit fuel expenses for your currently assigned vehicle")

        vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicleId).first()
        if not vehicle: raise NotFoundException("Vehicle")

        total = Decimal(str(data.liter)) * Decimal(str(data.pricePerLiter))

        fe = FuelExpense(
            driverId=driver.id,
            vehicleId=data.vehicleId,
            bookingId=data.bookingId,
            liter=data.liter,
            pricePerLiter=data.pricePerLiter,
            totalAmount=total,
            odometerBefore=data.odometerBefore,
            odometerAfter=data.odometerAfter,
            note=data.note,
        )
        db.add(fe)
        db.flush()

        # Update vehicle odometer
        vehicle.currentOdometer = data.odometerAfter

        log_action(db, current_user.id, "CREATE", "FuelExpense", fe.id,
                   f"Driver {driver.user.name} submitted fuel expense {data.liter}L for {vehicle.plateNumber}")
        db.commit()
        db.refresh(fe)
        return _serialize(fe)

    def update_expense(self, db: Session, expense_id: int, data: FuelExpenseUpdateRequest, current_user: User) -> dict:
        fe = db.query(FuelExpense).filter(FuelExpense.id == expense_id).first()
        if not fe: raise NotFoundException("Fuel expense")

        if data.liter is not None:         fe.liter          = data.liter
        if data.pricePerLiter is not None: fe.pricePerLiter  = data.pricePerLiter
        if data.odometerBefore is not None: fe.odometerBefore = data.odometerBefore
        if data.odometerAfter is not None:  fe.odometerAfter  = data.odometerAfter
        if data.note is not None:           fe.note           = data.note

        # Recalculate total
        fe.totalAmount = Decimal(str(fe.liter)) * Decimal(str(fe.pricePerLiter))

        log_action(db, current_user.id, "UPDATE", "FuelExpense", fe.id, f"Updated fuel expense #{fe.id}")
        db.commit()
        db.refresh(fe)
        return _serialize(fe)

    def delete_expense(self, db: Session, expense_id: int, current_user: User) -> None:
        fe = db.query(FuelExpense).filter(FuelExpense.id == expense_id).first()
        if not fe: raise NotFoundException("Fuel expense")
        log_action(db, current_user.id, "DELETE", "FuelExpense", expense_id,
                   f"Deleted fuel expense #{expense_id}")
        db.delete(fe)
        db.commit()


fuel_service = FuelExpenseService()
