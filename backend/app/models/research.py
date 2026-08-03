from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.types import GUID, JSONType


class ResearchProject(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "research_projects"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    objective: Mapped[str | None] = mapped_column(Text)

    records: Mapped[list["ProjectRecord"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_records"
    __table_args__ = (UniqueConstraint("project_id", "record_id", name="uq_project_record"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("research_projects.id", ondelete="CASCADE"), index=True
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("records.id", ondelete="CASCADE"), index=True
    )

    project: Mapped[ResearchProject] = relationship(back_populates="records")


class SavedSearch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "saved_searches"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    query: Mapped[dict] = mapped_column(JSONType)
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_result_count: Mapped[int | None] = mapped_column()
    last_result_ids: Mapped[list | None] = mapped_column(JSONType)


class ResearchHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "research_history"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64))
    query: Mapped[dict | None] = mapped_column(JSONType)
    result_count: Mapped[int | None] = mapped_column()


class Note(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notes"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    record_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("records.id"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("research_projects.id"))
    body: Mapped[str] = mapped_column(Text)


class GeneratedReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "generated_reports"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("research_projects.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(512))
    summary_markdown: Mapped[str | None] = mapped_column(Text)
    content: Mapped[dict | None] = mapped_column(JSONType)
    ai_generated: Mapped[bool] = mapped_column(default=False)
