"""Enumerations shared across models and schemas."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    researcher = "researcher"
    reviewer = "reviewer"


class SourceType(str, enum.Enum):
    file_upload = "file_upload"
    json_api = "json_api"
    rss = "rss"
    demo = "demo"


class AccessMethod(str, enum.Enum):
    user_upload = "user_upload"
    official_api = "official_api"
    bulk_download = "bulk_download"
    rss_feed = "rss_feed"
    sample_data = "sample_data"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class ProcessingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class ReviewStatus(str, enum.Enum):
    not_reviewed = "not_reviewed"
    confirmed = "confirmed"
    rejected = "rejected"
    needs_more_info = "needs_more_info"
    duplicate = "duplicate"


class MatchCategory(str, enum.Enum):
    unlikely = "unlikely"
    possible = "possible"
    probable = "probable"
    strong = "strong"


class DatePrecision(str, enum.Enum):
    exact = "exact"
    partial = "partial"
    range = "range"
    unknown = "unknown"


class AuditAction(str, enum.Enum):
    login = "login"
    logout = "logout"
    register = "register"
    import_records = "import_records"
    upload_file = "upload_file"
    delete_record = "delete_record"
    search = "search"
    ai_operation = "ai_operation"
    generate_candidates = "generate_candidates"
    review_match = "review_match"
    create_project = "create_project"
    generate_report = "generate_report"
    save_search = "save_search"
