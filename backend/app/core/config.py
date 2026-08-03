"""Application configuration loaded from environment variables.

Configuration is intentionally environment-driven (12-factor). No secrets are
hard-coded. When ``OPENAI_API_KEY`` is empty the application runs in a
deterministic, local-only mode (see ``Settings.ai_enabled``).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_env: str = "development"
    app_name: str = "Public Records Research MVP"
    app_secret_key: str = "insecure-dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24
    jwt_algorithm: str = "HS256"

    # Database. Defaults to a local sqlite file so the app/tests can run without
    # a Postgres instance. Docker compose overrides this with Postgres.
    database_url: str = "sqlite+pysqlite:///./records.db"

    # Redis + Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False

    # OpenAI (optional). ``openai_base_url`` lets you point at any
    # OpenAI-compatible server (e.g. a self-hosted / custom-OpenAI endpoint).
    # Leave it empty to use the official OpenAI API.
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Uploads / processing
    max_upload_size_mb: int = 25
    upload_dir: str = "./data/uploads"
    ocr_enabled: bool = True

    # CORS. ``NoDecode`` stops pydantic-settings from JSON-decoding the raw env
    # value so the validator below can accept a plain comma-separated string.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def ai_enabled(self) -> bool:
        """True when an OpenAI key is configured. Gates all LLM calls."""
        return bool(self.openai_api_key.strip())

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
