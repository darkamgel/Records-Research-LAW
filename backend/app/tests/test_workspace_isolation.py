from __future__ import annotations

from app.tests.conftest import import_demo


def test_records_are_workspace_isolated(client, register):
    token_a = register(client, "a@ex.com", ws="A")
    token_b = register(client, "b@ex.com", ws="B")
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    import_demo(client, auth_a)

    a_results = client.post("/records/search", headers=auth_a, json={"q": "Rivera"}).json()
    b_results = client.post("/records/search", headers=auth_b, json={"q": "Rivera"}).json()
    assert a_results["total"] > 0
    assert b_results["total"] == 0  # workspace B cannot see workspace A's records


def test_cannot_access_other_workspace_record_by_id(client, register):
    token_a = register(client, "a@ex.com", ws="A")
    token_b = register(client, "b@ex.com", ws="B")
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}
    import_demo(client, auth_a)
    rec = client.post("/records/search", headers=auth_a, json={"q": "Rivera"}).json()["items"][0]

    # IDOR protection: workspace B gets 404 for a record it does not own.
    resp = client.get(f"/records/{rec['id']}", headers=auth_b)
    assert resp.status_code == 404
