"""Workspace LLM settings (UI-managed) and a simple test chatbot."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import Principal, get_principal, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.ai_settings import (
    AISettingsOut,
    AISettingsUpdate,
    AITestOut,
    ChatRequest,
    ChatResponse,
)
from app.services.ai_settings import (
    get_workspace_ai_client,
    public_ai_status,
    upsert_workspace_ai_config,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/settings/ai", tags=["ai-settings"])

CHAT_SYSTEM = (
    "You are a helpful assistant built into the Public Records Research app. "
    "You help users verify that their LLM connection works. Keep answers short "
    "and clear. Do not claim to make identity determinations. If asked about "
    "records matching, remind the user that match scores are review guidance only."
)


@router.get("", response_model=AISettingsOut)
def get_ai_settings(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    return public_ai_status(db, principal.workspace_id)


@router.put("", response_model=AISettingsOut)
def update_ai_settings(
    body: AISettingsUpdate,
    principal: Principal = Depends(
        require_roles(UserRole.admin, UserRole.researcher)
    ),
    db: Session = Depends(get_db),
):
    upsert_workspace_ai_config(
        db,
        principal.workspace_id,
        enabled=body.enabled,
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        embedding_model=body.embedding_model,
        clear_api_key=body.clear_api_key,
    )
    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="ai_settings_update",
        detail={
            "enabled": body.enabled,
            "model": body.model,
            "base_url_set": bool(body.base_url),
            "key_updated": bool(body.api_key and body.api_key.strip()) or body.clear_api_key,
        },
    )
    db.commit()
    return public_ai_status(db, principal.workspace_id)


@router.post("/test", response_model=AITestOut)
def test_ai_connection(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    ai = get_workspace_ai_client(db, principal.workspace_id)
    result = ai.ping()
    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="ai_operation",
        detail={"operation": "connectivity_test", "ok": result.get("ok")},
    )
    db.commit()
    return AITestOut(**result)


@router.post("/chat", response_model=ChatResponse)
def chat_with_llm(
    body: ChatRequest,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    ai = get_workspace_ai_client(db, principal.workspace_id)
    if not ai.enabled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "LLM is not configured. Open Settings → AI / LLM and add an API key "
            "(and base URL/model if you use a custom OpenAI-compatible server).",
        )
    history = [
        {"role": m.role, "content": m.content}
        for m in body.history
        if m.role in ("user", "assistant") and m.content.strip()
    ]
    history.append({"role": "user", "content": body.message.strip()})
    try:
        reply = ai.chat(history, system=CHAT_SYSTEM, max_tokens=600, temperature=0.4)
    except Exception as exc:  # pragma: no cover - network path
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"LLM request failed: {str(exc)[:400]}",
        ) from exc

    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="ai_operation",
        detail={"operation": "chat", "chars": len(body.message)},
    )
    db.commit()
    return ChatResponse(reply=reply, model=ai.model, configured=True)
