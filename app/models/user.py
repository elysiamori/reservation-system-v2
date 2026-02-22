from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    employeeId   = Column(String(50), unique=True, nullable=False, index=True)
    name         = Column(String(150), nullable=False)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    password     = Column(String(255), nullable=False)
    profilePhoto = Column(String(500), nullable=True)
    isActive     = Column(Boolean, default=True, nullable=False)
    roleId       = Column(Integer, ForeignKey("roles.id"), nullable=False)
    departmentId = Column(Integer, ForeignKey("departments.id"), nullable=False)
    createdAt    = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updatedAt    = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                          onupdate=func.now(), nullable=False)

    # ─── Relationships ─────────────────────────────────────────────────────────
    role               = relationship("Role", back_populates="users")
    department         = relationship("Department", back_populates="users")
    refresh_tokens     = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_otps = relationship("PasswordResetOTP", back_populates="user", cascade="all, delete-orphan")
    driver_profile     = relationship("Driver", back_populates="user", uselist=False)
    bookings           = relationship("Booking", foreign_keys="Booking.userId", back_populates="user")
    approved_bookings  = relationship("Booking", foreign_keys="Booking.approvedById", back_populates="approved_by")
    approval_logs      = relationship("ApprovalLog", back_populates="approver")
    maintenance_records = relationship("MaintenanceRecord", back_populates="created_by")
    audit_logs         = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.roleId}>"
