from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_principal
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    CurrentUserOut,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    WorkspaceOut,
)
from app.services import auth_service
from app.services.audit import log_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    try:
        user, workspace = auth_service.register_user(
            db,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            workspace_name=body.workspace_name,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_audit(
        db,
        workspace_id=workspace.id,
        user_id=user.id,
        action="register",
        target_type="user",
        target_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, body.email, body.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    workspaces = auth_service.user_workspaces(db, user)
    log_audit(
        db,
        workspace_id=workspaces[0].id if workspaces else None,
        user_id=user.id,
        action="login",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/logout")
def logout(principal=Depends(get_principal), db: Session = Depends(get_db)):
    # Stateless JWT: logout is a client-side token discard. We record the event.
    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="logout",
    )
    db.commit()
    return {"detail": "Logged out. Discard the access token client-side."}


@router.get("/me", response_model=CurrentUserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspaces = auth_service.user_workspaces(db, user)
    return CurrentUserOut(
        user=UserOut.model_validate(user),
        workspaces=[WorkspaceOut.model_validate(w) for w in workspaces],
        active_workspace_id=workspaces[0].id if workspaces else None,
    )
