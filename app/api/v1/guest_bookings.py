from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_admin_user, get_current_user
from app.models.user import User
from app.schemas.guest_booking import (
    GuestBookingCreateRequest,
    GuestBookingCompleteRequest,
    GuestBookingCancelRequest,
)
from app.schemas.common import success_response, paginated_response
from app.services.guest_booking_service import guest_booking_service

router = APIRouter(prefix="/guest-bookings")


# ─── PUBLIC (tanpa login) ─────────────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="[PUBLIC] Buat booking tanpa login — dapat accessToken sebagai kunci",
)
def create_guest_booking(
    body: GuestBookingCreateRequest,
    db:   Session = Depends(get_db),
):
    """
    Endpoint publik — tidak perlu login.

    Input: nama, email, nomor HP, departemen, resource, tanggal, tujuan.

    Response berisi `accessToken` — **simpan token ini!**
    Token digunakan untuk cek status dan update booking.
    """
    data = guest_booking_service.create(db, body)
    return success_response(
        "Booking berhasil dibuat! Simpan accessToken Anda untuk cek status booking.",
        data,
    )


@router.get(
    "/{token}",
    summary="[PUBLIC] Cek status booking dengan accessToken",
)
def get_guest_booking(
    token: str,
    db:    Session = Depends(get_db),
):
    """Gunakan accessToken dari saat booking untuk melihat detail & status."""
    data = guest_booking_service.get_by_token(db, token)
    return success_response("Detail booking ditemukan", data)


@router.patch(
    "/{token}/complete",
    summary="[PUBLIC] Tandai booking selesai dengan accessToken",
)
def complete_guest_booking(
    token: str,
    body:  GuestBookingCompleteRequest = GuestBookingCompleteRequest(),
    db:    Session = Depends(get_db),
):
    """
    Tamu menandai booking sudah selesai (resource sudah dikembalikan).
    Booking harus berstatus APPROVED atau ONGOING.
    """
    data = guest_booking_service.complete_by_token(db, token, body.note)
    return success_response("Booking ditandai selesai. Terima kasih!", data)


@router.patch(
    "/{token}/cancel",
    summary="[PUBLIC] Batalkan booking dengan accessToken",
)
def cancel_guest_booking(
    token: str,
    body:  GuestBookingCancelRequest = GuestBookingCancelRequest(),
    db:    Session = Depends(get_db),
):
    """Tamu membatalkan booking. Hanya bisa jika masih berstatus PENDING."""
    data = guest_booking_service.cancel_by_token(db, token, body.note)
    return success_response("Booking berhasil dibatalkan", data)


# ─── ADMIN / APPROVER (perlu login) ──────────────────────────────────────────

@router.get(
    "",
    summary="[Admin/Approver] List semua guest booking",
)
def list_guest_bookings(
    page:       int           = Query(1, ge=1),
    limit:      int           = Query(20, ge=1, le=100),
    status:     Optional[str] = Query(None, description="PENDING|APPROVED|REJECTED|ONGOING|COMPLETED|CANCELLED"),
    resourceId: Optional[int] = Query(None),
    db:         Session       = Depends(get_db),
    _:          User          = Depends(get_admin_user),
):
    data, total = guest_booking_service.list_all(db, page, limit, status, resourceId)
    return paginated_response("Guest bookings retrieved", data, total, page, limit)


@router.post(
    "/{guest_booking_id}/approve",
    summary="[Admin/Approver] Approve guest booking",
)
def approve_guest_booking(
    guest_booking_id: int,
    db:               Session = Depends(get_db),
    current_user:     User    = Depends(get_admin_user),
):
    data = guest_booking_service.approve(db, guest_booking_id, None, current_user.id)
    return success_response("Guest booking diapprove", data)


@router.post(
    "/{guest_booking_id}/reject",
    summary="[Admin/Approver] Reject guest booking",
)
def reject_guest_booking(
    guest_booking_id: int,
    note:             str,
    db:               Session = Depends(get_db),
    current_user:     User    = Depends(get_admin_user),
):
    data = guest_booking_service.reject(db, guest_booking_id, note, current_user.id)
    return success_response("Guest booking direject", data)


@router.patch(
    "/{guest_booking_id}/start",
    summary="[Admin] Start guest booking → ONGOING",
)
def start_guest_booking(
    guest_booking_id: int,
    db:               Session = Depends(get_db),
    current_user:     User    = Depends(get_admin_user),
):
    data = guest_booking_service.start(db, guest_booking_id, current_user.id)
    return success_response("Guest booking dimulai (ONGOING)", data)
