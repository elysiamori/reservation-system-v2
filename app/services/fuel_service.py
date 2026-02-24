from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.fuel_expense import FuelExpense, FuelType
from app.models.driver import Driver
from app.models.vehicle import Vehicle
from app.models.master_setting import MasterSetting
from app.models.role import RoleName
from app.models.user import User
from app.schemas.fuel_expense import FuelExpenseCreateRequest, FuelExpenseUpdateRequest
from app.utils.audit import log_action
from app.utils.exceptions import NotFoundException, ForbiddenException


SETTING_KEY_BBM = "price_per_liter_bbm"
SETTING_KEY_KWH = "price_per_kwh_listrik"


def _get_default_price(db: Session, key: str) -> Decimal | None:
    setting = db.query(MasterSetting).filter(MasterSetting.key == key).first()
    return Decimal(str(setting.value)) if setting else None


def _serialize(e: FuelExpense) -> dict:
    base = {
        "id":        e.id,
        "fuelType":  e.fuelType.value,
        "driver": {
            "id":   e.driver.id,
            "name": e.driver.user.name,
        },
        "vehicle": {
            "id":          e.vehicle.id,
            "plateNumber": e.vehicle.plateNumber,
        },
        "bookingId":   e.bookingId,
        "totalAmount": float(e.totalAmount),
        "note":        e.note,
        "createdAt":   e.createdAt.isoformat(),
    }
    if e.fuelType == FuelType.BBM:
        base.update({
            "liter":          float(e.liter) if e.liter else None,
            "pricePerLiter":  float(e.pricePerLiter) if e.pricePerLiter else None,
            "odometerBefore": e.odometerBefore,
            "odometerAfter":  e.odometerAfter,
        })
    else:
        base.update({
            "kwh":          float(e.kwh) if e.kwh else None,
            "pricePerKwh":  float(e.pricePerKwh) if e.pricePerKwh else None,
            "batteryBefore": float(e.batteryBefore) if e.batteryBefore else None,
            "batteryAfter":  float(e.batteryAfter) if e.batteryAfter else None,
        })
    return base


class FuelService:

    def list_expenses(
        self, db: Session, current_user: User,
        page: int, limit: int,
        vehicle_id: int | None, driver_id: int | None,
        start_date: str | None, end_date: str | None,
        fuel_type: str | None = None,
    ) -> tuple[list[dict], int]:
        q = db.query(FuelExpense)
        if current_user.role.name == RoleName.DRIVER:
            driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
            if driver:
                q = q.filter(FuelExpense.driverId == driver.id)
            else:
                return [], 0

        if vehicle_id: q = q.filter(FuelExpense.vehicleId == vehicle_id)
        if driver_id:  q = q.filter(FuelExpense.driverId  == driver_id)
        if fuel_type:  q = q.filter(FuelExpense.fuelType  == fuel_type)
        if start_date: q = q.filter(FuelExpense.createdAt >= start_date)
        if end_date:   q = q.filter(FuelExpense.createdAt <= end_date)

        total = q.count()
        items = q.order_by(FuelExpense.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()
        return [_serialize(e) for e in items], total

    def get_expense(self, db: Session, expense_id: int, current_user: User) -> dict:
        e = db.query(FuelExpense).filter(FuelExpense.id == expense_id).first()
        if not e:
            raise NotFoundException("Fuel expense")
        if current_user.role.name == RoleName.DRIVER:
            driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
            if not driver or e.driverId != driver.id:
                raise ForbiddenException("You can only view your own fuel expenses")
        return _serialize(e)

    def create_expense(self, db: Session, data: FuelExpenseCreateRequest, current_user: User) -> dict:
        driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
        if not driver:
            raise NotFoundException("Driver profile for this user")

        vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicleId).first()
        if not vehicle:
            raise NotFoundException("Vehicle")

        total_amount: Decimal

        if data.fuelType == FuelType.BBM:
            price = data.pricePerLiter
            if price is None:
                price = _get_default_price(db, SETTING_KEY_BBM)
            if price is None:
                raise ForbiddenException("No price per liter set. Please input manually or set master settings.")
            total_amount = data.liter * price

            expense = FuelExpense(
                driverId=driver.id,
                vehicleId=data.vehicleId,
                bookingId=data.bookingId,
                fuelType=FuelType.BBM,
                liter=data.liter,
                pricePerLiter=price,
                odometerBefore=data.odometerBefore,
                odometerAfter=data.odometerAfter,
                totalAmount=total_amount,
                note=data.note,
            )
            # Update vehicle odometer
            if data.odometerAfter > vehicle.currentOdometer:
                vehicle.currentOdometer = data.odometerAfter

        else:  # LISTRIK
            price = data.pricePerKwh
            if price is None:
                price = _get_default_price(db, SETTING_KEY_KWH)
            if price is None:
                raise ForbiddenException("No price per kWh set. Please input manually or set master settings.")
            total_amount = data.kwh * price

            expense = FuelExpense(
                driverId=driver.id,
                vehicleId=data.vehicleId,
                bookingId=data.bookingId,
                fuelType=FuelType.LISTRIK,
                kwh=data.kwh,
                pricePerKwh=price,
                batteryBefore=data.batteryBefore,
                batteryAfter=data.batteryAfter,
                totalAmount=total_amount,
                note=data.note,
            )

        db.add(expense)
        db.flush()
        log_action(db, current_user.id, "CREATE", "FuelExpense", expense.id,
                   f"Driver {driver.user.name} submitted {data.fuelType.value} expense for vehicle {vehicle.plateNumber}")
        db.commit()
        db.refresh(expense)
        return _serialize(expense)

    def update_expense(self, db: Session, expense_id: int, data: FuelExpenseUpdateRequest, current_user: User) -> dict:
        e = db.query(FuelExpense).filter(FuelExpense.id == expense_id).first()
        if not e:
            raise NotFoundException("Fuel expense")

        for field, val in data.model_dump(exclude_none=True).items():
            setattr(e, field, val)

        # Recalculate total
        if e.fuelType == FuelType.BBM and e.liter and e.pricePerLiter:
            e.totalAmount = e.liter * e.pricePerLiter
        elif e.fuelType == FuelType.LISTRIK and e.kwh and e.pricePerKwh:
            e.totalAmount = e.kwh * e.pricePerKwh

        log_action(db, current_user.id, "UPDATE", "FuelExpense", e.id, "Fuel expense updated by admin")
        db.commit()
        db.refresh(e)
        return _serialize(e)

    def delete_expense(self, db: Session, expense_id: int, current_user: User) -> None:
        e = db.query(FuelExpense).filter(FuelExpense.id == expense_id).first()
        if not e:
            raise NotFoundException("Fuel expense")
        log_action(db, current_user.id, "DELETE", "FuelExpense", e.id, "Fuel expense deleted")
        db.delete(e)
        db.commit()


fuel_service = FuelService()
