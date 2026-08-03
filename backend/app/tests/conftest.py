"""Pytest fixtures.

A fresh SQLite database and upload directory are created per test. The suite runs
entirely without a live OpenAI key (deterministic mode); tests that exercise the
AI path monkeypatch the AI client with canned, schema-valid responses.
"""

from __future__ import annotations

import os
import tempfile

# Configure environment BEFORE importing the app so settings pick it up.
_TMP = tempfile.mkdtemp(prefix="prr_test_")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TMP}/test.db"
os.environ["UPLOAD_DIR"] = f"{_TMP}/uploads"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["OPENAI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401  (register tables)
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(fastapi_app) as c:
        yield c


def _register(client: TestClient, email: str, password: str = "password123", ws: str = "WS"):
    r = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Test", "workspace_name": ws},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


@pytest.fixture
def token(client):
    return _register(client, "user1@example.com", ws="Workspace One")


@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def register():
    return _register


def import_demo(client: TestClient, auth: dict) -> str:
    src = client.post(
        "/sources",
        headers=auth,
        json={
            "source_key": "demo",
            "source_name": "Demo",
            "source_type": "demo",
            "access_method": "sample_data",
        },
    )
    sid = src.json()["id"]
    client.post(f"/sources/{sid}/import", headers=auth, json={"limit": 50})
    return sid
