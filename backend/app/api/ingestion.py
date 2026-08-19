"""
Ingestion control and observability endpoints.

GET  /api/ingestion/status  — Current source health + metrics summary
GET  /api/ingestion/runs    — Recent ingestion run history
POST /api/ingestion/run     — Manually trigger an ingestion run
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.job import IngestionRun, Job
from app.schemas.job import (
    IngestionRunOut,
    IngestionStatusOut,
    IngestionTriggerResponse,
    LastRunSummary,
)
from app.services.circuit_breaker import CircuitState
from app.services.ingestion import get_circuit_breaker, run_ingestion
from app.sources.factory import get_source

router = APIRouter(prefix="/api/ingestion", tags=["Ingestion"])

# Simple lock to prevent concurrent ingestion runs
_ingestion_lock = asyncio.Lock()


@router.get("/status", response_model=IngestionStatusOut)
def ingestion_status(db: Session = Depends(get_db)):
    """
    Return current ingestion status and source health.

    This is the primary endpoint polled by the dashboard.
    """
    cb = get_circuit_breaker()
    source = get_source()

    # Last successful run
    last_success: IngestionRun | None = (
        db.query(IngestionRun)
        .filter(
            IngestionRun.source == source.source_name,
            IngestionRun.status == "SUCCESS",
        )
        .order_by(IngestionRun.completed_at.desc())
        .first()
    )

    # Last run (any status)
    last_run_record: IngestionRun | None = (
        db.query(IngestionRun)
        .filter(IngestionRun.source == source.source_name)
        .order_by(IngestionRun.completed_at.desc())
        .first()
    )

    jobs_stored = db.query(Job).count()

    # Determine overall status
    cb_state = cb.state
    if cb_state == CircuitState.OPEN:
        overall_status = "circuit_open"
    elif cb_state == CircuitState.HALF_OPEN:
        overall_status = "degraded"
    elif last_run_record and last_run_record.status not in ("SUCCESS", "WARNING"):
        overall_status = "degraded"
    elif jobs_stored == 0:
        overall_status = "no_data"
    else:
        overall_status = "healthy"

    # Cache age
    cache_age: float | None = None
    data_is_cached = False
    if last_success and last_success.completed_at:
        now = datetime.now(tz=timezone.utc)
        completed = last_success.completed_at
        if completed.tzinfo is None:
            completed = completed.replace(tzinfo=timezone.utc)
        cache_age = (now - completed).total_seconds()

        # Data is "cached" if last run wasn't a success
        if last_run_record and last_run_record.status != "SUCCESS":
            data_is_cached = True

    # Last run summary
    last_run_summary: LastRunSummary | None = None
    if last_run_record:
        rejected = last_run_record.validation_failures or 0
        last_run_summary = LastRunSummary(
            fetched=last_run_record.records_fetched or 0,
            accepted=last_run_record.records_accepted or 0,
            duplicates=last_run_record.duplicates or 0,
            rejected=rejected,
            latency_ms=last_run_record.latency_ms,
            status=last_run_record.status,
        )

    return IngestionStatusOut(
        source=source.source_name,
        status=overall_status,
        circuit_breaker_state=cb_state.value,
        last_successful_run=last_success.completed_at if last_success else None,
        last_run_at=last_run_record.completed_at if last_run_record else None,
        jobs_stored=jobs_stored,
        last_run=last_run_summary,
        data_is_cached=data_is_cached,
        cache_age_seconds=cache_age,
    )


@router.get("/runs", response_model=list[IngestionRunOut])
def ingestion_runs(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Return the most recent ingestion run records (newest first)."""
    runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [IngestionRunOut.model_validate(r) for r in runs]


@router.post("/run", response_model=IngestionTriggerResponse)
async def trigger_ingestion(
    source: str | None = None,
    scenario: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Manually trigger an ingestion run.

    Pass optional `source` ("arbeitnow" or "mock") and `scenario`
    ("normal", "empty", "rate_limited", "server_error", "malformed")
    to trigger specific resilience test scenarios directly from the UI.
    """
    if _ingestion_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="An ingestion run is already in progress. Please wait.",
        )

    async with _ingestion_lock:
        target_source = get_source(source_name=source, mock_scenario=scenario)
        return await run_ingestion(source=target_source, db=db)
