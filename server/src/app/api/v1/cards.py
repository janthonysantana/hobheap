from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...models.entities import Card, CardVersion, User
from ...schemas.base import CardCreate, CardOut, CardUpdate
from ...services.auth import get_current_user
from sqlalchemy.orm import joinedload
from ...models.entities import Tag, CardTag

router = APIRouter(prefix="/cards", tags=["cards"])


@router.post("/", response_model=CardOut, status_code=status.HTTP_201_CREATED)
async def create_card(payload: CardCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = Card(owner_id=current_user.id, **payload.model_dump())
    db.add(card)
    await db.flush()
    # initial version
    version = CardVersion(card_id=card.id, version_number=1, content_md=card.content_md)
    db.add(version)
    return card


@router.get("/{card_id}", response_model=CardOut)
async def get_card(card_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = await db.get(Card, card_id)
    if not card or card.owner_id != current_user.id or card.is_deleted:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@router.patch("/{card_id}", response_model=CardOut)
async def update_card(card_id: int, payload: CardUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = await db.get(Card, card_id)
    if not card or card.owner_id != current_user.id or card.is_deleted:
        raise HTTPException(status_code=404, detail="Card not found")
    data = payload.model_dump(exclude_unset=True)
    original_content = card.content_md
    for k, v in data.items():
        setattr(card, k, v)
    if "content_md" in data and data["content_md"] != original_content:
        # new version number
        version_number = len(card.versions) + 1
        db.add(CardVersion(card_id=card.id, version_number=version_number, content_md=card.content_md))
    return card


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(card_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = await db.get(Card, card_id)
    if not card or card.owner_id != current_user.id or card.is_deleted:
        raise HTTPException(status_code=404, detail="Card not found")
    card.is_deleted = True
    return None


@router.get("/", response_model=list[CardOut])
async def list_cards(limit: int = 50, offset: int = 0, template_type: str | None = None, tag: str | None = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Card).where(Card.owner_id == current_user.id, Card.is_deleted == False)  # noqa: E712
    if template_type:
        stmt = stmt.where(Card.template_type == template_type)
    if tag:
        # join through association
        stmt = stmt.join(Card.tags).where(Tag.name == tag)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.scalars(stmt)
    return result.all()
