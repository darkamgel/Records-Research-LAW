from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.types import GUID, EnumType, JSONType
from app.models.enums import MatchCategory, ReviewStatus


class RecordRelationship(UUIDMixin, TimestampMixin, Base):
    """A user-confirmed relationship between two records within a project."""

    __tablename__ = "record_relationships"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("research_projects.id"))
    record_a_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("records.id"))
    record_b_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("records.id"))
    relationship_type: Mapped[str] = mapped_column(String(64), default="same_entity")
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))


class MatchCandidate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "match_candidates"
    __table_args__ = (
        UniqueConstraint("workspace_id", "record_a_id", "record_b_id", name="uq_candidate_pair"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    record_a_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("records.id", ondelete="CASCADE"), index=True
    )
    record_b_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("records.id", ondelete="CASCADE"), index=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    category: Mapped[MatchCategory] = mapped_column(
        EnumType(MatchCategory), default=MatchCategory.unlikely
    )
    feature_scores: Mapped[dict | None] = mapped_column(JSONType)
    supporting_evidence: Mapped[list | None] = mapped_column(JSONType)
    conflicting_evidence: Mapped[list | None] = mapped_column(JSONType)
    missing_information: Mapped[list | None] = mapped_column(JSONType)
    rationale: Mapped[str | None] = mapped_column(Text)
    rationale_source: Mapped[str] = mapped_column(String(32), default="deterministic")  # or "ai"
    review_status: Mapped[ReviewStatus] = mapped_column(
        EnumType(ReviewStatus), default=ReviewStatus.not_reviewed, index=True
    )

    evidence: Mapped[list["MatchEvidence"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["ReviewDecision"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class MatchEvidence(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "match_evidence"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("match_candidates.id", ondelete="CASCADE"), index=True
    )
    feature: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    kind: Mapped[str] = mapped_column(String(32))  # supporting|conflicting|missing
    detail: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[MatchCandidate] = relationship(back_populates="evidence")


class ReviewDecision(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_decisions"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("match_candidates.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("research_projects.id"))
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    decision: Mapped[ReviewStatus] = mapped_column(EnumType(ReviewStatus))
    notes: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[MatchCandidate] = relationship(back_populates="decisions")
