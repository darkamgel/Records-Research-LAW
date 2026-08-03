"""Seed the database with a demo user, workspace, and synthetic records.

Idempotent: running twice will not duplicate the demo user. Safe to run after
``alembic upgrade head``.

Usage:
    python -m app.seed
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal
from app.entity_resolution.engine import generate_candidates
from app.models.enums import AccessMethod, SourceType, UserRole
from app.models.source import Source
from app.models.user import User, Workspace, WorkspaceMember
from app.services.auth_service import register_user
from app.services.ingestion import run_source_import

logger = get_logger(__name__)

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demopassword123"


def seed() -> None:
    configure_logging()
    db = SessionLocal()
    try:
        existing = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
        if existing:
            logger.info("Demo user already exists; skipping user/import creation.")
            print(f"Demo user already present: {DEMO_EMAIL} / {DEMO_PASSWORD}")
            return

        user, workspace = register_user(
            db,
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            full_name="Demo Researcher",
            workspace_name="Demonstration Workspace",
        )
        # Add a reviewer role membership example is implicit (admin owner already).
        db.flush()

        source = Source(
            workspace_id=workspace.id,
            source_key="demo",
            source_name="Demonstration Public Records (Synthetic)",
            source_type=SourceType.demo,
            jurisdiction="Demo County, DX",
            access_method=AccessMethod.sample_data,
            supported_record_types=[
                "court_filing",
                "probate_notice",
                "public_notice",
                "property_record",
                "organization_filing",
            ],
            terms_notes="Fictional demonstration data generated locally.",
            attribution="Synthetic sample data (this project).",
        )
        db.add(source)
        db.flush()

        job = run_source_import(db, source=source, config=None, limit=50, user_id=user.id)
        logger.info("Imported demo records: created=%s", job.records_created)

        candidates = generate_candidates(db, workspace.id, limit=500)
        db.commit()

        print("Seed complete.")
        print(f"  Login:      {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"  Workspace:  {workspace.name} ({workspace.id})")
        print(f"  Records:    {job.records_created}")
        print(f"  Candidates: {len(candidates)}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
