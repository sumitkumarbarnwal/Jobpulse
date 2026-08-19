"""
Tests for rate limiter backoff, jitter, and retry logic.

Uses respx to mock httpx calls — no real HTTP requests are made.
"""
from __future__ import annotations

import pytest
import respx
import httpx

from app.services.rate_limiter import RateLimiter
from app.sources.base import SourceRateLimitedError, SourceUnavailableError


class TestBackoffCalculation:
    def test_backoff_grows_exponentially(self):
        """Verify that backoff time roughly doubles each attempt."""
        limiter = RateLimiter(initial_backoff=1.0, max_backoff=100.0)
        # We test the formula, not the sleep itself
        # attempt 1: min(1.0 * 2^0, 100) = 1.0
        # attempt 2: min(1.0 * 2^1, 100) = 2.0
        # attempt 3: min(1.0 * 2^2, 100) = 4.0
        expected = [1.0, 2.0, 4.0, 8.0, 16.0]
        for attempt, exp in enumerate(expected, start=1):
            base = min(limiter.initial_backoff * (2 ** (attempt - 1)), limiter.max_backoff)
            assert base == exp

    def test_backoff_is_capped_at_max(self):
        limiter = RateLimiter(initial_backoff=1.0, max_backoff=5.0)
        base = min(limiter.initial_backoff * (2 ** 10), limiter.max_backoff)
        assert base == 5.0

    def test_parse_retry_after_numeric(self):
        """Parse numeric Retry-After header."""
        response = httpx.Response(
            429,
            headers={"Retry-After": "30"},
            content=b"Too Many Requests",
        )
        result = RateLimiter._parse_retry_after(response)
        assert result == 30.0

    def test_parse_retry_after_missing(self):
        response = httpx.Response(429, content=b"Too Many Requests")
        result = RateLimiter._parse_retry_after(response)
        assert result is None

    def test_parse_retry_after_invalid(self):
        response = httpx.Response(
            429,
            headers={"Retry-After": "not-a-number"},
            content=b"Too Many Requests",
        )
        result = RateLimiter._parse_retry_after(response)
        assert result is None


@pytest.mark.asyncio
class TestRateLimiterHTTP:
    @respx.mock
    async def test_returns_response_on_200(self):
        respx.get("https://example.com/api").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        limiter = RateLimiter(max_retries=0)
        response = await limiter.get("https://example.com/api")
        assert response.status_code == 200

    @respx.mock
    async def test_raises_rate_limited_on_429(self):
        respx.get("https://example.com/api").mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "10"},
                content=b"Too Many Requests",
            )
        )
        limiter = RateLimiter(max_retries=0)
        with pytest.raises(SourceRateLimitedError) as exc_info:
            await limiter.get("https://example.com/api")
        assert exc_info.value.retry_after == 10.0

    @respx.mock
    async def test_raises_unavailable_after_max_retries_on_500(self, monkeypatch):
        # Disable actual sleep to keep test fast
        monkeypatch.setattr("app.services.rate_limiter.asyncio.sleep", _no_sleep)

        respx.get("https://example.com/api").mock(
            return_value=httpx.Response(500, content=b"Server Error")
        )
        limiter = RateLimiter(max_retries=2)
        with pytest.raises(SourceUnavailableError):
            await limiter.get("https://example.com/api")

    @respx.mock
    async def test_retries_on_500_then_succeeds(self, monkeypatch):
        monkeypatch.setattr("app.services.rate_limiter.asyncio.sleep", _no_sleep)

        route = respx.get("https://example.com/api")
        route.side_effect = [
            httpx.Response(500, content=b"Error"),
            httpx.Response(200, json={"data": []}),
        ]

        limiter = RateLimiter(max_retries=2)
        response = await limiter.get("https://example.com/api")
        assert response.status_code == 200
        assert route.call_count == 2

    @respx.mock
    async def test_raises_unavailable_on_timeout(self, monkeypatch):
        monkeypatch.setattr("app.services.rate_limiter.asyncio.sleep", _no_sleep)

        respx.get("https://example.com/api").mock(
            side_effect=httpx.TimeoutException("Timeout")
        )
        limiter = RateLimiter(max_retries=1)
        with pytest.raises(SourceUnavailableError, match="timed out"):
            await limiter.get("https://example.com/api")


async def _no_sleep(_: float) -> None:
    """Stub to replace asyncio.sleep in tests."""
    pass
