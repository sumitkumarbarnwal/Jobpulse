"""
Tests for deduplication logic in the ingestion pipeline.
"""
from __future__ import annotations

import pytest

from app.services.ingestion import _persist_jobs
from app.sources.base import RawJob


def _make_job(n: int, **kwargs) -> RawJob:
    return RawJob(
        external_id=f"job-{n:03d}",
        title=kwargs.get("title", f"Job {n}"),
        company=kwargs.get("company", "Test Corp"),
        url=kwargs.get("url", f"https://example.com/jobs/job-{n:03d}"),
        source=kwargs.get("source", "test"),
        remote=kwargs.get("remote", False),
    )


class TestDeduplication:
    def test_new_jobs_are_accepted(self, db_session):
        jobs = [_make_job(1), _make_job(2), _make_job(3)]
        accepted, dupes, failures = _persist_jobs(db_session, jobs, source="test")
        assert accepted == 3
        assert dupes == 0
        assert failures == 0

    def test_duplicate_jobs_are_not_inserted_twice(self, db_session):
        job = _make_job(1)
        # First insert
        accepted1, dupes1, _ = _persist_jobs(db_session, [job], source="test")
        assert accepted1 == 1
        assert dupes1 == 0

        # Second insert with same external_id
        accepted2, dupes2, _ = _persist_jobs(db_session, [job], source="test")
        assert accepted2 == 0
        assert dupes2 == 1

    def test_duplicate_count_is_accurate(self, db_session):
        jobs = [_make_job(i) for i in range(5)]
        _persist_jobs(db_session, jobs, source="test")

        # Re-ingest all 5 — all should be duplicates
        accepted, dupes, _ = _persist_jobs(db_session, jobs, source="test")
        assert accepted == 0
        assert dupes == 5

    def test_mixed_new_and_duplicate(self, db_session):
        # Insert jobs 1-3
        _persist_jobs(db_session, [_make_job(i) for i in range(1, 4)], source="test")

        # Re-ingest jobs 1-3 (dupes) + new jobs 4-5
        all_jobs = [_make_job(i) for i in range(1, 6)]
        accepted, dupes, _ = _persist_jobs(db_session, all_jobs, source="test")
        assert accepted == 2
        assert dupes == 3

    def test_same_external_id_different_source_are_separate(self, db_session):
        job_a = _make_job(1, source="source_a")
        job_b = RawJob(
            external_id="job-001",  # same external_id
            title="Job 1",
            company="Test Corp",
            url="https://example.com/jobs/job-001",
            source="source_b",  # different source
        )

        accepted_a, _, _ = _persist_jobs(db_session, [job_a], source="source_a")
        accepted_b, _, _ = _persist_jobs(db_session, [job_b], source="source_b")

        assert accepted_a == 1
        assert accepted_b == 1

    def test_jobs_missing_required_fields_are_rejected(self, db_session):
        from app.sources.base import RawJob as _RawJob

        # Create a job then manually clear required fields to simulate corrupt data
        job = _make_job(1)

        # Bypass Pydantic by manipulating the model object
        bad_job = job.model_copy(update={"title": ""})

        _, _, failures = _persist_jobs(db_session, [bad_job], source="test")
        assert failures == 1

    def test_total_job_count_in_db_is_correct(self, db_session):
        from app.models.job import Job

        jobs = [_make_job(i) for i in range(10)]
        _persist_jobs(db_session, jobs, source="test")

        count = db_session.query(Job).count()
        assert count == 10

        # Re-ingesting same set should not increase count
        _persist_jobs(db_session, jobs, source="test")
        count = db_session.query(Job).count()
        assert count == 10
