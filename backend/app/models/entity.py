from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.types import GUID, JSONType


class Entity(UUIDMixin, TimestampMixin, Base):
    """A canonical extracted entity value (person, org, place, identifier...)."""

    __tablename__ = "entities"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    value: Mapped[str] = mapped_column(String(1024))
    normalized_value: Mapped[str | None] = mapped_column(String(1024), index=True)


class EntityMention(UUIDMixin, TimestampMixin, Base):
    """A specific occurrence of an entity in a record/document with provenance."""

    __tablename__ = "entity_mentions"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    record_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("records.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documents.id"))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("entities.id"))
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    value: Mapped[str] = mapped_column(String(1024))
    normalized_value: Mapped[str | None] = mapped_column(String(1024))
    extraction_method: Mapped[str] = mapped_column(String(50))  # regex|spacy|address|llm
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    page_number: Mapped[int | None] = mapped_column(Integer)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    source_text: Mapped[str | None] = mapped_column(Text)


class Person(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "people"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    record_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("records.id"))
    original_name: Mapped[str] = mapped_column(String(512))
    normalized_name: Mapped[str | None] = mapped_column(String(512), index=True)
    first_name: Mapped[str | None] = mapped_column(String(255))
    middle_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255), index=True)
    prefix: Mapped[str | None] = mapped_column(String(32))
    suffix: Mapped[str | None] = mapped_column(String(32))


class Organization(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    record_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("records.id"))
    original_name: Mapped[str] = mapped_column(String(512))
    normalized_name: Mapped[str | None] = mapped_column(String(512), index=True)


class Address(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "addresses"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    record_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("records.id"))
    original_address: Mapped[str] = mapped_column(String(1024))
    normalized_address: Mapped[str | None] = mapped_column(String(1024), index=True)
    street: Mapped[str | None] = mapped_column(String(512))
    unit: Mapped[str | None] = mapped_column(String(64))
    city: Mapped[str | None] = mapped_column(String(255), index=True)
    state: Mapped[str | None] = mapped_column(String(64), index=True)
    zip_code: Mapped[str | None] = mapped_column(String(16), index=True)
    components: Mapped[dict | None] = mapped_column(JSONType)
