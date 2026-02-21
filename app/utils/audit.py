from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    description: str | None = None,
) -> None:
    """
    Write an audit log entry.

    Args:
        db:          Active DB session (will flush but NOT commit — caller commits)
        user_id:     ID of user performing the action (None = system action)
        action:      Verb: CREATE, UPDATE, DELETE, APPROVE, REJECT, LOGIN, LOGOUT, etc.
        entity_type: Model name: "Booking", "User", "Vehicle", etc.
        entity_id:   Primary key of the affected record
        description: Human-readable description (shown in audit log UI)

    Usage:
        log_action(db, current_user.id, "APPROVE", "Booking", booking.id,
                   f"Booking #{booking.id} approved for {booking.user.name}")
        db.commit()
    """
    entry = AuditLog(
        userId=user_id,
        action=action,
        entityType=entity_type,
        entityId=entity_id,
        description=description,
    )
    db.add(entry)
    # Do NOT commit here — let the caller's transaction commit everything atomically
