"""
Provider-agnostic source interface.

Any job source (Arbeitnow, RSS feed, sandbox, etc.) must implement
the JobSource Protocol.  The rest of the application only depends on
this interface — never on a concrete adapter.

Adding a new source:
    1. Create a new file under app/sources/
    2. Implement a class that satisfies JobSource
    3. Register it in app/sources/factory.py

Nothing else needs to change.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Normalized internal job representation
# ─────────────────────────────────────────────────────────────────────────────

class RawJob(BaseModel):
    """
    Normalized job record produced by any source adapter.

    Every adapter must map its provider-specific response into this model.
    The ingestion service only deals with RawJob objects — never with raw
    API responses.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Required
    external_id: str
    title: str
    company: str
    url: str
    source: str

    # Optional (provider may not supply all of these)
    location: str | None = None
    description: str | None = None
    remote: bool = False
    category: str | None = None
    tags: list[str] = []
    published_at: datetime | None = None

    @field_validator("title", "company", "url", "external_id", mode="before")
    @classmethod
    def must_not_be_empty(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            raise ValueError("field must not be empty")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Protocol
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class JobSource(Protocol):
    """
    Interface that every source adapter must satisfy.

    The ingestion service calls ``fetch_jobs()`` and receives a list of
    RawJob objects.  It does not know or care which provider is behind it.
    """

    source_name: str  # e.g. "arbeitnow", "mock"

    async def fetch_jobs(self) -> list[RawJob]:
        """
        Fetch raw jobs from the source.

        Raises:
            httpx.TimeoutException: if the request timed out.
            httpx.HTTPStatusError: if the server returned a non-2xx response
                that the adapter decided not to retry.
            SourceEmptyError: if the source returned an empty dataset.
            SourceSchemaError: if the response cannot be parsed.
        """
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Custom exceptions raised by adapters
# ─────────────────────────────────────────────────────────────────────────────

class SourceError(Exception):
    """Base class for source-level errors."""
    http_status: int | None = None


class SourceEmptyError(SourceError):
    """The source returned zero jobs (unexpected)."""


class SourceSchemaError(SourceError):
    """The source returned a response that failed schema validation."""


class SourceRateLimitedError(SourceError):
    """HTTP 429: server is rate-limiting us."""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limited; retry_after={retry_after}")
    http_status = 429


class SourceUnavailableError(SourceError):
    """The source is currently unreachable (5xx, timeout, network error)."""
    http_status: int | None = None
