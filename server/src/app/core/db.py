from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


# Create async engine. For sqlite aiosqlite driver already in url; for postgres ensure +asyncpg or psycopg async not in default
if settings.database_url.startswith("sqlite"):  # aiosqlite already appended
    engine = create_async_engine(settings.database_url, echo=settings.debug)
else:
    # Ensure async driver for postgres
    if "+psycopg" in settings.database_url:
        # psycopg supports both sync/async when using 'postgresql+psycopg'
        engine = create_async_engine(settings.database_url, echo=settings.debug)
    else:
        # fallback: user supplied maybe postgresql://; add +psycopg
        engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+psycopg://"), echo=settings.debug)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:  # type: ignore[arg-type]
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
