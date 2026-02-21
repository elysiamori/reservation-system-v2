from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, RefreshTokenRequest, LogoutRequest,
    ForgotPasswordRequest, VerifyOTPRequest,
    ResetPasswordRequest, ChangePasswordRequest, RegisterRequest,
)
from app.schemas.common import SuccessResponse, success_response
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth")


# ─── POST /auth/register ──────────────────────────────────────────────────────
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    response_model=SuccessResponse,
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.
    - Employee ID and email must be unique.
    - roleId and departmentId must exist.
    - Password minimum 8 characters, 1 uppercase, 1 number.
    """
    user = auth_service.register(db, data)
    return success_response("Registration successful", {
        "id":           user.id,
        "employeeId":   user.employeeId,
        "name":         user.name,
        "email":        user.email,
        "role":         user.role.name.value,
        "department":   user.department.name,
        "isActive":     user.isActive,
    })


# ─── POST /auth/login ─────────────────────────────────────────────────────────
@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Login and receive access + refresh tokens",
    response_model=SuccessResponse,
)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user.
    Returns accessToken (15 min) and refreshToken (7 days).
    """
    result = auth_service.login(db, data)
    return success_response("Login successful", result)


# ─── POST /auth/refresh ───────────────────────────────────────────────────────
@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    summary="Get new access token using refresh token",
    response_model=SuccessResponse,
)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    result = auth_service.refresh_token(db, data.refreshToken)
    return success_response("Token refreshed", result)


# ─── POST /auth/logout ────────────────────────────────────────────────────────
@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke refresh token (logout)",
    response_model=SuccessResponse,
)
def logout(
    data: LogoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auth_service.logout(db, data.refreshToken, current_user.id)
    return success_response("Logged out successfully", None)


# ─── POST /auth/forgot-password ───────────────────────────────────────────────
@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request OTP for password reset",
    response_model=SuccessResponse,
)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Sends OTP to the registered email address.
    Always returns 200 — even if email does not exist (prevents enumeration).
    """
    auth_service.forgot_password(db, data)
    return success_response("If the email exists, an OTP has been sent.", None)


# ─── POST /auth/verify-otp ────────────────────────────────────────────────────
@router.post(
    "/verify-otp",
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and receive a password reset token",
    response_model=SuccessResponse,
)
def verify_otp(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    reset_token = auth_service.verify_otp(db, str(data.email), data.otpCode)
    return success_response("OTP verified successfully", {
        "resetToken": reset_token,
        "note":       "Use this resetToken in POST /auth/reset-password within 15 minutes.",
    })


# ─── POST /auth/reset-password ────────────────────────────────────────────────
@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password using reset token from OTP verification",
    response_model=SuccessResponse,
)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, data)
    return success_response("Password reset successfully. Please login with your new password.", None)


# ─── PATCH /auth/change-password ──────────────────────────────────────────────
@router.patch(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password (requires current password, authenticated)",
    response_model=SuccessResponse,
)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auth_service.change_password(db, data, current_user)
    return success_response("Password changed successfully.", None)


# ─── GET /auth/me ─────────────────────────────────────────────────────────────
@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    response_model=SuccessResponse,
)
def get_me(current_user: User = Depends(get_current_user)):
    return success_response("User profile retrieved", {
        "id":           current_user.id,
        "employeeId":   current_user.employeeId,
        "name":         current_user.name,
        "email":        current_user.email,
        "isActive":     current_user.isActive,
        "role":         {"id": current_user.role.id, "name": current_user.role.name.value},
        "department":   {"id": current_user.department.id, "name": current_user.department.name},
        "createdAt":    current_user.createdAt.isoformat(),
    })
