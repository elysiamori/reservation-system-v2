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

# Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Get Current User ─────────────────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate JWT Bearer token and return the current User.
    Raises 401 if token is missing, invalid, or expired.
    Raises 403 if account is inactive.
    """
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


# ─── Role Guards ──────────────────────────────────────────────────────────────
def require_roles(*roles: RoleName):
    """
    Factory that returns a FastAPI dependency requiring one of the given roles.

    Usage:
        @router.get("/admin-only")
        def admin_route(current_user = Depends(require_roles(RoleName.ADMIN))):
            ...

        @router.get("/approver-or-admin")
        def route(current_user = Depends(require_roles(RoleName.APPROVER, RoleName.ADMIN))):
            ...
    """
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in roles:
            raise ForbiddenException(
                f"This action requires one of these roles: {[r.value for r in roles]}"
            )
        return current_user
    return dependency


# ─── Pre-built role dependencies ─────────────────────────────────────────────
# Use these directly in route decorators for common role combinations

def get_admin_user(current_user: User = Depends(require_roles(RoleName.ADMIN))) -> User:
    return current_user

def get_approver_or_admin(
    current_user: User = Depends(require_roles(RoleName.APPROVER, RoleName.ADMIN))
) -> User:
    return current_user

def get_driver_user(current_user: User = Depends(require_roles(RoleName.DRIVER))) -> User:
    return current_user

def get_any_authenticated(current_user: User = Depends(get_current_user)) -> User:
    """Any authenticated user regardless of role."""
    return current_user
