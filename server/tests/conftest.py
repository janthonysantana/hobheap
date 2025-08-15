import sys
from pathlib import Path
import pytest_asyncio

# ensure src directory is on path BEFORE importing app modules
root = Path(__file__).resolve().parents[1]
src_path = root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from app.core.db import Base, engine  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db_session():
    # Create all tables once for the test session.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def anyio_backend():  # Force asyncio backend for anyio tests
    return "asyncio"
