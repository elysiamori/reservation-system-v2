import enum
from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ApprovalAction(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id         = Column(Integer, primary_key=True, index=True)
    bookingId  = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    approverId = Column(Integer, ForeignKey("users.id"), nullable=False)
    action     = Column(Enum(ApprovalAction), nullable=False)
    note       = Column(Text, nullable=True)
    createdAt  = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    booking  = relationship("Booking", back_populates="approval_logs")
    approver = relationship("User", back_populates="approval_logs")

    def __repr__(self):
        return f"<ApprovalLog id={self.id} bookingId={self.bookingId} action={self.action}>"
