from __future__ import annotations

import datetime as dt
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base

# Naming conventions help with migrations later
metadata_obj = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), unique=True)
    # For passwordless OTP we may store a hashed last used code or ephemeral secrets in separate table later
    preferred_signin_method: Mapped[Optional[str]] = mapped_column(String(32))  # 'email'|'phone'

    cards: Mapped[List["Card"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Card(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    # plain, flashcard, checklist, template ids etc.
    template_type: Mapped[str] = mapped_column(String(50), default="plain", index=True)

    owner: Mapped[User] = relationship(back_populates="cards")
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary="card_tags", back_populates="cards")
    versions: Mapped[List["CardVersion"]] = relationship(back_populates="card", cascade="all, delete-orphan")


class CardVersion(Base, TimestampMixin):
    __tablename__ = "card_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)

    card: Mapped[Card] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("card_id", "version_number", name="uq_card_version"),
    )


class Document(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    grid_rows: Mapped[int] = mapped_column(Integer, default=3)
    grid_cols: Mapped[int] = mapped_column(Integer, default=3)

    owner: Mapped[User] = relationship(back_populates="documents")
    cards: Mapped[List["DocumentCard"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentCard.position"
    )


class DocumentCard(Base, TimestampMixin):
    __tablename__ = "document_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)

    # top-left anchor cell position (row-major) or store row/col separate
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    col: Mapped[int] = mapped_column(Integer, nullable=False)
    span_rows: Mapped[int] = mapped_column(Integer, default=1)
    span_cols: Mapped[int] = mapped_column(Integer, default=1)
    position: Mapped[int] = mapped_column(Integer, default=0)  # ordering in layering if needed

    document: Mapped[Document] = relationship(back_populates="cards")
    card: Mapped[Card] = relationship()

    __table_args__ = (
        UniqueConstraint("document_id", "card_id", name="uq_doc_card_unique"),
        CheckConstraint("row >= 0 AND col >= 0", name="ck_doc_card_non_negative"),
    )


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    cards: Mapped[List[Card]] = relationship("Card", secondary="card_tags", back_populates="tags")


class CardTag(Base):
    __tablename__ = "card_tags"

    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    # track explicit user vs implicit AI link (?) could store boolean; for simplicity rely on Tag.is_ai_generated


class OTP(Base, TimestampMixin):
    __tablename__ = "otps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    user: Mapped[User] = relationship()
