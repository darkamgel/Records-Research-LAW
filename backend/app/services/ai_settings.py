"""Resolve and persist per-workspace LLM settings."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import AIClient, AIConfig, get_ai_client
from app.core.config import settings
from app.core.secrets import decrypt_secret, encrypt_secret
from app.models.ai_settings import WorkspaceAIConfig


def get_workspace_ai_row(db: Session, workspace_id: uuid.UUID) -> WorkspaceAIConfig | None:
    return db.execute(
        select(WorkspaceAIConfig).where(WorkspaceAIConfig.workspace_id == workspace_id)
    ).scalar_one_or_none()


def resolve_ai_config(db: Session, workspace_id: uuid.UUID) -> AIConfig:
    """Workspace UI config wins; otherwise fall back to environment variables."""
    row = get_workspace_ai_row(db, workspace_id)
    if row is None or not row.enabled:
        return AIConfig.from_env()
    key = decrypt_secret(row.api_key_encrypted)
    if not key:
        # Enabled row but no key → still allow env fallback.
        env = AIConfig.from_env()
        if env.enabled:
            return AIConfig(
                api_key=env.api_key,
                base_url=row.base_url or env.base_url,
                model=row.model or env.model,
                embedding_model=row.embedding_model or env.embedding_model,
            )
        return AIConfig(
            api_key="",
            base_url=row.base_url or "",
            model=row.model,
            embedding_model=row.embedding_model,
        )
    return AIConfig(
        api_key=key,
        base_url=(row.base_url or "").strip(),
        model=row.model or settings.openai_model,
        embedding_model=row.embedding_model or settings.openai_embedding_model,
    )


def get_workspace_ai_client(db: Session, workspace_id: uuid.UUID) -> AIClient:
    return get_ai_client(resolve_ai_config(db, workspace_id))


def upsert_workspace_ai_config(
    db: Session,
    workspace_id: uuid.UUID,
    *,
    enabled: bool,
    api_key: str | None,
    base_url: str | None,
    model: str | None,
    embedding_model: str | None,
    clear_api_key: bool = False,
) -> WorkspaceAIConfig:
    row = get_workspace_ai_row(db, workspace_id)
    if row is None:
        row = WorkspaceAIConfig(workspace_id=workspace_id)
        db.add(row)

    row.enabled = enabled
    if clear_api_key:
        row.api_key_encrypted = None
        row.api_key_hint = None
    elif api_key is not None and api_key.strip():
        key = api_key.strip()
        row.api_key_encrypted = encrypt_secret(key)
        row.api_key_hint = key[-4:] if len(key) >= 4 else key
    if base_url is not None:
        row.base_url = base_url.strip() or None
    if model is not None and model.strip():
        row.model = model.strip()
    if embedding_model is not None and embedding_model.strip():
        row.embedding_model = embedding_model.strip()

    db.flush()
    return row


def public_ai_status(db: Session, workspace_id: uuid.UUID) -> dict:
    """Safe payload for the UI (never includes the raw API key)."""
    row = get_workspace_ai_row(db, workspace_id)
    cfg = resolve_ai_config(db, workspace_id)
    source = "workspace" if row and row.api_key_encrypted else ("environment" if AIConfig.from_env().enabled else "none")
    if row and not row.api_key_encrypted and AIConfig.from_env().enabled:
        source = "environment"
    if row and row.api_key_encrypted:
        source = "workspace"
    return {
        "enabled": cfg.enabled,
        "configured": cfg.enabled,
        "source": source,
        "has_api_key": bool(cfg.api_key),
        "api_key_hint": (row.api_key_hint if row else None),
        "base_url": (row.base_url if row else settings.openai_base_url) or "",
        "model": cfg.model,
        "embedding_model": cfg.embedding_model,
        "ui_enabled": bool(row.enabled) if row else True,
        "env_fallback_available": AIConfig.from_env().enabled,
    }
