import random
import string
from datetime import datetime, timedelta, timezone

from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.utils.exceptions import TokenExpiredException, UnauthorizedException

# ─── Password Hashing ─────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT ──────────────────────────────────────────────────────────────────────
def create_access_token(user_id: int, role: str) -> str:
    """
    Create a short-lived JWT access token.
    Payload: sub (user_id), role, type, exp
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    """
    Create a long-lived JWT refresh token.
    Returns (token_string, expiry_datetime).
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expire


def verify_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.
    Raises 401 if invalid, 401 (TOKEN_EXPIRED) if expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredException()
    except JWTError:
        raise UnauthorizedException("Invalid or malformed token")


def verify_refresh_token(token: str) -> dict:
    """
    Decode and validate a JWT refresh token.
    Raises 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")
        return payload
    except ExpiredSignatureError:
        raise UnauthorizedException("Refresh token has expired, please login again")
    except JWTError:
        raise UnauthorizedException("Invalid refresh token")


# ─── OTP ──────────────────────────────────────────────────────────────────────
def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP string of given length."""
    return "".join(random.choices(string.digits, k=length))


def otp_expiry() -> datetime:
    """Return OTP expiry timestamp (UTC)."""
    return datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
