import enum
from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BookingStatus(str, enum.Enum):
    PENDING   = "PENDING"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"
    ONGOING   = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    OVERDUE   = "OVERDUE"


class Booking(Base):
    __tablename__ = "bookings"

    id           = Column(Integer, primary_key=True, index=True)
    userId       = Column(Integer, ForeignKey("users.id"), nullable=False)
    resourceId   = Column(Integer, ForeignKey("resources.id"), nullable=False)
    startDate    = Column(TIMESTAMP(timezone=True), nullable=False)
    endDate      = Column(TIMESTAMP(timezone=True), nullable=False)
    purpose      = Column(Text, nullable=False)
    status       = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False, index=True)
    approvedById = Column(Integer, ForeignKey("users.id"), nullable=True)
    approvedAt   = Column(TIMESTAMP(timezone=True), nullable=True)
    # Vehicle-specific: assigned by admin after approval
    assignedDriverId  = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    assignedVehicleId = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    assignedAt        = Column(TIMESTAMP(timezone=True), nullable=True)
    returnedAt   = Column(TIMESTAMP(timezone=True), nullable=True)
    createdAt    = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updatedAt    = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                          onupdate=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    user              = relationship("User", foreign_keys=[userId], back_populates="bookings")
    resource          = relationship("Resource", back_populates="bookings")
    approved_by       = relationship("User", foreign_keys=[approvedById], back_populates="approved_bookings")
    assigned_driver   = relationship("Driver", foreign_keys=[assignedDriverId], backref="booking_assignments")
    assigned_vehicle  = relationship("Vehicle", foreign_keys=[assignedVehicleId], backref="booking_assignments")
    approval_logs     = relationship("ApprovalLog", back_populates="booking", cascade="all, delete-orphan")
    fuel_expenses     = relationship("FuelExpense", back_populates="booking")
    driver_ratings    = relationship("DriverRating", back_populates="booking", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Booking id={self.id} status={self.status} resourceId={self.resourceId}>"
