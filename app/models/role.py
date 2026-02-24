import enum
from sqlalchemy import Column, Integer, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class RoleName(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    ADMIN    = "ADMIN"
    DRIVER   = "DRIVER"


class Role(Base):
    __tablename__ = "roles"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(Enum(RoleName), unique=True, nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role id={self.id} name={self.name}>"
