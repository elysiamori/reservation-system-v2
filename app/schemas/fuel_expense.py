from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from decimal import Decimal


class FuelExpenseCreateRequest(BaseModel):
    vehicleId:      int
    bookingId:      Optional[int] = None
    liter:          Decimal
    pricePerLiter:  Decimal
    odometerBefore: int
    odometerAfter:  int
    note:           Optional[str] = None

    @field_validator("liter", "pricePerLiter")
    @classmethod
    def check_positive(cls, v):
        if v <= 0: raise ValueError("Value must be greater than 0")
        return v

    @field_validator("odometerBefore")
    @classmethod
    def check_odo_before(cls, v):
        if v < 0: raise ValueError("Odometer cannot be negative")
        return v

    @model_validator(mode="after")
    def check_odometer(self) -> "FuelExpenseCreateRequest":
        if self.odometerAfter <= self.odometerBefore:
            raise ValueError("odometerAfter must be greater than odometerBefore")
        return self


class FuelExpenseUpdateRequest(BaseModel):
    liter:          Optional[Decimal] = None
    pricePerLiter:  Optional[Decimal] = None
    odometerBefore: Optional[int]     = None
    odometerAfter:  Optional[int]     = None
    note:           Optional[str]     = None
