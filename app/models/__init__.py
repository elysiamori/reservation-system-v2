"""
Import all models here so that:
1. Alembic can auto-detect them when generating migrations
2. Relationships between models resolve correctly

Order matters — import parent tables before child tables.
"""

from app.models.role import Role
from app.models.department import Department
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.password_reset_otp import PasswordResetOTP
from app.models.resource import Resource
from app.models.vehicle_category import VehicleCategory
from app.models.vehicle import Vehicle
from app.models.room import Room
from app.models.driver import Driver
from app.models.booking import Booking
from app.models.approval_log import ApprovalLog
from app.models.driver_assignment import DriverAssignment
from app.models.fuel_expense import FuelExpense, FuelType
from app.models.maintenance_record import MaintenanceRecord
from app.models.audit_log import AuditLog
from app.models.driver_rating import DriverRating
from app.models.master_setting import MasterSetting
from app.models.guest_booking import GuestBooking
from app.models.attachment import Attachment

__all__ = [
    "Role",
    "Department",
    "User",
    "RefreshToken",
    "PasswordResetOTP",
    "Resource",
    "VehicleCategory",
    "Vehicle",
    "Room",
    "Driver",
    "Booking",
    "ApprovalLog",
    "DriverAssignment",
    "FuelExpense",
    "FuelType",
    "MaintenanceRecord",
    "AuditLog",
    "DriverRating",
    "MasterSetting",
    "GuestBooking",
    "Attachment",
]
