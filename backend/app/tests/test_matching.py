from __future__ import annotations

from app.entity_resolution.blocking import block_keys, generate_pairs
from app.entity_resolution.features import compute_features
from app.entity_resolution.scoring import score_pair
from app.tests.conftest import import_demo


class _Rec:
    def __init__(self, **kw):
        self.__dict__.update(
            {
                "normalized_name": None,
                "normalized_last_name": None,
                "normalized_address": None,
                "city": None,
                "state": None,
                "zip_code": None,
                "case_number": None,
                "filing_date": None,
                "embedding": None,
                "normalized_payload": {},
                "id": id(self),
            }
        )
        self.__dict__.update(kw)


def test_blocking_generates_pairs_for_shared_keys():
    r1 = _Rec(normalized_last_name="rivera", state="DX")
    r2 = _Rec(normalized_last_name="rivera", state="DX")
    r3 = _Rec(normalized_last_name="chen", state="DX")
    assert block_keys(r1) & block_keys(r2)
    pairs = generate_pairs([r1, r2, r3])
    assert (0, 1) in pairs
    assert (0, 2) not in pairs


def test_scoring_strong_vs_different():
    from datetime import date

    strong_a = _Rec(
        normalized_name="jon rivera", normalized_last_name="rivera",
        normalized_address="482 maple st springfield dx 55011", city="Springfield",
        state="DX", zip_code="55011", case_number="2023-CV-004821",
        filing_date=date(2023, 3, 14),
        normalized_payload={"person": {"first": "jon", "last": "rivera"}},
    )
    strong_b = _Rec(
        normalized_name="jonathan rivera", normalized_last_name="rivera",
        normalized_address="482 maple st springfield dx 55011", city="Springfield",
        state="DX", zip_code="55011", case_number="2023-CV-004821",
        filing_date=date(2023, 4, 2),
        normalized_payload={"person": {"first": "jonathan", "last": "rivera"}},
    )
    result = score_pair(compute_features(strong_a, strong_b))
    assert result.confidence >= 85
    assert result.category == "strong"
    assert result.supporting  # has supporting evidence
    assert "identity determination" in result.rationale

    diff_a = _Rec(
        normalized_name="david thompson", normalized_last_name="thompson",
        state="DX", zip_code="55011", case_number="2024-TR-1",
        normalized_payload={"person": {"first": "david", "last": "thompson"}},
    )
    diff_b = _Rec(
        normalized_name="david thomson", normalized_last_name="thomson",
        state="ZZ", zip_code="90120", case_number="2024-SC-2",
        normalized_payload={"person": {"first": "david", "last": "thomson"}},
    )
    diff = score_pair(compute_features(diff_a, diff_b))
    assert diff.confidence < result.confidence


def test_candidate_generation_and_review_flow(client, auth):
    import_demo(client, auth)
    gen = client.post("/matches/generate", headers=auth, json={"limit": 500})
    assert gen.status_code == 200
    candidates = sorted(gen.json(), key=lambda c: -c["confidence_score"])
    assert candidates, "expected at least one candidate"
    top = candidates[0]
    assert top["confidence_score"] >= 85
    assert top["category"] == "strong"
    assert top["rationale"]
    assert top["review_status"] == "not_reviewed"

    # human review: approve
    approved = client.post(
        f"/matches/{top['id']}/approve", headers=auth, json={"decision": "confirmed"}
    )
    assert approved.json()["review_status"] == "confirmed"

    # reject another
    if len(candidates) > 1:
        rej = client.post(
            f"/matches/{candidates[1]['id']}/reject", headers=auth, json={"decision": "rejected"}
        )
        assert rej.json()["review_status"] == "rejected"
