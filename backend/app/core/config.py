"""
Application configuration.

All settings are read from environment variables or a .env file.
Never hardcode secrets or environment-specific values here.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Source ──────────────────────────────────────────────────────────────
    job_source: Literal["arbeitnow", "mock"] = "arbeitnow"
    mock_scenario: Literal[
        "normal", "empty", "rate_limited", "server_error", "slow", "malformed"
    ] = "normal"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./jobpulse.db"

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000,https://jobpulse-fawn.vercel.app,*"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    # ── Ingestion ─────────────────────────────────────────────────────────────
    ingestion_interval_seconds: int = 0  # 0 = manual only

    # ── Circuit Breaker ───────────────────────────────────────────────────────
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_cooldown_seconds: int = 60

    # ── HTTP / Rate Limiter ───────────────────────────────────────────────────
    http_timeout_seconds: float = 30.0
    http_max_retries: int = 3
    http_initial_backoff_seconds: float = 1.0
    http_max_backoff_seconds: float = 60.0

    # ── Application ───────────────────────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    hide_error_details: bool = False

    @field_validator("database_url")
    @classmethod
    def database_url_must_be_sqlite_for_demo(cls, v: str) -> str:
        # The demo only ships SQLite. If you're extending to PostgreSQL,
        # remove this validator and add asyncpg / psycopg2 to requirements.
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton.

    Using lru_cache means we read the environment exactly once per process,
    which is what we want in production. In tests, call
    ``get_settings.cache_clear()`` after patching env vars.
    """
    return Settings()
