"""Record search: keyword, full-text, fuzzy-name, exact-name, and semantic.

Full-text uses PostgreSQL ``to_tsvector``/``websearch_to_tsquery`` when running on
Postgres and falls back to ``LIKE`` on SQLite. Fuzzy name matching uses
``pg_trgm`` similarity on Postgres and RapidFuzz in Python on SQLite. Semantic
search ranks by cosine similarity over stored embeddings.
"""

from __future__ import annotations

import uuid

from rapidfuzz import fuzz
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from app.ai.client import cosine_similarity, get_ai_client
from app.models.record import Record
from app.schemas.search import SearchQuery
from app.services.normalization import normalize_name


def _base_filters(q: SearchQuery, workspace_id: uuid.UUID):
    filters = [Record.workspace_id == workspace_id]
    if q.jurisdiction:
        filters.append(Record.jurisdiction.ilike(f"%{q.jurisdiction}%"))
    if q.source_id:
        filters.append(Record.source_id == uuid.UUID(q.source_id))
    if q.record_type:
        filters.append(Record.record_type == q.record_type)
    if q.state:
        filters.append(Record.state == q.state.upper())
    if q.city:
        filters.append(Record.city.ilike(f"%{q.city}%"))
    if q.zip_code:
        filters.append(Record.zip_code.like(f"{q.zip_code}%"))
    if q.case_number:
        filters.append(Record.case_number.ilike(f"%{q.case_number}%"))
    if q.address:
        filters.append(Record.normalized_address.ilike(f"%{q.address.lower()}%"))
    if q.filing_date_from:
        filters.append(Record.filing_date >= q.filing_date_from)
    if q.filing_date_to:
        filters.append(Record.filing_date <= q.filing_date_to)
    if q.is_demo is not None:
        filters.append(Record.is_demo == q.is_demo)
    return filters


def _apply_sort(stmt, q: SearchQuery):
    col = {
        "created_at": Record.created_at,
        "filing_date": Record.filing_date,
        "title": Record.title,
    }.get(q.sort, Record.created_at)
    return stmt.order_by(col.desc() if q.sort_dir == "desc" else col.asc())


def search_records(
    db: Session, workspace_id: uuid.UUID, q: SearchQuery
) -> tuple[list[Record], int]:
    is_pg = db.bind.dialect.name == "postgresql"
    filters = _base_filters(q, workspace_id)

    # Name-specific modes.
    if q.mode == "exact_name" and (q.name or q.q):
        target = normalize_name(q.name or q.q or "").normalized
        filters.append(Record.normalized_name == target)
        return _paginate(db, filters, q)

    if q.mode == "fuzzy_name" and (q.name or q.q):
        return _fuzzy_name_search(db, filters, q, is_pg)

    if q.mode == "semantic" and (q.q or q.name):
        return _semantic_search(db, filters, q)

    # keyword / fulltext
    term = q.q or q.name
    if term:
        if q.mode == "fulltext" and is_pg:
            filters.append(
                text("to_tsvector('english', coalesce(search_text,'')) @@ websearch_to_tsquery('english', :term)")
            )
            stmt = select(Record).where(and_(*filters)).params(term=term)
        else:
            like = f"%{term.lower()}%"
            filters.append(
                or_(
                    func.lower(Record.search_text).like(like),
                    func.lower(Record.title).like(like),
                    func.lower(Record.primary_name).like(like),
                )
            )
            stmt = select(Record).where(and_(*filters))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = _apply_sort(stmt, q).limit(q.limit).offset(q.offset)
        return list(db.execute(stmt).scalars()), total

    return _paginate(db, filters, q)


def _paginate(db: Session, filters, q: SearchQuery) -> tuple[list[Record], int]:
    stmt = select(Record).where(and_(*filters))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = _apply_sort(stmt, q).limit(q.limit).offset(q.offset)
    return list(db.execute(stmt).scalars()), total


def _fuzzy_name_search(db, filters, q: SearchQuery, is_pg: bool) -> tuple[list[Record], int]:
    target = normalize_name(q.name or q.q or "").normalized
    if is_pg:
        stmt = (
            select(Record)
            .where(and_(*filters, Record.normalized_name.isnot(None)))
            .where(text("similarity(normalized_name, :t) > 0.3"))
            .params(t=target)
            .order_by(text("similarity(normalized_name, :t) DESC"))
        )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.limit(q.limit).offset(q.offset)
        return list(db.execute(stmt).scalars()), total
    # SQLite: rank in Python with RapidFuzz.
    candidates = list(db.execute(select(Record).where(and_(*filters))).scalars())
    scored = [
        (r, fuzz.token_sort_ratio(target, r.normalized_name or ""))
        for r in candidates
        if r.normalized_name
    ]
    scored = [s for s in scored if s[1] >= 60]
    scored.sort(key=lambda x: x[1], reverse=True)
    total = len(scored)
    page = [r for r, _ in scored[q.offset : q.offset + q.limit]]
    return page, total


def _semantic_search(db, filters, q: SearchQuery) -> tuple[list[Record], int]:
    ai = get_ai_client()
    query_vec = ai.embed(q.q or q.name or "")
    candidates = list(db.execute(select(Record).where(and_(*filters))).scalars())
    scored = [
        (r, cosine_similarity(query_vec, list(r.embedding)))
        for r in candidates
        if r.embedding
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    total = len(scored)
    page = [r for r, _ in scored[q.offset : q.offset + q.limit]]
    return page, total
