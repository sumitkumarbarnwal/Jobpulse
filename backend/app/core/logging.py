"""
Structured logging configuration.

Uses Python's stdlib logging with a JSON-friendly format in production.
In development, uses a human-readable format.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure the root logger.

    Call once at application startup (in main.py lifespan).
    """
    settings = get_settings()

    level = logging.DEBUG if settings.app_env == "development" else logging.INFO

    formatter: logging.Formatter
    if settings.app_env == "production":
        # Structured, single-line format that log aggregators can parse.
        formatter = logging.Formatter(
            fmt='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s}',
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quieten noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("something happened")
    """
    return logging.getLogger(name)
