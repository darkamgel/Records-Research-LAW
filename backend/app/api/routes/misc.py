from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok", "ai_enabled": settings.ai_enabled, "env": settings.app_env}


@router.get("/compliance")
def compliance_notice():
    return {
        "title": "Responsible Use & Compliance Notice",
        "summary": (
            "This is a research productivity tool that operates only on publicly "
            "available or user-uploaded information. It does not make identity "
            "determinations."
        ),
        "restrictions": [
            "Does not bypass authentication, CAPTCHAs, or rate limits.",
            "Does not scrape sources that prohibit automated access.",
            "Prefers official APIs, bulk downloads, RSS feeds, and public exports.",
            "Preserves source provenance for every record.",
            "AI summaries and match suggestions are clearly labeled.",
            "Does not infer protected characteristics or use facial recognition.",
            "Not for legal, employment, housing, credit, insurance, immigration, "
            "educational, or law-enforcement decisions.",
            "All potential matches require human review; nothing is auto-confirmed.",
        ],
        "ai_mode": "enabled" if settings.ai_enabled else "deterministic (no API key)",
    }
