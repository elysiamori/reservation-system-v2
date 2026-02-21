from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal


class MaintenanceCreateRequest(BaseModel):
    resourceId:  int
    description: str
    startDate:   datetime
    endDate:     Optional[datetime] = None
    cost:        Optional[Decimal]  = None

    @field_validator("description")
    @classmethod
    def check_desc(cls, v):
        if not v.strip(): raise ValueError("Description cannot be empty")
        return v.strip()

    @field_validator("cost")
    @classmethod
    def check_cost(cls, v):
        if v is not None and v < 0: raise ValueError("Cost cannot be negative")
        return v


class MaintenanceUpdateRequest(BaseModel):
    description: Optional[str]      = None
    startDate:   Optional[datetime] = None
    endDate:     Optional[datetime] = None
    cost:        Optional[Decimal]  = None

    @field_validator("cost")
    @classmethod
    def check_cost(cls, v):
        if v is not None and v < 0: raise ValueError("Cost cannot be negative")
        return v
