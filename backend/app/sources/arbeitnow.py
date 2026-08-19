"""
Arbeitnow source adapter.

Fetches public job listings from https://www.arbeitnow.com/api/job-board-api
No API key is required. The adapter uses conservative request behavior:
  - Single request per ingestion run
  - HTTP timeout
  - Exponential backoff with jitter on transient failures
  - Respect for Retry-After headers on 429 responses

This adapter does NOT:
  - Rotate IPs
  - Spoof User-Agent beyond a reasonable identifier
  - Bypass any access controls
  - Retry indefinitely
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.rate_limiter import RateLimiter
from app.sources.base import (
    RawJob,
    SourceEmptyError,
    SourceRateLimitedError,
    SourceSchemaError,
    SourceUnavailableError,
)

# Arbeitnow appends a plain-text markdown link after the HTML body, e.g.:
#   "Find [Jobs in Germany](https://www.arbeitnow.com/) on Arbeitnow"
# This pattern strips it so the stored description is clean HTML only.
_ARBEITNOW_TRAILING_LINK_RE = re.compile(
    r"Find\s+\[.*?\]\(https?://[^)]+\)\s+on\s+\w+",
    re.IGNORECASE | re.DOTALL,
)


def _clean_description(html: str | None) -> str | None:
    """
    Remove Arbeitnow-injected artefacts from a job description.

    1. Strips the trailing markdown link appended after the HTML body.
    2. Removes inline style attributes that force near-white text colour
       (rgb(236,240,241) / rgb(255,255,255)) which would be invisible in
       light-mode UIs and look wrong in dark-mode ones.
    """
    if not html:
        return html

    # 1. Strip trailing markdown link
    cleaned = _ARBEITNOW_TRAILING_LINK_RE.sub("", html).rstrip()

    # 2. Remove injected white-text style overrides
    #    e.g. <span style="color: rgb(236, 240, 241);">
    cleaned = re.sub(
        r'\s*style="[^"]*color\s*:\s*rgb\(\s*2[0-9]{2}\s*,\s*2[0-9]{2}\s*,\s*2[0-9]{2}\s*\)[^"]*"',
        "",
        cleaned,
    )

    return cleaned or None

logger = get_logger(__name__)

ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"
SOURCE_NAME = "arbeitnow"


class ArbeitnowAdapter:
    """
    Fetches jobs from the Arbeitnow public job board API.

    Implements the JobSource Protocol (structural subtyping — no explicit
    inheritance required).
    """

    source_name: str = SOURCE_NAME

    def __init__(self) -> None:
        settings = get_settings()
        self._rate_limiter = RateLimiter(
            timeout=settings.http_timeout_seconds,
            max_retries=settings.http_max_retries,
            initial_backoff=settings.http_initial_backoff_seconds,
            max_backoff=settings.http_max_backoff_seconds,
        )

    async def fetch_jobs(self) -> list[RawJob]:
        """
        Fetch jobs from the Arbeitnow API.

        Returns a list of normalized RawJob objects.

        Raises:
            SourceEmptyError: if the API returns zero jobs.
            SourceRateLimitedError: if the API returns 429.
            SourceSchemaError: if the response cannot be parsed.
            SourceUnavailableError: if the source is unreachable after retries.
        """
        logger.info("Fetching jobs from Arbeitnow API: %s", ARBEITNOW_API_URL)

        response = await self._rate_limiter.get(
            ARBEITNOW_API_URL,
            headers={
                "Accept": "application/json",
                "User-Agent": "JobPulse-Ingestion/1.0 (+https://github.com/jobpulse)",
            },
        )

        raw_data = self._parse_response(response)
        jobs = self._normalize(raw_data)

        if not jobs:
            raise SourceEmptyError("Arbeitnow returned zero jobs")

        logger.info("Arbeitnow: fetched %d raw jobs", len(jobs))
        return jobs

    # ── Private helpers ───────────────────────────────────────────────────────

    def _parse_response(self, response: httpx.Response) -> list[dict[str, Any]]:
        """Parse and validate the HTTP response structure."""
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise SourceSchemaError(f"Invalid JSON from Arbeitnow: {exc}") from exc

        if not isinstance(data, dict) or "data" not in data:
            raise SourceSchemaError(
                f"Unexpected response structure — expected {{data: [...]}}, got keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
            )

        items = data["data"]
        if not isinstance(items, list):
            raise SourceSchemaError(
                f"Expected data to be a list, got {type(items).__name__}"
            )

        return items

    def _normalize(self, items: list[dict[str, Any]]) -> list[RawJob]:
        """
        Map Arbeitnow API fields to the normalized RawJob model.

        Arbeitnow response shape (per item):
            slug          → external_id
            title         → title
            company_name  → company
            location      → location
            description   → description
            url           → url
            remote        → remote
            job_types     → tags
            tags          → category (first tag used as category)
            created_at    → published_at  (Unix timestamp)
        """
        normalized: list[RawJob] = []

        for item in items:
            try:
                # Arbeitnow uses Unix timestamps for created_at
                published_at: datetime | None = None
                raw_ts = item.get("created_at")
                if raw_ts:
                    try:
                        published_at = datetime.fromtimestamp(
                            int(raw_ts), tz=timezone.utc
                        )
                    except (ValueError, OSError, OverflowError):
                        published_at = None

                # Combine job_types and tags into a unified tag list
                tags: list[str] = []
                for tag_field in ("job_types", "tags"):
                    raw_tags = item.get(tag_field, [])
                    if isinstance(raw_tags, list):
                        tags.extend(str(t) for t in raw_tags if t)

                # Deduplicate while preserving order
                seen: set[str] = set()
                unique_tags: list[str] = []
                for t in tags:
                    if t not in seen:
                        seen.add(t)
                        unique_tags.append(t)

                category = unique_tags[0] if unique_tags else None

                job = RawJob(
                    external_id=str(item.get("slug", "")),
                    title=str(item.get("title", "")),
                    company=str(item.get("company_name", "")),
                    location=item.get("location") or None,
                    description=_clean_description(item.get("description") or None),
                    url=str(item.get("url", "")),
                    remote=bool(item.get("remote", False)),
                    category=category,
                    tags=unique_tags,
                    published_at=published_at,
                    source=SOURCE_NAME,
                )
                normalized.append(job)

            except (ValidationError, KeyError, TypeError) as exc:
                # Log but continue — one bad record shouldn't fail the run
                logger.warning(
                    "Skipping malformed Arbeitnow record: %s — %s",
                    item.get("slug", "<no-slug>"),
                    exc,
                )

        return normalized
