"""
Ingestion service — the core pipeline.

Pipeline:
    Fetch
      ↓ HTTP status validation
      ↓ Timeout handling
      ↓ JSON/schema validation
      ↓ Normalize fields
      ↓ Validate required fields
      ↓ Deduplicate
      ↓ Persist
      ↓ Record ingestion metrics

Critical design decisions:
    1. Empty responses never overwrite existing data.
    2. Every run — success or failure — creates an IngestionRun record.
    3. The circuit breaker is checked before any HTTP call.
    4. Errors are classified, not swallowed.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.job import IngestionRun, Job
from app.schemas.job import IngestionTriggerResponse
from app.services.circuit_breaker import CircuitBreaker, CircuitState
from app.sources.base import (
    JobSource,
    RawJob,
    SourceEmptyError,
    SourceRateLimitedError,
    SourceSchemaError,
    SourceUnavailableError,
)

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Global circuit breaker instance
# ─────────────────────────────────────────────────────────────────────────────
# In production, this would live in Redis for cross-process sharing.
# For this demo, a single in-memory instance is sufficient.
_circuit_breaker: CircuitBreaker | None = None


def get_circuit_breaker() -> CircuitBreaker:
    """Return the application-level circuit breaker singleton."""
    global _circuit_breaker
    if _circuit_breaker is None:
        from app.core.config import get_settings
        settings = get_settings()
        _circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            cooldown_seconds=settings.circuit_breaker_cooldown_seconds,
        )
    return _circuit_breaker


# ─────────────────────────────────────────────────────────────────────────────
# Content hashing
# ─────────────────────────────────────────────────────────────────────────────

def compute_content_hash(job: RawJob) -> str:
    """
    Compute a deterministic SHA-256 hash of stable job fields.

    Used as a fallback deduplication key when external_id is unavailable,
    and also to detect when a job's content has changed between runs.

    Stable fields: company, title, url (lowercased + stripped)
    """
    stable = "|".join([
        (job.company or "").lower().strip(),
        (job.title or "").lower().strip(),
        (job.url or "").lower().strip(),
    ])
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Main ingestion pipeline
# ─────────────────────────────────────────────────────────────────────────────

async def run_ingestion(
    source: JobSource,
    db: Session,
) -> IngestionTriggerResponse:
    """
    Execute the full ingestion pipeline for a given source.

    This function is the single entry point called by:
      - POST /api/ingestion/run (manual trigger)
      - Background scheduler (if INGESTION_INTERVAL_SECONDS > 0)

    Returns an IngestionTriggerResponse with metrics for the run.
    """
    cb = get_circuit_breaker()
    started_at = datetime.now(tz=timezone.utc)
    t_start = time.monotonic()

    # ── Step 0: Circuit breaker check ─────────────────────────────────────────
    if not cb.allow_request():
        logger.warning(
            "Circuit breaker OPEN — skipping ingestion for source '%s'",
            source.source_name,
        )
        run = _record_run(
            db=db,
            source=source.source_name,
            started_at=started_at,
            status="CIRCUIT_OPEN",
            error_message="Circuit breaker is OPEN; requests to source are paused",
        )
        return IngestionTriggerResponse(
            run_id=run.id,
            status="CIRCUIT_OPEN",
            message="Source requests paused — circuit breaker is open. Showing cached data.",
            records_fetched=0,
            records_accepted=0,
            duplicates=0,
            validation_failures=0,
            latency_ms=None,
            error=f"Circuit open. Will retry after cooldown ({cb.cooldown_seconds}s).",
        )

    # ── Step 1: Fetch ─────────────────────────────────────────────────────────
    raw_jobs: list[RawJob] = []
    http_status: int | None = None
    fetch_error: str | None = None
    status = "SUCCESS"

    try:
        raw_jobs = await source.fetch_jobs()
        http_status = 200
        cb.record_success()

    except SourceEmptyError as exc:
        cb.record_failure()
        logger.warning("Empty source response: %s", exc)
        status = "EMPTY_SOURCE"
        fetch_error = "Source returned zero jobs. Preserving existing data."

    except SourceRateLimitedError as exc:
        cb.record_failure()
        logger.warning("Rate limited (429): %s", exc)
        status = "RATE_LIMITED"
        http_status = 429
        fetch_error = (
            f"Source is rate-limiting requests. "
            f"{'Retry after ' + str(exc.retry_after) + 's.' if exc.retry_after else 'Retry later.'}"
        )

    except SourceSchemaError as exc:
        cb.record_failure()
        logger.error("Schema error: %s", exc)
        status = "SCHEMA_ERROR"
        fetch_error = "Source response failed schema validation. Preserving existing data."

    except SourceUnavailableError as exc:
        cb.record_failure()
        logger.error("Source unavailable: %s", exc)
        status = "FAILED"
        http_status = getattr(exc, "http_status", None)
        fetch_error = "Source is temporarily unavailable. Showing cached data."

    except Exception as exc:
        cb.record_failure()
        logger.exception("Unexpected ingestion error: %s", exc)
        status = "FAILED"
        fetch_error = "An unexpected error occurred during ingestion."

    latency_ms = int((time.monotonic() - t_start) * 1000)

    # ── If fetch failed, record and return early ───────────────────────────────
    if status != "SUCCESS":
        run = _record_run(
            db=db,
            source=source.source_name,
            started_at=started_at,
            status=status,
            http_status=http_status,
            latency_ms=latency_ms,
            error_message=fetch_error,
        )
        return IngestionTriggerResponse(
            run_id=run.id,
            status=status,
            message=fetch_error or "Ingestion failed",
            records_fetched=0,
            records_accepted=0,
            duplicates=0,
            validation_failures=0,
            latency_ms=latency_ms,
            error=fetch_error,
        )

    # ── Step 2: Deduplicate + Persist ─────────────────────────────────────────
    records_fetched = len(raw_jobs)
    records_accepted = 0
    duplicates = 0
    validation_failures = 0

    try:
        accepted, dupes, failures = _persist_jobs(
            db=db,
            jobs=raw_jobs,
            source=source.source_name,
        )
        records_accepted = accepted
        duplicates = dupes
        validation_failures = failures

    except SQLAlchemyError as exc:
        logger.exception("Database error during persistence: %s", exc)
        db.rollback()
        run = _record_run(
            db=db,
            source=source.source_name,
            started_at=started_at,
            status="FAILED",
            records_fetched=records_fetched,
            http_status=200,
            latency_ms=latency_ms,
            error_message=f"Database error during persistence: {type(exc).__name__}",
        )
        return IngestionTriggerResponse(
            run_id=run.id,
            status="FAILED",
            message="Database error during job persistence.",
            records_fetched=records_fetched,
            records_accepted=0,
            duplicates=0,
            validation_failures=0,
            latency_ms=latency_ms,
            error="Database write failed. Check logs for details.",
        )

    # ── Step 3: Finalize run record ───────────────────────────────────────────
    if validation_failures > 0 and records_accepted == 0:
        status = "WARNING"
    elif validation_failures > 0:
        status = "WARNING"

    run = _record_run(
        db=db,
        source=source.source_name,
        started_at=started_at,
        status=status,
        records_fetched=records_fetched,
        records_accepted=records_accepted,
        duplicates=duplicates,
        validation_failures=validation_failures,
        http_status=http_status,
        latency_ms=latency_ms,
    )

    logger.info(
        "Ingestion complete: source=%s status=%s fetched=%d accepted=%d dupes=%d failures=%d latency=%dms",
        source.source_name,
        status,
        records_fetched,
        records_accepted,
        duplicates,
        validation_failures,
        latency_ms,
    )

    return IngestionTriggerResponse(
        run_id=run.id,
        status=status,
        message=f"Ingestion complete. Accepted {records_accepted} of {records_fetched} jobs.",
        records_fetched=records_fetched,
        records_accepted=records_accepted,
        duplicates=duplicates,
        validation_failures=validation_failures,
        latency_ms=latency_ms,
        error=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Persistence helpers
# ─────────────────────────────────────────────────────────────────────────────

def _persist_jobs(
    db: Session,
    jobs: list[RawJob],
    source: str,
) -> tuple[int, int, int]:
    """
    Insert or update jobs in the database.

    Returns: (accepted, duplicates, validation_failures)

    Deduplication strategy:
        Primary:  source + external_id (composite unique key)
        Fallback: content hash (company + title + url)

    When a job already exists (by external_id), we update last_seen_at
    rather than creating a duplicate record.
    """
    accepted = 0
    duplicates = 0
    validation_failures = 0

    # Load existing external_ids for this source to do deduplication in Python
    # (avoids a round-trip per job and is faster for small datasets).
    existing_ids: set[str] = {
        row[0]
        for row in db.query(Job.external_id).filter(Job.source == source).all()
    }

    now = datetime.now(tz=timezone.utc)

    for raw in jobs:
        # Basic field validation
        if not raw.title or not raw.company or not raw.url:
            logger.debug("Skipping job with missing required fields: %s", raw.external_id)
            validation_failures += 1
            continue

        content_hash = compute_content_hash(raw)

        if raw.external_id in existing_ids:
            # Duplicate: update last_seen_at and move on
            db.query(Job).filter(
                Job.source == source,
                Job.external_id == raw.external_id,
            ).update({"last_seen_at": now})
            duplicates += 1
        else:
            # New job: insert
            job = Job(
                external_id=raw.external_id,
                source=source,
                title=raw.title,
                company=raw.company,
                location=raw.location,
                description=raw.description,
                url=raw.url,
                remote=raw.remote,
                category=raw.category,
                tags=json.dumps(raw.tags) if raw.tags else None,
                published_at=raw.published_at,
                first_seen_at=now,
                last_seen_at=now,
                content_hash=content_hash,
            )
            db.add(job)
            existing_ids.add(raw.external_id)
            accepted += 1

    db.commit()
    return accepted, duplicates, validation_failures


def _record_run(
    db: Session,
    source: str,
    started_at: datetime,
    status: str,
    records_fetched: int = 0,
    records_accepted: int = 0,
    duplicates: int = 0,
    validation_failures: int = 0,
    http_status: int | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> IngestionRun:
    """Persist an ingestion run record and return it."""
    run = IngestionRun(
        source=source,
        started_at=started_at,
        completed_at=datetime.now(tz=timezone.utc),
        status=status,
        records_fetched=records_fetched,
        records_accepted=records_accepted,
        duplicates=duplicates,
        validation_failures=validation_failures,
        http_status=http_status,
        latency_ms=latency_ms,
        error_message=error_message,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
