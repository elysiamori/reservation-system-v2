from fastapi import HTTPException, status


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR CODES — Machine-readable constants for frontend switch/case
# ═══════════════════════════════════════════════════════════════════════════════
class ErrorCode:
    VALIDATION_ERROR        = "VALIDATION_ERROR"
    UNAUTHORIZED            = "UNAUTHORIZED"
    TOKEN_EXPIRED           = "TOKEN_EXPIRED"
    REFRESH_TOKEN_INVALID   = "REFRESH_TOKEN_INVALID"
    FORBIDDEN               = "FORBIDDEN"
    NOT_FOUND               = "NOT_FOUND"
    DUPLICATE_ENTRY         = "DUPLICATE_ENTRY"
    BOOKING_CONFLICT        = "BOOKING_CONFLICT"
    BOOKING_NOT_PENDING     = "BOOKING_NOT_PENDING"
    RESOURCE_UNAVAILABLE    = "RESOURCE_UNAVAILABLE"
    INVALID_DATE_RANGE      = "INVALID_DATE_RANGE"
    SELF_APPROVAL           = "SELF_APPROVAL"
    DRIVER_NOT_ASSIGNED     = "DRIVER_NOT_ASSIGNED"
    ACCOUNT_INACTIVE        = "ACCOUNT_INACTIVE"
    OTP_INVALID             = "OTP_INVALID"
    OTP_EXPIRED             = "OTP_EXPIRED"
    INTERNAL_SERVER_ERROR   = "INTERNAL_SERVER_ERROR"


# ═══════════════════════════════════════════════════════════════════════════════
# BASE EXCEPTION
# ═══════════════════════════════════════════════════════════════════════════════
class AppException(HTTPException):
    """
    Base exception for all application-level errors.
    Carries a machine-readable error_code for frontend handling.
    """
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str,
        details: list | None = None,
        field: str | None = None,
    ):
        super().__init__(status_code=status_code, detail={
            "message": message,
            "error": {
                "code": error_code,
                "details": details,
                "field": field,
            }
        })


# ═══════════════════════════════════════════════════════════════════════════════
# CONCRETE EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, message, ErrorCode.UNAUTHORIZED)


class TokenExpiredException(AppException):
    def __init__(self):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Access token has expired", ErrorCode.TOKEN_EXPIRED)


class RefreshTokenInvalidException(AppException):
    def __init__(self):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Refresh token is invalid or revoked", ErrorCode.REFRESH_TOKEN_INVALID)


class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(status.HTTP_403_FORBIDDEN, message, ErrorCode.FORBIDDEN)


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{resource} not found", ErrorCode.NOT_FOUND)


class DuplicateEntryException(AppException):
    def __init__(self, message: str = "Record already exists", field: str | None = None):
        super().__init__(status.HTTP_409_CONFLICT, message, ErrorCode.DUPLICATE_ENTRY, field=field)


class BookingConflictException(AppException):
    def __init__(self):
        super().__init__(
            status.HTTP_409_CONFLICT,
            "Resource is already booked for the requested time range",
            ErrorCode.BOOKING_CONFLICT,
        )


class BookingNotPendingException(AppException):
    def __init__(self):
        super().__init__(
            status.HTTP_400_BAD_REQUEST,
            "Booking must be in PENDING status to perform this action",
            ErrorCode.BOOKING_NOT_PENDING,
        )


class ResourceUnavailableException(AppException):
    def __init__(self):
        super().__init__(
            status.HTTP_400_BAD_REQUEST,
            "Resource is not available (MAINTENANCE or INACTIVE)",
            ErrorCode.RESOURCE_UNAVAILABLE,
        )


class InvalidDateRangeException(AppException):
    def __init__(self):
        super().__init__(
            status.HTTP_400_BAD_REQUEST,
            "End date must be after start date",
            ErrorCode.INVALID_DATE_RANGE,
        )


class SelfApprovalException(AppException):
    def __init__(self):
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            "You cannot approve or reject your own booking",
            ErrorCode.SELF_APPROVAL,
        )


class AccountInactiveException(AppException):
    def __init__(self):
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            "Your account has been deactivated. Contact admin.",
            ErrorCode.ACCOUNT_INACTIVE,
        )


class OTPInvalidException(AppException):
    def __init__(self):
        super().__init__(status.HTTP_400_BAD_REQUEST, "OTP code is invalid", ErrorCode.OTP_INVALID)


class OTPExpiredException(AppException):
    def __init__(self):
        super().__init__(status.HTTP_400_BAD_REQUEST, "OTP code has expired", ErrorCode.OTP_EXPIRED)


class DriverNotAssignedException(AppException):
    def __init__(self):
        super().__init__(
            status.HTTP_400_BAD_REQUEST,
            "Driver does not have an active vehicle assignment",
            ErrorCode.DRIVER_NOT_ASSIGNED,
        )
