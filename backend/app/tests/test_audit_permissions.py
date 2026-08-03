from __future__ import annotations

from app.tests.conftest import import_demo


def test_audit_log_records_key_actions(client, auth):
    import_demo(client, auth)
    client.post("/records/search", headers=auth, json={"q": "Rivera"})
    audit = client.get("/audit", headers=auth).json()
    actions = {e["action"] for e in audit["items"]}
    assert "register" in actions
    assert "import_records" in actions
    assert "search" in actions


def test_audit_is_workspace_scoped(client, register):
    token_a = register(client, "a@ex.com", ws="A")
    token_b = register(client, "b@ex.com", ws="B")
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}
    import_demo(client, auth_a)
    a_audit = client.get("/audit", headers=auth_a).json()
    b_audit = client.get("/audit", headers=auth_b).json()
    assert a_audit["total"] > b_audit["total"]


def test_compliance_notice_available(client):
    resp = client.get("/compliance")
    assert resp.status_code == 200
    body = resp.json()
    assert "restrictions" in body
    assert any("human review" in r.lower() for r in body["restrictions"])


def test_adapters_declare_compliance_metadata(client, auth):
    adapters = client.get("/sources/adapters", headers=auth).json()
    keys = {a["source_key"] for a in adapters}
    assert {"csv_upload", "pdf_upload", "json_api", "rss", "demo"} <= keys
    for a in adapters:
        assert a["access_method"]
        assert a["terms_notes"]
        assert a["attribution"]
