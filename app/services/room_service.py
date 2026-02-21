from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.resource import Resource, ResourceType, ResourceStatus
from app.models.room import Room
from app.schemas.room import RoomCreateRequest, RoomUpdateRequest, RoomStatusRequest
from app.utils.audit import log_action
from app.utils.exceptions import NotFoundException


def _serialize(r: Room) -> dict:
    return {
        "id": r.id,
        "resource": {
            "id":     r.resource.id,
            "name":   r.resource.name,
            "type":   r.resource.type.value,
            "status": r.resource.status.value,
        },
        "location": r.location,
        "capacity": r.capacity,
    }


class RoomService:

    def list_rooms(
        self, db: Session, page: int, limit: int,
        search: str | None, status: str | None, min_capacity: int | None,
    ) -> tuple[list[dict], int]:
        q = db.query(Room).join(Room.resource)

        if search:
            kw = f"%{search}%"
            q = q.filter(or_(Resource.name.ilike(kw), Room.location.ilike(kw)))
        if status:
            q = q.filter(Resource.status == status)
        if min_capacity:
            q = q.filter(Room.capacity >= min_capacity)

        total = q.count()
        items = q.order_by(Resource.name).offset((page - 1) * limit).limit(limit).all()
        return [_serialize(r) for r in items], total

    def get_room(self, db: Session, room_id: int) -> dict:
        r = db.query(Room).filter(Room.id == room_id).first()
        if not r:
            raise NotFoundException("Room")
        return _serialize(r)

    def create_room(self, db: Session, data: RoomCreateRequest, actor_id: int) -> dict:
        resource = Resource(name=data.name, type=ResourceType.ROOM, status=ResourceStatus.AVAILABLE)
        db.add(resource)
        db.flush()

        room = Room(resourceId=resource.id, location=data.location, capacity=data.capacity)
        db.add(room)
        db.flush()
        log_action(db, actor_id, "CREATE", "Room", room.id,
                   f"Created room '{data.name}' at {data.location}")
        db.commit()
        db.refresh(room)
        return _serialize(room)

    def update_room(self, db: Session, room_id: int, data: RoomUpdateRequest, actor_id: int) -> dict:
        r = db.query(Room).filter(Room.id == room_id).first()
        if not r:
            raise NotFoundException("Room")

        if data.name:     r.resource.name = data.name
        if data.location: r.location       = data.location
        if data.capacity is not None: r.capacity = data.capacity

        log_action(db, actor_id, "UPDATE", "Room", r.id, f"Updated room '{r.resource.name}'")
        db.commit()
        db.refresh(r)
        return _serialize(r)

    def update_status(self, db: Session, room_id: int, data: RoomStatusRequest, actor_id: int) -> dict:
        r = db.query(Room).filter(Room.id == room_id).first()
        if not r:
            raise NotFoundException("Room")

        old = r.resource.status.value
        r.resource.status = data.status
        log_action(db, actor_id, "UPDATE", "Room", r.id,
                   f"Status {old} -> {data.status.value}" + (f" | {data.reason}" if data.reason else ""))
        db.commit()
        db.refresh(r)
        return _serialize(r)

    def delete_room(self, db: Session, room_id: int, actor_id: int) -> None:
        r = db.query(Room).filter(Room.id == room_id).first()
        if not r:
            raise NotFoundException("Room")
        resource_id = r.resourceId
        log_action(db, actor_id, "DELETE", "Room", room_id, f"Deleted room '{r.resource.name}'")
        db.delete(r)
        db.flush()
        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if resource:
            db.delete(resource)
        db.commit()


room_service = RoomService()
