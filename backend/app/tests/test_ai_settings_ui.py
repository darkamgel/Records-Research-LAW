"""Workspace AI settings from the UI + chat gatekeeping."""

from __future__ import annotations


def test_ai_settings_get_and_update(client, auth):
    r = client.get("/settings/ai", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "configured" in body
    assert "model" in body
    # No raw key ever returned
    assert "api_key" not in body
    assert "api_key_encrypted" not in body

    r2 = client.put(
        "/settings/ai",
        headers=auth,
        json={
            "enabled": True,
            "api_key": "sk-test-key-for-ui-1234",
            "base_url": "https://example.invalid/v1",
            "model": "test-model",
            "embedding_model": "test-embed",
        },
    )
    assert r2.status_code == 200, r2.text
    out = r2.json()
    assert out["has_api_key"] is True
    assert out["api_key_hint"] == "1234"
    assert out["model"] == "test-model"
    assert out["base_url"] == "https://example.invalid/v1"
    assert out["source"] == "workspace"


def test_chat_requires_configuration(client, auth, monkeypatch):
    # Ensure no env key and no workspace key.
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from app.core.config import get_settings
    from app.ai import client as ai_mod

    get_settings.cache_clear()
    ai_mod._ai_client = None

    # Clear any workspace key by creating a fresh user workspace via register fixture already used.
    # Put empty config.
    client.put(
        "/settings/ai",
        headers=auth,
        json={"enabled": True, "clear_api_key": True, "model": "x"},
    )
    # Force env empty for resolve
    monkeypatch.setattr(
        "app.services.ai_settings.AIConfig.from_env",
        lambda: __import__("app.ai.client", fromlist=["AIConfig"]).AIConfig(),
    )

    r = client.post(
        "/settings/ai/chat",
        headers=auth,
        json={"message": "hello", "history": []},
    )
    assert r.status_code == 400
    assert "not configured" in r.json()["detail"].lower()
