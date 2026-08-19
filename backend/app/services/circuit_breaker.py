"""
In-memory Circuit Breaker.

Implements a simple three-state circuit breaker to protect the application
from hammering an unavailable source.

States:
    CLOSED    — Normal operation. Failures are counted.
    OPEN      — Too many failures. Requests are rejected immediately.
    HALF_OPEN — Cooldown elapsed. One probe request is allowed through.

State transitions:
    CLOSED + failures >= threshold   → OPEN
    OPEN + cooldown elapsed          → HALF_OPEN
    HALF_OPEN + success              → CLOSED
    HALF_OPEN + failure              → OPEN

Production note:
    This is an in-memory implementation. In a distributed system with
    multiple backend instances, the circuit state must be stored in a
    shared store (e.g., Redis) to be meaningful.
"""
from __future__ import annotations

import time
from enum import Enum

from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Simple in-memory circuit breaker.

    Usage:
        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=60)

        if cb.allow_request():
            try:
                result = await do_something()
                cb.record_success()
            except Exception:
                cb.record_failure()
        else:
            # Circuit is open — serve cached data
            ...
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None  # monotonic time

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        """Current circuit state (auto-transitions OPEN → HALF_OPEN)."""
        if self._state == CircuitState.OPEN and self._cooldown_elapsed():
            logger.info("Circuit breaker: OPEN → HALF_OPEN (cooldown elapsed)")
            self._state = CircuitState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        """Return True if a request should be allowed through."""
        state = self.state  # triggers auto-transition if needed
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True
        # OPEN
        return False

    def record_success(self) -> None:
        """Record a successful request."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker: HALF_OPEN → CLOSED (probe succeeded)")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        logger.warning(
            "Circuit breaker: failure recorded (%d/%d)",
            self._failure_count,
            self.failure_threshold,
        )

        if self._state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker: HALF_OPEN → OPEN (probe failed)")
            self._open()
        elif self._failure_count >= self.failure_threshold:
            logger.error(
                "Circuit breaker: CLOSED → OPEN (threshold reached: %d failures)",
                self._failure_count,
            )
            self._open()

    def reset(self) -> None:
        """Manually reset the circuit breaker (useful in tests)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None

    # ── Status dict (for API responses) ──────────────────────────────────────

    def status_dict(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "seconds_until_half_open": self._seconds_until_half_open(),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()

    def _cooldown_elapsed(self) -> bool:
        if self._opened_at is None:
            return False
        return (time.monotonic() - self._opened_at) >= self.cooldown_seconds

    def _seconds_until_half_open(self) -> float | None:
        if self._state != CircuitState.OPEN or self._opened_at is None:
            return None
        elapsed = time.monotonic() - self._opened_at
        remaining = self.cooldown_seconds - elapsed
        return max(0.0, remaining)
