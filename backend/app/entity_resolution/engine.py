"""Matching engine: orchestrates blocking, features, scoring, persistence.

This is the deterministic core of Workflow B. The optional LLM explanation is
added by the AI workflow layer and never alters the numeric score.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.entity_resolution.blocking import block_keys, generate_pairs
from app.entity_resolution.features import compute_features
from app.entity_resolution.scoring import ScoreResult, score_pair
from app.models.enums import MatchCategory
from app.models.matching import MatchCandidate, MatchEvidence
from app.models.record import Record

logger = get_logger(__name__)


def _pair_key(a_id: uuid.UUID, b_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return (a_id, b_id) if str(a_id) <= str(b_id) else (b_id, a_id)


def analyze_pair(a: Record, b: Record) -> ScoreResult:
    features = compute_features(a, b)
    return score_pair(features)


def generate_candidates(
    db: Session,
    workspace_id: uuid.UUID,
    *,
    record_id: uuid.UUID | None = None,
    record_ids: list[uuid.UUID] | None = None,
    min_score: float = 40.0,
    limit: int = 500,
) -> list[MatchCandidate]:
    """Compute candidate pairs and persist those at/above ``min_score``.

    - If ``record_id`` is given, only pairs involving that record are considered.
    - If ``record_ids`` is given, only those records are compared with each other.
    - Otherwise all workspace records are considered (bounded by blocking).
    """
    query = select(Record).where(Record.workspace_id == workspace_id)
    if record_ids:
        query = query.where(Record.id.in_(record_ids))
    records = list(db.execute(query).scalars())
    if len(records) < 2:
        return []

    index_by_id = {r.id: i for i, r in enumerate(records)}

    if record_id is not None and record_id in index_by_id:
        target_idx = index_by_id[record_id]
        target = records[target_idx]
        target_keys = block_keys(target)
        pairs: set[tuple[int, int]] = set()
        for i, r in enumerate(records):
            if i == target_idx:
                continue
            if block_keys(r) & target_keys:
                pairs.add(tuple(sorted((target_idx, i))))  # type: ignore[arg-type]
    else:
        pairs = generate_pairs(records)

    created: list[MatchCandidate] = []
    for i, j in pairs:
        a, b = records[i], records[j]
        result = analyze_pair(a, b)
        if result.confidence < min_score:
            continue
        a_id, b_id = _pair_key(a.id, b.id)
        existing = db.execute(
            select(MatchCandidate).where(
                MatchCandidate.workspace_id == workspace_id,
                MatchCandidate.record_a_id == a_id,
                MatchCandidate.record_b_id == b_id,
            )
        ).scalar_one_or_none()

        candidate = existing or MatchCandidate(
            workspace_id=workspace_id, record_a_id=a_id, record_b_id=b_id
        )
        candidate.confidence_score = result.confidence
        candidate.category = MatchCategory(result.category)
        candidate.feature_scores = result.feature_scores
        candidate.supporting_evidence = result.supporting
        candidate.conflicting_evidence = result.conflicting
        candidate.missing_information = result.missing
        candidate.rationale = result.rationale
        candidate.rationale_source = "deterministic"

        if existing is None:
            db.add(candidate)
            db.flush()
        else:
            # refresh evidence rows
            for ev in list(candidate.evidence):
                db.delete(ev)
            db.flush()

        for item in result.supporting + result.conflicting:
            db.add(
                MatchEvidence(
                    candidate_id=candidate.id,
                    feature=item["feature"],
                    score=item["score"],
                    weight=item["weight"],
                    kind="supporting" if item in result.supporting else "conflicting",
                    detail=item["detail"],
                )
            )
        created.append(candidate)
        if len(created) >= limit:
            break

    db.flush()
    return created
