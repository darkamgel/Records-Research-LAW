from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User, Workspace, WorkspaceMember


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "workspace"
    return f"{base}-{uuid.uuid4().hex[:6]}"


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()


def register_user(
    db: Session, *, email: str, password: str, full_name: str | None, workspace_name: str | None
) -> tuple[User, Workspace]:
    existing = get_user_by_email(db, email)
    if existing:
        raise ValueError("Email already registered")

    user = User(
        email=email.lower(),
        full_name=full_name,
        hashed_password=hash_password(password),
        role=UserRole.researcher,
    )
    db.add(user)
    db.flush()

    workspace = Workspace(
        name=workspace_name or f"{(full_name or email.split('@')[0])}'s Workspace",
        slug=_slugify(workspace_name or email.split("@")[0]),
        owner_id=user.id,
    )
    db.add(workspace)
    db.flush()

    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=UserRole.admin))
    db.flush()
    return user, workspace


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def user_workspaces(db: Session, user: User) -> list[Workspace]:
    rows = db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    ).scalars()
    return list(rows)


def membership_role(db: Session, user_id: uuid.UUID, workspace_id: uuid.UUID) -> UserRole | None:
    m = db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    ).scalar_one_or_none()
    return m.role if m else None
