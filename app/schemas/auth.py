from pydantic import BaseModel, EmailStr, field_validator, model_validator
import re


# ─── Helpers ──────────────────────────────────────────────────────────────────
def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one digit")
    return v


# ─── Request Schemas ──────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refreshToken: str


class LogoutRequest(BaseModel):
    refreshToken: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email:   EmailStr
    otpCode: str


class ResetPasswordRequest(BaseModel):
    resetToken:      str
    newPassword:     str
    confirmPassword: str

    @field_validator("newPassword")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.newPassword != self.confirmPassword:
            raise ValueError("Passwords do not match")
        return self


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword:     str
    confirmPassword: str

    @field_validator("newPassword")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.newPassword != self.confirmPassword:
            raise ValueError("Passwords do not match")
        return self


class RegisterRequest(BaseModel):
    employeeId:   str
    name:         str
    email:        EmailStr
    password:     str
    roleId:       int
    departmentId: int

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("employeeId")
    @classmethod
    def employee_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Employee ID cannot be empty")
        return v.strip().upper()


# ─── Response Schemas ─────────────────────────────────────────────────────────
class UserInToken(BaseModel):
    id:         int
    employeeId: str
    name:       str
    email:      str
    role:       str
    department: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    accessToken:  str
    refreshToken: str
    tokenType:    str = "Bearer"
    expiresIn:    int          # seconds
    user:         UserInToken


class RefreshResponse(BaseModel):
    accessToken: str
    expiresIn:   int


class OTPVerifyResponse(BaseModel):
    resetToken: str
    message:    str = "OTP verified. Use resetToken to reset your password."
