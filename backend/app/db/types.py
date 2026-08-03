"""Portable SQLAlchemy column types.

These let the same ORM models run on PostgreSQL (production, via docker compose)
and SQLite (fast, dependency-free test runs). Postgres-specific features such as
``pgvector`` and JSONB are used when the dialect supports them, with graceful
fallbacks elsewhere.
"""

from __future__ import annotations

import enum as _enum
import json
import uuid
from typing import Any

from sqlalchemy import CHAR, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's native ``UUID`` type; otherwise stores as a 36-char string.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class JSONType(TypeDecorator):
    """JSONB on Postgres, JSON-encoded TEXT elsewhere."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.loads(value)


class Embedding(TypeDecorator):
    """Vector embedding column.

    On PostgreSQL this maps to ``pgvector``'s ``vector`` type when available so
    that ANN indexes can be added in production. Elsewhere the embedding is stored
    as JSON and cosine similarity is computed in Python (fine at MVP scale).
    """

    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 1536, *args: Any, **kwargs: Any) -> None:
        self.dim = dim
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector

                return dialect.type_descriptor(Vector(self.dim))
            except Exception:  # pragma: no cover - pgvector optional at runtime
                return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(list(value))

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value) if value is not None else None
        return json.loads(value)


class EnumType(TypeDecorator):
    """Store a Python ``str`` Enum by its value; return the Enum member on load.

    Portable across dialects (plain VARCHAR) and keeps ``.value`` usable on
    loaded instances, unlike a bare ``String`` column typed as ``Mapped[Enum]``.
    """

    impl = String
    cache_ok = True

    def __init__(self, enum_cls: type[_enum.Enum], length: int = 32, *a: Any, **k: Any) -> None:
        self.enum_cls = enum_cls
        super().__init__(length=length, *a, **k)

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, _enum.Enum):
            return value.value
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        try:
            return self.enum_cls(value)
        except ValueError:
            return value


def uuid_str(value: Any) -> str:
    return str(value)
