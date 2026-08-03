"""FastAPI dependencies: auth, current user, active workspace, role guards."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth_service import membership_role, user_workspaces

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user: User
    workspace_id: uuid.UUID
    role: UserRole


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_access_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    try:
        user = db.get(User, uuid.UUID(payload["sub"]))
    except (ValueError, TypeError):
        user = None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def get_principal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
) -> Principal:
    workspaces = user_workspaces(db, user)
    if not workspaces:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No workspace membership")

    if x_workspace_id:
        try:
            wsid = uuid.UUID(x_workspace_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid workspace id") from exc
        if wsid not in {w.id for w in workspaces}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this workspace")
    else:
        wsid = workspaces[0].id

    role = membership_role(db, user.id, wsid) or UserRole.researcher
    return Principal(user=user, workspace_id=wsid, role=role)


def require_roles(*roles: UserRole) -> Callable[[Principal], Principal]:
    allowed = set(roles)

    def _guard(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed and principal.user.role != UserRole.admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return principal

    return _guard
