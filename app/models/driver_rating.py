from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DriverRating(Base):
    __tablename__ = "driver_ratings"

    id         = Column(Integer, primary_key=True, index=True)
    bookingId  = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True)
    driverId   = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    ratedById  = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating     = Column(Integer, nullable=False)   # 1–5
    review     = Column(Text, nullable=True)
    createdAt  = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="chk_rating_range"),
    )

    # ─── Relationships ─────────────────────────────────────────────────────────
    booking  = relationship("Booking", back_populates="driver_ratings")
    driver   = relationship("Driver", back_populates="ratings")
    rated_by = relationship("User", foreign_keys=[ratedById], backref="given_ratings")

    def __repr__(self):
        return f"<DriverRating id={self.id} driver={self.driverId} rating={self.rating}>"
