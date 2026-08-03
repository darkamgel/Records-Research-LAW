"""Deterministic feature computation for a candidate record pair.

Each feature returns a score in 0..1 plus a human-readable detail and a "kind"
(supporting / conflicting / missing) so evidence can be surfaced to reviewers.
The LLM is never used here — these are the numbers the confidence score is built
from.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from app.ai.client import cosine_similarity


@dataclass
class FeatureResult:
    feature: str
    score: float | None  # None => could not be computed (missing info)
    kind: str  # supporting | conflicting | missing | neutral
    detail: str


def _both(a: str | None, b: str | None) -> bool:
    return bool(a) and bool(b)


def _str_sim(a: str, b: str) -> float:
    return max(fuzz.token_sort_ratio(a, b), JaroWinkler.similarity(a, b) * 100) / 100.0


def _kind_from(score: float, high: float = 0.85, low: float = 0.4) -> str:
    if score >= high:
        return "supporting"
    if score <= low:
        return "conflicting"
    return "neutral"


class RecordView:
    """Lightweight accessor over a Record ORM object (or dict) for features."""

    def __init__(self, rec: object) -> None:
        self._get = (lambda k: rec.get(k)) if isinstance(rec, dict) else (lambda k: getattr(rec, k, None))

    def __getattr__(self, item: str):
        return self._get(item)


def compute_features(a: object, b: object) -> list[FeatureResult]:
    ra, rb = RecordView(a), RecordView(b)
    results: list[FeatureResult] = []

    def name_parts(view: RecordView) -> dict[str, str | None]:
        payload = view.normalized_payload or {}
        person = (payload.get("person") or {}) if isinstance(payload, dict) else {}
        return {
            "first": person.get("first"),
            "middle": person.get("middle"),
            "last": person.get("last") or view.normalized_last_name,
            "full": view.normalized_name,
        }

    na, nb = name_parts(ra), name_parts(rb)

    # Name features.
    for feat, key in (("first_name", "first"), ("middle_name", "middle"), ("last_name", "last")):
        if _both(na[key], nb[key]):
            score = _str_sim(na[key], nb[key])
            results.append(FeatureResult(feat, score, _kind_from(score),
                                         f"{key} name '{na[key]}' vs '{nb[key]}' -> {score:.2f}"))
        else:
            results.append(FeatureResult(feat, None, "missing", f"{key} name missing on one side"))

    if _both(na["full"], nb["full"]):
        score = _str_sim(na["full"], nb["full"])
        results.append(FeatureResult("full_name", score, _kind_from(score),
                                     f"full name '{na['full']}' vs '{nb['full']}' -> {score:.2f}"))
    else:
        results.append(FeatureResult("full_name", None, "missing", "full name missing on one side"))

    # Address feature.
    if _both(ra.normalized_address, rb.normalized_address):
        score = _str_sim(ra.normalized_address, rb.normalized_address)
        results.append(FeatureResult("address", score, _kind_from(score, 0.8, 0.3),
                                     f"address similarity {score:.2f}"))
    else:
        results.append(FeatureResult("address", None, "missing", "address missing on one side"))

    # Geographic feature (city/state/zip agreement).
    geo_score, geo_detail = _geographic(ra, rb)
    if geo_score is None:
        results.append(FeatureResult("geographic", None, "missing", "no shared geo fields"))
    else:
        results.append(FeatureResult("geographic", geo_score, _kind_from(geo_score, 0.9, 0.2), geo_detail))

    # Date compatibility.
    date_score, date_detail, date_kind = _date_compat(ra, rb)
    results.append(FeatureResult("date", date_score, date_kind, date_detail))

    # Organization.
    oa = _org(ra)
    ob = _org(rb)
    if _both(oa, ob):
        score = _str_sim(oa, ob)
        results.append(FeatureResult("organization", score, _kind_from(score),
                                     f"org '{oa}' vs '{ob}' -> {score:.2f}"))
    else:
        results.append(FeatureResult("organization", None, "missing", "organization missing on one side"))

    # Identifier match (case/parcel number).
    ida, idb = ra.case_number, rb.case_number
    if _both(ida, idb):
        same = ida.strip().upper() == idb.strip().upper()
        results.append(FeatureResult("identifier", 1.0 if same else 0.0,
                                     "supporting" if same else "conflicting",
                                     f"case number {'matches' if same else 'differs'}: {ida} / {idb}"))
    else:
        results.append(FeatureResult("identifier", None, "missing", "case number missing on one side"))

    # Semantic similarity (embeddings).
    if ra.embedding and rb.embedding:
        score = max(0.0, cosine_similarity(list(ra.embedding), list(rb.embedding)))
        results.append(FeatureResult("semantic", score, _kind_from(score, 0.8, 0.2),
                                     f"semantic similarity {score:.2f}"))
    else:
        results.append(FeatureResult("semantic", None, "missing", "embedding unavailable"))

    # Source reliability: official sources slightly more reliable than uploads.
    rel = _source_reliability(ra, rb)
    results.append(FeatureResult("source_reliability", rel, "neutral",
                                 f"source reliability factor {rel:.2f}"))

    return results


def _org(view: RecordView) -> str | None:
    payload = view.normalized_payload or {}
    if isinstance(payload, dict):
        org = payload.get("organization")
        if isinstance(org, dict):
            return org.get("normalized")
        if isinstance(org, str):
            return org
    return None


def _geographic(a: RecordView, b: RecordView) -> tuple[float | None, str]:
    scores = []
    details = []
    if _both(a.zip_code, b.zip_code):
        same = a.zip_code[:5] == b.zip_code[:5]
        scores.append(1.0 if same else 0.0)
        details.append(f"ZIP {'match' if same else 'differ'}")
    if _both(a.state, b.state):
        same = a.state.upper() == b.state.upper()
        scores.append(1.0 if same else 0.0)
        details.append(f"state {'match' if same else 'differ'}")
    if _both(a.city, b.city):
        same = a.city.strip().lower() == b.city.strip().lower()
        scores.append(1.0 if same else 0.0)
        details.append(f"city {'match' if same else 'differ'}")
    if not scores:
        return None, "no shared geographic fields"
    return sum(scores) / len(scores), ", ".join(details)


def _date_compat(a: RecordView, b: RecordView) -> tuple[float | None, str, str]:
    da, db = a.filing_date, b.filing_date
    if not (da and db):
        return None, "filing date missing on one side", "missing"
    delta = abs((da - db).days)
    if delta == 0:
        return 1.0, "same filing date", "supporting"
    if delta <= 30:
        return 0.8, f"filing dates within {delta} days", "supporting"
    if delta <= 365:
        return 0.4, f"filing dates {delta} days apart", "neutral"
    return 0.1, f"filing dates {delta} days apart", "conflicting"


def _source_reliability(a: RecordView, b: RecordView) -> float:
    # Neutral default; hook for weighting official sources higher in future.
    return 0.6
