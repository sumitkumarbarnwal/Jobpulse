"""
REST API endpoint tests.

Tests pagination, filtering, and correct HTTP status codes.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.ingestion import _persist_jobs
from app.sources.base import RawJob


def _make_job(n: int, **kwargs) -> RawJob:
    return RawJob(
        external_id=f"job-{n:03d}",
        title=kwargs.get("title", f"Job {n}"),
        company=kwargs.get("company", "Test Corp"),
        location=kwargs.get("location", "Berlin, Germany"),
        url=f"https://example.com/jobs/job-{n:03d}",
        source="test",
        remote=kwargs.get("remote", False),
    )


def _seed_jobs(db_session, n: int = 5, prefix: str = "", **kwargs):
    jobs = [
        RawJob(
            external_id=f"{prefix}job-{i:03d}",
            title=kwargs.get("title", f"Job {i}"),
            company=kwargs.get("company", "Test Corp"),
            location=kwargs.get("location", "Berlin, Germany"),
            url=f"https://example.com/jobs/{prefix}job-{i:03d}",
            source="test",
            remote=kwargs.get("remote", False),
        )
        for i in range(n)
    ]
    _persist_jobs(db_session, jobs, source="test")
    return jobs


class TestJobsAPI:
    def test_empty_database_returns_empty_list(self, client):
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["jobs"] == []
        assert data["total"] == 0

    def test_returns_seeded_jobs(self, client, db_session):
        _seed_jobs(db_session, 5)
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        assert resp.json()["total"] == 5
        assert len(resp.json()["jobs"]) == 5

    def test_pagination_page_1(self, client, db_session):
        _seed_jobs(db_session, 25)
        resp = client.get("/api/jobs?page=1&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["jobs"]) == 10
        assert data["total"] == 25
        assert data["pages"] == 3
        assert data["page"] == 1

    def test_pagination_page_3(self, client, db_session):
        _seed_jobs(db_session, 25)
        resp = client.get("/api/jobs?page=3&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["jobs"]) == 5  # last page has 5

    def test_search_filter_by_title(self, client, db_session):
        _seed_jobs(db_session, 3, title="Python Engineer")
        _make_job_custom = RawJob(
            external_id="go-engineer-001",
            title="Go Engineer",
            company="Go Corp",
            url="https://example.com/go-engineer-001",
            source="test",
        )
        _persist_jobs(db_session, [_make_job_custom], source="test")

        resp = client.get("/api/jobs?search=python")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        for job in data["jobs"]:
            assert "python" in job["title"].lower()

    def test_search_filter_by_company(self, client, db_session):
        _seed_jobs(db_session, 2, company="Acme Corp")
        _persist_jobs(
            db_session,
            [RawJob(
                external_id="other-001",
                title="Other Job",
                company="Other Co",
                url="https://example.com/other-001",
                source="test",
            )],
            source="test",
        )
        resp = client.get("/api/jobs?search=acme")
        assert resp.json()["total"] == 2

    def test_remote_filter_true(self, client, db_session):
        _seed_jobs(db_session, 3, prefix="remote-", remote=True)
        _seed_jobs(db_session, 2, prefix="onsite-", remote=False)

        resp = client.get("/api/jobs?remote=true")
        assert resp.json()["total"] == 3

    def test_remote_filter_false(self, client, db_session):
        _seed_jobs(db_session, 3, prefix="r-", remote=True)
        _seed_jobs(db_session, 2, prefix="nr-", remote=False)

        resp = client.get("/api/jobs?remote=false")
        data = resp.json()
        assert data["total"] == 2
        for job in data["jobs"]:
            assert job["remote"] is False

    def test_location_filter(self, client, db_session):
        berlin_jobs = [
            RawJob(
                external_id=f"berlin-{i}",
                title=f"Berlin Job {i}",
                company="Corp",
                url=f"https://example.com/berlin-{i}",
                source="test",
                location="Berlin, Germany",
            )
            for i in range(3)
        ]
        london_job = RawJob(
            external_id="london-0",
            title="London Job",
            company="Corp",
            url="https://example.com/london-0",
            source="test",
            location="London, UK",
        )
        _persist_jobs(db_session, berlin_jobs + [london_job], source="test")

        resp = client.get("/api/jobs?location=berlin")
        assert resp.json()["total"] == 3

    def test_get_job_by_id(self, client, db_session):
        from app.models.job import Job

        _seed_jobs(db_session, 1)
        job = db_session.query(Job).first()
        assert job is not None

        resp = client.get(f"/api/jobs/{job.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job.id
        assert data["title"] == job.title

    def test_get_job_not_found(self, client):
        resp = client.get("/api/jobs/999999")
        assert resp.status_code == 404

    def test_invalid_page_param(self, client):
        resp = client.get("/api/jobs?page=0")  # page must be >= 1
        assert resp.status_code == 422

    def test_limit_max_100(self, client, db_session):
        _seed_jobs(db_session, 5)
        resp = client.get("/api/jobs?limit=200")  # limit must be <= 100
        assert resp.status_code == 422


class TestHealthAPI:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert data["database"] == "connected"


class TestIngestionAPI:
    def test_ingestion_status_returns_expected_fields(self, client):
        resp = client.get("/api/ingestion/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "source" in data
        assert "status" in data
        assert "jobs_stored" in data
        assert "circuit_breaker_state" in data

    def test_ingestion_runs_returns_list(self, client):
        resp = client.get("/api/ingestion/runs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
