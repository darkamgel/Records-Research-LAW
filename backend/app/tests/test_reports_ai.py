from __future__ import annotations

from app.ai.client import local_embedding
from app.tests.conftest import import_demo


def _make_project_with_records(client, auth):
    import_demo(client, auth)
    recs = client.post("/records/search", headers=auth, json={"q": "Rivera"}).json()["items"]
    p = client.post(
        "/projects", headers=auth, json={"name": "Rivera Case", "objective": "Trace filings"}
    ).json()
    client.post(
        f"/projects/{p['id']}/records",
        headers=auth,
        json={"record_ids": [r["id"] for r in recs]},
    )
    return p


def test_deterministic_report_no_api_key(client, auth):
    p = _make_project_with_records(client, auth)
    rep = client.post(f"/projects/{p['id']}/report", headers=auth, json={"use_ai": True})
    assert rep.status_code == 200
    body = rep.json()
    # No API key => deterministic template, clearly not AI-generated.
    assert body["ai_generated"] is False
    assert "Research Summary" in body["summary_markdown"]
    assert "identity determination" in body["summary_markdown"].lower()
    # every listed record is cited
    assert body["content"]["cited_record_ids"]


def test_report_exports(client, auth):
    p = _make_project_with_records(client, auth)
    rep = client.post(f"/projects/{p['id']}/report", headers=auth, json={"use_ai": False}).json()
    for fmt, ctype in [("markdown", "text/markdown"), ("json", "application/json"),
                       ("csv", "text/csv"), ("html", "text/html")]:
        r = client.get(f"/projects/reports/{rep['id']}/export?fmt={fmt}", headers=auth)
        assert r.status_code == 200
        assert ctype in r.headers["content-type"]


class _FakeAI:
    enabled = True

    def structured_json(self, system, user, **kw):
        # Return a schema-valid summary that cites a record id present in the prompt.
        import re

        ids = re.findall(r"\[record: ([0-9a-f-]+)\]", user)
        cited = ids[:1]
        return {
            "summary_markdown": f"AI summary of the case. [record: {cited[0] if cited else 'none'}]",
            "cited_record_ids": cited,
        }

    def embed(self, text):
        return local_embedding(text)


def test_ai_report_with_mocked_openai(client, auth, monkeypatch):
    import app.services.ai_settings as ai_settings

    # Reports resolve the LLM via workspace settings (UI/env), not the process singleton.
    monkeypatch.setattr(ai_settings, "get_workspace_ai_client", lambda db, wid: _FakeAI())
    p = _make_project_with_records(client, auth)
    rep = client.post(f"/projects/{p['id']}/report", headers=auth, json={"use_ai": True}).json()
    assert rep["ai_generated"] is True
    assert "AI summary" in rep["summary_markdown"]
    assert rep["content"]["cited_record_ids"]
