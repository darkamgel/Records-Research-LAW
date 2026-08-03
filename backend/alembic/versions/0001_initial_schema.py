"""Initial schema.

Creates the full normalized schema from the SQLAlchemy metadata (portable across
PostgreSQL and SQLite) and, on PostgreSQL only, enables the ``pg_trgm`` and
``vector`` extensions plus full-text / trigram / vector indexes used by search
and matching.

Building the schema from ``Base.metadata`` keeps a single source of truth for
the ~26 tables in this MVP while still running as a normal Alembic revision.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-03
"""

from __future__ import annotations

from alembic import op

from app.db.base import Base
from app.models import *  # noqa: F401,F403  (register tables on metadata)

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Trigram indexes for fuzzy name/address search.
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_records_norm_name_trgm "
            "ON records USING gin (normalized_name gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_records_norm_addr_trgm "
            "ON records USING gin (normalized_address gin_trgm_ops)"
        )
        # Full-text search index over the aggregated search_text column.
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_records_search_fts "
            "ON records USING gin (to_tsvector('english', coalesce(search_text, '')))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_records_search_fts")
        op.execute("DROP INDEX IF EXISTS ix_records_norm_addr_trgm")
        op.execute("DROP INDEX IF EXISTS ix_records_norm_name_trgm")
    Base.metadata.drop_all(bind=bind)
