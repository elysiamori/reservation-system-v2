import enum
from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class FuelType(str, enum.Enum):
    BBM     = "BBM"       # Gasoline / Solar
    LISTRIK = "LISTRIK"   # Electric (SPKLU)


class FuelExpense(Base):
    __tablename__ = "fuel_expenses"

    id             = Column(Integer, primary_key=True, index=True)
    driverId       = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    vehicleId      = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    bookingId      = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    fuelType       = Column(Enum(FuelType), nullable=False, default=FuelType.BBM)

    # BBM fields
    liter          = Column(Numeric(10, 2), nullable=True)
    pricePerLiter  = Column(Numeric(12, 2), nullable=True)
    odometerBefore = Column(Integer, nullable=True)
    odometerAfter  = Column(Integer, nullable=True)

    # Listrik fields
    kwh            = Column(Numeric(10, 2), nullable=True)
    pricePerKwh    = Column(Numeric(12, 2), nullable=True)
    batteryBefore  = Column(Numeric(5, 2), nullable=True)   # %
    batteryAfter   = Column(Numeric(5, 2), nullable=True)   # %

    # Common
    totalAmount    = Column(Numeric(14, 2), nullable=False)
    note           = Column(Text, nullable=True)
    createdAt      = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    driver  = relationship("Driver", back_populates="fuel_expenses")
    vehicle = relationship("Vehicle", back_populates="fuel_expenses")
    booking = relationship("Booking", back_populates="fuel_expenses")

    def __repr__(self):
        return f"<FuelExpense id={self.id} type={self.fuelType} total={self.totalAmount}>"
