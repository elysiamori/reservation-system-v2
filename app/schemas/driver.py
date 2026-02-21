from pydantic import BaseModel, field_validator
from typing import Optional


class DriverCreateRequest(BaseModel):
    userId:        int
    licenseNumber: str
    phoneNumber:   str

    @field_validator("licenseNumber", "phoneNumber")
    @classmethod
    def not_empty(cls, v):
        if not v.strip(): raise ValueError("Field cannot be empty")
        return v.strip()


class DriverUpdateRequest(BaseModel):
    licenseNumber: Optional[str] = None
    phoneNumber:   Optional[str] = None


class AssignVehicleRequest(BaseModel):
    vehicleId: int
