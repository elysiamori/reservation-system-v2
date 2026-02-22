from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id           = Column(Integer, primary_key=True, index=True)
    uploadedById = Column("uploadedById", Integer, ForeignKey("users.id"), nullable=False)
    vehicleId    = Column("vehicleId",  Integer, ForeignKey("vehicles.id",  ondelete="CASCADE"), nullable=True)
    roomId       = Column("roomId",     Integer, ForeignKey("rooms.id",     ondelete="CASCADE"), nullable=True)
    bookingId    = Column("bookingId",  Integer, ForeignKey("bookings.id",  ondelete="CASCADE"), nullable=True)
    fileUrl      = Column("fileUrl",    String(500), nullable=False)
    fileName     = Column("fileName",   String(255), nullable=False)
    fileType     = Column("fileType",   String(100), nullable=False)
    fileSize     = Column("fileSize",   Integer, nullable=True)
    description  = Column(Text, nullable=True)
    createdAt    = Column("createdAt",  TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            '(CASE WHEN "vehicleId" IS NOT NULL THEN 1 ELSE 0 END +'
            ' CASE WHEN "roomId"    IS NOT NULL THEN 1 ELSE 0 END +'
            ' CASE WHEN "bookingId" IS NOT NULL THEN 1 ELSE 0 END) = 1',
            name="chk_one_target"
        ),
    )

    uploaded_by = relationship("User",    foreign_keys=[uploadedById])
    vehicle     = relationship("Vehicle", foreign_keys=[vehicleId])
    room        = relationship("Room",    foreign_keys=[roomId])
    booking     = relationship("Booking", foreign_keys=[bookingId])
