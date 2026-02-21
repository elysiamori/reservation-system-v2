from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class VehicleCategory(Base):
    __tablename__ = "vehicle_categories"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    vehicles = relationship("Vehicle", back_populates="category")

    def __repr__(self):
        return f"<VehicleCategory id={self.id} name={self.name}>"
