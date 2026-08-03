from __future__ import annotations

from app.document_processing.entities import deterministic_extract
from app.services.normalization import (
    normalize_address,
    normalize_date,
    normalize_name,
    normalize_org,
)


def test_name_normalization_orderings():
    a = normalize_name("Rivera, Jon A.")
    b = normalize_name("Jon A. Rivera")
    assert a.last == "rivera"
    assert a.first == "jon"
    assert a.normalized == b.normalized


def test_name_prefix_suffix():
    n = normalize_name("Dr. Margaret Chen Jr.")
    assert n.prefix.lower() == "dr"
    assert n.suffix.lower() == "jr"
    assert n.last == "chen"


def test_address_normalization_and_zip():
    a = normalize_address("482 Maple Street, Springfield, DX 55011")
    b = normalize_address("482 Maple St, Springfield, DX 55011")
    assert a.zip_code == "55011"
    assert "st" in a.normalized  # 'street' abbreviated to 'st'
    assert a.normalized == b.normalized


def test_date_precisions():
    assert normalize_date("2023-03-14").precision == "exact"
    assert normalize_date("2020").precision == "partial"
    assert normalize_date("2020 to 2021").precision == "range"
    assert normalize_date("").precision == "unknown"
    assert normalize_date("March 14, 2023").iso == "2023-03-14"


def test_org_normalization():
    a = normalize_org("Rivera Holdings, L.L.C.")
    b = normalize_org("Rivera Holdings LLC")
    assert a.normalized == b.normalized


def test_deterministic_entity_extraction_spans():
    text = "Case No. 2023-CV-004821 filed by Jonathan Rivera at 482 Maple Street, Springfield DX 55011 on 03/14/2023."
    ents = deterministic_extract(text)
    types = {e.entity_type for e in ents}
    assert "case_number" in types
    assert "zip_code" in types
    assert "date" in types
    # every mention keeps a char span or source text for traceability
    case = next(e for e in ents if e.entity_type == "case_number")
    assert case.char_start is not None and case.char_end is not None
