"""Research report assembly + export (markdown/json/csv/html)."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import AIClient
from app.ai.workflows import generate_summary
from app.models.matching import MatchCandidate, RecordRelationship
from app.models.record import Record
from app.models.research import GeneratedReport, ProjectRecord, ResearchProject
from app.services.audit import log_audit


def _record_dict(r: Record) -> dict:
    return {
        "id": str(r.id),
        "title": r.title,
        "record_type": r.record_type,
        "primary_name": r.primary_name,
        "case_number": r.case_number,
        "filing_date": r.filing_date.isoformat() if r.filing_date else None,
        "jurisdiction": r.jurisdiction,
        "original_url": r.original_url,
    }


def generate_project_report(
    db: Session,
    *,
    project: ResearchProject,
    title: str | None,
    use_ai: bool,
    user_id: uuid.UUID | None,
    ai: AIClient | None = None,
) -> GeneratedReport:
    record_ids = [
        pr.record_id
        for pr in db.execute(
            select(ProjectRecord).where(ProjectRecord.project_id == project.id)
        ).scalars()
    ]
    records = list(
        db.execute(select(Record).where(Record.id.in_(record_ids))).scalars()
    ) if record_ids else []
    record_dicts = [_record_dict(r) for r in records]

    confirmed_rels = list(
        db.execute(
            select(RecordRelationship).where(RecordRelationship.project_id == project.id)
        ).scalars()
    )
    confirmed = [
        f"Records {rel.record_a_id} and {rel.record_b_id} confirmed as {rel.relationship_type}"
        for rel in confirmed_rels
    ]

    candidates = list(
        db.execute(
            select(MatchCandidate).where(
                MatchCandidate.workspace_id == project.workspace_id,
                MatchCandidate.record_a_id.in_(record_ids or [uuid.uuid4()]),
            )
        ).scalars()
    )
    unreviewed = [
        f"Possible link {c.record_a_id} ~ {c.record_b_id} "
        f"(confidence {c.confidence_score:.0f}/100, {c.category.value}) — {c.review_status.value}"
        for c in candidates
        if c.review_status.value == "not_reviewed"
    ]

    state = generate_summary(
        {
            "project_name": project.name,
            "objective": project.objective,
            "records": record_dicts,
            "confirmed": confirmed,
            "unreviewed": unreviewed,
            "use_ai": use_ai,
        },
        ai=ai,
    )

    content = {
        "project_name": project.name,
        "objective": project.objective,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": record_dicts,
        "confirmed_relationships": confirmed,
        "unreviewed_relationships": unreviewed,
        "cited_record_ids": state.get("cited_ids", []),
        "candidates": [
            {
                "record_a_id": str(c.record_a_id),
                "record_b_id": str(c.record_b_id),
                "confidence_score": c.confidence_score,
                "category": c.category.value,
                "review_status": c.review_status.value,
                "supporting_evidence": c.supporting_evidence,
                "conflicting_evidence": c.conflicting_evidence,
                "rationale": c.rationale,
            }
            for c in candidates
        ],
        "ai_generated": state.get("ai_generated", False),
        "disclaimer": (
            "This report is a research productivity aid. It does not make identity "
            "determinations. All potential matches require human review."
        ),
    }

    report = GeneratedReport(
        workspace_id=project.workspace_id,
        project_id=project.id,
        created_by=user_id,
        title=title or f"Report: {project.name}",
        summary_markdown=state.get("summary_markdown"),
        content=content,
        ai_generated=state.get("ai_generated", False),
    )
    db.add(report)
    db.flush()
    log_audit(
        db,
        workspace_id=project.workspace_id,
        user_id=user_id,
        action="generate_report",
        target_type="report",
        target_id=str(report.id),
        detail={"ai_generated": report.ai_generated, "records": len(records)},
    )
    return report


# --------------------------------------------------------------------------- exports
def report_to_markdown(report: GeneratedReport) -> str:
    return report.summary_markdown or ""


def report_to_html(report: GeneratedReport) -> str:
    md = report.summary_markdown or ""
    # Minimal, printable HTML wrapper (no external deps).
    body = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{report.title}</title>"
        "<style>body{font-family:system-ui,Arial,sans-serif;max-width:800px;margin:2rem auto;"
        "line-height:1.5;padding:0 1rem} pre{white-space:pre-wrap}</style></head>"
        f"<body><pre>{body}</pre></body></html>"
    )


def report_to_csv(report: GeneratedReport) -> str:
    content = report.content or {}
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "title", "record_type", "primary_name", "case_number",
                     "filing_date", "jurisdiction", "original_url"])
    for r in content.get("records", []):
        writer.writerow([
            r.get("id"), r.get("title"), r.get("record_type"), r.get("primary_name"),
            r.get("case_number"), r.get("filing_date"), r.get("jurisdiction"),
            r.get("original_url"),
        ])
    return out.getvalue()
