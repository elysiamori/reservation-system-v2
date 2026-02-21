from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id          = Column(Integer, primary_key=True, index=True)
    resourceId  = Column(Integer, ForeignKey("resources.id"), nullable=False)
    description = Column(Text, nullable=False)
    startDate   = Column(TIMESTAMP(timezone=True), nullable=False)
    endDate     = Column(TIMESTAMP(timezone=True), nullable=True)  # NULL = ongoing maintenance
    cost        = Column(Numeric(12, 2), nullable=True)
    createdById = Column(Integer, ForeignKey("users.id"), nullable=False)
    createdAt   = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    resource   = relationship("Resource", back_populates="maintenance_records")
    created_by = relationship("User", back_populates="maintenance_records")

    def __repr__(self):
        return f"<MaintenanceRecord id={self.id} resourceId={self.resourceId}>"
