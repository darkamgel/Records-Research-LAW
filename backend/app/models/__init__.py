"""SQLAlchemy models. Importing this package registers all tables on ``Base``."""

from app.db.base import Base
from app.models.ai_settings import WorkspaceAIConfig
from app.models.audit import AuditLog
from app.models.entity import (
    Address,
    Entity,
    EntityMention,
    Organization,
    Person,
)
from app.models.matching import (
    MatchCandidate,
    MatchEvidence,
    RecordRelationship,
    ReviewDecision,
)
from app.models.record import (
    Document,
    DocumentChunk,
    DocumentPage,
    Record,
)
from app.models.research import (
    GeneratedReport,
    Note,
    ProjectRecord,
    ResearchHistory,
    ResearchProject,
    SavedSearch,
)
from app.models.source import (
    IngestionJob,
    Source,
    SourceConfiguration,
    UploadedFile,
)
from app.models.user import User, Workspace, WorkspaceMember

__all__ = [
    "Base",
    "User",
    "Workspace",
    "WorkspaceMember",
    "Source",
    "SourceConfiguration",
    "IngestionJob",
    "UploadedFile",
    "Record",
    "Document",
    "DocumentPage",
    "DocumentChunk",
    "Entity",
    "EntityMention",
    "Person",
    "Organization",
    "Address",
    "RecordRelationship",
    "MatchCandidate",
    "MatchEvidence",
    "ReviewDecision",
    "ResearchProject",
    "ProjectRecord",
    "SavedSearch",
    "ResearchHistory",
    "Note",
    "GeneratedReport",
    "AuditLog",
    "WorkspaceAIConfig",
]
