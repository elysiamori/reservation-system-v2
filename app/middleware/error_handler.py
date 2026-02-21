import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from app.utils.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all AppException subclasses (our custom exceptions)."""
    detail = exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": detail.get("message", "An error occurred"),
            "error": detail.get("error", {"code": ErrorCode.    INTERNAL_SERVER_ERROR}),
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors (422).
    Converts FastAPI's default validation error format into our standardized format.
    """
    details = []
    for error in exc.errors():
        # Get field name — loc is a tuple like ("body", "email")
        loc = error.get("loc", [])
        field = ".".join(str(l) for l in loc if l != "body") if loc else "unknown"
        details.append({
            "field": field,
            "message": error.get("msg", "Invalid value"),
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error. Please check your input.",
            "error": {
                "code": ErrorCode.VALIDATION_ERROR,
                "details": details,
                "field": None,
            }
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """
    Handle SQLAlchemy IntegrityError (unique constraint violations, FK violations).
    Prevents raw DB errors from leaking to the client.
    """
    logger.warning(f"IntegrityError on {request.method} {request.url}: {exc.orig}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "message": "A record with this data already exists.",
            "error": {
                "code": ErrorCode.DUPLICATE_ENTRY,
                "details": None,
                "field": None,
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.
    Logs the full traceback, returns a safe 500 response.
    """
    logger.error(
        f"Unhandled exception on {request.method} {request.url}\n"
        f"{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred. Please try again later.",
            "error": {
                "code": ErrorCode.INTERNAL_SERVER_ERROR,
                "details": None,
                "field": None,
            }
        }
    )
