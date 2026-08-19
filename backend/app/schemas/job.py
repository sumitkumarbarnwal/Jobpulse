"""
Pydantic schemas for API responses.

These are intentionally separate from the ORM models so that:
  1. We control exactly what fields the API exposes.
  2. ORM internals (SQLAlchemy lazy-loading, etc.) stay out of API responses.
  3. Adding or renaming DB columns doesn't break the API contract.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# Job schemas
# ─────────────────────────────────────────────────────────────────────────────

class JobOut(BaseModel):
    """Job listing as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    source: str
    title: str
    company: str
    location: str | None
    description: str | None
    url: str
    remote: bool
    category: str | None
    tags: str | None  # JSON-encoded list; frontend parses it
    published_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime


class JobListResponse(BaseModel):
    """Paginated list of jobs."""

    jobs: list[JobOut]
    total: int
    page: int
    limit: int
    pages: int


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion schemas
# ─────────────────────────────────────────────────────────────────────────────

class IngestionRunOut(BaseModel):
    """Single ingestion run as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    records_fetched: int
    records_accepted: int
    duplicates: int
    validation_failures: int
    http_status: int | None
    latency_ms: int | None
    error_message: str | None


class LastRunSummary(BaseModel):
    fetched: int
    accepted: int
    duplicates: int
    rejected: int
    latency_ms: int | None
    status: str


class IngestionStatusOut(BaseModel):
    """Summary status for the /api/ingestion/status endpoint."""

    source: str
    status: str  # healthy | degraded | circuit_open | no_data
    circuit_breaker_state: str  # CLOSED | OPEN | HALF_OPEN
    last_successful_run: datetime | None
    last_run_at: datetime | None
    jobs_stored: int
    last_run: LastRunSummary | None
    data_is_cached: bool
    cache_age_seconds: float | None  # seconds since last successful run


class IngestionTriggerResponse(BaseModel):
    """Response from POST /api/ingestion/run."""

    run_id: int
    status: str
    message: str
    records_fetched: int
    records_accepted: int
    duplicates: int
    validation_failures: int
    latency_ms: int | None
    error: str | None


# ─────────────────────────────────────────────────────────────────────────────
# Health schema
# ─────────────────────────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status: str  # ok | degraded | error
    database: str  # connected | error
    source: str
    last_successful_ingestion: datetime | None
    jobs_stored: int
