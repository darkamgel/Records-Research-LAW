"""Per-workspace LLM configuration (set from the UI for deployment)."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.types import GUID


class WorkspaceAIConfig(Base, UUIDMixin, TimestampMixin):
    """OpenAI-compatible LLM settings scoped to a workspace.

    API keys are stored encrypted at rest. Environment variables remain a fallback
    when no workspace config exists (useful for local/dev).
    """

    __tablename__ = "workspace_ai_configs"
    __table_args__ = (UniqueConstraint("workspace_id", name="uq_workspace_ai_config"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Fernet token (or empty). Never return the raw key from the API.
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    model: Mapped[str] = mapped_column(String(255), default="gpt-4o-mini")
    embedding_model: Mapped[str] = mapped_column(
        String(255), default="text-embedding-3-small"
    )
    # Last 4 chars of the key for UI display only.
    api_key_hint: Mapped[str | None] = mapped_column(String(8), nullable=True)
