from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import Principal, get_principal
from app.db.session import get_db
from app.models.record import Record
from app.models.research import GeneratedReport, ProjectRecord, ResearchProject
from app.schemas.project import (
    ProjectCreate,
    ProjectDetailOut,
    ProjectOut,
    ProjectRecordsRequest,
    ReportOut,
    ReportRequest,
)
from app.schemas.record import RecordOut
from app.services.audit import log_audit
from app.services.report_service import (
    generate_project_report,
    report_to_csv,
    report_to_html,
    report_to_markdown,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    project = ResearchProject(
        workspace_id=principal.workspace_id,
        created_by=principal.user.id,
        name=body.name,
        objective=body.objective,
    )
    db.add(project)
    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="create_project",
        target_type="project",
        target_id=str(project.id),
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    rows = db.execute(
        select(ResearchProject)
        .where(ResearchProject.workspace_id == principal.workspace_id)
        .order_by(ResearchProject.created_at.desc())
    ).scalars()
    return list(rows)


def _get_project(db, principal, project_id) -> ResearchProject:
    project = db.get(ResearchProject, project_id)
    if project is None or project.workspace_id != principal.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.get("/{project_id}", response_model=ProjectDetailOut)
def get_project(
    project_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    project = _get_project(db, principal, project_id)
    record_ids = [
        pr.record_id
        for pr in db.execute(
            select(ProjectRecord).where(ProjectRecord.project_id == project.id)
        ).scalars()
    ]
    records = (
        list(db.execute(select(Record).where(Record.id.in_(record_ids))).scalars())
        if record_ids
        else []
    )
    return ProjectDetailOut(
        id=project.id,
        name=project.name,
        objective=project.objective,
        created_at=project.created_at,
        records=[RecordOut.model_validate(r) for r in records],
    )


@router.post("/{project_id}/records", response_model=ProjectDetailOut)
def add_records(
    project_id: uuid.UUID,
    body: ProjectRecordsRequest,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    project = _get_project(db, principal, project_id)
    for rid in body.record_ids:
        rec = db.get(Record, rid)
        if rec is None or rec.workspace_id != principal.workspace_id:
            continue
        exists = db.execute(
            select(ProjectRecord).where(
                ProjectRecord.project_id == project.id, ProjectRecord.record_id == rid
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(ProjectRecord(project_id=project.id, record_id=rid))
    db.commit()
    return get_project(project_id, principal, db)


@router.delete("/{project_id}/records/{record_id}", response_model=ProjectDetailOut)
def remove_record(
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    project = _get_project(db, principal, project_id)
    pr = db.execute(
        select(ProjectRecord).where(
            ProjectRecord.project_id == project.id, ProjectRecord.record_id == record_id
        )
    ).scalar_one_or_none()
    if pr:
        db.delete(pr)
        db.commit()
    return get_project(project_id, principal, db)


@router.post("/{project_id}/report", response_model=ReportOut)
def generate_report(
    project_id: uuid.UUID,
    body: ReportRequest,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    project = _get_project(db, principal, project_id)
    from app.services.ai_settings import get_workspace_ai_client

    ai = get_workspace_ai_client(db, principal.workspace_id)
    report = generate_project_report(
        db,
        project=project,
        title=body.title,
        use_ai=body.use_ai,
        user_id=principal.user.id,
        ai=ai,
    )
    db.commit()
    db.refresh(report)
    return report


@router.get("/{project_id}/reports", response_model=list[ReportOut])
def list_reports(
    project_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    _get_project(db, principal, project_id)
    rows = db.execute(
        select(GeneratedReport)
        .where(GeneratedReport.project_id == project_id)
        .order_by(GeneratedReport.created_at.desc())
    ).scalars()
    return list(rows)


def _get_report(db, principal, report_id) -> GeneratedReport:
    report = db.get(GeneratedReport, report_id)
    if report is None or report.workspace_id != principal.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return report


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    return _get_report(db, principal, report_id)


@router.get("/reports/{report_id}/export")
def export_report(
    report_id: uuid.UUID,
    fmt: str = "markdown",
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    report = _get_report(db, principal, report_id)
    if fmt == "markdown":
        return PlainTextResponse(report_to_markdown(report), media_type="text/markdown")
    if fmt == "json":
        return Response(
            content=__import__("json").dumps(report.content, indent=2, default=str),
            media_type="application/json",
        )
    if fmt == "csv":
        return PlainTextResponse(
            report_to_csv(report),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=report.csv"},
        )
    if fmt == "html":
        return Response(content=report_to_html(report), media_type="text/html")
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported format")
