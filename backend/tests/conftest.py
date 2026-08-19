"""
Test configuration and fixtures.

Key design decisions:
  - Uses an in-memory SQLite database so tests are isolated and fast.
  - HTTP calls are mocked with respx — the real Arbeitnow API is NEVER
    called during tests.
  - The circuit breaker is reset between tests to prevent state leakage.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app
from app.services.ingestion import get_circuit_breaker


# ─────────────────────────────────────────────────────────────────────────────
# In-memory database fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def db_engine():
    """Create a fresh in-memory SQLite engine for each test.

    Uses StaticPool so all sessions share the same in-memory connection.
    Without StaticPool, each session gets its own connection and therefore
    its own blank in-memory database.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    # Import models BEFORE create_all so all tables are registered
    import app.models.job  # noqa: F401
    from app.db.database import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # force single shared connection
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Return a database session bound to the in-memory engine."""
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine, db_session):
    """Return a FastAPI TestClient with the in-memory database injected.

    Tables are already created by db_engine. We override the get_db dependency
    to use the in-memory test session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Circuit breaker reset
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset the circuit breaker before every test."""
    cb = get_circuit_breaker()
    cb.reset()
    yield
    cb.reset()


# ─────────────────────────────────────────────────────────────────────────────
# Sample data fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def arbeitnow_200_response():
    """Sample successful Arbeitnow API response."""
    return {
        "data": [
            {
                "slug": "senior-python-engineer-acme-123",
                "title": "Senior Python Engineer",
                "company_name": "Acme Corp",
                "location": "Berlin, Germany",
                "description": "<p>Great opportunity for a Python developer.</p>",
                "url": "https://www.arbeitnow.com/jobs/acme/senior-python-engineer-acme-123",
                "remote": True,
                "tags": ["Python", "FastAPI"],
                "job_types": ["Full-time"],
                "created_at": 1750000000,
            },
            {
                "slug": "react-developer-techstart-456",
                "title": "React Developer",
                "company_name": "TechStart GmbH",
                "location": "Amsterdam",
                "description": "<p>Join our frontend team.</p>",
                "url": "https://www.arbeitnow.com/jobs/techstart/react-developer-techstart-456",
                "remote": False,
                "tags": ["React", "TypeScript"],
                "job_types": ["Full-time"],
                "created_at": 1749900000,
            },
        ],
        "links": {"first": "...", "last": "..."},
    }


@pytest.fixture
def arbeitnow_empty_response():
    return {"data": [], "links": {}}


@pytest.fixture
def arbeitnow_malformed_response():
    return {"unexpected_key": "not a job board response"}
