import secrets
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.guest_booking import GuestBooking
from app.models.booking import Booking, BookingStatus
from app.models.resource import Resource, ResourceStatus
from app.schemas.guest_booking import GuestBookingCreateRequest
from app.utils.audit import log_action
from app.utils.exceptions import (
    NotFoundException, BookingConflictException,
    ResourceUnavailableException, ForbiddenException,
)


def _serialize(gb: GuestBooking) -> dict:
    return {
        "id":             gb.id,
        "guestName":      gb.guestName,
        "guestEmail":     gb.guestEmail,
        "guestPhone":     gb.guestPhone,
        "departmentName": gb.departmentName,
        "resource": {
            "id":     gb.resource.id,
            "name":   gb.resource.name,
            "type":   gb.resource.type.value,
            "status": gb.resource.status.value,
        },
        "startDate":    gb.startDate.isoformat(),
        "endDate":      gb.endDate.isoformat(),
        "purpose":      gb.purpose,
        "status":       gb.status,
        "approvedBy":   {"id": gb.approved_by.id, "name": gb.approved_by.name} if gb.approved_by else None,
        "approvedAt":   gb.approvedAt.isoformat()  if gb.approvedAt  else None,
        "rejectionNote":gb.rejectionNote,
        "returnedAt":   gb.returnedAt.isoformat()  if gb.returnedAt  else None,
        "createdAt":    gb.createdAt.isoformat(),
        "updatedAt":    gb.updatedAt.isoformat(),
    }


def _check_conflict(db: Session, resource_id: int, start: datetime, end: datetime, exclude_booking_id: int = None):
    # Cek vs bookings biasa
    regular_query = db.query(Booking).filter(
        Booking.resourceId == resource_id,
        Booking.status.in_([BookingStatus.PENDING, BookingStatus.APPROVED, BookingStatus.ONGOING]),
        Booking.startDate < end,
        Booking.endDate > start,
    )

    if exclude_booking_id:
        regular_query = regular_query.filter(Booking.id != exclude_booking_id)

    regular_conflict = regular_query.first()
    if regular_conflict:
        raise BookingConflictException()

    guest_query = db.query(GuestBooking).filter(
        GuestBooking.resourceId == resource_id,
        GuestBooking.status.in_([BookingStatus.PENDING, BookingStatus.APPROVED, BookingStatus.ONGOING]),
        GuestBooking.startDate < end,
        GuestBooking.endDate > start,
    )

    if exclude_booking_id:
        guest_query = guest_query.filter(GuestBooking.id != exclude_booking_id)

    guest_conflict = guest_query.first()
    if guest_conflict:
        raise BookingConflictException()


class GuestBookingService:

    def create(self, db: Session, data: GuestBookingCreateRequest) -> dict:
        resource = db.query(Resource).filter(Resource.id == data.resourceId).first()
        if not resource:
            raise NotFoundException("Resource")
        if resource.status != ResourceStatus.AVAILABLE:
            raise ResourceUnavailableException()

        _check_conflict(db, data.resourceId, data.startDate, data.endDate)

        # Buat accessToken unik (64 karakter hex)
        access_token = secrets.token_hex(32)

        gb = GuestBooking(
            guestName=data.guestName,
            guestEmail=str(data.guestEmail),
            guestPhone=data.guestPhone,
            departmentName=data.departmentName,
            resourceId=data.resourceId,
            startDate=data.startDate,
            endDate=data.endDate,
            purpose=data.purpose,
            status="PENDING",
            accessToken=access_token,
        )
        db.add(gb)
        db.commit()
        db.refresh(gb)

        result = _serialize(gb)
        # Sertakan token di response CREATE saja — setelah ini token hanya dikirim ke email/dicatat user
        result["accessToken"] = access_token
        result["_info"] = "Simpan accessToken ini. Gunakan untuk cek status atau update booking Anda."
        return result

    def get_by_token(self, db: Session, token: str) -> dict:
        gb = db.query(GuestBooking).filter(GuestBooking.accessToken == token).first()
        if not gb:
            raise NotFoundException("Guest booking dengan token ini")
        return _serialize(gb)

    def complete_by_token(self, db: Session, token: str, note: str | None) -> dict:
        gb = db.query(GuestBooking).filter(GuestBooking.accessToken == token).first()
        if not gb:
            raise NotFoundException("Guest booking dengan token ini")
        if gb.status not in ["ONGOING", "APPROVED"]:
            raise ForbiddenException(
                f"Booking tidak bisa diselesaikan. Status saat ini: {gb.status}. "
                "Hanya APPROVED atau ONGOING yang bisa ditandai selesai."
            )
        gb.status     = "COMPLETED"
        gb.returnedAt = datetime.now(timezone.utc)
        db.commit()
        db.refresh(gb)
        return _serialize(gb)

    def cancel_by_token(self, db: Session, token: str, note: str | None) -> dict:
        gb = db.query(GuestBooking).filter(GuestBooking.accessToken == token).first()
        if not gb:
            raise NotFoundException("Guest booking dengan token ini")
        if gb.status != "PENDING":
            raise ForbiddenException(
                f"Hanya booking berstatus PENDING yang bisa dibatalkan. Status saat ini: {gb.status}"
            )
        gb.status = "CANCELLED"
        if note:
            gb.rejectionNote = note
        db.commit()
        db.refresh(gb)
        return _serialize(gb)

    # ─── Admin/Approver endpoints ─────────────────────────────────────────────
    def list_all(
        self, db: Session, page: int, limit: int,
        status: str | None, resource_id: int | None,
    ) -> tuple[list[dict], int]:
        q = db.query(GuestBooking)
        if status:      q = q.filter(GuestBooking.status == status)
        if resource_id: q = q.filter(GuestBooking.resourceId == resource_id)
        total = q.count()
        items = q.order_by(GuestBooking.createdAt.desc())\
                 .offset((page - 1) * limit).limit(limit).all()
        return [_serialize(gb) for gb in items], total

    def approve(self, db: Session, guest_booking_id: int, note: str | None, actor_id: int) -> dict:
        gb = db.query(GuestBooking).filter(GuestBooking.id == guest_booking_id).first()
        if not gb:
            raise NotFoundException("Guest booking")
        if gb.status != "PENDING":
            raise ForbiddenException(f"Hanya PENDING yang bisa diapprove. Status: {gb.status}")

        _check_conflict(db, gb.resourceId, gb.startDate, gb.endDate, exclude_booking_id=guest_booking_id)

        gb.status      = "APPROVED"
        gb.approvedById = actor_id
        gb.approvedAt  = datetime.now(timezone.utc)
        log_action(db, actor_id, "APPROVE", "GuestBooking", gb.id,
                   f"Guest booking #{gb.id} oleh {gb.guestName} diapprove")
        db.commit()
        db.refresh(gb)
        return _serialize(gb)

    def reject(self, db: Session, guest_booking_id: int, note: str, actor_id: int) -> dict:
        gb = db.query(GuestBooking).filter(GuestBooking.id == guest_booking_id).first()
        if not gb:
            raise NotFoundException("Guest booking")
        if gb.status != "PENDING":
            raise ForbiddenException(f"Hanya PENDING yang bisa direject. Status: {gb.status}")

        gb.status       = "REJECTED"
        gb.approvedById = actor_id
        gb.approvedAt   = datetime.now(timezone.utc)
        gb.rejectionNote = note
        log_action(db, actor_id, "REJECT", "GuestBooking", gb.id,
                   f"Guest booking #{gb.id} direject. Alasan: {note}")
        db.commit()
        db.refresh(gb)
        return _serialize(gb)

    def start(self, db: Session, guest_booking_id: int, actor_id: int) -> dict:
        gb = db.query(GuestBooking).filter(GuestBooking.id == guest_booking_id).first()
        if not gb:
            raise NotFoundException("Guest booking")
        if gb.status != "APPROVED":
            raise ForbiddenException("Hanya APPROVED yang bisa distart")
        gb.status = "ONGOING"
        log_action(db, actor_id, "START", "GuestBooking", gb.id,
                   f"Guest booking #{gb.id} dimulai (ONGOING)")
        db.commit()
        db.refresh(gb)
        return _serialize(gb)


guest_booking_service = GuestBookingService()
