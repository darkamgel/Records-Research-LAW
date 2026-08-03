"""Weighted confidence scoring from deterministic features.

The LLM never controls this number. The score is a weight-normalized average of
available feature scores (0..100), with a capped penalty for strong
contradictions. Categories are review guidance, NOT identity confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.entity_resolution.config import (
    CATEGORY_THRESHOLDS,
    CONTRADICTION_PENALTY,
    DEFAULT_WEIGHTS,
)
from app.entity_resolution.features import FeatureResult


@dataclass
class ScoreResult:
    confidence: float
    category: str
    feature_scores: dict[str, float]
    supporting: list[dict] = field(default_factory=list)
    conflicting: list[dict] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    rationale: str = ""


def _category(score: float) -> str:
    for threshold, name in CATEGORY_THRESHOLDS:
        if score >= threshold:
            return name
    return "unlikely"


def score_pair(
    features: list[FeatureResult], weights: dict[str, float] | None = None
) -> ScoreResult:
    weights = weights or DEFAULT_WEIGHTS
    feature_scores: dict[str, float] = {}
    supporting: list[dict] = []
    conflicting: list[dict] = []
    missing: list[str] = []

    weighted_sum = 0.0
    weight_total = 0.0
    contradictions = 0

    for f in features:
        if f.feature == "source_reliability":
            # Used only as a small tie-breaker multiplier, not a base feature.
            continue
        if f.score is None:
            missing.append(f.feature)
            continue
        w = weights.get(f.feature, 0.0)
        feature_scores[f.feature] = round(f.score, 3)
        weighted_sum += f.score * w
        weight_total += w
        item = {"feature": f.feature, "score": round(f.score, 3), "weight": w, "detail": f.detail}
        if f.kind == "supporting":
            supporting.append(item)
        elif f.kind == "conflicting":
            conflicting.append(item)
            contradictions += 1

    base = (weighted_sum / weight_total) * 100 if weight_total else 0.0
    penalty = min(CONTRADICTION_PENALTY, contradictions * (CONTRADICTION_PENALTY / 2))
    confidence = max(0.0, min(100.0, base - penalty))
    confidence = round(confidence, 1)

    rationale = _build_rationale(confidence, supporting, conflicting, missing)
    return ScoreResult(
        confidence=confidence,
        category=_category(confidence),
        feature_scores=feature_scores,
        supporting=supporting,
        conflicting=conflicting,
        missing=missing,
        rationale=rationale,
    )


def _build_rationale(
    confidence: float, supporting: list[dict], conflicting: list[dict], missing: list[str]
) -> str:
    parts = [
        f"Deterministic confidence {confidence:.0f}/100 ({_category(confidence)}). "
        "This is review guidance only and is not an identity determination."
    ]
    if supporting:
        parts.append("Supporting: " + "; ".join(s["detail"] for s in supporting[:5]) + ".")
    if conflicting:
        parts.append("Conflicting: " + "; ".join(c["detail"] for c in conflicting[:5]) + ".")
    if missing:
        parts.append("Missing information for: " + ", ".join(missing[:6]) + ".")
    return " ".join(parts)
