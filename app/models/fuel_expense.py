from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class FuelExpense(Base):
    __tablename__ = "fuel_expenses"

    id             = Column(Integer, primary_key=True, index=True)
    driverId       = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    vehicleId      = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    bookingId      = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    liter          = Column(Numeric(10, 2), nullable=False)
    pricePerLiter  = Column(Numeric(12, 2), nullable=False)
    totalAmount    = Column(Numeric(14, 2), nullable=False)   # Calculated: liter * pricePerLiter
    odometerBefore = Column(Integer, nullable=False)
    odometerAfter  = Column(Integer, nullable=False)
    note           = Column(Text, nullable=True)
    createdAt      = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    driver  = relationship("Driver", back_populates="fuel_expenses")
    vehicle = relationship("Vehicle", back_populates="fuel_expenses")
    booking = relationship("Booking", back_populates="fuel_expenses")

    def __repr__(self):
        return f"<FuelExpense id={self.id} driverId={self.driverId} total={self.totalAmount}>"
