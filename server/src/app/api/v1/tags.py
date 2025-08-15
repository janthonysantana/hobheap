from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ...core.db import get_db
from ...services.auth import get_current_user
from ...models.entities import Tag, Card, CardVersion
from ...repositories.tags import tag_repository
from ...schemas.base import TagCreate, TagOut, CardVersionOut, TagAssignIn, TagAssignOut
from ...core.db import get_db

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(payload: TagCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    tag = await tag_repository.create(db, name=payload.name, is_ai=payload.is_ai_generated)
    return tag


@router.get("/", response_model=list[TagOut])
async def list_tags(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.scalars(select(Tag).limit(limit).offset(offset))
    return result.all()


@router.get("/cards/{card_id}/versions", response_model=list[CardVersionOut])
async def list_card_versions(card_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    card = await db.get(Card, card_id)
    if not card or card.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    # eager load versions order by version_number
    result = await db.scalars(select(CardVersion).where(CardVersion.card_id == card_id).order_by(CardVersion.version_number))
    return result.all()


@router.post("/assign", response_model=TagAssignOut)
async def assign_tags(payload: TagAssignIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    card = await db.get(Card, payload.card_id)
    if not card or card.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    # fetch existing tag ids via association table query
    existing_tag_ids = set()
    existing_rows = await db.execute(
        select(Tag.id).join_from(Tag, Tag.cards).where(Card.id == card.id)
    )
    for (tid,) in existing_rows.all():
        existing_tag_ids.add(tid)
    new_tags: list[Tag] = []
    for name in payload.tags:
        tag = await tag_repository.create(db, name=name, is_ai=False)
        new_tags.append(tag)
        if tag.id in existing_tag_ids:
            continue
        # insert association manually to avoid triggering lazy load on card.tags
        await db.execute(
            Tag.__table__.metadata.tables['card_tags'].insert().values(card_id=card.id, tag_id=tag.id)
        )
        existing_tag_ids.add(tag.id)
    return TagAssignOut(card_id=card.id, tags=new_tags)
