from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.types import GUID, Embedding, EnumType, JSONType
from app.models.enums import ProcessingStatus


class Record(UUIDMixin, TimestampMixin, Base):
    """A normalized public record with full source provenance."""

    __tablename__ = "records"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("sources.id"), index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documents.id"))
    external_record_id: Mapped[str | None] = mapped_column(String(255), index=True)
    record_type: Mapped[str | None] = mapped_column(String(100), index=True)
    title: Mapped[str | None] = mapped_column(String(1024))
    description: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(String(255), index=True)
    filing_date: Mapped[date | None] = mapped_column(Date, index=True)
    event_date: Mapped[date | None] = mapped_column(Date, index=True)
    case_number: Mapped[str | None] = mapped_column(String(255), index=True)
    original_url: Mapped[str | None] = mapped_column(String(1024))
    source_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Normalized primary-person/org fields promoted for indexing + blocking.
    primary_name: Mapped[str | None] = mapped_column(String(512), index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(512), index=True)
    normalized_last_name: Mapped[str | None] = mapped_column(String(255), index=True)
    normalized_address: Mapped[str | None] = mapped_column(String(1024), index=True)
    city: Mapped[str | None] = mapped_column(String(255), index=True)
    state: Mapped[str | None] = mapped_column(String(64), index=True)
    zip_code: Mapped[str | None] = mapped_column(String(16), index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONType)
    normalized_payload: Mapped[dict | None] = mapped_column(JSONType)
    search_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(Embedding(1536))
    is_demo: Mapped[bool] = mapped_column(default=False)


class Document(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    uploaded_file_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("uploaded_files.id")
    )
    title: Mapped[str | None] = mapped_column(String(1024))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    extraction_quality: Mapped[float] = mapped_column(default=0.0)
    ocr_used: Mapped[bool] = mapped_column(default=False)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        EnumType(ProcessingStatus), default=ProcessingStatus.pending
    )
    full_text: Mapped[str | None] = mapped_column(Text)
    doc_metadata: Mapped[dict | None] = mapped_column(JSONType)
    warnings: Mapped[list | None] = mapped_column(JSONType)

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentPage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_pages"

    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    ocr_used: Mapped[bool] = mapped_column(default=False)

    document: Mapped[Document] = relationship(back_populates="pages")


class DocumentChunk(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(Embedding(1536))

    document: Mapped[Document] = relationship(back_populates="chunks")
