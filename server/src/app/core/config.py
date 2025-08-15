from __future__ import annotations

import os
from functools import lru_cache
from pydantic import AnyUrl, BaseModel, field_validator


class Settings(BaseModel):
    environment: str = os.getenv("ENVIRONMENT", "local")
    debug: bool = os.getenv("DEBUG", "0") == "1"
    project_name: str = os.getenv("PROJECT_NAME", "hobheap")

    database_url: str = os.getenv(
        "DATABASE_URL",
        # Example fallback for local dev (adjust as needed). Use PostgreSQL long term.
        "sqlite+aiosqlite:///./dev.db",
    )

    access_token_expire_days: int = 30

    otp_length: int = 6

    rate_limit_auth_attempts: int = 3
    rate_limit_auth_window_seconds: int = 300  # 5 minutes lock window

    @field_validator("database_url")
    @classmethod
    def validate_db_scheme(cls, v: str) -> str:
        if v.startswith("sqlite"):
            return v
        # allow postgres / postgresql
        if v.startswith("postgres://"):
            # SQLAlchemy recommends postgresql+psycopg
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        if v.startswith("postgresql"):
            return v
        raise ValueError("Unsupported database scheme")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
