from __future__ import annotations

import io

CSV = (
    "id,name,record_type,case_number,filing_date,jurisdiction,address,description\n"
    "U-1,Jane Q Public,court_filing,2021-CV-1,2021-01-05,Demo County DX,"
    "10 Main St Springfield DX 55011,Test filing\n"
    "U-2,John Q Public,court_filing,2021-CV-2,2021-02-05,Demo County DX,"
    "12 Main St Springfield DX 55011,Another filing\n"
)


def _upload(client, auth, data: bytes, filename: str, content_type: str):
    return client.post(
        "/files/upload",
        headers=auth,
        files={"file": (filename, io.BytesIO(data), content_type)},
    )


def test_csv_upload_creates_records(client, auth):
    r = _upload(client, auth, CSV.encode(), "filings.csv", "text/csv")
    assert r.status_code == 201, r.text
    assert r.json()["processing_status"] == "completed"

    results = client.post("/records/search", headers=auth, json={"q": "Public"}).json()
    assert results["total"] == 2


def test_reject_unsupported_type(client, auth):
    r = _upload(client, auth, b"MZ\x00binary", "evil.exe", "application/octet-stream")
    assert r.status_code == 415


def test_duplicate_file_detected(client, auth):
    r1 = _upload(client, auth, CSV.encode(), "filings.csv", "text/csv")
    assert r1.status_code == 201
    r2 = _upload(client, auth, CSV.encode(), "filings-copy.csv", "text/csv")
    assert r2.status_code == 409  # same sha256


def test_empty_file_rejected(client, auth):
    r = _upload(client, auth, b"", "empty.csv", "text/csv")
    assert r.status_code == 400


def test_pdf_upload_extracts_text(client, auth):
    from app.tests.pdf_helpers import SAMPLE_TEXT_PDF

    r = _upload(client, auth, SAMPLE_TEXT_PDF, "filing.pdf", "application/pdf")
    assert r.status_code == 201, r.text
    docs = client.get("/documents", headers=auth).json()
    assert len(docs) == 1
    assert docs[0]["page_count"] == 1
    assert docs[0]["char_count"] > 50
    assert docs[0]["ocr_used"] is False
