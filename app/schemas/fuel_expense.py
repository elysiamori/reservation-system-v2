from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from decimal import Decimal
from app.models.fuel_expense import FuelType


class FuelExpenseBBMCreate(BaseModel):
    """Schema for gasoline/diesel fuel expense."""
    vehicleId:      int
    bookingId:      Optional[int] = None
    fuelType:       FuelType = FuelType.BBM
    liter:          Decimal
    pricePerLiter:  Optional[Decimal] = None   # if None, use master setting default
    odometerBefore: int
    odometerAfter:  int
    note:           Optional[str] = None

    @field_validator("liter")
    @classmethod
    def check_liter(cls, v):
        if v <= 0: raise ValueError("Liter must be greater than 0")
        return v

    @model_validator(mode="after")
    def check_odometer(self):
        if self.odometerAfter <= self.odometerBefore:
            raise ValueError("odometerAfter must be greater than odometerBefore")
        return self


class FuelExpenseListrikCreate(BaseModel):
    """Schema for electric vehicle charging expense."""
    vehicleId:    int
    bookingId:    Optional[int] = None
    fuelType:     FuelType = FuelType.LISTRIK
    kwh:          Decimal
    pricePerKwh:  Optional[Decimal] = None     # if None, use master setting default
    batteryBefore: Optional[Decimal] = None    # % before charging
    batteryAfter:  Optional[Decimal] = None    # % after charging
    note:          Optional[str] = None

    @field_validator("kwh")
    @classmethod
    def check_kwh(cls, v):
        if v <= 0: raise ValueError("kWh must be greater than 0")
        return v


class FuelExpenseCreateRequest(BaseModel):
    """Unified schema — fill BBM or Listrik fields based on fuelType."""
    vehicleId:      int
    bookingId:      Optional[int] = None
    fuelType:       FuelType

    # BBM fields
    liter:          Optional[Decimal] = None
    pricePerLiter:  Optional[Decimal] = None
    odometerBefore: Optional[int] = None
    odometerAfter:  Optional[int] = None

    # Listrik fields
    kwh:            Optional[Decimal] = None
    pricePerKwh:    Optional[Decimal] = None
    batteryBefore:  Optional[Decimal] = None
    batteryAfter:   Optional[Decimal] = None

    note:           Optional[str] = None

    @model_validator(mode="after")
    def validate_fuel_fields(self):
        if self.fuelType == FuelType.BBM:
            if self.liter is None or self.liter <= 0:
                raise ValueError("liter is required and must be > 0 for BBM")
            if self.odometerBefore is None:
                raise ValueError("odometerBefore is required for BBM")
            if self.odometerAfter is None:
                raise ValueError("odometerAfter is required for BBM")
            if self.odometerAfter <= self.odometerBefore:
                raise ValueError("odometerAfter must be greater than odometerBefore")
        elif self.fuelType == FuelType.LISTRIK:
            if self.kwh is None or self.kwh <= 0:
                raise ValueError("kwh is required and must be > 0 for LISTRIK")
        return self


class FuelExpenseUpdateRequest(BaseModel):
    liter:          Optional[Decimal] = None
    pricePerLiter:  Optional[Decimal] = None
    odometerBefore: Optional[int] = None
    odometerAfter:  Optional[int] = None
    kwh:            Optional[Decimal] = None
    pricePerKwh:    Optional[Decimal] = None
    batteryBefore:  Optional[Decimal] = None
    batteryAfter:   Optional[Decimal] = None
    note:           Optional[str] = None
