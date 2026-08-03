from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.types import GUID, EnumType, JSONType
from app.models.enums import AccessMethod, JobStatus, ProcessingStatus, SourceType


class Source(UUIDMixin, TimestampMixin, Base):
    """A registered public-record source adapter instance."""

    __tablename__ = "sources"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    source_key: Mapped[str] = mapped_column(String(100), index=True)  # adapter identifier
    source_name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[SourceType] = mapped_column(EnumType(SourceType))
    jurisdiction: Mapped[str | None] = mapped_column(String(255))
    base_url: Mapped[str | None] = mapped_column(String(1024))
    access_method: Mapped[AccessMethod] = mapped_column(EnumType(AccessMethod))
    supported_record_types: Mapped[list | None] = mapped_column(JSONType)
    terms_notes: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer)
    requires_auth: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    configurations: Mapped[list["SourceConfiguration"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class SourceConfiguration(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "source_configurations"

    source_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    # Non-secret configuration only (endpoint, query params, mapping, etc.).
    config: Mapped[dict | None] = mapped_column(JSONType)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    source: Mapped[Source] = relationship(back_populates="configurations")


class IngestionJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_jobs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("sources.id"))
    uploaded_file_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("uploaded_files.id")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[JobStatus] = mapped_column(
        EnumType(JobStatus), default=JobStatus.pending, index=True
    )
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0..100
    error_message: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[dict | None] = mapped_column(JSONType)


class UploadedFile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "uploaded_files"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    original_filename: Mapped[str] = mapped_column(String(512))
    stored_filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)  # sha256 hex
    size_bytes: Mapped[int] = mapped_column(Integer)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        EnumType(ProcessingStatus), default=ProcessingStatus.pending, index=True
    )
    processing_error: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    # Provenance for imported/authored public records.
    source_name: Mapped[str | None] = mapped_column(String(255))
    original_url: Mapped[str | None] = mapped_column(String(1024))
    jurisdiction: Mapped[str | None] = mapped_column(String(255))
    record_type: Mapped[str | None] = mapped_column(String(100))
