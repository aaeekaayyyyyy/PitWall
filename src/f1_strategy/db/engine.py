"""Database engine and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from f1_strategy.config import get_settings
from f1_strategy.db.models import Base


def get_engine():
    """Create and return the SQLAlchemy engine from application settings."""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        pool_pre_ping=True,
    )


_engine = None
_SessionLocal: sessionmaker | None = None


def get_session_factory():
    """Return a session factory bound to the application engine."""
    global _engine, _SessionLocal
    if _engine is None:
        _engine = get_engine()
        _SessionLocal = sessionmaker(
            bind=_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager yielding a database session. Commits on success, rolls back on error."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables() -> None:
    """Create all tables defined in the models. Safe to call repeatedly (idempotent for existing tables)."""
    global _engine
    if _engine is None:
        _engine = get_engine()
    Base.metadata.create_all(bind=_engine)
