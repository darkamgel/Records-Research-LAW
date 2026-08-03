from __future__ import annotations

from pydantic import BaseModel, Field


class AISettingsOut(BaseModel):
    enabled: bool
    configured: bool
    source: str  # workspace | environment | none
    has_api_key: bool
    api_key_hint: str | None = None
    base_url: str = ""
    model: str
    embedding_model: str
    ui_enabled: bool = True
    env_fallback_available: bool = False


class AISettingsUpdate(BaseModel):
    enabled: bool = True
    api_key: str | None = Field(
        default=None,
        description="Leave empty to keep the existing key. Send a new value to replace it.",
    )
    clear_api_key: bool = False
    base_url: str | None = None
    model: str | None = None
    embedding_model: str | None = None


class AITestOut(BaseModel):
    ok: bool
    model: str | None = None
    base_url: str | None = None
    reply: str | None = None
    error: str | None = None


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    reply: str
    model: str
    configured: bool
