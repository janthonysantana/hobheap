from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ORMModel(BaseModel):
    class Config:
        from_attributes = True  # pydantic v2 equivalent of orm_mode


class TimestampModel(ORMModel):
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: str
    phone: Optional[str] = None


class UserOut(TimestampModel):
    id: int
    email: str
    phone: Optional[str] = None
    preferred_signin_method: Optional[str] = None


class TagOut(ORMModel):
    id: int
    name: str
    is_ai_generated: bool


class TagCreate(BaseModel):
    name: str
    is_ai_generated: bool = False


class TagAssignIn(BaseModel):
    card_id: int
    tags: list[str]


class TagAssignOut(ORMModel):
    card_id: int
    tags: list[TagOut]


class CardBase(BaseModel):
    title: Optional[str] = None
    content_md: str
    template_type: str = "plain"


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    title: Optional[str] = None
    content_md: Optional[str] = None
    template_type: Optional[str] = None
    is_deleted: Optional[bool] = None


class CardOut(TimestampModel):
    id: int
    owner_id: int
    title: Optional[str]
    content_md: str
    template_type: str


class CardVersionOut(ORMModel):
    id: int
    card_id: int
    version_number: int
    content_md: str
    created_at: datetime


class DocumentBase(BaseModel):
    title: str
    grid_rows: int = 3
    grid_cols: int = 3


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    grid_rows: Optional[int] = None
    grid_cols: Optional[int] = None
    is_deleted: Optional[bool] = None


class DocumentOut(TimestampModel):
    id: int
    owner_id: int
    title: str
    grid_rows: int
    grid_cols: int


class DocumentCardCreate(BaseModel):
    card_id: int
    row: int
    col: int
    span_rows: int = 1
    span_cols: int = 1
    position: int = 0


class DocumentCardOut(TimestampModel):
    id: int
    document_id: int
    card_id: int
    row: int
    col: int
    span_rows: int
    span_cols: int
    position: int


class OTPIssueOut(ORMModel):
    user_id: int
    masked_destination: str
    sent: bool
