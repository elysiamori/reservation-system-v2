from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.booking import Booking, BookingStatus
from app.models.approval_log import ApprovalLog, ApprovalAction
from app.models.resource import Resource, ResourceStatus
from app.models.role import RoleName
from app.models.user import User
from app.schemas.booking import BookingCreateRequest, ApproveRequest, RejectRequest
from app.utils.audit import log_action
from app.utils.email import send_booking_status_email
from app.utils.exceptions import (
    NotFoundException, BookingConflictException, BookingNotPendingException,
    ResourceUnavailableException, InvalidDateRangeException, SelfApprovalException,
    ForbiddenException,
)


def _serialize(b: Booking) -> dict:
    return {
        "id":     b.id,
        "status": b.status.value,
        "user": {
            "id":         b.user.id,
            "name":       b.user.name,
            "employeeId": b.user.employeeId,
            "department": b.user.department.name,
        },
        "resource": {
            "id":     b.resource.id,
            "name":   b.resource.name,
            "type":   b.resource.type.value,
            "status": b.resource.status.value,
        },
        "startDate":   b.startDate.isoformat(),
        "endDate":     b.endDate.isoformat(),
        "purpose":     b.purpose,
        "approvedBy":  {
            "id":   b.approved_by.id,
            "name": b.approved_by.name,
        } if b.approved_by else None,
        "approvedAt":  b.approvedAt.isoformat()  if b.approvedAt  else None,
        "returnedAt":  b.returnedAt.isoformat()  if b.returnedAt  else None,
        "createdAt":   b.createdAt.isoformat(),
        "updatedAt":   b.updatedAt.isoformat(),
    }


def _check_conflict(db: Session, resource_id: int, start: datetime, end: datetime, exclude_id: int | None = None):
    """Raise BookingConflictException if there's an overlapping active booking."""
    q = db.query(Booking).filter(
        Booking.resourceId == resource_id,
        Booking.status.in_([BookingStatus.PENDING, BookingStatus.APPROVED, BookingStatus.ONGOING]),
        Booking.startDate < end,
        Booking.endDate   > start,
    )
    if exclude_id:
        q = q.filter(Booking.id != exclude_id)
    if q.first():
        raise BookingConflictException()


class BookingService:

    def list_bookings(
        self, db: Session, current_user: User,
        page: int, limit: int,
        status: str | None, resource_id: int | None,
        resource_type: str | None, start_date: str | None, end_date: str | None,
        user_id: int | None,
    ) -> tuple[list[dict], int]:
        q = db.query(Booking)

        # Role-based visibility
        if current_user.role.name == RoleName.EMPLOYEE:
            q = q.filter(Booking.userId == current_user.id)
        elif current_user.role.name == RoleName.DRIVER:
            # Driver sees bookings linked to their assigned vehicles
            from app.models.driver import Driver
            from app.models.driver_assignment import DriverAssignment
            from app.models.vehicle import Vehicle
            driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
            if driver:
                active = db.query(DriverAssignment).filter(
                    DriverAssignment.driverId == driver.id,
                    DriverAssignment.releasedAt == None,
                ).first()
                if active:
                    q = q.join(Resource, Booking.resourceId == Resource.id)\
                         .join(Vehicle, Vehicle.resourceId == Resource.id)\
                         .filter(Vehicle.id == active.vehicleId)
                else:
                    q = q.filter(Booking.id == -1)  # no results
            else:
                q = q.filter(Booking.id == -1)

        # Filters
        if status:         q = q.filter(Booking.status == status)
        if resource_id:    q = q.filter(Booking.resourceId == resource_id)
        if resource_type:
            q = q.join(Resource, Booking.resourceId == Resource.id)\
                 .filter(Resource.type == resource_type)
        if user_id and current_user.role.name in [RoleName.ADMIN, RoleName.APPROVER]:
            q = q.filter(Booking.userId == user_id)
        if start_date:     q = q.filter(Booking.startDate >= start_date)
        if end_date:       q = q.filter(Booking.endDate   <= end_date)

        total = q.count()
        items = q.order_by(Booking.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()
        return [_serialize(b) for b in items], total

    def get_booking(self, db: Session, booking_id: int, current_user: User) -> dict:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        # Employee can only see own bookings
        if current_user.role.name == RoleName.EMPLOYEE and b.userId != current_user.id:
            raise ForbiddenException("You can only view your own bookings")
        return _serialize(b)

    def create_booking(self, db: Session, data: BookingCreateRequest, current_user: User) -> dict:
        resource = db.query(Resource).filter(Resource.id == data.resourceId).first()
        if not resource:
            raise NotFoundException("Resource")
        if resource.status != ResourceStatus.AVAILABLE:
            raise ResourceUnavailableException()
        if data.endDate <= data.startDate:
            raise InvalidDateRangeException()

        _check_conflict(db, data.resourceId, data.startDate, data.endDate)

        b = Booking(
            userId=current_user.id,
            resourceId=data.resourceId,
            startDate=data.startDate,
            endDate=data.endDate,
            purpose=data.purpose,
            status=BookingStatus.PENDING,
        )
        db.add(b)
        db.flush()
        log_action(db, current_user.id, "CREATE", "Booking", b.id,
                   f"{current_user.name} created booking for {resource.name}")
        db.commit()
        db.refresh(b)
        return _serialize(b)

    def cancel_booking(self, db: Session, booking_id: int, current_user: User) -> dict:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        if current_user.role.name == RoleName.EMPLOYEE and b.userId != current_user.id:
            raise ForbiddenException("You can only cancel your own bookings")
        if b.status != BookingStatus.PENDING:
            raise BookingNotPendingException()

        b.status = BookingStatus.CANCELLED
        log_action(db, current_user.id, "CANCEL", "Booking", b.id, f"Booking #{b.id} cancelled")
        db.commit()
        db.refresh(b)
        return _serialize(b)

    def approve_booking(self, db: Session, booking_id: int, data: ApproveRequest, current_user: User) -> dict:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        if b.userId == current_user.id:
            raise SelfApprovalException()
        if b.status != BookingStatus.PENDING:
            raise BookingNotPendingException()

        # Re-check conflict (status might have changed after creation)
        _check_conflict(db, b.resourceId, b.startDate, b.endDate, exclude_id=b.id)

        b.status       = BookingStatus.APPROVED
        b.approvedById = current_user.id
        b.approvedAt   = datetime.now(timezone.utc)

        log_entry = ApprovalLog(
            bookingId=b.id, approverId=current_user.id,
            action=ApprovalAction.APPROVED, note=data.note,
        )
        db.add(log_entry)
        log_action(db, current_user.id, "APPROVE", "Booking", b.id,
                   f"Booking #{b.id} approved for {b.user.name}")
        db.commit()
        db.refresh(b)

        send_booking_status_email(
            b.user.email, b.user.name, b.id,
            b.resource.name, "APPROVED", data.note,
        )
        return _serialize(b)

    def reject_booking(self, db: Session, booking_id: int, data: RejectRequest, current_user: User) -> dict:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        if b.userId == current_user.id:
            raise SelfApprovalException()
        if b.status != BookingStatus.PENDING:
            raise BookingNotPendingException()

        b.status       = BookingStatus.REJECTED
        b.approvedById = current_user.id
        b.approvedAt   = datetime.now(timezone.utc)

        log_entry = ApprovalLog(
            bookingId=b.id, approverId=current_user.id,
            action=ApprovalAction.REJECTED, note=data.note,
        )
        db.add(log_entry)
        log_action(db, current_user.id, "REJECT", "Booking", b.id,
                   f"Booking #{b.id} rejected. Reason: {data.note}")
        db.commit()
        db.refresh(b)

        send_booking_status_email(
            b.user.email, b.user.name, b.id,
            b.resource.name, "REJECTED", data.note,
        )
        return _serialize(b)

    def start_booking(self, db: Session, booking_id: int, current_user: User) -> dict:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        if b.status != BookingStatus.APPROVED:
            raise ForbiddenException("Only APPROVED bookings can be started")

        b.status = BookingStatus.ONGOING
        log_action(db, current_user.id, "START", "Booking", b.id, f"Booking #{b.id} marked as ONGOING")
        db.commit()
        db.refresh(b)
        return _serialize(b)

    def complete_booking(self, db: Session, booking_id: int, current_user: User) -> dict:
        b = db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.status.in_([BookingStatus.ONGOING, BookingStatus.OVERDUE]),
        ).first()
        if not b:
            raise NotFoundException("Booking (must be ONGOING or OVERDUE)")

        b.status     = BookingStatus.COMPLETED
        b.returnedAt = datetime.now(timezone.utc)
        log_action(db, current_user.id, "COMPLETE", "Booking", b.id,
                   f"Booking #{b.id} completed — resource returned")
        db.commit()
        db.refresh(b)
        return _serialize(b)

    def get_approval_log(self, db: Session, booking_id: int) -> list[dict]:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        logs = db.query(ApprovalLog).filter(ApprovalLog.bookingId == booking_id)\
                 .order_by(ApprovalLog.createdAt.asc()).all()
        return [{
            "id":        l.id,
            "approver":  {"id": l.approver.id, "name": l.approver.name},
            "action":    l.action.value,
            "note":      l.note,
            "createdAt": l.createdAt.isoformat(),
        } for l in logs]

    # ─── Scheduler helper (called by cron / background task) ─────────────────
    def mark_overdue(self, db: Session) -> int:
        """Mark APPROVED bookings past endDate as OVERDUE. Returns count updated."""
        now = datetime.now(timezone.utc)
        result = db.query(Booking).filter(
            Booking.status == BookingStatus.APPROVED,
            Booking.endDate < now,
        ).all()
        count = 0
        for b in result:
            b.status = BookingStatus.OVERDUE
            log_action(db, None, "SYSTEM_OVERDUE", "Booking", b.id,
                       f"Booking #{b.id} auto-marked OVERDUE")
            count += 1
        if count:
            db.commit()
        return count


booking_service = BookingService()
