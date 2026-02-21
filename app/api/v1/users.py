from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_admin_user
from app.models.user import User
from app.schemas.user import UserCreateRequest, UserUpdateRequest
from app.schemas.common import success_response, paginated_response
from app.services.user_service import user_service

router = APIRouter(prefix="/users")


# GET /users — Admin only
@router.get("", status_code=status.HTTP_200_OK, summary="List all users (paginated)")
def list_users(
    page:         int            = Query(1,    ge=1),
    limit:        int            = Query(20,   ge=1, le=100),
    search:       Optional[str]  = Query(None, description="Search by name, email, or employeeId"),
    roleId:       Optional[int]  = Query(None),
    departmentId: Optional[int]  = Query(None),
    isActive:     Optional[bool] = Query(None),
    db:           Session        = Depends(get_db),
    _:            User           = Depends(get_admin_user),
):
    data, total = user_service.list_users(db, page, limit, search, roleId, departmentId, isActive)
    return paginated_response("Users retrieved successfully", data, total, page, limit)


# GET /users/me — Any authenticated user
@router.get("/me", status_code=status.HTTP_200_OK, summary="Get current user profile")
def get_me(current_user: User = Depends(get_current_user)):
    return success_response("Profile retrieved", {
        "id":           current_user.id,
        "employeeId":   current_user.employeeId,
        "name":         current_user.name,
        "email":        current_user.email,
        "isActive":     current_user.isActive,
        "role":         {"id": current_user.role.id, "name": current_user.role.name.value},
        "department":   {"id": current_user.department.id, "name": current_user.department.name},
        "createdAt":    current_user.createdAt.isoformat(),
        "updatedAt":    current_user.updatedAt.isoformat(),
    })


# GET /users/departments — Any authenticated user (for dropdowns)
@router.get("/departments", status_code=status.HTTP_200_OK, summary="List all departments")
def list_departments(
    db: Session = Depends(get_db),
    _:  User    = Depends(get_current_user),
):
    data = user_service.list_departments(db)
    return success_response("Departments retrieved", data)


# GET /users/roles — Any authenticated user (for dropdowns)
@router.get("/roles", status_code=status.HTTP_200_OK, summary="List all roles")
def list_roles(
    db: Session = Depends(get_db),
    _:  User    = Depends(get_current_user),
):
    data = user_service.list_roles(db)
    return success_response("Roles retrieved", data)


# GET /users/{id} — Admin only
@router.get("/{user_id}", status_code=status.HTTP_200_OK, summary="Get user by ID")
def get_user(
    user_id: int,
    db:      Session = Depends(get_db),
    _:       User    = Depends(get_admin_user),
):
    data = user_service.get_user(db, user_id)
    return success_response("User retrieved", data)


# POST /users — Admin only
@router.post("", status_code=status.HTTP_201_CREATED, summary="Create new user")
def create_user(
    body: UserCreateRequest,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = user_service.create_user(db, body, current_user.id)
    return success_response("User created successfully", data)


# PUT /users/{id} — Admin only
@router.put("/{user_id}", status_code=status.HTTP_200_OK, summary="Update user")
def update_user(
    user_id: int,
    body:    UserUpdateRequest,
    db:      Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = user_service.update_user(db, user_id, body, current_user.id)
    return success_response("User updated successfully", data)


# PATCH /users/{id}/toggle-active — Admin only
@router.patch("/{user_id}/toggle-active", status_code=status.HTTP_200_OK,
              summary="Activate or deactivate a user")
def toggle_active(
    user_id: int,
    db:      Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    data = user_service.toggle_active(db, user_id, current_user.id)
    status_str = "activated" if data["isActive"] else "deactivated"
    return success_response(f"User {status_str} successfully", data)


# DELETE /users/{id} — Admin only
@router.delete("/{user_id}", status_code=status.HTTP_200_OK, summary="Delete user")
def delete_user(
    user_id: int,
    db:      Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    user_service.delete_user(db, user_id, current_user.id)
    return success_response("User deleted successfully", None)
