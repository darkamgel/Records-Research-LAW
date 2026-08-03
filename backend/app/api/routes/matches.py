from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.workflows import analyze_match
from app.core.deps import Principal, get_principal
from app.db.session import get_db
from app.entity_resolution.engine import generate_candidates
from app.models.enums import MatchCategory, ReviewStatus
from app.models.matching import MatchCandidate, RecordRelationship, ReviewDecision
from app.models.record import Record
from app.schemas.match import (
    GenerateCandidatesRequest,
    MatchCandidateDetailOut,
    MatchCandidateOut,
    ReviewRequest,
)
from app.schemas.record import RecordOut
from app.services.audit import log_audit

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/generate", response_model=list[MatchCandidateOut])
def generate(
    body: GenerateCandidatesRequest,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    record_ids = None
    if body.project_id:
        from app.models.research import ProjectRecord

        record_ids = [
            pr.record_id
            for pr in db.execute(
                select(ProjectRecord).where(ProjectRecord.project_id == body.project_id)
            ).scalars()
        ]

    candidates = generate_candidates(
        db,
        principal.workspace_id,
        record_id=body.record_id,
        record_ids=record_ids,
        limit=body.limit,
    )

    if body.use_ai_explanation:
        from app.services.ai_settings import get_workspace_ai_client

        ai = get_workspace_ai_client(db, principal.workspace_id)
        for cand in candidates:
            a = db.get(Record, cand.record_a_id)
            b = db.get(Record, cand.record_b_id)
            result = analyze_match(a, b, use_ai=True, ai=ai)
            cand.rationale = result["rationale"]
            cand.rationale_source = result["rationale_source"]
        log_audit(
            db,
            workspace_id=principal.workspace_id,
            user_id=principal.user.id,
            action="ai_operation",
            detail={"operation": "match_explanation", "count": len(candidates)},
        )

    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="generate_candidates",
        detail={"count": len(candidates)},
    )
    db.commit()
    return candidates


@router.get("", response_model=list[MatchCandidateOut])
def list_candidates(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
    review_status: ReviewStatus | None = None,
    category: MatchCategory | None = None,
    min_score: float = Query(default=0.0, ge=0, le=100),
    limit: int = 50,
    offset: int = 0,
):
    stmt = select(MatchCandidate).where(
        MatchCandidate.workspace_id == principal.workspace_id,
        MatchCandidate.confidence_score >= min_score,
    )
    if review_status:
        stmt = stmt.where(MatchCandidate.review_status == review_status)
    if category:
        stmt = stmt.where(MatchCandidate.category == category)
    stmt = stmt.order_by(MatchCandidate.confidence_score.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars())


def _get_candidate(db, principal, candidate_id) -> MatchCandidate:
    cand = db.get(MatchCandidate, candidate_id)
    if cand is None or cand.workspace_id != principal.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    return cand


@router.get("/{candidate_id}", response_model=MatchCandidateDetailOut)
def candidate_detail(
    candidate_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    cand = _get_candidate(db, principal, candidate_id)
    detail = MatchCandidateDetailOut.model_validate(cand)
    a = db.get(Record, cand.record_a_id)
    b = db.get(Record, cand.record_b_id)
    detail.record_a = RecordOut.model_validate(a) if a else None
    detail.record_b = RecordOut.model_validate(b) if b else None
    return detail


def _review(db, principal, candidate_id, decision: ReviewStatus, notes, project_id):
    cand = _get_candidate(db, principal, candidate_id)
    cand.review_status = decision
    db.add(
        ReviewDecision(
            workspace_id=principal.workspace_id,
            candidate_id=cand.id,
            project_id=project_id,
            reviewer_id=principal.user.id,
            decision=decision,
            notes=notes,
        )
    )
    # Only create a confirmed relationship on an explicit user decision.
    if decision == ReviewStatus.confirmed:
        db.add(
            RecordRelationship(
                workspace_id=principal.workspace_id,
                project_id=project_id,
                record_a_id=cand.record_a_id,
                record_b_id=cand.record_b_id,
                relationship_type="same_entity",
                confirmed_by=principal.user.id,
            )
        )
    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="review_match",
        target_type="match_candidate",
        target_id=str(cand.id),
        detail={"decision": decision.value},
    )
    db.commit()
    db.refresh(cand)
    return cand


@router.post("/{candidate_id}/review", response_model=MatchCandidateOut)
def review(
    candidate_id: uuid.UUID,
    body: ReviewRequest,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    return _review(db, principal, candidate_id, body.decision, body.notes, body.project_id)


@router.post("/{candidate_id}/approve", response_model=MatchCandidateOut)
def approve(candidate_id: uuid.UUID, body: ReviewRequest | None = None,
            principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    notes = body.notes if body else None
    pid = body.project_id if body else None
    return _review(db, principal, candidate_id, ReviewStatus.confirmed, notes, pid)


@router.post("/{candidate_id}/reject", response_model=MatchCandidateOut)
def reject(candidate_id: uuid.UUID, body: ReviewRequest | None = None,
           principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    notes = body.notes if body else None
    pid = body.project_id if body else None
    return _review(db, principal, candidate_id, ReviewStatus.rejected, notes, pid)


@router.post("/{candidate_id}/needs-info", response_model=MatchCandidateOut)
def needs_info(candidate_id: uuid.UUID, body: ReviewRequest | None = None,
               principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    notes = body.notes if body else None
    pid = body.project_id if body else None
    return _review(db, principal, candidate_id, ReviewStatus.needs_more_info, notes, pid)
