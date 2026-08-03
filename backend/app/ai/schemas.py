"""Pydantic schemas for validating LLM structured output.

An LLM response is never persisted unless it validates against one of these.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError


class LLMPerson(BaseModel):
    name: str


class LLMOrg(BaseModel):
    name: str


class LLMAddress(BaseModel):
    text: str


class LLMDate(BaseModel):
    text: str


class LLMExtraction(BaseModel):
    people: list[LLMPerson] = Field(default_factory=list)
    organizations: list[LLMOrg] = Field(default_factory=list)
    addresses: list[LLMAddress] = Field(default_factory=list)
    dates: list[LLMDate] = Field(default_factory=list)
    case_numbers: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)


class LLMMatchExplanation(BaseModel):
    rationale: str


class LLMSummary(BaseModel):
    summary_markdown: str
    cited_record_ids: list[str] = Field(default_factory=list)


def safe_validate(model: type[BaseModel], data: dict | None):
    """Validate and return the model instance, or None on any failure."""
    if not data:
        return None
    try:
        return model.model_validate(data)
    except ValidationError:
        return None
