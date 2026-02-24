from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.booking import Booking, BookingStatus
from app.models.approval_log import ApprovalLog, ApprovalAction
from app.models.resource import Resource, ResourceStatus, ResourceType
from app.models.role import RoleName
from app.models.user import User
from app.models.driver import Driver
from app.models.vehicle import Vehicle
from app.models.driver_rating import DriverRating
from app.schemas.booking import (
    BookingCreateRequest, ApproveRequest, RejectRequest,
    AssignVehicleRequest, DriverRatingCreateRequest,
)
from app.utils.audit import log_action
from app.utils.email import send_booking_status_email
from app.utils.exceptions import (
    NotFoundException, BookingConflictException, BookingNotPendingException,
    ResourceUnavailableException, InvalidDateRangeException, SelfApprovalException,
    ForbiddenException,
)


def _serialize(b: Booking) -> dict:
    data = {
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
        # Vehicle-specific assignment
        "assignedDriver":  None,
        "assignedVehicle": None,
        "assignedAt":      b.assignedAt.isoformat() if b.assignedAt else None,
    }

    if b.assigned_driver:
        d = b.assigned_driver
        data["assignedDriver"] = {
            "id":          d.id,
            "name":        d.user.name,
            "phoneNumber": d.phoneNumber,
        }
    if b.assigned_vehicle:
        v = b.assigned_vehicle
        data["assignedVehicle"] = {
            "id":          v.id,
            "plateNumber": v.plateNumber,
            "brand":       v.brand,
            "model":       v.model,
            "capacity":    v.capacity,
        }

    return data


def _check_conflict(
    db: Session, resource_id: int, start: datetime, end: datetime, exclude_id: int | None = None
):
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

        if current_user.role.name == RoleName.DRIVER:
            # Driver sees only vehicle bookings assigned to them
            driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
            if driver:
                q = q.filter(Booking.assignedDriverId == driver.id)
            else:
                q = q.filter(Booking.id == -1)
        elif current_user.role.name == RoleName.EMPLOYEE:
            q = q.filter(Booking.userId == current_user.id)

        if status:       q = q.filter(Booking.status == status)
        if resource_id:  q = q.filter(Booking.resourceId == resource_id)
        if resource_type:
            q = q.join(Resource, Booking.resourceId == Resource.id)\
                 .filter(Resource.type == resource_type)
        if user_id and current_user.role.name == RoleName.ADMIN:
            q = q.filter(Booking.userId == user_id)
        if start_date: q = q.filter(Booking.startDate >= start_date)
        if end_date:   q = q.filter(Booking.endDate   <= end_date)

        total = q.count()
        items = q.order_by(Booking.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()
        return [_serialize(b) for b in items], total

    def get_booking(self, db: Session, booking_id: int, current_user: User) -> dict:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        if current_user.role.name == RoleName.EMPLOYEE and b.userId != current_user.id:
            raise ForbiddenException("You can only view your own bookings")
        if current_user.role.name == RoleName.DRIVER:
            driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
            if not driver or b.assignedDriverId != driver.id:
                raise ForbiddenException("You can only view bookings assigned to you")
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
        """Admin approves a PENDING booking."""
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        if b.userId == current_user.id:
            raise SelfApprovalException()
        if b.status != BookingStatus.PENDING:
            raise BookingNotPendingException()

        _check_conflict(db, b.resourceId, b.startDate, b.endDate, exclude_id=b.id)

        b.status       = BookingStatus.APPROVED
        b.approvedById = current_user.id
        b.approvedAt   = datetime.now(timezone.utc)

        db.add(ApprovalLog(
            bookingId=b.id, approverId=current_user.id,
            action=ApprovalAction.APPROVED, note=data.note,
        ))
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

        db.add(ApprovalLog(
            bookingId=b.id, approverId=current_user.id,
            action=ApprovalAction.REJECTED, note=data.note,
        ))
        log_action(db, current_user.id, "REJECT", "Booking", b.id,
                   f"Booking #{b.id} rejected. Reason: {data.note}")
        db.commit()
        db.refresh(b)

        send_booking_status_email(
            b.user.email, b.user.name, b.id,
            b.resource.name, "REJECTED", data.note,
        )
        return _serialize(b)

    def assign_vehicle(
        self, db: Session, booking_id: int, data: AssignVehicleRequest, current_user: User
    ) -> dict:
        """Admin assigns a vehicle and driver to an approved VEHICLE booking."""
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        if b.status != BookingStatus.APPROVED:
            raise ForbiddenException("Only APPROVED bookings can have vehicle/driver assigned")
        if b.resource.type != ResourceType.VEHICLE:
            raise ForbiddenException("Assignment only applies to vehicle bookings")

        driver = db.query(Driver).filter(Driver.id == data.driverId, Driver.isActive == True).first()
        if not driver:
            raise NotFoundException("Driver (active)")

        vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicleId).first()
        if not vehicle:
            raise NotFoundException("Vehicle")

        # Check vehicle availability in the booking period
        conflict = db.query(Booking).filter(
            Booking.assignedVehicleId == data.vehicleId,
            Booking.status.in_([BookingStatus.APPROVED, BookingStatus.ONGOING]),
            Booking.startDate < b.endDate,
            Booking.endDate   > b.startDate,
            Booking.id != booking_id,
        ).first()
        if conflict:
            raise BookingConflictException()

        b.assignedDriverId  = data.driverId
        b.assignedVehicleId = data.vehicleId
        b.assignedAt        = datetime.now(timezone.utc)

        log_action(db, current_user.id, "ASSIGN", "Booking", b.id,
                   f"Driver {driver.user.name} and vehicle {vehicle.plateNumber} assigned to booking #{b.id}")
        db.commit()
        db.refresh(b)
        return _serialize(b)

    def start_booking(self, db: Session, booking_id: int, current_user: User) -> dict:
        """
        Driver or Admin marks booking as ONGOING.
        Rules: booking must be APPROVED, assigned to this driver,
               current time >= startDate and <= endDate.
        """
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        if b.status != BookingStatus.APPROVED:
            raise ForbiddenException("Only APPROVED bookings can be started")
        if b.resource.type != ResourceType.VEHICLE:
            raise ForbiddenException("Only vehicle bookings can be started by driver")

        # Check assignment
        if current_user.role.name == RoleName.DRIVER:
            driver = db.query(Driver).filter(Driver.userId == current_user.id).first()
            if not driver or b.assignedDriverId != driver.id:
                raise ForbiddenException("You are not assigned to this booking")

        # Check time window: now >= startDate
        now = datetime.now(timezone.utc)
        booking_start = b.startDate if b.startDate.tzinfo else b.startDate.replace(tzinfo=timezone.utc)
        booking_end   = b.endDate   if b.endDate.tzinfo   else b.endDate.replace(tzinfo=timezone.utc)

        if now < booking_start:
            raise ForbiddenException(
                f"Trip cannot be started before scheduled time: {booking_start.isoformat()}"
            )
        if now > booking_end:
            raise ForbiddenException("Booking period has already ended")

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

    def rate_driver(
        self, db: Session, booking_id: int, data: DriverRatingCreateRequest, current_user: User
    ) -> dict:
        """User rates driver after booking is COMPLETED."""
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b:
            raise NotFoundException("Booking")
        if b.status != BookingStatus.COMPLETED:
            raise ForbiddenException("You can only rate a driver for completed bookings")
        if b.userId != current_user.id:
            raise ForbiddenException("You can only rate for your own bookings")
        if b.resource.type != ResourceType.VEHICLE:
            raise ForbiddenException("Driver rating is only for vehicle bookings")
        if not b.assignedDriverId:
            raise ForbiddenException("No driver was assigned to this booking")

        existing = db.query(DriverRating).filter(DriverRating.bookingId == booking_id).first()
        if existing:
            raise ForbiddenException("You have already rated this booking")

        rating = DriverRating(
            bookingId=booking_id,
            driverId=b.assignedDriverId,
            ratedById=current_user.id,
            rating=data.rating,
            review=data.review,
        )
        db.add(rating)
        log_action(db, current_user.id, "RATE_DRIVER", "DriverRating", b.id,
                   f"User {current_user.name} rated driver {b.assignedDriverId} — {data.rating}/5")
        db.commit()
        db.refresh(rating)
        return {
            "id":       rating.id,
            "bookingId": rating.bookingId,
            "driverId":  rating.driverId,
            "rating":    rating.rating,
            "review":    rating.review,
            "createdAt": rating.createdAt.isoformat(),
        }

    def get_driver_ratings(self, db: Session, driver_id: int) -> dict:
        ratings = db.query(DriverRating).filter(DriverRating.driverId == driver_id).all()
        avg = round(sum(r.rating for r in ratings) / len(ratings), 2) if ratings else None
        return {
            "driverId":    driver_id,
            "totalRatings": len(ratings),
            "averageRating": avg,
            "ratings": [{
                "id":        r.id,
                "rating":    r.rating,
                "review":    r.review,
                "ratedBy":   {"id": r.rated_by.id, "name": r.rated_by.name},
                "createdAt": r.createdAt.isoformat(),
            } for r in ratings],
        }

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

    def mark_overdue(self, db: Session) -> int:
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
