"""
Source adapter factory.

Centralizes adapter instantiation so the rest of the application never
imports a concrete adapter directly.  Adding a new adapter means:
  1. Create the adapter class
  2. Register it here
"""
from __future__ import annotations

from app.core.config import get_settings
from app.sources.base import JobSource


def get_source(
    source_name: str | None = None,
    mock_scenario: str | None = None,
) -> JobSource:
    """Return the configured source adapter.

    If source_name is provided, instantiates that source directly.
    Otherwise reads from settings.JOB_SOURCE.
    """
    settings = get_settings()
    target_source = source_name or settings.job_source

    if target_source == "mock":
        from app.sources.mock import MockAdapter
        scenario = mock_scenario or settings.mock_scenario
        return MockAdapter(scenario=scenario)

    # Default: arbeitnow
    from app.sources.arbeitnow import ArbeitnowAdapter
    return ArbeitnowAdapter()
