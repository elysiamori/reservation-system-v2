from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_admin_user
from app.models.user import User
from app.schemas.attachment import AttachmentCreateRequest, ProfilePhotoRequest
from app.schemas.common import success_response
from app.services import attachment_service as svc

router = APIRouter()


# ══════════════════════════════════════════════════════
#  VEHICLE ATTACHMENTS
# ══════════════════════════════════════════════════════
@router.get("/vehicles/{vehicle_id}/attachments",
            summary="List lampiran kendaraan")
def list_vehicle_attachments(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    data = svc.list_vehicle_attachments(db, vehicle_id)
    return success_response(f"{len(data)} lampiran ditemukan", data)


@router.post("/vehicles/{vehicle_id}/attachments",
             status_code=status.HTTP_201_CREATED,
             summary="Tambah lampiran ke kendaraan (semua user terotentikasi)")
def add_vehicle_attachment(
    vehicle_id: int,
    body: AttachmentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = svc.add_vehicle_attachment(db, vehicle_id, body, current_user.id)
    return success_response("Lampiran berhasil ditambahkan", data)


# ══════════════════════════════════════════════════════
#  ROOM ATTACHMENTS
# ══════════════════════════════════════════════════════
@router.get("/rooms/{room_id}/attachments",
            summary="List lampiran ruangan")
def list_room_attachments(
    room_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    data = svc.list_room_attachments(db, room_id)
    return success_response(f"{len(data)} lampiran ditemukan", data)


@router.post("/rooms/{room_id}/attachments",
             status_code=status.HTTP_201_CREATED,
             summary="Tambah lampiran ke ruangan (semua user terotentikasi)")
def add_room_attachment(
    room_id: int,
    body: AttachmentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = svc.add_room_attachment(db, room_id, body, current_user.id)
    return success_response("Lampiran berhasil ditambahkan", data)


# ══════════════════════════════════════════════════════
#  BOOKING ATTACHMENTS
# ══════════════════════════════════════════════════════
@router.get("/bookings/{booking_id}/attachments",
            summary="List lampiran dokumen booking")
def list_booking_attachments(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = svc.list_booking_attachments(db, booking_id, current_user.id, current_user.role.name)
    return success_response(f"{len(data)} lampiran ditemukan", data)


@router.post("/bookings/{booking_id}/attachments",
             status_code=status.HTTP_201_CREATED,
             summary="Tambah lampiran dokumen ke booking")
def add_booking_attachment(
    booking_id: int,
    body: AttachmentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = svc.add_booking_attachment(db, booking_id, body, current_user.id, current_user.role.name)
    return success_response("Lampiran berhasil ditambahkan", data)


# ══════════════════════════════════════════════════════
#  DELETE
# ══════════════════════════════════════════════════════
@router.delete("/attachments/{attachment_id}",
               status_code=status.HTTP_200_OK,
               summary="Hapus lampiran")
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc.delete_attachment(db, attachment_id, current_user.id, current_user.role.name)
    return success_response("Lampiran berhasil dihapus")


# ══════════════════════════════════════════════════════
#  PROFILE PHOTO
# ══════════════════════════════════════════════════════
@router.put("/users/me/profile-photo",
            summary="Ganti foto profil sendiri")
def update_my_photo(
    body: ProfilePhotoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = svc.update_profile_photo(db, current_user.id, body)
    return success_response("Foto profil berhasil diperbarui", data)


@router.delete("/users/me/profile-photo",
               summary="Hapus foto profil sendiri")
def remove_my_photo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = svc.remove_profile_photo(db, current_user.id)
    return success_response("Foto profil berhasil dihapus", data)


@router.put("/users/{user_id}/profile-photo",
            summary="Ganti foto profil user lain (Admin)")
def update_user_photo(
    user_id: int,
    body: ProfilePhotoRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    data = svc.update_profile_photo(db, user_id, body)
    return success_response("Foto profil berhasil diperbarui", data)

