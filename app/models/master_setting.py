from sqlalchemy import Column, Integer, String, Numeric, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base


class MasterSetting(Base):
    """Stores global admin-managed default values (e.g., fuel prices)."""
    __tablename__ = "master_settings"

    id          = Column(Integer, primary_key=True, index=True)
    key         = Column(String(100), unique=True, nullable=False, index=True)
    value       = Column(Numeric(14, 4), nullable=False)
    unit        = Column(String(50), nullable=True)   # e.g. "IDR/liter", "IDR/kWh"
    description = Column(Text, nullable=True)
    updatedAt   = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<MasterSetting key={self.key} value={self.value}>"
