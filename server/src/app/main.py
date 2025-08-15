from __future__ import annotations

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI

from .core.db import engine
from .api.v1 import users, cards, documents, tags

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: D401
    # Initialize shared resources here (e.g., caches) in future.
    yield


app = FastAPI(title="hobheap API", version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


app.include_router(users.router, prefix="/api/v1")
app.include_router(cards.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(tags.router, prefix="/api/v1")