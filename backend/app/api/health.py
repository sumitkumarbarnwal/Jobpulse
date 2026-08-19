"""
Health check endpoint.

GET /health

Returns overall system health. Reports unhealthy if the database
is unavailable — we never lie about the system state.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import SessionLocal
from app.models.job import IngestionRun, Job
from app.schemas.job import HealthOut
from app.services.ingestion import get_circuit_breaker
from app.sources.factory import get_source

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthOut)
def health_check():
    """
    System health check.

    Status values:
        ok       — Database connected, system normal
        degraded — Database connected but source has issues
        error    — Database unavailable
    """
    source = get_source()
    db_status = "connected"
    jobs_stored = 0
    last_successful_ingestion: datetime | None = None

    try:
        db = SessionLocal()
        try:
            jobs_stored = db.query(Job).count()
            last_run = (
                db.query(IngestionRun)
                .filter(IngestionRun.status == "SUCCESS")
                .order_by(IngestionRun.completed_at.desc())
                .first()
            )
            if last_run:
                last_successful_ingestion = last_run.completed_at
        finally:
            db.close()
    except SQLAlchemyError:
        db_status = "error"

    cb = get_circuit_breaker()
    if db_status == "error":
        overall = "error"
    elif cb.state.value == "OPEN":
        overall = "degraded"
    else:
        overall = "ok"

    status_code = 200 if overall in ("ok", "degraded") else 503

    payload = HealthOut(
        status=overall,
        database=db_status,
        source=source.source_name,
        last_successful_ingestion=last_successful_ingestion,
        jobs_stored=jobs_stored,
    )

    return JSONResponse(
        content=payload.model_dump(mode="json"),
        status_code=status_code,
    )
