from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id              = Column(Integer, primary_key=True, index=True)
    resourceId      = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"),
                             unique=True, nullable=False)
    plateNumber     = Column(String(20), unique=True, nullable=False, index=True)
    brand           = Column(String(100), nullable=False)
    model           = Column(String(100), nullable=False)
    year            = Column(Integer, nullable=False)
    currentOdometer = Column(Integer, default=0, nullable=False)
    categoryId      = Column(Integer, ForeignKey("vehicle_categories.id"), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    resource     = relationship("Resource", back_populates="vehicle")
    category     = relationship("VehicleCategory", back_populates="vehicles")
    assignments  = relationship("DriverAssignment", back_populates="vehicle")
    fuel_expenses = relationship("FuelExpense", back_populates="vehicle")

    def __repr__(self):
        return f"<Vehicle id={self.id} plate={self.plateNumber}>"
