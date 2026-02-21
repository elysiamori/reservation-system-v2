from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id         = Column(Integer, primary_key=True, index=True)
    resourceId = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"),
                        unique=True, nullable=False)
    location   = Column(String(255), nullable=False)
    capacity   = Column(Integer, nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    resource = relationship("Resource", back_populates="room")

    def __repr__(self):
        return f"<Room id={self.id} location={self.location} capacity={self.capacity}>"
