from pydantic import BaseModel, field_validator
from typing import Optional
from app.models.resource import ResourceStatus


class VehicleCategoryOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class ResourceOut(BaseModel):
    id:     int
    name:   str
    type:   str
    status: str
    model_config = {"from_attributes": True}


# ─── Requests ─────────────────────────────────────────────────────────────────
class VehicleCreateRequest(BaseModel):
    name:            str    # resource name
    plateNumber:     str
    brand:           str
    model:           str
    year:            int
    currentOdometer: int = 0
    categoryId:      int
    capacity:        int = 4   # number of passengers

    @field_validator("year")
    @classmethod
    def check_year(cls, v):
        if not (1900 <= v <= 2100): raise ValueError("Year must be between 1900 and 2100")
        return v

    @field_validator("currentOdometer")
    @classmethod
    def check_odo(cls, v):
        if v < 0: raise ValueError("Odometer cannot be negative")
        return v

    @field_validator("capacity")
    @classmethod
    def check_capacity(cls, v):
        if v <= 0: raise ValueError("Capacity must be greater than 0")
        return v

    @field_validator("plateNumber")
    @classmethod
    def check_plate(cls, v):
        if not v.strip(): raise ValueError("Plate number cannot be empty")
        return v.strip().upper()


class VehicleUpdateRequest(BaseModel):
    name:            Optional[str] = None
    brand:           Optional[str] = None
    model:           Optional[str] = None
    year:            Optional[int] = None
    currentOdometer: Optional[int] = None
    categoryId:      Optional[int] = None
    plateNumber:     Optional[str] = None
    capacity:        Optional[int] = None


class VehicleStatusRequest(BaseModel):
    status: ResourceStatus
    reason: Optional[str] = None


class CategoryCreateRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def check_name(cls, v):
        if not v.strip(): raise ValueError("Category name cannot be empty")
        return v.strip()
