from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_admin_user
from app.models.user import User
from app.schemas.master_setting import MasterSettingUpdate
from app.schemas.common import success_response
from app.services.master_setting_service import master_setting_service

router = APIRouter(prefix="/master-settings")


@router.get("", summary="List all master settings (Admin)")
def list_settings(
    db: Session = Depends(get_db),
    _:  User    = Depends(get_admin_user),
):
    return success_response("Master settings retrieved", master_setting_service.list_settings(db))


@router.get("/{key}", summary="Get specific master setting (Admin)")
def get_setting(
    key: str,
    db:  Session = Depends(get_db),
    _:   User    = Depends(get_admin_user),
):
    return success_response("Setting retrieved", master_setting_service.get_setting(db, key))


@router.put("/{key}", summary="Create or update a master setting (Admin)")
def upsert_setting(
    key:          str,
    body:         MasterSettingUpdate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_admin_user),
):
    return success_response("Setting updated", master_setting_service.upsert_setting(db, key, body, current_user))
