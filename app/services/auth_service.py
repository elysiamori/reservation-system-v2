from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.models.refresh_token import RefreshToken
from app.models.password_reset_otp import PasswordResetOTP
from app.schemas.auth import (
    LoginRequest, RegisterRequest, ChangePasswordRequest,
    ResetPasswordRequest, ForgotPasswordRequest,
)
from app.utils.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token, verify_refresh_token,
    generate_otp, otp_expiry,
)
from app.utils.email import send_otp_email
from app.utils.audit import log_action
from app.utils.exceptions import (
    UnauthorizedException, AccountInactiveException,
    NotFoundException, DuplicateEntryException,
    RefreshTokenInvalidException, OTPInvalidException, OTPExpiredException,
)
from app.config import settings


class AuthService:

    # ─── Login ────────────────────────────────────────────────────────────────
    def login(self, db: Session, data: LoginRequest) -> dict:
        user = db.query(User).filter(User.email == data.email).first()

        if not user or not verify_password(data.password, user.password):
            raise UnauthorizedException("Invalid email or password")

        if not user.isActive:
            raise AccountInactiveException()

        # Create tokens
        access_token = create_access_token(user.id, user.role.name.value)
        refresh_token_str, refresh_expires = create_refresh_token(user.id)

        # Persist refresh token
        refresh_token = RefreshToken(
            userId=user.id,
            token=refresh_token_str,
            expiresAt=refresh_expires,
            revoked=False,
        )
        db.add(refresh_token)

        # Audit
        log_action(db, user.id, "LOGIN", "User", user.id, f"{user.name} logged in")
        db.commit()

        return {
            "accessToken":  access_token,
            "refreshToken": refresh_token_str,
            "tokenType":    "Bearer",
            "expiresIn":    0,
            "user": {
                "id":         user.id,
                "employeeId": user.employeeId,
                "name":       user.name,
                "email":      user.email,
                "role":       user.role.name.value,
                "department": user.department.name,
            }
        }

    # ─── Refresh Token ────────────────────────────────────────────────────────
    def refresh_token(self, db: Session, refresh_token_str: str) -> dict:
        payload = verify_refresh_token(refresh_token_str)
        user_id = int(payload.get("sub"))

        stored = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_str,
            RefreshToken.userId == user_id,
            RefreshToken.revoked == False,
        ).first()

        if not stored:
            raise RefreshTokenInvalidException()

        if stored.expiresAt.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            stored.revoked = True
            db.commit()
            raise RefreshTokenInvalidException()

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.isActive:
            raise AccountInactiveException()

        access_token = create_access_token(user.id, user.role.name.value)

        return {
            "accessToken": access_token,
            "expiresIn":   settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    # ─── Logout ───────────────────────────────────────────────────────────────
    def logout(self, db: Session, refresh_token_str: str, user_id: int) -> None:
        stored = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_str,
            RefreshToken.userId == user_id,
        ).first()
        if stored:
            stored.revoked = True

        log_action(db, user_id, "LOGOUT", "User", user_id, "User logged out")
        db.commit()

    # ─── Register ─────────────────────────────────────────────────────────────
    def register(self, db: Session, data: RegisterRequest) -> User:
        # Check uniqueness
        if db.query(User).filter(User.email == data.email).first():
            raise DuplicateEntryException("Email already registered", field="email")
        if db.query(User).filter(User.employeeId == data.employeeId).first():
            raise DuplicateEntryException("Employee ID already exists", field="employeeId")

        # Validate FK references
        role = db.query(Role).filter(Role.id == data.roleId).first()
        if not role:
            raise NotFoundException("Role")

        department = db.query(Department).filter(Department.id == data.departmentId).first()
        if not department:
            raise NotFoundException("Department")

        user = User(
            employeeId=data.employeeId,
            name=data.name,
            email=data.email,
            password=hash_password(data.password),
            isActive=True,
            roleId=data.roleId,
            departmentId=data.departmentId,
        )
        db.add(user)
        db.flush()  # Get user.id without committing

        log_action(db, user.id, "REGISTER", "User", user.id,
                   f"New user registered: {user.name} ({user.email})")
        db.commit()
        db.refresh(user)
        return user

    # ─── Forgot Password ──────────────────────────────────────────────────────
    def forgot_password(self, db: Session, data: ForgotPasswordRequest) -> None:
        """
        Always returns success (HTTP 200) to prevent email enumeration.
        OTP is only sent if the email actually exists.
        """
        user = db.query(User).filter(User.email == data.email).first()
        if not user or not user.isActive:
            return  # Silent — don't reveal whether email exists

        # Invalidate previous OTPs for this user
        db.query(PasswordResetOTP).filter(
            PasswordResetOTP.userId == user.id,
            PasswordResetOTP.isUsed == False,
        ).update({"isUsed": True})

        otp_code = generate_otp(settings.OTP_LENGTH)
        otp = PasswordResetOTP(
            userId=user.id,
            otpCode=otp_code,
            expiresAt=otp_expiry(),
            isUsed=False,
        )
        db.add(otp)
        db.commit()

        send_otp_email(user.email, user.name, otp_code)

    # ─── Verify OTP ───────────────────────────────────────────────────────────
    def verify_otp(self, db: Session, email: str, otp_code: str) -> str:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise OTPInvalidException()

        otp = db.query(PasswordResetOTP).filter(
            PasswordResetOTP.userId == user.id,
            PasswordResetOTP.otpCode == otp_code,
            PasswordResetOTP.isUsed == False,
        ).order_by(PasswordResetOTP.id.desc()).first()

        if not otp:
            raise OTPInvalidException()

        if otp.expiresAt.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise OTPExpiredException()

        # Mark OTP used
        otp.isUsed = True
        db.commit()

        # Issue a short-lived reset token (re-use JWT with type=reset)
        from jose import jwt
        from datetime import timedelta
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        reset_token = jwt.encode(
            {"sub": str(user.id), "type": "reset", "exp": expire},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        return reset_token

    # ─── Reset Password ───────────────────────────────────────────────────────
    def reset_password(self, db: Session, data: ResetPasswordRequest) -> None:
        from jose import jwt, JWTError, ExpiredSignatureError
        from app.utils.exceptions import UnauthorizedException

        try:
            payload = jwt.decode(data.resetToken, settings.SECRET_KEY,
                                 algorithms=[settings.ALGORITHM])
            if payload.get("type") != "reset":
                raise UnauthorizedException("Invalid reset token")
            user_id = int(payload.get("sub"))
        except ExpiredSignatureError:
            raise UnauthorizedException("Reset token has expired. Request a new OTP.")
        except JWTError:
            raise UnauthorizedException("Invalid reset token")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User")

        user.password = hash_password(data.newPassword)
        log_action(db, user.id, "RESET_PASSWORD", "User", user.id, "Password reset via OTP")
        db.commit()

    # ─── Change Password ──────────────────────────────────────────────────────
    def change_password(
        self, db: Session, data: ChangePasswordRequest, current_user: User
    ) -> None:
        if not verify_password(data.currentPassword, current_user.password):
            raise UnauthorizedException("Current password is incorrect")

        current_user.password = hash_password(data.newPassword)
        log_action(db, current_user.id, "CHANGE_PASSWORD", "User", current_user.id,
                   f"{current_user.name} changed their password")
        db.commit()


auth_service = AuthService()
