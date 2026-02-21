from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.driver_assignment import DriverAssignment
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.role import RoleName
from app.schemas.driver import DriverCreateRequest, DriverUpdateRequest, AssignVehicleRequest
from app.utils.audit import log_action
from app.utils.exceptions import (
    NotFoundException, DuplicateEntryException, ForbiddenException
)


def _serialize(d: Driver, with_assignment: bool = True) -> dict:
    result = {
        "id":            d.id,
        "user": {
            "id":         d.user.id,
            "name":       d.user.name,
            "employeeId": d.user.employeeId,
            "email":      d.user.email,
        },
        "licenseNumber": d.licenseNumber,
        "phoneNumber":   d.phoneNumber,
        "isActive":      d.isActive,
        "createdAt":     d.createdAt.isoformat(),
    }
    if with_assignment:
        active = next((a for a in d.assignments if a.releasedAt is None), None)
        result["currentAssignment"] = {
            "assignmentId": active.id,
            "vehicle": {
                "id":          active.vehicle.id,
                "plateNumber": active.vehicle.plateNumber,
                "brand":       active.vehicle.brand,
                "model":       active.vehicle.model,
            },
            "assignedAt": active.assignedAt.isoformat(),
        } if active else None
    return result


class DriverService:

    def list_drivers(self, db: Session, page: int, limit: int, is_active: bool | None) -> tuple[list[dict], int]:
        q = db.query(Driver)
        if is_active is not None:
            q = q.filter(Driver.isActive == is_active)
        total = q.count()
        items = q.order_by(Driver.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()
        return [_serialize(d) for d in items], total

    def get_driver(self, db: Session, driver_id: int) -> dict:
        d = db.query(Driver).filter(Driver.id == driver_id).first()
        if not d: raise NotFoundException("Driver")
        return _serialize(d)

    def create_driver(self, db: Session, data: DriverCreateRequest, actor_id: int) -> dict:
        user = db.query(User).filter(User.id == data.userId).first()
        if not user: raise NotFoundException("User")
        if user.role.name != RoleName.DRIVER:
            raise ForbiddenException("User must have DRIVER role to be registered as a driver")
        if db.query(Driver).filter(Driver.userId == data.userId).first():
            raise DuplicateEntryException("This user is already registered as a driver")

        d = Driver(
            userId=data.userId,
            licenseNumber=data.licenseNumber,
            phoneNumber=data.phoneNumber,
            isActive=True,
        )
        db.add(d)
        db.flush()
        log_action(db, actor_id, "CREATE", "Driver", d.id,
                   f"Registered driver {user.name} ({data.licenseNumber})")
        db.commit()
        db.refresh(d)
        return _serialize(d)

    def update_driver(self, db: Session, driver_id: int, data: DriverUpdateRequest, actor_id: int) -> dict:
        d = db.query(Driver).filter(Driver.id == driver_id).first()
        if not d: raise NotFoundException("Driver")

        if data.licenseNumber: d.licenseNumber = data.licenseNumber
        if data.phoneNumber:   d.phoneNumber   = data.phoneNumber

        log_action(db, actor_id, "UPDATE", "Driver", d.id, f"Updated driver {d.user.name}")
        db.commit()
        db.refresh(d)
        return _serialize(d)

    def toggle_active(self, db: Session, driver_id: int, actor_id: int) -> dict:
        d = db.query(Driver).filter(Driver.id == driver_id).first()
        if not d: raise NotFoundException("Driver")
        d.isActive = not d.isActive
        action = "ACTIVATE" if d.isActive else "DEACTIVATE"
        log_action(db, actor_id, action, "Driver", d.id, f"{action} driver {d.user.name}")
        db.commit()
        db.refresh(d)
        return _serialize(d)

    def assign_vehicle(self, db: Session, driver_id: int, data: AssignVehicleRequest, actor_id: int) -> dict:
        d = db.query(Driver).filter(Driver.id == driver_id).first()
        if not d: raise NotFoundException("Driver")
        if not d.isActive: raise ForbiddenException("Cannot assign vehicle to inactive driver")

        vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicleId).first()
        if not vehicle: raise NotFoundException("Vehicle")

        # Check driver not already assigned
        existing_driver = db.query(DriverAssignment).filter(
            DriverAssignment.driverId == driver_id,
            DriverAssignment.releasedAt == None,
        ).first()
        if existing_driver:
            raise ForbiddenException("Driver already has an active vehicle assignment. Release first.")

        # Check vehicle not already taken
        existing_vehicle = db.query(DriverAssignment).filter(
            DriverAssignment.vehicleId == data.vehicleId,
            DriverAssignment.releasedAt == None,
        ).first()
        if existing_vehicle:
            raise ForbiddenException("Vehicle is already assigned to another driver")

        assignment = DriverAssignment(
            driverId=driver_id,
            vehicleId=data.vehicleId,
            assignedAt=datetime.now(timezone.utc),
        )
        db.add(assignment)
        db.flush()
        log_action(db, actor_id, "ASSIGN", "DriverAssignment", assignment.id,
                   f"Driver {d.user.name} assigned to vehicle {vehicle.plateNumber}")
        db.commit()
        db.refresh(assignment)
        return {
            "assignmentId": assignment.id,
            "driverId":     driver_id,
            "vehicle": {
                "id":          vehicle.id,
                "plateNumber": vehicle.plateNumber,
                "brand":       vehicle.brand,
                "model":       vehicle.model,
            },
            "assignedAt": assignment.assignedAt.isoformat(),
        }

    def release_vehicle(self, db: Session, driver_id: int, actor_id: int) -> dict:
        d = db.query(Driver).filter(Driver.id == driver_id).first()
        if not d: raise NotFoundException("Driver")

        assignment = db.query(DriverAssignment).filter(
            DriverAssignment.driverId == driver_id,
            DriverAssignment.releasedAt == None,
        ).first()
        if not assignment:
            raise NotFoundException("Active driver assignment")

        assignment.releasedAt = datetime.now(timezone.utc)
        log_action(db, actor_id, "RELEASE", "DriverAssignment", assignment.id,
                   f"Driver {d.user.name} released from vehicle")
        db.commit()
        return {"message": "Driver released successfully", "releasedAt": assignment.releasedAt.isoformat()}

    def get_assignments(self, db: Session, driver_id: int, page: int, limit: int) -> tuple[list[dict], int]:
        d = db.query(Driver).filter(Driver.id == driver_id).first()
        if not d: raise NotFoundException("Driver")

        q = db.query(DriverAssignment).filter(DriverAssignment.driverId == driver_id)\
              .order_by(DriverAssignment.assignedAt.desc())
        total = q.count()
        items = q.offset((page - 1) * limit).limit(limit).all()
        return [{
            "id":         a.id,
            "vehicle": {
                "id":          a.vehicle.id,
                "plateNumber": a.vehicle.plateNumber,
                "brand":       a.vehicle.brand,
                "model":       a.vehicle.model,
            },
            "assignedAt":  a.assignedAt.isoformat(),
            "releasedAt":  a.releasedAt.isoformat() if a.releasedAt else None,
            "isActive":    a.releasedAt is None,
        } for a in items], total


driver_service = DriverService()
