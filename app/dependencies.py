from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.role import RoleName
from app.utils.security import verify_access_token
from app.utils.exceptions import (
    UnauthorizedException,
    ForbiddenException,
    AccountInactiveException,
    NotFoundException,
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise UnauthorizedException("No authentication token provided")
    payload = verify_access_token(credentials.credentials)
    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException("Invalid token payload")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise NotFoundException("User")
    if not user.isActive:
        raise AccountInactiveException()
    return user


def require_roles(*roles: RoleName):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in roles:
            raise ForbiddenException(
                f"This action requires one of these roles: {[r.value for r in roles]}"
            )
        return current_user
    return dependency


def get_admin_user(current_user: User = Depends(require_roles(RoleName.ADMIN))) -> User:
    return current_user


def get_driver_user(current_user: User = Depends(require_roles(RoleName.DRIVER))) -> User:
    return current_user


def get_admin_or_driver(
    current_user: User = Depends(require_roles(RoleName.ADMIN, RoleName.DRIVER))
) -> User:
    return current_user


def get_any_authenticated(current_user: User = Depends(get_current_user)) -> User:
    return current_user
