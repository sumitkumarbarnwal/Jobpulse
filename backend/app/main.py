"""
FastAPI application entry point.

Registers:
  - CORS middleware
  - API routers
  - Mock source router (always mounted, only useful when JOB_SOURCE=mock)
  - Lifespan: database initialization

Environment variables are read from .env via app/core/config.py.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, ingestion, jobs
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.database import init_db
from app.sources.mock import mock_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs setup before first request, teardown on shutdown."""
    configure_logging()
    settings = get_settings()
    logger.info("JobPulse starting up — source=%s env=%s", settings.job_source, settings.app_env)

    # Create database tables
    init_db()
    logger.info("Database initialized")

    yield

    logger.info("JobPulse shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="JobPulse API",
        description=(
            "Resilient job ingestion monitor. "
            "Fetches public job listings, validates, deduplicates, and exposes them "
            "through a clean REST API."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In production, set CORS_ORIGINS to your actual frontend domain.
    # Wildcard "*" is acceptable only for fully public read-only APIs.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(jobs.router)
    app.include_router(ingestion.router)
    app.include_router(mock_router)  # /mock-source/jobs — for HTTP-level testing

    return app


app = create_app()
