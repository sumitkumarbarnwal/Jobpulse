"""
Tests for field normalization and content hashing.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

from app.services.ingestion import compute_content_hash
from app.sources.base import RawJob


class TestContentHashing:
    def test_hash_is_deterministic(self):
        job = RawJob(
            external_id="test-001",
            title="Python Engineer",
            company="Acme Corp",
            url="https://example.com/jobs/test-001",
            source="arbeitnow",
        )
        h1 = compute_content_hash(job)
        h2 = compute_content_hash(job)
        assert h1 == h2

    def test_hash_is_case_insensitive(self):
        job1 = RawJob(
            external_id="test-001",
            title="Python Engineer",
            company="Acme Corp",
            url="https://example.com/jobs/test-001",
            source="arbeitnow",
        )
        job2 = RawJob(
            external_id="test-001",
            title="PYTHON ENGINEER",
            company="ACME CORP",
            url="HTTPS://EXAMPLE.COM/JOBS/TEST-001",
            source="arbeitnow",
        )
        assert compute_content_hash(job1) == compute_content_hash(job2)

    def test_hash_differs_for_different_jobs(self):
        job1 = RawJob(
            external_id="test-001",
            title="Python Engineer",
            company="Acme Corp",
            url="https://example.com/jobs/test-001",
            source="arbeitnow",
        )
        job2 = RawJob(
            external_id="test-002",
            title="Go Engineer",
            company="Other Corp",
            url="https://example.com/jobs/test-002",
            source="arbeitnow",
        )
        assert compute_content_hash(job1) != compute_content_hash(job2)

    def test_hash_is_sha256(self):
        job = RawJob(
            external_id="test-001",
            title="Python Engineer",
            company="Acme Corp",
            url="https://example.com/jobs/test-001",
            source="arbeitnow",
        )
        h = compute_content_hash(job)
        assert len(h) == 64  # SHA-256 = 64 hex chars


class TestRawJobNormalization:
    def test_strips_whitespace(self):
        job = RawJob(
            external_id="  test-001  ",
            title="  Python Engineer  ",
            company="  Acme Corp  ",
            url="  https://example.com/  ",
            source="arbeitnow",
        )
        assert job.external_id == "test-001"
        assert job.title == "Python Engineer"
        assert job.company == "Acme Corp"
        assert job.url == "https://example.com/"

    def test_default_remote_is_false(self):
        job = RawJob(
            external_id="test-001",
            title="Engineer",
            company="Co",
            url="https://example.com",
            source="arbeitnow",
        )
        assert job.remote is False

    def test_default_tags_is_empty_list(self):
        job = RawJob(
            external_id="test-001",
            title="Engineer",
            company="Co",
            url="https://example.com",
            source="arbeitnow",
        )
        assert job.tags == []

    def test_requires_non_empty_title(self):
        with pytest.raises(Exception):
            RawJob(
                external_id="test-001",
                title="",
                company="Co",
                url="https://example.com",
                source="arbeitnow",
            )

    def test_requires_non_empty_company(self):
        with pytest.raises(Exception):
            RawJob(
                external_id="test-001",
                title="Engineer",
                company="",
                url="https://example.com",
                source="arbeitnow",
            )

    def test_optional_fields_can_be_none(self):
        job = RawJob(
            external_id="test-001",
            title="Engineer",
            company="Co",
            url="https://example.com",
            source="arbeitnow",
            location=None,
            description=None,
            category=None,
            published_at=None,
        )
        assert job.location is None
        assert job.description is None


class TestArbeitnowNormalization:
    """Test the Arbeitnow adapter's normalization logic."""

    def test_normalizes_arbeitnow_response(self, arbeitnow_200_response):
        """Test that Arbeitnow API items are correctly mapped to RawJob."""
        from app.sources.arbeitnow import ArbeitnowAdapter

        adapter = ArbeitnowAdapter()
        items = arbeitnow_200_response["data"]
        jobs = adapter._normalize(items)

        assert len(jobs) == 2

        first = jobs[0]
        assert first.external_id == "senior-python-engineer-acme-123"
        assert first.title == "Senior Python Engineer"
        assert first.company == "Acme Corp"
        assert first.location == "Berlin, Germany"
        assert first.remote is True
        assert "Python" in first.tags
        assert first.source == "arbeitnow"

    def test_parses_unix_timestamp(self, arbeitnow_200_response):
        from app.sources.arbeitnow import ArbeitnowAdapter

        adapter = ArbeitnowAdapter()
        items = arbeitnow_200_response["data"]
        jobs = adapter._normalize(items)

        assert jobs[0].published_at is not None
        assert jobs[0].published_at.tzinfo is not None

    def test_skips_malformed_records(self):
        from app.sources.arbeitnow import ArbeitnowAdapter

        adapter = ArbeitnowAdapter()
        items = [
            {"slug": "", "title": "", "company_name": ""},  # missing required fields
            {
                "slug": "valid-job-123",
                "title": "Valid Job",
                "company_name": "Valid Co",
                "url": "https://example.com/jobs/valid-job-123",
                "remote": False,
                "tags": [],
                "job_types": [],
                "created_at": 1750000000,
            },
        ]
        jobs = adapter._normalize(items)
        # The malformed record is skipped, valid one passes
        valid = [j for j in jobs if j.title == "Valid Job"]
        assert len(valid) == 1

    def test_deduplicates_tags(self):
        from app.sources.arbeitnow import ArbeitnowAdapter

        adapter = ArbeitnowAdapter()
        items = [
            {
                "slug": "test-job-dedup",
                "title": "Test Job",
                "company_name": "Test Co",
                "url": "https://example.com/test-job-dedup",
                "remote": True,
                "tags": ["Python", "FastAPI"],
                "job_types": ["Python", "Full-time"],  # Python appears in both
                "created_at": 1750000000,
            }
        ]
        jobs = adapter._normalize(items)
        assert jobs[0].tags.count("Python") == 1
