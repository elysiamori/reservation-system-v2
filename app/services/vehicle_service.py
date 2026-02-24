from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.resource import Resource, ResourceType, ResourceStatus
from app.models.vehicle import Vehicle
from app.models.vehicle_category import VehicleCategory
from app.schemas.vehicle import (
    VehicleCreateRequest, VehicleUpdateRequest,
    VehicleStatusRequest, CategoryCreateRequest,
)
from app.utils.audit import log_action
from app.utils.exceptions import NotFoundException, DuplicateEntryException


def _serialize(v: Vehicle) -> dict:
    return {
        "id": v.id,
        "resource": {
            "id":     v.resource.id,
            "name":   v.resource.name,
            "type":   v.resource.type.value,
            "status": v.resource.status.value,
        },
        "plateNumber":     v.plateNumber,
        "brand":           v.brand,
        "model":           v.model,
        "year":            v.year,
        "currentOdometer": v.currentOdometer,
        "capacity":        v.capacity,
        "category":        {"id": v.category.id, "name": v.category.name},
    }


class VehicleService:

    def list_vehicles(
        self, db: Session, page: int, limit: int,
        search: str | None, category_id: int | None, status: str | None,
    ) -> tuple[list[dict], int]:
        q = db.query(Vehicle).join(Vehicle.resource).join(Vehicle.category)

        if search:
            kw = f"%{search}%"
            q = q.filter(or_(
                Vehicle.plateNumber.ilike(kw),
                Vehicle.brand.ilike(kw),
                Vehicle.model.ilike(kw),
                Resource.name.ilike(kw),
            ))
        if category_id:
            q = q.filter(Vehicle.categoryId == category_id)
        if status:
            q = q.filter(Resource.status == status)

        total = q.count()
        items = q.order_by(Resource.name).offset((page - 1) * limit).limit(limit).all()
        return [_serialize(v) for v in items], total

    def get_vehicle(self, db: Session, vehicle_id: int) -> dict:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise NotFoundException("Vehicle")
        return _serialize(v)

    def create_vehicle(self, db: Session, data: VehicleCreateRequest, actor_id: int) -> dict:
        if not db.query(VehicleCategory).filter(VehicleCategory.id == data.categoryId).first():
            raise NotFoundException("Vehicle category")
        if db.query(Vehicle).filter(Vehicle.plateNumber == data.plateNumber).first():
            raise DuplicateEntryException("Plate number already registered", field="plateNumber")

        resource = Resource(name=data.name, type=ResourceType.VEHICLE, status=ResourceStatus.AVAILABLE)
        db.add(resource)
        db.flush()

        vehicle = Vehicle(
            resourceId=resource.id,
            plateNumber=data.plateNumber,
            brand=data.brand,
            model=data.model,
            year=data.year,
            currentOdometer=data.currentOdometer,
            categoryId=data.categoryId,
            capacity=data.capacity,
        )
        db.add(vehicle)
        db.flush()
        log_action(db, actor_id, "CREATE", "Vehicle", vehicle.id,
                   f"Created vehicle {data.plateNumber} ({data.brand} {data.model})")
        db.commit()
        db.refresh(vehicle)
        return _serialize(vehicle)

    def update_vehicle(self, db: Session, vehicle_id: int, data: VehicleUpdateRequest, actor_id: int) -> dict:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise NotFoundException("Vehicle")

        if data.plateNumber and data.plateNumber != v.plateNumber:
            if db.query(Vehicle).filter(Vehicle.plateNumber == data.plateNumber, Vehicle.id != vehicle_id).first():
                raise DuplicateEntryException("Plate number already used", field="plateNumber")
        if data.categoryId and not db.query(VehicleCategory).filter(VehicleCategory.id == data.categoryId).first():
            raise NotFoundException("Vehicle category")

        if data.name:            v.resource.name   = data.name
        if data.brand:           v.brand            = data.brand
        if data.model:           v.model            = data.model
        if data.year:            v.year             = data.year
        if data.currentOdometer is not None: v.currentOdometer = data.currentOdometer
        if data.categoryId:      v.categoryId       = data.categoryId
        if data.plateNumber:     v.plateNumber      = data.plateNumber
        if data.capacity is not None: v.capacity    = data.capacity

        log_action(db, actor_id, "UPDATE", "Vehicle", v.id, f"Updated vehicle {v.plateNumber}")
        db.commit()
        db.refresh(v)
        return _serialize(v)

    def update_status(self, db: Session, vehicle_id: int, data: VehicleStatusRequest, actor_id: int) -> dict:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise NotFoundException("Vehicle")

        old_status = v.resource.status.value
        v.resource.status = data.status
        log_action(db, actor_id, "UPDATE", "Vehicle", v.id,
                   f"Status changed {old_status} -> {data.status.value}" +
                   (f" | Reason: {data.reason}" if data.reason else ""))
        db.commit()
        db.refresh(v)
        return _serialize(v)

    def delete_vehicle(self, db: Session, vehicle_id: int, actor_id: int) -> None:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise NotFoundException("Vehicle")
        resource_id = v.resourceId
        log_action(db, actor_id, "DELETE", "Vehicle", vehicle_id,
                   f"Deleted vehicle {v.plateNumber}")
        db.delete(v)
        db.flush()
        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if resource:
            db.delete(resource)
        db.commit()

    # ─── Categories ───────────────────────────────────────────────────────────
    def list_categories(self, db: Session) -> list[dict]:
        cats = db.query(VehicleCategory).order_by(VehicleCategory.name).all()
        return [{"id": c.id, "name": c.name} for c in cats]

    def create_category(self, db: Session, data: CategoryCreateRequest, actor_id: int) -> dict:
        if db.query(VehicleCategory).filter(VehicleCategory.name == data.name).first():
            raise DuplicateEntryException("Category already exists", field="name")
        cat = VehicleCategory(name=data.name)
        db.add(cat)
        db.flush()
        log_action(db, actor_id, "CREATE", "VehicleCategory", cat.id, f"Created category {cat.name}")
        db.commit()
        db.refresh(cat)
        return {"id": cat.id, "name": cat.name}

    def delete_category(self, db: Session, category_id: int, actor_id: int) -> None:
        cat = db.query(VehicleCategory).filter(VehicleCategory.id == category_id).first()
        if not cat:
            raise NotFoundException("Vehicle category")
        log_action(db, actor_id, "DELETE", "VehicleCategory", category_id, f"Deleted category {cat.name}")
        db.delete(cat)
        db.commit()


vehicle_service = VehicleService()
