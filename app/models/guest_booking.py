from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.booking import BookingStatus


class GuestBooking(Base):
    __tablename__ = "guest_bookings"

    id              = Column(Integer, primary_key=True, index=True)
    guestName       = Column("guestName",      String(150), nullable=False)
    guestEmail      = Column("guestEmail",     String(255), nullable=False)
    guestPhone      = Column("guestPhone",     String(20),  nullable=False)
    departmentName  = Column("departmentName", String(100), nullable=False)
    resourceId      = Column("resourceId",     Integer, ForeignKey("resources.id"), nullable=False)
    startDate       = Column("startDate",      TIMESTAMP(timezone=True), nullable=False)
    endDate         = Column("endDate",        TIMESTAMP(timezone=True), nullable=False)
    purpose         = Column(Text, nullable=False)
    status          = Column(BookingStatus.__class__, nullable=False, default="PENDING")
    accessToken     = Column("accessToken",    String(64),  nullable=False, unique=True)
    approvedById    = Column("approvedById",   Integer, ForeignKey("users.id"), nullable=True)
    approvedAt      = Column("approvedAt",     TIMESTAMP(timezone=True), nullable=True)
    rejectionNote   = Column("rejectionNote",  Text, nullable=True)
    returnedAt      = Column("returnedAt",     TIMESTAMP(timezone=True), nullable=True)
    createdAt       = Column("createdAt",      TIMESTAMP(timezone=True), server_default=func.now())
    updatedAt       = Column("updatedAt",      TIMESTAMP(timezone=True), server_default=func.now(),
                             onupdate=func.now())

    resource    = relationship("Resource")
    approved_by = relationship("User", foreign_keys=[approvedById])
