from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    q: str | None = None
    mode: str = Field(default="keyword", description="keyword|fulltext|semantic|fuzzy_name|exact_name")
    name: str | None = None
    address: str | None = None
    case_number: str | None = None
    jurisdiction: str | None = None
    source_id: str | None = None
    record_type: str | None = None
    state: str | None = None
    city: str | None = None
    zip_code: str | None = None
    filing_date_from: date | None = None
    filing_date_to: date | None = None
    is_demo: bool | None = None
    limit: int = Field(default=25, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    sort: str = Field(default="created_at", description="created_at|filing_date|title|relevance")
    sort_dir: str = Field(default="desc")
