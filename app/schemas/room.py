from pydantic import BaseModel, field_validator
from typing import Optional
from app.models.resource import ResourceStatus


class RoomCreateRequest(BaseModel):
    name:     str
    location: str
    capacity: int

    @field_validator("capacity")
    @classmethod
    def check_capacity(cls, v):
        if v <= 0: raise ValueError("Capacity must be greater than 0")
        return v

    @field_validator("name", "location")
    @classmethod
    def check_not_empty(cls, v):
        if not v.strip(): raise ValueError("Field cannot be empty")
        return v.strip()


class RoomUpdateRequest(BaseModel):
    name:     Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = None

    @field_validator("capacity")
    @classmethod
    def check_capacity(cls, v):
        if v is not None and v <= 0: raise ValueError("Capacity must be greater than 0")
        return v


class RoomStatusRequest(BaseModel):
    status: ResourceStatus
    reason: Optional[str] = None
