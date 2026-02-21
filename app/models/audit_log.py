from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    userId      = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL = system action
    action      = Column(String(100), nullable=False)       # e.g. CREATE, UPDATE, DELETE, APPROVE
    entityType  = Column(String(100), nullable=False)       # e.g. Booking, User, Vehicle
    entityId    = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    createdAt   = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog id={self.id} action={self.action} entity={self.entityType}:{self.entityId}>"
