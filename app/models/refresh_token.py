from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id        = Column(Integer, primary_key=True, index=True)
    userId    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token     = Column(Text, nullable=False, unique=True)
    expiresAt = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked   = Column(Boolean, default=False, nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken id={self.id} userId={self.userId} revoked={self.revoked}>"
