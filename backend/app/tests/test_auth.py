from __future__ import annotations


def test_register_login_me(client):
    r = client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "password123", "workspace_name": "W"},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]

    # duplicate registration is rejected
    dup = client.post("/auth/register", json={"email": "a@b.com", "password": "password123"})
    assert dup.status_code == 409

    login = client.post("/auth/login", json={"email": "a@b.com", "password": "password123"})
    assert login.status_code == 200

    bad = client.post("/auth/login", json={"email": "a@b.com", "password": "wrongpass"})
    assert bad.status_code == 401

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "a@b.com"
    assert len(me.json()["workspaces"]) == 1


def test_protected_route_requires_auth(client):
    assert client.get("/dashboard/metrics").status_code == 401
    assert client.post("/records/search", json={}).status_code == 401


def test_short_password_rejected(client):
    r = client.post("/auth/register", json={"email": "x@y.com", "password": "short"})
    assert r.status_code == 422
