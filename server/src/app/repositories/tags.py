from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base import Repository
from ..models.entities import Tag

class TagRepository(Repository[Tag]):
    def __init__(self):
        super().__init__(Tag)

    async def get_by_name(self, db: AsyncSession, name: str) -> Tag | None:
        return await db.scalar(select(Tag).where(Tag.name == name))

    async def create(self, db: AsyncSession, name: str, is_ai: bool = False) -> Tag:
        existing = await self.get_by_name(db, name)
        if existing:
            return existing
        tag = Tag(name=name, is_ai_generated=is_ai)
        db.add(tag)
        await db.flush()
        return tag


tag_repository = TagRepository()
