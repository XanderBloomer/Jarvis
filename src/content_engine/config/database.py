"""Database connection and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from content_engine.config.settings import get_settings


def get_engine():
    """Create database engine."""
    settings = get_settings()
    return create_engine(settings.database_url, echo=(settings.app_env == "development"))


def get_session_factory():
    """Create session factory."""
    engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Get a database session (dependency injection for FastAPI)."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session  # type: ignore[misc]
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
