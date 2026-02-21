from pydantic import BaseModel
from typing import TypeVar, Generic, Any

T = TypeVar("T")


# ─── Pagination Meta ───────────────────────────────────────────────────────────
class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    totalPages: int
    hasNext: bool
    hasPrev: bool


# ─── Error Detail (per field) ──────────────────────────────────────────────────
class ErrorDetail(BaseModel):
    field: str
    message: str


# ─── Error Body ───────────────────────────────────────────────────────────────
class ErrorBody(BaseModel):
    code: str
    details: list[ErrorDetail] | None = None
    field: str | None = None


# ─── Standard Success Response ────────────────────────────────────────────────
class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T | None = None


# ─── Paginated Success Response ───────────────────────────────────────────────
class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: list[T]
    meta: PaginationMeta


# ─── Error Response ───────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error: ErrorBody


# ─── Helper Functions ─────────────────────────────────────────────────────────
def success_response(message: str, data: Any = None) -> dict:
    """Return a standardized success dict (used in route handlers)."""
    return {"success": True, "message": message, "data": data}


def paginated_response(
    message: str,
    data: list,
    total: int,
    page: int,
    limit: int,
) -> dict:
    """Return a standardized paginated dict."""
    total_pages = (total + limit - 1) // limit if limit > 0 else 0
    return {
        "success": True,
        "message": message,
        "data": data,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": total_pages,
            "hasNext": page < total_pages,
            "hasPrev": page > 1,
        }
    }


# ─── Common Query Params ──────────────────────────────────────────────────────
class PaginationParams(BaseModel):
    page: int = 1
    limit: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit

    def clamp(self, max_limit: int = 100) -> "PaginationParams":
        """Ensure limit doesn't exceed max."""
        self.limit = min(self.limit, max_limit)
        self.page  = max(self.page, 1)
        return self
