from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class MasterSettingUpdate(BaseModel):
    value:       Decimal
    unit: Optional[str] = None
    description: Optional[str] = None


class MasterSettingOut(BaseModel):
    key:         str
    value:       float
    unit:        Optional[str] = None
    description: Optional[str] = None
    model_config = {"from_attributes": True}
