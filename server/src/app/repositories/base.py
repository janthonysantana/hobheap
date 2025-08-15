from __future__ import annotations
from typing import Generic, TypeVar, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar("T")

class Repository(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def get(self, db: AsyncSession, id_: int) -> T | None:
        return await db.get(self.model, id_)

    async def list(self, db: AsyncSession, *, limit: int = 50, offset: int = 0):
        result = await db.scalars(select(self.model).limit(limit).offset(offset))
        return result.all()
