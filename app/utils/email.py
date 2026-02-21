import logging

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, name: str, otp_code: str) -> bool:
    """
    SMTP disabled — OTP printed to console for development.
    Replace with real provider (SendGrid / Resend / SMTP) when ready.
    """
    logger.info("=" * 60)
    logger.info(f"[OTP EMAIL]  To   : {to_email}")
    logger.info(f"[OTP EMAIL]  Name : {name}")
    logger.info(f"[OTP CODE]   >>>  : {otp_code}")
    logger.info("=" * 60)
    return True


def send_booking_status_email(
    to_email: str,
    name: str,
    booking_id: int,
    resource_name: str,
    status: str,
    note: str | None = None,
) -> bool:
    logger.info(f"[BOOKING EMAIL] To={to_email} | Booking#{booking_id} | Status={status}")
    return True
