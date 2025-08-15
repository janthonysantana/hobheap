from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...models.entities import Card, Document, DocumentCard, User
from ...schemas.base import (
    DocumentCardCreate,
    DocumentCreate,
    DocumentOut,
    DocumentUpdate,
)

router = APIRouter(prefix="/documents", tags=["documents"])


from ...services.auth import get_current_user


@router.post("/", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = Document(owner_id=current_user.id, **payload.model_dump())
    db.add(doc)
    await db.flush()
    return doc


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = await db.get(Document, document_id)
    if not doc or doc.owner_id != current_user.id or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch("/{document_id}", response_model=DocumentOut)
async def update_document(document_id: int, payload: DocumentUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = await db.get(Document, document_id)
    if not doc or doc.owner_id != current_user.id or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(doc, k, v)
    return doc


@router.post("/{document_id}/cards", status_code=status.HTTP_201_CREATED)
async def add_card_to_document(document_id: int, payload: DocumentCardCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = await db.get(Document, document_id)
    if not doc or doc.owner_id != current_user.id or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    card = await db.get(Card, payload.card_id)
    if not card or card.owner_id != current_user.id or card.is_deleted:
        raise HTTPException(status_code=404, detail="Card not found")
    # ensure not already present (explicit query to avoid async lazy load issues)
    existing = await db.scalar(
        select(DocumentCard).where(
            DocumentCard.document_id == doc.id,
            DocumentCard.card_id == card.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="Card already added")
    doc_card = DocumentCard(document_id=doc.id, card_id=card.id, **payload.model_dump(exclude={"card_id"}))
    db.add(doc_card)
    await db.flush()
    return {"document_card_id": doc_card.id}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_document(document_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = await db.get(Document, document_id)
    if not doc or doc.owner_id != current_user.id or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.is_deleted = True
    return None


@router.get("/", response_model=list[DocumentOut])
async def list_documents(limit: int = 50, offset: int = 0, tag: str | None = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Document).where(Document.owner_id == current_user.id, Document.is_deleted == False)  # noqa: E712
    if tag:
        from ...models.entities import Tag, DocumentCard, Card, CardTag
        stmt = stmt.join(Document.cards).join(DocumentCard.card).join(Card.tags).where(Tag.name == tag)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.scalars(stmt)
    return result.all()
