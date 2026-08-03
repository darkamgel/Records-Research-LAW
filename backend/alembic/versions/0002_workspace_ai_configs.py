"""Add workspace_ai_configs for UI-managed LLM settings.

Revision ID: 0002_workspace_ai_configs
Revises: 0001_initial_schema
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import GUID

revision = "0002_workspace_ai_configs"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_ai_configs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("base_url", sa.String(length=1024), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=False, server_default="gpt-4o-mini"),
        sa.Column(
            "embedding_model",
            sa.String(length=255),
            nullable=False,
            server_default="text-embedding-3-small",
        ),
        sa.Column("api_key_hint", sa.String(length=8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", name="uq_workspace_ai_config"),
    )
    op.create_index("ix_workspace_ai_configs_workspace_id", "workspace_ai_configs", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_ai_configs_workspace_id", table_name="workspace_ai_configs")
    op.drop_table("workspace_ai_configs")
