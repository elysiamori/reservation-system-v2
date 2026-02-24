from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime, timezone


class BookingCreateRequest(BaseModel):
    resourceId: int
    startDate:  datetime
    endDate:    datetime
    purpose:    str

    @field_validator("purpose")
    @classmethod
    def check_purpose(cls, v):
        if not v.strip(): raise ValueError("Purpose cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def check_dates(self):
        if self.endDate <= self.startDate:
            raise ValueError("endDate must be after startDate")
        return self


class ApproveRequest(BaseModel):
    note: Optional[str] = None


class RejectRequest(BaseModel):
    note: str

    @field_validator("note")
    @classmethod
    def check_note(cls, v):
        if not v.strip(): raise ValueError("Rejection note is required")
        return v.strip()


class CancelRequest(BaseModel):
    note: Optional[str] = None


class AssignVehicleRequest(BaseModel):
    """Admin assigns vehicle and driver to an approved vehicle booking."""
    driverId:  int
    vehicleId: int


class DriverRatingCreateRequest(BaseModel):
    rating: int
    review: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def check_rating(cls, v):
        if not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return v
