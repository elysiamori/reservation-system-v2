from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.schemas.user import UserCreateRequest, UserUpdateRequest
from app.utils.security import hash_password
from app.utils.audit import log_action
from app.utils.exceptions import (
    NotFoundException, DuplicateEntryException, ForbiddenException
)


def _serialize_user(u: User) -> dict:
    return {
        "id":           u.id,
        "employeeId":   u.employeeId,
        "name":         u.name,
        "email":        u.email,
        "isActive":     u.isActive,
        "role":         {"id": u.role.id, "name": u.role.name.value},
        "department":   {"id": u.department.id, "name": u.department.name},
        "createdAt":    u.createdAt.isoformat(),
        "updatedAt":    u.updatedAt.isoformat(),
    }


class UserService:

    # ─── List ─────────────────────────────────────────────────────────────────
    def list_users(
        self, db: Session,
        page: int, limit: int,
        search: str | None,
        role_id: int | None,
        department_id: int | None,
        is_active: bool | None,
    ) -> tuple[list[dict], int]:
        q = db.query(User)

        if search:
            kw = f"%{search}%"
            q = q.filter(or_(
                User.name.ilike(kw),
                User.email.ilike(kw),
                User.employeeId.ilike(kw),
            ))
        if role_id is not None:
            q = q.filter(User.roleId == role_id)
        if department_id is not None:
            q = q.filter(User.departmentId == department_id)
        if is_active is not None:
            q = q.filter(User.isActive == is_active)

        total = q.count()
        users = q.order_by(User.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()
        return [_serialize_user(u) for u in users], total

    # ─── Get by ID ────────────────────────────────────────────────────────────
    def get_user(self, db: Session, user_id: int) -> dict:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise NotFoundException("User")
        return _serialize_user(u)

    # ─── Create ───────────────────────────────────────────────────────────────
    def create_user(self, db: Session, data: UserCreateRequest, actor_id: int) -> dict:
        if db.query(User).filter(User.email == data.email).first():
            raise DuplicateEntryException("Email already registered", field="email")
        if db.query(User).filter(User.employeeId == data.employeeId).first():
            raise DuplicateEntryException("Employee ID already exists", field="employeeId")
        if not db.query(Role).filter(Role.id == data.roleId).first():
            raise NotFoundException("Role")
        if not db.query(Department).filter(Department.id == data.departmentId).first():
            raise NotFoundException("Department")

        u = User(
            employeeId=data.employeeId,
            name=data.name,
            email=data.email,
            password=hash_password(data.password),
            isActive=True,
            roleId=data.roleId,
            departmentId=data.departmentId,
        )
        db.add(u)
        db.flush()
        log_action(db, actor_id, "CREATE", "User", u.id,
                   f"Admin created user {u.name} ({u.email})")
        db.commit()
        db.refresh(u)
        return _serialize_user(u)

    # ─── Update ───────────────────────────────────────────────────────────────
    def update_user(self, db: Session, user_id: int, data: UserUpdateRequest, actor_id: int) -> dict:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise NotFoundException("User")

        if data.email and data.email != u.email:
            if db.query(User).filter(User.email == data.email, User.id != user_id).first():
                raise DuplicateEntryException("Email already used by another user", field="email")
        if data.roleId and not db.query(Role).filter(Role.id == data.roleId).first():
            raise NotFoundException("Role")
        if data.departmentId and not db.query(Department).filter(Department.id == data.departmentId).first():
            raise NotFoundException("Department")

        if data.name:         u.name         = data.name
        if data.email:        u.email        = data.email
        if data.roleId:       u.roleId       = data.roleId
        if data.departmentId: u.departmentId = data.departmentId

        log_action(db, actor_id, "UPDATE", "User", u.id, f"Admin updated user {u.name}")
        db.commit()
        db.refresh(u)
        return _serialize_user(u)

    # ─── Toggle Active ────────────────────────────────────────────────────────
    def toggle_active(self, db: Session, user_id: int, actor_id: int) -> dict:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise NotFoundException("User")
        if u.id == actor_id:
            raise ForbiddenException("You cannot deactivate your own account")

        u.isActive = not u.isActive
        action = "ACTIVATE" if u.isActive else "DEACTIVATE"
        log_action(db, actor_id, action, "User", u.id,
                   f"Admin {action.lower()}d user {u.name}")
        db.commit()
        db.refresh(u)
        return _serialize_user(u)

    # ─── Delete ───────────────────────────────────────────────────────────────
    def delete_user(self, db: Session, user_id: int, actor_id: int) -> None:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise NotFoundException("User")
        if u.id == actor_id:
            raise ForbiddenException("You cannot delete your own account")

        log_action(db, actor_id, "DELETE", "User", u.id,
                   f"Admin deleted user {u.name} ({u.email})")
        db.delete(u)
        db.commit()

    # ─── List Departments ─────────────────────────────────────────────────────
    def list_departments(self, db: Session) -> list[dict]:
        deps = db.query(Department).order_by(Department.name).all()
        return [{"id": d.id, "name": d.name} for d in deps]

    # ─── List Roles ───────────────────────────────────────────────────────────
    def list_roles(self, db: Session) -> list[dict]:
        roles = db.query(Role).all()
        return [{"id": r.id, "name": r.name.value} for r in roles]


user_service = UserService()
