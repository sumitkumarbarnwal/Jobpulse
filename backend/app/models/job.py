"""
ORM models for the JobPulse database.

Two tables:
  - jobs:           Deduplicated, normalized job listings.
  - ingestion_runs: Audit log of every ingestion attempt with metrics.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Job(Base):
    """A normalized, deduplicated job listing."""

    __tablename__ = "jobs"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Deduplication key ─────────────────────────────────────────────────────
    # Stable unique identifier: "<source>:<external_id>" or a content hash.
    # UNIQUE constraint enforces deduplication at the database layer.
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Composite unique: the same job can come from multiple sources.
    # (We declare the unique index explicitly in __table_args__ below)

    # ── Core fields ───────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[str] = mapped_column(String(256), nullable=False)
    location: Mapped[str] = mapped_column(String(256), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # ── Timestamps ────────────────────────────────────────────────────────────
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # ── Deduplication hash ────────────────────────────────────────────────────
    # SHA-256 of stable content fields; used to detect duplicate slugs
    # when a provider doesn't expose a reliable external_id.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    __table_args__ = (
        # Composite unique on (source, external_id) — the deduplication key.
        {"sqlite_autoincrement": False},
    )


from sqlalchemy import UniqueConstraint  # noqa: E402

Job.__table_args__ = (
    UniqueConstraint("source", "external_id", name="uq_job_source_external_id"),
    {"sqlite_autoincrement": False},
)


class IngestionRun(Base):
    """Audit record of a single ingestion attempt."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    # Values: SUCCESS | WARNING | FAILED | RATE_LIMITED | SCHEMA_ERROR |
    #         EMPTY_SOURCE | CIRCUIT_OPEN | TIMEOUT
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # ── Metrics ───────────────────────────────────────────────────────────────
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_accepted: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    validation_failures: Mapped[int] = mapped_column(Integer, default=0)

    # ── HTTP details ──────────────────────────────────────────────────────────
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Error ─────────────────────────────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
