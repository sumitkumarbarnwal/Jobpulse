"""
HTTP Rate Limiter / Request Policy.

Implements conservative request pacing:
  - HTTP timeout
  - Limited retry count (no indefinite retries)
  - Exponential backoff with jitter
  - Respect Retry-After header on 429 responses
  - Clear error classification

This module does NOT implement IP rotation, header spoofing, or any
technique designed to evade access controls.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Any

import httpx

from app.core.logging import get_logger
from app.sources.base import (
    SourceRateLimitedError,
    SourceUnavailableError,
)

logger = get_logger(__name__)


class RateLimiter:
    """
    Wraps httpx with a retry policy suitable for public API calls.

    Retry decision matrix:
        200     → return response
        429     → raise SourceRateLimitedError (caller handles)
        5xx     → retry up to max_retries with exponential backoff
        timeout → retry up to max_retries with exponential backoff
        4xx     → raise immediately (client error, not transient)
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 60.0,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Perform a GET request with retry logic.

        Returns the httpx.Response on success.
        Raises SourceRateLimitedError, SourceUnavailableError, or
        httpx.TimeoutException on final failure.
        """
        attempt = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                attempt += 1
                logger.debug("GET %s (attempt %d/%d)", url, attempt, self.max_retries + 1)

                try:
                    response = await client.get(url, headers=headers or {}, **kwargs)
                except httpx.TimeoutException as exc:
                    logger.warning("Timeout on attempt %d: %s", attempt, exc)
                    if attempt > self.max_retries:
                        raise SourceUnavailableError(
                            f"Request timed out after {self.max_retries + 1} attempts"
                        ) from exc
                    await self._backoff(attempt, exc_type="timeout")
                    continue

                except httpx.RequestError as exc:
                    logger.warning("Network error on attempt %d: %s", attempt, exc)
                    if attempt > self.max_retries:
                        raise SourceUnavailableError(
                            f"Network error after {self.max_retries + 1} attempts: {exc}"
                        ) from exc
                    await self._backoff(attempt, exc_type="network")
                    continue

                # ── HTTP response received ────────────────────────────────────
                if response.status_code == 200:
                    return response

                if response.status_code == 429:
                    retry_after = self._parse_retry_after(response)
                    logger.warning(
                        "Rate limited (429). retry_after=%.1fs", retry_after or 0
                    )
                    raise SourceRateLimitedError(retry_after=retry_after)

                if response.status_code >= 500:
                    logger.warning(
                        "Server error %d on attempt %d",
                        response.status_code,
                        attempt,
                    )
                    if attempt > self.max_retries:
                        err = SourceUnavailableError(
                            f"HTTP {response.status_code} after {self.max_retries + 1} attempts"
                        )
                        err.http_status = response.status_code
                        raise err
                    await self._backoff(attempt, exc_type="5xx")
                    continue

                # 4xx (other than 429): not retryable
                response.raise_for_status()
                return response  # unreachable, but explicit

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _backoff(self, attempt: int, exc_type: str = "") -> None:
        """
        Wait before the next retry using exponential backoff + jitter.

        Jitter is added to prevent synchronized retries from multiple
        instances hammering the same endpoint simultaneously (thundering herd).

        Formula: min(initial * 2^(attempt-1), max) + uniform(0, 1)
        """
        base = min(
            self.initial_backoff * (2 ** (attempt - 1)),
            self.max_backoff,
        )
        jitter = random.uniform(0, min(base * 0.5, 5.0))
        wait = base + jitter

        logger.info(
            "Backoff (%s): waiting %.2fs before retry %d",
            exc_type,
            wait,
            attempt + 1,
        )
        await asyncio.sleep(wait)

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        """Parse the Retry-After header if present.

        Returns seconds to wait, or None if not present/parseable.
        """
        raw = response.headers.get("Retry-After")
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            # Retry-After can also be an HTTP-date; skip parsing for now.
            return None
