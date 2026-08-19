"""
Integration tests for the ingestion pipeline.

All HTTP calls are mocked — the real Arbeitnow API is never called.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from app.services.ingestion import get_circuit_breaker, run_ingestion
from app.sources.base import (
    RawJob,
    SourceEmptyError,
    SourceRateLimitedError,
    SourceSchemaError,
    SourceUnavailableError,
)


def _make_source(jobs=None, raise_exc=None):
    """Create a mock JobSource for testing."""

    class _MockSource:
        source_name = "test"

        async def fetch_jobs(self):
            if raise_exc is not None:
                raise raise_exc
            return jobs or []

    return _MockSource()


def _sample_jobs(n: int) -> list[RawJob]:
    return [
        RawJob(
            external_id=f"job-{i:03d}",
            title=f"Job {i}",
            company="Test Corp",
            url=f"https://example.com/jobs/job-{i:03d}",
            source="test",
        )
        for i in range(n)
    ]


@pytest.mark.asyncio
class TestIngestionPipeline:
    async def test_successful_ingestion_returns_success_status(self, db_session):
        source = _make_source(jobs=_sample_jobs(5))
        result = await run_ingestion(source, db_session)
        assert result.status == "SUCCESS"
        assert result.records_fetched == 5
        assert result.records_accepted == 5
        assert result.duplicates == 0

    async def test_second_ingestion_detects_duplicates(self, db_session):
        source = _make_source(jobs=_sample_jobs(5))
        await run_ingestion(source, db_session)

        result = await run_ingestion(source, db_session)
        assert result.status == "SUCCESS"
        assert result.duplicates == 5
        assert result.records_accepted == 0

    async def test_empty_source_returns_empty_status(self, db_session):
        source = _make_source(raise_exc=SourceEmptyError("empty"))
        result = await run_ingestion(source, db_session)
        assert result.status == "EMPTY_SOURCE"
        assert result.records_fetched == 0

    async def test_empty_source_does_not_delete_existing_jobs(self, db_session):
        from app.models.job import Job

        # First: load 5 jobs
        source = _make_source(jobs=_sample_jobs(5))
        await run_ingestion(source, db_session)
        assert db_session.query(Job).count() == 5

        # Second: source is empty
        empty_source = _make_source(raise_exc=SourceEmptyError("empty"))
        await run_ingestion(empty_source, db_session)

        # Existing jobs must remain
        assert db_session.query(Job).count() == 5

    async def test_rate_limited_returns_rate_limited_status(self, db_session):
        source = _make_source(raise_exc=SourceRateLimitedError(retry_after=5.0))
        result = await run_ingestion(source, db_session)
        assert result.status == "RATE_LIMITED"

    async def test_schema_error_returns_schema_error_status(self, db_session):
        source = _make_source(raise_exc=SourceSchemaError("bad schema"))
        result = await run_ingestion(source, db_session)
        assert result.status == "SCHEMA_ERROR"

    async def test_unavailable_returns_failed_status(self, db_session):
        source = _make_source(raise_exc=SourceUnavailableError("down"))
        result = await run_ingestion(source, db_session)
        assert result.status == "FAILED"

    async def test_circuit_open_blocks_ingestion(self, db_session):
        cb = get_circuit_breaker()
        cb._state = __import__("app.services.circuit_breaker", fromlist=["CircuitState"]).CircuitState.OPEN
        cb._opened_at = __import__("time").monotonic()

        source = _make_source(jobs=_sample_jobs(3))
        result = await run_ingestion(source, db_session)
        assert result.status == "CIRCUIT_OPEN"
        assert result.records_fetched == 0

    async def test_run_is_recorded_in_db(self, db_session):
        from app.models.job import IngestionRun

        source = _make_source(jobs=_sample_jobs(3))
        result = await run_ingestion(source, db_session)

        run = db_session.query(IngestionRun).filter(IngestionRun.id == result.run_id).first()
        assert run is not None
        assert run.source == "test"
        assert run.status == "SUCCESS"
        assert run.records_fetched == 3
        assert run.records_accepted == 3

    async def test_failed_run_is_recorded_in_db(self, db_session):
        from app.models.job import IngestionRun

        source = _make_source(raise_exc=SourceUnavailableError("down"))
        result = await run_ingestion(source, db_session)

        run = db_session.query(IngestionRun).filter(IngestionRun.id == result.run_id).first()
        assert run is not None
        assert run.status == "FAILED"
        assert run.error_message is not None

    async def test_circuit_breaker_opens_after_repeated_failures(self, db_session):
        from app.services.circuit_breaker import CircuitState

        cb = get_circuit_breaker()
        cb.reset()
        cb.failure_threshold = 3

        source = _make_source(raise_exc=SourceUnavailableError("down"))
        for _ in range(3):
            await run_ingestion(source, db_session)

        assert cb.state == CircuitState.OPEN
