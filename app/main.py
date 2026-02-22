import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import check_db_connection
from app.utils.exceptions import AppException
from app.middleware.error_handler import (
    app_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    generic_exception_handler,
)

from app.api.v1 import auth
from app.api.v1 import users
from app.api.v1 import vehicles
from app.api.v1 import rooms
from app.api.v1 import bookings
from app.api.v1 import drivers
from app.api.v1 import fuel_expenses
from app.api.v1 import maintenance
from app.api.v1 import reports
from app.api.v1 import guest_bookings
from app.api.v1 import attachments

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Vehicle & Room Resource Booking System API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ─── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React dev server
            "http://localhost:8000",  # Local API
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "https://abstemiously-gymnocarpous-hans.ngrok-free.dev",  # Domain ngrok Anda
            "*"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Exception Handlers ───────────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # ─── Routers ──────────────────────────────────────────────────────────────
    PREFIX = "/api/v1"
    app.include_router(auth.router,          prefix=PREFIX, tags=["Auth"])
    app.include_router(users.router,         prefix=PREFIX, tags=["Users"])
    app.include_router(vehicles.router,      prefix=PREFIX, tags=["Vehicles"])
    app.include_router(rooms.router,         prefix=PREFIX, tags=["Rooms"])
    app.include_router(bookings.router,      prefix=PREFIX, tags=["Bookings"])
    app.include_router(drivers.router,       prefix=PREFIX, tags=["Drivers"])
    app.include_router(fuel_expenses.router, prefix=PREFIX, tags=["Fuel Expenses"])
    app.include_router(maintenance.router,   prefix=PREFIX, tags=["Maintenance"])
    app.include_router(guest_bookings.router, prefix=PREFIX, tags=["Guest Bookings"])
    app.include_router(attachments.router,   prefix=PREFIX, tags=["Attachments"])
    app.include_router(reports.router,       prefix=PREFIX, tags=["Reports"])

    # ─── Startup ──────────────────────────────────────────────────────────────
    @app.on_event("startup")
    def on_startup():
        ok = check_db_connection()
        logger.info("✅ DB connected" if ok else "❌ DB connection FAILED")

    # ─── Health ───────────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    def health():
        return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT,
                reload=settings.is_development)
