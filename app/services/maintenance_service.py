from sqlalchemy.orm import Session

from app.models.maintenance_record import MaintenanceRecord
from app.models.resource import Resource, ResourceStatus
from app.schemas.maintenance import MaintenanceCreateRequest, MaintenanceUpdateRequest
from app.utils.audit import log_action
from app.utils.exceptions import NotFoundException


def _serialize(m: MaintenanceRecord) -> dict:
    return {
        "id": m.id,
        "resource": {
            "id":     m.resource.id,
            "name":   m.resource.name,
            "type":   m.resource.type.value,
            "status": m.resource.status.value,
        },
        "description": m.description,
        "startDate":   m.startDate.isoformat(),
        "endDate":     m.endDate.isoformat() if m.endDate else None,
        "isOngoing":   m.endDate is None,
        "cost":        float(m.cost) if m.cost else None,
        "createdBy": {
            "id":   m.created_by.id,
            "name": m.created_by.name,
        },
        "createdAt": m.createdAt.isoformat(),
    }


class MaintenanceService:

    def list_records(
        self, db: Session, page: int, limit: int,
        resource_id: int | None, resource_type: str | None, ongoing: bool | None,
    ) -> tuple[list[dict], int]:
        q = db.query(MaintenanceRecord).join(MaintenanceRecord.resource)

        if resource_id:    q = q.filter(MaintenanceRecord.resourceId == resource_id)
        if resource_type:  q = q.filter(Resource.type == resource_type)
        if ongoing is True:  q = q.filter(MaintenanceRecord.endDate == None)
        if ongoing is False: q = q.filter(MaintenanceRecord.endDate != None)

        total = q.count()
        items = q.order_by(MaintenanceRecord.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()
        return [_serialize(m) for m in items], total

    def get_record(self, db: Session, record_id: int) -> dict:
        m = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
        if not m: raise NotFoundException("Maintenance record")
        return _serialize(m)

    def create_record(self, db: Session, data: MaintenanceCreateRequest, actor_id: int) -> dict:
        resource = db.query(Resource).filter(Resource.id == data.resourceId).first()
        if not resource: raise NotFoundException("Resource")

        # Auto-set resource to MAINTENANCE
        resource.status = ResourceStatus.MAINTENANCE

        record = MaintenanceRecord(
            resourceId=data.resourceId,
            description=data.description,
            startDate=data.startDate,
            endDate=data.endDate,
            cost=data.cost,
            createdById=actor_id,
        )
        db.add(record)
        db.flush()
        log_action(db, actor_id, "CREATE", "MaintenanceRecord", record.id,
                   f"Maintenance started for resource '{resource.name}'")
        db.commit()
        db.refresh(record)
        return _serialize(record)

    def update_record(self, db: Session, record_id: int, data: MaintenanceUpdateRequest, actor_id: int) -> dict:
        m = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
        if not m: raise NotFoundException("Maintenance record")

        if data.description is not None: m.description = data.description
        if data.startDate is not None:   m.startDate   = data.startDate
        if data.cost is not None:        m.cost        = data.cost

        # When endDate is set -> maintenance completed -> restore resource to AVAILABLE
        if data.endDate is not None:
            m.endDate = data.endDate
            m.resource.status = ResourceStatus.AVAILABLE
            log_action(db, actor_id, "COMPLETE", "MaintenanceRecord", m.id,
                       f"Maintenance completed for '{m.resource.name}' — status restored to AVAILABLE")
        else:
            log_action(db, actor_id, "UPDATE", "MaintenanceRecord", m.id,
                       f"Updated maintenance record #{m.id}")

        db.commit()
        db.refresh(m)
        return _serialize(m)

    def delete_record(self, db: Session, record_id: int, actor_id: int) -> None:
        m = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
        if not m: raise NotFoundException("Maintenance record")
        log_action(db, actor_id, "DELETE", "MaintenanceRecord", record_id,
                   f"Deleted maintenance record #{record_id}")
        db.delete(m)
        db.commit()


maintenance_service = MaintenanceService()
