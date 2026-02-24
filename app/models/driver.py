from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id            = Column(Integer, primary_key=True, index=True)
    userId        = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                           unique=True, nullable=False)
    licenseNumber = Column(String(100), nullable=False)
    phoneNumber   = Column(String(20), nullable=False)
    isActive      = Column(Boolean, default=True, nullable=False)
    createdAt     = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    user          = relationship("User", back_populates="driver_profile")
    assignments   = relationship("DriverAssignment", back_populates="driver")
    fuel_expenses = relationship("FuelExpense", back_populates="driver")
    ratings       = relationship("DriverRating", back_populates="driver")

    def __repr__(self):
        return f"<Driver id={self.id} userId={self.userId} isActive={self.isActive}>"
