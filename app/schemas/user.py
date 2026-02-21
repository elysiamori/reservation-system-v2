from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re


def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one digit")
    return v


# ─── Nested ───────────────────────────────────────────────────────────────────
class RoleOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class DepartmentOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


# ─── Request ──────────────────────────────────────────────────────────────────
class UserCreateRequest(BaseModel):
    employeeId:   str
    name:         str
    email:        EmailStr
    password:     str
    roleId:       int
    departmentId: int

    @field_validator("password")
    @classmethod
    def check_password(cls, v): return validate_password_strength(v)

    @field_validator("name")
    @classmethod
    def check_name(cls, v):
        if not v.strip(): raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("employeeId")
    @classmethod
    def check_emp_id(cls, v):
        if not v.strip(): raise ValueError("Employee ID cannot be empty")
        return v.strip().upper()


class UserUpdateRequest(BaseModel):
    name:         Optional[str] = None
    email:        Optional[EmailStr] = None
    roleId:       Optional[int] = None
    departmentId: Optional[int] = None

    @field_validator("name")
    @classmethod
    def check_name(cls, v):
        if v is not None and not v.strip(): raise ValueError("Name cannot be empty")
        return v.strip() if v else v


# ─── Response ─────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id:           int
    employeeId:   str
    name:         str
    email:        str
    isActive:     bool
    role:         RoleOut
    department:   DepartmentOut
    createdAt:    str
    updatedAt:    str

    model_config = {"from_attributes": True}
