from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id        = Column(Integer, primary_key=True, index=True)
    name      = Column(String(100), unique=True, nullable=False)
    createdAt = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    users = relationship("User", back_populates="department")

    def __repr__(self):
        return f"<Department id={self.id} name={self.name}>"
