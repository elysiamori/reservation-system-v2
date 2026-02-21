from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id        = Column(Integer, primary_key=True, index=True)
    userId    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    otpCode   = Column(String(10), nullable=False)
    expiresAt = Column(TIMESTAMP(timezone=True), nullable=False)
    isUsed    = Column(Boolean, default=False, nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    user = relationship("User", back_populates="password_reset_otps")

    def __repr__(self):
        return f"<PasswordResetOTP id={self.id} userId={self.userId} isUsed={self.isUsed}>"
