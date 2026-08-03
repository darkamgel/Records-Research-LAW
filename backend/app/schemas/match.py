from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MatchCategory, ReviewStatus
from app.schemas.common import ORMModel
from app.schemas.record import RecordOut


class GenerateCandidatesRequest(BaseModel):
    record_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    limit: int = Field(default=200, ge=1, le=2000)
    use_ai_explanation: bool = False


class EvidenceItem(BaseModel):
    feature: str
    score: float
    weight: float
    kind: str
    detail: str | None = None


class MatchCandidateOut(ORMModel):
    id: uuid.UUID
    record_a_id: uuid.UUID
    record_b_id: uuid.UUID
    confidence_score: float
    category: MatchCategory
    feature_scores: dict | None
    supporting_evidence: list | None
    conflicting_evidence: list | None
    missing_information: list | None
    rationale: str | None
    rationale_source: str
    review_status: ReviewStatus
    created_at: datetime


class MatchCandidateDetailOut(MatchCandidateOut):
    record_a: RecordOut | None = None
    record_b: RecordOut | None = None


class ReviewRequest(BaseModel):
    decision: ReviewStatus
    notes: str | None = None
    project_id: uuid.UUID | None = None
