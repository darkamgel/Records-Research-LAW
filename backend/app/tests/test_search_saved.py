from __future__ import annotations

from app.tests.conftest import import_demo


def test_search_modes(client, auth):
    import_demo(client, auth)
    kw = client.post("/records/search", headers=auth, json={"q": "Rivera", "mode": "keyword"})
    assert kw.json()["total"] >= 2

    fuzzy = client.post(
        "/records/search", headers=auth, json={"name": "Jon Rivera", "mode": "fuzzy_name"}
    )
    assert fuzzy.json()["total"] >= 1

    exact = client.post(
        "/records/search", headers=auth, json={"name": "Jonathan A. Rivera", "mode": "exact_name"}
    )
    assert exact.json()["total"] >= 1

    semantic = client.post(
        "/records/search", headers=auth, json={"q": "breach of contract", "mode": "semantic"}
    )
    assert semantic.json()["total"] >= 1

    case = client.post("/records/search", headers=auth, json={"case_number": "2023-CV-004821"})
    assert case.json()["total"] == 2

    jur = client.post("/records/search", headers=auth, json={"jurisdiction": "Metro City"})
    assert jur.json()["total"] >= 1


def test_saved_search_crud_and_execute(client, auth):
    import_demo(client, auth)
    created = client.post(
        "/saved-searches",
        headers=auth,
        json={"name": "Riveras", "query": {"q": "Rivera", "mode": "keyword"}},
    )
    assert created.status_code == 201
    ss_id = created.json()["id"]

    listed = client.get("/saved-searches", headers=auth).json()
    assert len(listed) == 1

    ex = client.post(f"/saved-searches/{ss_id}/execute", headers=auth).json()
    assert ex["result_count"] >= 2
    assert len(ex["new_result_ids"]) == ex["result_count"]

    # second run: nothing new
    ex2 = client.post(f"/saved-searches/{ss_id}/execute", headers=auth).json()
    assert ex2["new_result_ids"] == []

    updated = client.put(f"/saved-searches/{ss_id}", headers=auth, json={"name": "Renamed"})
    assert updated.json()["name"] == "Renamed"

    assert client.delete(f"/saved-searches/{ss_id}", headers=auth).status_code == 204
    assert client.get("/saved-searches", headers=auth).json() == []


def test_record_export_csv(client, auth):
    import_demo(client, auth)
    resp = client.post("/records/export", headers=auth, json={"q": "Rivera"})
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Rivera" in resp.text
