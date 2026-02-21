from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime, timezone


class GuestBookingCreateRequest(BaseModel):
    guestName:      str
    guestEmail:     EmailStr
    guestPhone:     str
    departmentName: str
    resourceId:     int
    startDate:      datetime
    endDate:        datetime
    purpose:        str

    @field_validator("guestName", "guestPhone", "departmentName", "purpose")
    @classmethod
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field tidak boleh kosong")
        return v.strip()

    @model_validator(mode="after")
    def check_dates(self) -> "GuestBookingCreateRequest":
        now = datetime.now(timezone.utc)
        start = self.startDate
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if start <= now:
            raise ValueError("startDate harus di masa depan")
        if self.endDate <= self.startDate:
            raise ValueError("endDate harus setelah startDate")
        return self


class GuestBookingCompleteRequest(BaseModel):
    note: Optional[str] = None


class GuestBookingCancelRequest(BaseModel):
    note: Optional[str] = None
