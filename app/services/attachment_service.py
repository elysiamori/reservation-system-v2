from sqlalchemy.orm import Session
from app.models.attachment import Attachment
from app.models.vehicle import Vehicle
from app.models.room import Room
from app.models.booking import Booking
from app.models.user import User
from app.schemas.attachment import AttachmentCreateRequest, ProfilePhotoRequest
from app.utils.exceptions import NotFoundException, ForbiddenException


def _serialize(a: Attachment) -> dict:
    return {
        "id":          a.id,
        "fileUrl":     a.fileUrl,
        "fileName":    a.fileName,
        "fileType":    a.fileType,
        "fileSize":    a.fileSize,
        "description": a.description,
        "uploadedBy":  {"id": a.uploaded_by.id, "name": a.uploaded_by.name} if a.uploaded_by else None,
        "createdAt":   a.createdAt.isoformat() if a.createdAt else None,
    }


# ─── VEHICLE ATTACHMENTS ──────────────────────────────────────────────────────
def list_vehicle_attachments(db: Session, vehicle_id: int) -> list[dict]:
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise NotFoundException("Vehicle")
    items = db.query(Attachment).filter(Attachment.vehicleId == vehicle_id)\
               .order_by(Attachment.createdAt.desc()).all()
    return [_serialize(a) for a in items]


def add_vehicle_attachment(db: Session, vehicle_id: int, data: AttachmentCreateRequest, actor_id: int) -> dict:
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise NotFoundException("Vehicle")
    a = Attachment(vehicleId=vehicle_id, uploadedById=actor_id,
                   fileUrl=data.fileUrl, fileName=data.fileName,
                   fileType=data.fileType, fileSize=data.fileSize, description=data.description)
    db.add(a); db.commit(); db.refresh(a)
    return _serialize(a)


def delete_attachment(db: Session, attachment_id: int, actor_id: int, actor_role: str) -> None:
    a = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not a:
        raise NotFoundException("Attachment")
    if actor_role not in ("ADMIN",) and a.uploadedById != actor_id:
        raise ForbiddenException("Anda hanya bisa menghapus attachment yang Anda upload")
    db.delete(a); db.commit()


# ─── ROOM ATTACHMENTS ─────────────────────────────────────────────────────────
def list_room_attachments(db: Session, room_id: int) -> list[dict]:
    r = db.query(Room).filter(Room.id == room_id).first()
    if not r:
        raise NotFoundException("Room")
    items = db.query(Attachment).filter(Attachment.roomId == room_id)\
               .order_by(Attachment.createdAt.desc()).all()
    return [_serialize(a) for a in items]


def add_room_attachment(db: Session, room_id: int, data: AttachmentCreateRequest, actor_id: int) -> dict:
    r = db.query(Room).filter(Room.id == room_id).first()
    if not r:
        raise NotFoundException("Room")
    a = Attachment(roomId=room_id, uploadedById=actor_id,
                   fileUrl=data.fileUrl, fileName=data.fileName,
                   fileType=data.fileType, fileSize=data.fileSize, description=data.description)
    db.add(a); db.commit(); db.refresh(a)
    return _serialize(a)


# ─── BOOKING ATTACHMENTS ──────────────────────────────────────────────────────
def list_booking_attachments(db: Session, booking_id: int, actor_id: int, actor_role: str) -> list[dict]:
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    if not b:
        raise NotFoundException("Booking")
    # Employee hanya bisa lihat booking miliknya
    if actor_role == "EMPLOYEE" and b.userId != actor_id:
        raise ForbiddenException("Anda tidak punya akses ke booking ini")
    items = db.query(Attachment).filter(Attachment.bookingId == booking_id)\
               .order_by(Attachment.createdAt.desc()).all()
    return [_serialize(a) for a in items]


def add_booking_attachment(db: Session, booking_id: int, data: AttachmentCreateRequest, actor_id: int, actor_role: str) -> dict:
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    if not b:
        raise NotFoundException("Booking")
    if actor_role == "EMPLOYEE" and b.userId != actor_id:
        raise ForbiddenException("Anda hanya bisa menambah lampiran ke booking Anda sendiri")
    a = Attachment(bookingId=booking_id, uploadedById=actor_id,
                   fileUrl=data.fileUrl, fileName=data.fileName,
                   fileType=data.fileType, fileSize=data.fileSize, description=data.description)
    db.add(a); db.commit(); db.refresh(a)
    return _serialize(a)


# ─── PROFILE PHOTO ────────────────────────────────────────────────────────────
def update_profile_photo(db: Session, user_id: int, data: ProfilePhotoRequest) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User")
    user.profilePhoto = data.photoUrl
    db.commit(); db.refresh(user)
    return {
        "id":           user.id,
        "name":         user.name,
        "email":        user.email,
        "profilePhoto": user.profilePhoto,
    }


def remove_profile_photo(db: Session, user_id: int) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User")
    user.profilePhoto = None
    db.commit(); db.refresh(user)
    return {"id": user.id, "name": user.name, "profilePhoto": None}
