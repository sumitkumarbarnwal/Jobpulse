"""
Mock source adapter.

Provides controlled test scenarios WITHOUT touching any external API.
Select a scenario with the MOCK_SCENARIO environment variable.

Scenarios:
    normal        — Returns 15 well-formed jobs
    empty         — Returns zero jobs (triggers EMPTY_SOURCE_RESPONSE handling)
    rate_limited  — Raises SourceRateLimitedError (simulates HTTP 429)
    server_error  — Raises SourceUnavailableError (simulates HTTP 500)
    slow          — Waits 3 seconds then returns normal data
    malformed     — Returns data that fails schema validation

Also registers a /mock-source/jobs router for external HTTP testing.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.sources.base import (
    RawJob,
    SourceEmptyError,
    SourceRateLimitedError,
    SourceSchemaError,
    SourceUnavailableError,
)

logger = get_logger(__name__)

SOURCE_NAME = "mock"

# ─────────────────────────────────────────────────────────────────────────────
# Seed data
# ─────────────────────────────────────────────────────────────────────────────

_SEED_JOBS: list[RawJob] = [
    RawJob(
        external_id=f"mock-job-{i:03d}",
        title=title,
        company=company,
        location=location,
        description=f"<p>We are looking for a talented {title} to join our team. "
                    f"You will work on exciting projects with modern technology stacks.</p>",
        url=f"https://example.com/jobs/mock-job-{i:03d}",
        remote=remote,
        category=category,
        tags=tags,
        published_at=datetime(2026, 8, 18 - (i % 5), 10, 0, 0, tzinfo=timezone.utc),
        source=SOURCE_NAME,
    )
    for i, (title, company, location, remote, category, tags) in enumerate(
        [
            ("Senior Python Engineer", "Acme Corp", "Berlin, Germany", True, "Engineering", ["Python", "FastAPI", "Remote"]),
            ("React Frontend Developer", "TechStart GmbH", "Amsterdam, Netherlands", False, "Engineering", ["React", "TypeScript", "Vite"]),
            ("DevOps Engineer", "CloudScale Inc", "Remote", True, "DevOps", ["Docker", "Kubernetes", "CI/CD"]),
            ("Data Engineer", "DataFlow Ltd", "London, UK", False, "Data", ["Python", "Spark", "SQL"]),
            ("Product Manager", "Innovate AG", "Zürich, Switzerland", False, "Product", ["Agile", "Roadmapping"]),
            ("Backend Engineer (Go)", "Golang GmbH", "Remote", True, "Engineering", ["Go", "gRPC", "Microservices"]),
            ("Machine Learning Engineer", "AI Labs", "San Francisco, CA", False, "ML", ["Python", "PyTorch", "MLOps"]),
            ("Full Stack Developer", "Startup Hub", "Remote", True, "Engineering", ["Node.js", "React", "PostgreSQL"]),
            ("Site Reliability Engineer", "ReliaCo", "Vienna, Austria", False, "DevOps", ["Linux", "Prometheus", "Terraform"]),
            ("Mobile Developer (iOS)", "AppCraft", "Munich, Germany", False, "Mobile", ["Swift", "SwiftUI", "Xcode"]),
            ("Security Engineer", "SecureBase", "Remote", True, "Security", ["Penetration Testing", "SIEM", "IAM"]),
            ("UI/UX Designer", "DesignLab", "Barcelona, Spain", True, "Design", ["Figma", "User Research"]),
            ("Database Administrator", "DataSafe AG", "Frankfurt, Germany", False, "Data", ["PostgreSQL", "MySQL", "Performance Tuning"]),
            ("Cloud Architect", "CloudPath", "Remote", True, "Cloud", ["AWS", "Terraform", "Architecture"]),
            ("QA Engineer", "QualTest", "Warsaw, Poland", False, "QA", ["Selenium", "Pytest", "Test Automation"]),
        ],
        start=1,
    )
]

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI router for HTTP-level mock testing
# ─────────────────────────────────────────────────────────────────────────────

mock_router = APIRouter(prefix="/mock-source", tags=["Mock Source"])


@mock_router.get("/jobs")
async def mock_jobs_endpoint():
    """
    Mock HTTP endpoint that mirrors what a real job board API might return.

    The scenario is controlled by MOCK_SCENARIO env var.
    Use this endpoint to test the ingestion pipeline end-to-end via HTTP.
    """
    settings = get_settings()
    scenario = settings.mock_scenario

    if scenario == "empty":
        return JSONResponse({"data": [], "links": {}})

    if scenario == "rate_limited":
        return JSONResponse(
            {"error": "Too Many Requests"},
            status_code=429,
            headers={"Retry-After": "5"},
        )

    if scenario == "server_error":
        return JSONResponse({"error": "Internal Server Error"}, status_code=500)

    if scenario == "slow":
        await asyncio.sleep(3)
        # Fall through to normal response

    if scenario == "malformed":
        return JSONResponse({"unexpected_key": "bad data"})

    # Normal: return seed data
    data = [
        {
            "slug": job.external_id,
            "title": job.title,
            "company_name": job.company,
            "location": job.location,
            "description": job.description,
            "url": job.url,
            "remote": job.remote,
            "tags": job.tags,
            "job_types": [],
            "created_at": int(job.published_at.timestamp()) if job.published_at else None,
        }
        for job in _SEED_JOBS
    ]
    return JSONResponse({"data": data, "links": {}})


# ─────────────────────────────────────────────────────────────────────────────
# Mock adapter (in-process, no HTTP)
# ─────────────────────────────────────────────────────────────────────────────

class MockAdapter:
    """
    In-process mock that raises/returns based on MOCK_SCENARIO.

    Used by the ingestion service when JOB_SOURCE=mock.
    Does NOT make any HTTP requests — scenarios are handled entirely
    in memory, making tests deterministic and fast.
    """

    source_name: str = SOURCE_NAME

    def __init__(self, scenario: str | None = None) -> None:
        self.override_scenario = scenario

    async def fetch_jobs(self) -> list[RawJob]:
        settings = get_settings()
        scenario = self.override_scenario or settings.mock_scenario

        logger.info("MockAdapter running scenario: %s", scenario)

        if scenario == "empty":
            raise SourceEmptyError("Mock: empty source response — zero jobs returned")

        if scenario == "rate_limited":
            raise SourceRateLimitedError(retry_after=5.0)

        if scenario == "server_error":
            err = SourceUnavailableError("Mock: simulated HTTP 500 Internal Server Error")
            err.http_status = 500
            raise err

        if scenario == "slow":
            await asyncio.sleep(3)
            return list(_SEED_JOBS)

        if scenario == "malformed":
            raise SourceSchemaError("Mock: malformed response — schema mismatch")

        # Default: normal
        return list(_SEED_JOBS)
