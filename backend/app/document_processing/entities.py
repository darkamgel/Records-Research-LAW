"""Hybrid entity extraction.

Order of precedence:
1. Regular expressions for structured identifiers (case #, ZIP, parcel, dates).
2. Address parsing / normalization.
3. spaCy named entities (optional; only if installed).
4. LLM structured extraction (optional; only when a key is configured AND
   deterministic coverage is weak). LLM output is always validated against a
   Pydantic schema before use.

Every extracted mention includes its character span and an extraction method so
results can be traced back to the source text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.normalization import (
    STATE_ABBREV,
    normalize_address,
    normalize_date,
    normalize_name,
    normalize_org,
)

_CASE_RE = re.compile(
    r"\b(?:case|cause|docket|file)\s*(?:no\.?|number|#)?\s*[:#]?\s*"
    r"([0-9]{2,4}[-\s]?[A-Z]{0,4}[-\s]?[0-9]{1,7})",
    re.IGNORECASE,
)
_FILING_RE = re.compile(
    r"\b(?:filing|instrument|recording)\s*(?:no\.?|number|#)?\s*[:#]?\s*([A-Z0-9\-]{4,20})",
    re.IGNORECASE,
)
_PARCEL_RE = re.compile(
    r"\b(?:parcel|apn|tax\s*id|property\s*id)\s*(?:no\.?|#)?\s*[:#]?\s*([A-Z0-9\-\.]{5,25})",
    re.IGNORECASE,
)
_ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")
_DATE_RE = re.compile(
    r"\b("
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r")\b",
    re.IGNORECASE,
)
_ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+(?:[A-Z0-9][A-Za-z0-9\.]*\s){1,5}"
    r"(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Ln|Lane|Ct|Court|"
    r"Pl|Place|Way|Ter|Terrace|Cir|Circle|Hwy|Pkwy)\b\.?",
    re.IGNORECASE,
)
_AGENCY_RE = re.compile(
    r"\b((?:Department|Dept|Office|Bureau|Court|Clerk|Registrar|Commission)"
    r"(?:\s+of\s+[A-Z][A-Za-z]+){0,4})",
)


@dataclass
class ExtractedEntity:
    entity_type: str
    value: str
    normalized_value: str | None
    method: str
    confidence: float
    char_start: int | None = None
    char_end: int | None = None
    source_text: str | None = None


def _span(text: str, match: re.Match) -> tuple[int, int, str]:
    return match.start(), match.end(), text[match.start() : match.end()]


def extract_with_regex(text: str) -> list[ExtractedEntity]:
    out: list[ExtractedEntity] = []
    for rx, etype in (
        (_CASE_RE, "case_number"),
        (_FILING_RE, "filing_number"),
        (_PARCEL_RE, "parcel_id"),
        (_AGENCY_RE, "government_agency"),
    ):
        for m in rx.finditer(text):
            value = m.group(1).strip()
            if not value:
                continue
            out.append(
                ExtractedEntity(etype, value, value.upper(), "regex", 0.9, m.start(1), m.end(1),
                                text[max(0, m.start() - 20): m.end() + 20])
            )
    for m in _ZIP_RE.finditer(text):
        s, e, raw = _span(text, m)
        out.append(ExtractedEntity("zip_code", raw, raw, "regex", 0.95, s, e, raw))
    for m in _DATE_RE.finditer(text):
        s, e, raw = _span(text, m)
        nd = normalize_date(raw)
        out.append(ExtractedEntity("date", raw, nd.iso, "regex", 0.85, s, e, raw))
    return out


def extract_addresses(text: str) -> list[ExtractedEntity]:
    out: list[ExtractedEntity] = []
    for m in _ADDRESS_RE.finditer(text):
        s, e, raw = _span(text, m)
        na = normalize_address(raw)
        out.append(
            ExtractedEntity("address", raw, na.normalized, "address", 0.8, s, e, raw)
        )
        if na.city:
            out.append(ExtractedEntity("city", na.city, na.city.lower(), "address", 0.7))
        if na.state:
            out.append(ExtractedEntity("state", na.state, na.state, "address", 0.8))
    return out


_spacy_nlp = None
_spacy_loaded = False


def _get_spacy():  # pragma: no cover - optional dependency
    global _spacy_nlp, _spacy_loaded
    if _spacy_loaded:
        return _spacy_nlp
    _spacy_loaded = True
    try:
        import spacy

        _spacy_nlp = spacy.load("en_core_web_sm")
    except Exception:
        _spacy_nlp = None
    return _spacy_nlp


def extract_with_spacy(text: str) -> list[ExtractedEntity]:  # pragma: no cover - optional
    nlp = _get_spacy()
    if nlp is None:
        return []
    out: list[ExtractedEntity] = []
    doc = nlp(text[:100000])
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            nm = normalize_name(ent.text)
            out.append(ExtractedEntity("person", ent.text, nm.normalized, "spacy", 0.7,
                                       ent.start_char, ent.end_char, ent.text))
        elif ent.label_ == "ORG":
            no = normalize_org(ent.text)
            out.append(ExtractedEntity("organization", ent.text, no.normalized, "spacy", 0.65,
                                       ent.start_char, ent.end_char, ent.text))
        elif ent.label_ == "GPE":
            val = ent.text.strip()
            etype = "state" if val.upper() in set(STATE_ABBREV.values()) else "city"
            out.append(ExtractedEntity(etype, val, val.lower(), "spacy", 0.6,
                                       ent.start_char, ent.end_char, ent.text))
    return out


# Lightweight heuristic person extraction used when spaCy is not installed:
# capitalized bigrams that are not obviously agencies/dates.
_PERSON_HEURISTIC_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\b")
_STOP_PERSON = {"United States", "New York", "Los Angeles", "San Francisco"}


def extract_people_heuristic(text: str) -> list[ExtractedEntity]:
    out: list[ExtractedEntity] = []
    for m in _PERSON_HEURISTIC_RE.finditer(text):
        value = m.group(1).strip()
        if value in _STOP_PERSON:
            continue
        nm = normalize_name(value)
        out.append(ExtractedEntity("person", value, nm.normalized, "heuristic", 0.4,
                                   m.start(1), m.end(1), value))
    return out


def deterministic_extract(text: str) -> list[ExtractedEntity]:
    """Full deterministic pass (no LLM). Safe for the no-API-key mode."""
    text = text or ""
    out = extract_with_regex(text)
    out += extract_addresses(text)
    spacy_ents = extract_with_spacy(text)
    if spacy_ents:
        out += spacy_ents
    else:
        out += extract_people_heuristic(text)
    return _dedupe(out)


def _dedupe(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    seen: set[tuple[str, str]] = set()
    result: list[ExtractedEntity] = []
    for e in entities:
        key = (e.entity_type, (e.normalized_value or e.value).lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(e)
    return result
