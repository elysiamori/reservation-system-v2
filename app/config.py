from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ─── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "Resource Booking System"
    APP_ENV:  str = "development"
    APP_DEBUG: bool = True
    APP_HOST:  str = "0.0.0.0"
    APP_PORT:  int = 8000

    # ─── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL:          str
    DATABASE_POOL_SIZE:    int  = 10
    DATABASE_MAX_OVERFLOW: int  = 20
    DATABASE_POOL_TIMEOUT: int  = 30
    DATABASE_ECHO:         bool = False

    # ─── JWT ───────────────────────────────────────────────────────────────────
    SECRET_KEY:                    str
    ALGORITHM:                     str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES:   int = 15
    REFRESH_TOKEN_EXPIRE_DAYS:     int = 7

    # ─── OTP ───────────────────────────────────────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 10
    OTP_LENGTH:         int = 6

    # ─── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:8000,http://localhost:5501,https://reservation-system-kce.netlify.app"

    def get_cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    model_config = {"env_file": ".env.example", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
