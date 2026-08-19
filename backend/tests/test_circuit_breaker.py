"""
Circuit breaker unit tests.
"""
from __future__ import annotations

import time

import pytest

from app.services.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreakerStates:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        assert cb.state == CircuitState.CLOSED

    def test_allows_requests_when_closed(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        assert cb.allow_request() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_does_not_open_before_threshold(self):
        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=10)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_blocks_requests_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=10)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_transitions_to_half_open_after_cooldown(self):
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.05)  # wait for cooldown
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_allows_one_request(self):
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)
        cb.record_failure()
        time.sleep(0.05)
        assert cb.allow_request() is True

    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)
        cb.record_failure()
        time.sleep(0.05)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)
        cb.record_failure()
        time.sleep(0.05)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        # Failure count should reset — need 3 more to open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED  # only 2 failures after reset

    def test_reset_restores_closed_state(self):
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=10)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_status_dict_contains_expected_keys(self):
        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=60)
        status = cb.status_dict()
        assert "state" in status
        assert "failure_count" in status
        assert "failure_threshold" in status
        assert "cooldown_seconds" in status

    def test_seconds_until_half_open_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=60)
        cb.record_failure()
        status = cb.status_dict()
        assert status["seconds_until_half_open"] is not None
        assert 0 < status["seconds_until_half_open"] <= 60

    def test_seconds_until_half_open_is_none_when_closed(self):
        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=60)
        status = cb.status_dict()
        assert status["seconds_until_half_open"] is None
