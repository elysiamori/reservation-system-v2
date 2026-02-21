from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base


class DriverAssignment(Base):
    __tablename__ = "driver_assignments"

    id         = Column(Integer, primary_key=True, index=True)
    driverId   = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    vehicleId  = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    assignedAt = Column(TIMESTAMP(timezone=True), nullable=False)
    releasedAt = Column(TIMESTAMP(timezone=True), nullable=True)  # NULL = still assigned

    # ─── Relationships ─────────────────────────────────────────────────────────
    driver  = relationship("Driver", back_populates="assignments")
    vehicle = relationship("Vehicle", back_populates="assignments")

    def __repr__(self):
        return f"<DriverAssignment id={self.id} driverId={self.driverId} vehicleId={self.vehicleId}>"
