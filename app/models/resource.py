import enum
from sqlalchemy import Column, Integer, String, Enum, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ResourceType(str, enum.Enum):
    VEHICLE = "VEHICLE"
    ROOM    = "ROOM"


class ResourceStatus(str, enum.Enum):
    AVAILABLE   = "AVAILABLE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE    = "INACTIVE"


class Resource(Base):
    __tablename__ = "resources"

    id        = Column(Integer, primary_key=True, index=True)
    name      = Column(String(200), nullable=False)
    type      = Column(Enum(ResourceType), nullable=False)
    status    = Column(Enum(ResourceStatus), default=ResourceStatus.AVAILABLE, nullable=False)
    createdAt = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updatedAt = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                       onupdate=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    vehicle             = relationship("Vehicle", back_populates="resource", uselist=False)
    room                = relationship("Room", back_populates="resource", uselist=False)
    bookings            = relationship("Booking", back_populates="resource")
    maintenance_records = relationship("MaintenanceRecord", back_populates="resource")

    def __repr__(self):
        return f"<Resource id={self.id} name={self.name} type={self.type} status={self.status}>"
