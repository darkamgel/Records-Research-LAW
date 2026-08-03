"""Thin OpenAI wrapper with deterministic fallbacks.

Every method degrades gracefully when no API key is configured so the whole app
keeps working in "deterministic mode". Embeddings fall back to a stable local
hashing embedding that is good enough for MVP semantic ranking without network.

Configuration can come from environment variables (default) or a per-workspace
UI-managed config (preferred for deployments).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Matches the pgvector column width so deterministic-mode vectors also fit the
# production Postgres schema.
EMBEDDING_DIM = 1536


@dataclass
class AIConfig:
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key.strip())

    @classmethod
    def from_env(cls) -> AIConfig:
        return cls(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            embedding_model=settings.openai_embedding_model,
        )


class AIClient:
    def __init__(self, config: AIConfig | None = None) -> None:
        self.config = config or AIConfig.from_env()
        self._client: Any | None = None
        self.enabled = self.config.enabled
        self.model = self.config.model
        self.embedding_model = self.config.embedding_model
        if self.enabled:
            try:
                from openai import OpenAI

                base_url = self.config.base_url.strip() or None
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=base_url,
                    timeout=30.0,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("OpenAI client init failed; falling back: %s", exc)
                self.enabled = False

    # ----------------------------------------------------------------- chat
    def structured_json(
        self, system: str, user: str, *, max_tokens: int = 800, retries: int = 2
    ) -> dict | None:
        """Return parsed JSON from a JSON-only completion, or None on failure."""
        if not self.enabled or self._client is None:
            return None
        last_err: Exception | None = None
        for _ in range(retries + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                    temperature=0.0,
                )
                content = resp.choices[0].message.content or "{}"
                return json.loads(content)
            except Exception as exc:  # pragma: no cover - network path
                last_err = exc
        logger.warning("structured_json failed after retries: %s", last_err)
        return None

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.4,
    ) -> str:
        """Plain chat completion for the in-app LLM test bot."""
        if not self.enabled or self._client is None:
            raise RuntimeError(
                "LLM is not configured. Add an API key under Settings → AI / LLM."
            )
        payload: list[dict[str, str]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(messages)
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=payload,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            raise RuntimeError(_friendly_llm_error(exc, self.config.base_url)) from exc
        return (resp.choices[0].message.content or "").strip()

    def ping(self) -> dict[str, Any]:
        """Minimal round-trip to verify credentials / model / base URL."""
        if not self.enabled or self._client is None:
            return {"ok": False, "error": "No API key configured"}
        try:
            reply = self.chat(
                [{"role": "user", "content": "Reply with exactly: OK"}],
                system="You are a connectivity test. Reply with exactly the word OK.",
                max_tokens=16,
                temperature=0.0,
            )
            return {
                "ok": True,
                "model": self.model,
                "base_url": self.config.base_url or "(official OpenAI)",
                "reply": reply[:200],
            }
        except Exception as exc:  # pragma: no cover - network path
            return {
                "ok": False,
                "error": _friendly_llm_error(exc, self.config.base_url),
                "model": self.model,
            }

    # ------------------------------------------------------------- embeddings
    def embed(self, text: str) -> list[float]:
        if self.enabled and self._client is not None:
            try:  # pragma: no cover - network path
                resp = self._client.embeddings.create(
                    model=self.embedding_model, input=text[:8000]
                )
                return resp.data[0].embedding
            except Exception as exc:
                logger.warning("embedding failed, using local fallback: %s", exc)
        return local_embedding(text)


def _friendly_llm_error(exc: Exception, base_url: str) -> str:
    """Turn raw provider errors (often HTML 404 pages) into actionable guidance."""
    text = str(exc)
    looks_like_html = "<!DOCTYPE html" in text or "<html" in text.lower()
    if looks_like_html or "portal.apps." in (base_url or ""):
        return (
            "The Base URL looks like a web portal, not an OpenAI-compatible API. "
            "Open your provider’s “Endpoint quickstart”, copy the API base URL "
            "(usually like https://…/v1/api/<endpoint-id>), and paste it under "
            "Settings → AI / LLM. Current base URL: "
            f"{base_url or '(empty)'}."
        )
    if "incorrect api key" in text.lower() or "invalid_api_key" in text.lower():
        if not (base_url or "").strip():
            return (
                "Your key was sent to the official OpenAI API because Base URL is empty. "
                "ConfidentialMind / cm_api_ keys need a Base URL from the portal "
                "(Models or Endpoint quickstart → copy the endpoint API URL, e.g. "
                "https://…/v1/api/<endpoint-id>). Also set the Chat model to the "
                "Resource ID from the key’s Grants (e.g. mistral-medium-3-5-128b)."
            )
        return (
            "API key rejected by the server at this Base URL. Confirm the key is "
            "ACTIVE, has Invoke grant on the model, and that Base URL matches the "
            "endpoint that issued the key."
        )
    # Keep other errors short for the UI.
    return text[:400]


def local_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:  # noqa: C901
    """Deterministic bag-of-words hashing embedding, L2-normalized."""
    vec = [0.0] * dim
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    for tok in tokens:
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


_ai_client: AIClient | None = None


def get_ai_client(config: AIConfig | None = None) -> AIClient:
    """Return an AI client.

    - With ``config``: always build a fresh client for that config.
    - Without: return a process-wide client from environment variables (tests/dev).
    """
    if config is not None:
        return AIClient(config)
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client
