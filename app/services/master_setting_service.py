from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.master_setting import MasterSetting
from app.schemas.master_setting import MasterSettingUpdate
from app.utils.audit import log_action
from app.models.user import User


# Default keys
DEFAULT_SETTINGS = [
    {"key": "price_per_liter_bbm",     "value": 10000, "unit": "IDR/liter",  "description": "Default gasoline price per liter"},
    {"key": "price_per_kwh_listrik",   "value": 2466,  "unit": "IDR/kWh",    "description": "Default electricity price per kWh (PLN tariff)"},
]


def _serialize(s: MasterSetting) -> dict:
    return {
        "key":         s.key,
        "value":       float(s.value),
        "unit":        s.unit,
        "description": s.description,
        "updatedAt":   s.updatedAt.isoformat(),
    }


class MasterSettingService:

    def list_settings(self, db: Session) -> list[dict]:
        settings = db.query(MasterSetting).all()
        return [_serialize(s) for s in settings]

    def get_setting(self, db: Session, key: str) -> dict:
        s = db.query(MasterSetting).filter(MasterSetting.key == key).first()
        if not s:
            from app.utils.exceptions import NotFoundException
            raise NotFoundException(f"Setting '{key}'")
        return _serialize(s)

    def upsert_setting(self, db: Session, key: str, data: MasterSettingUpdate, current_user: User) -> dict:
        s = db.query(MasterSetting).filter(MasterSetting.key == key).first()
        if s:
            s.value       = data.value
            if data.description is not None:
                s.description = data.description
            if hasattr(data, "unit") and data.unit is not None:
                s.unit = data.unit
        else:
            s = MasterSetting(key=key, value=data.value, description=data.description)
            db.add(s)

        db.flush()
        log_action(db, current_user.id, "UPDATE", "MasterSetting", s.id,
                   f"Admin updated setting '{key}' to {data.value}")
        db.commit()
        db.refresh(s)
        return _serialize(s)

    def seed_defaults(self, db: Session) -> None:
        """Insert default settings if not already present."""
        for d in DEFAULT_SETTINGS:
            existing = db.query(MasterSetting).filter(MasterSetting.key == d["key"]).first()
            if not existing:
                db.add(MasterSetting(**d))
        db.commit()


master_setting_service = MasterSettingService()
