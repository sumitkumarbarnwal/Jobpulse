"""
SQLAlchemy database engine and session factory.

Uses SQLite with WAL (Write-Ahead Logging) journal mode for better
concurrent read performance and crash safety.

For a production PostgreSQL migration:
  1. Change DATABASE_URL to postgresql+psycopg2://...
  2. Remove the connect_args and WAL event listener below
  3. Add connection pooling (pool_size, max_overflow)
"""
from __future__ import annotations

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def _make_engine():
    settings = get_settings()
    connect_args = {}

    if settings.database_url.startswith("sqlite"):
        # check_same_thread=False is required for SQLite when used with
        # FastAPI's dependency injection, which may call the session from
        # different threads.
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=False,  # Set True to see raw SQL during debugging
    )

    # Enable WAL mode and foreign keys for every new SQLite connection.
    if settings.database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _make_engine()

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db():
    """FastAPI dependency that yields a database session.

    Usage in route:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind_engine=None) -> None:
    """Create all tables if they don't already exist.

    Called once at application startup in main.py lifespan.
    Pass bind_engine in tests to use the in-memory engine.
    """
    # Import models here so that SQLAlchemy registers them before create_all.
    import app.models.job  # noqa: F401

    target = bind_engine or engine
    Base.metadata.create_all(bind=target)
