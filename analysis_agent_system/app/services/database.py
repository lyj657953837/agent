"""Database connection and session management using SQLAlchemy."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from analysis_agent_system.app.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


# Engine & session factory (created lazily via property to allow testing overrides)
_engine = None
_SessionLocal = None


def get_engine():
    """Return the global SQLAlchemy engine (singleton)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Return the global session factory (singleton)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


def get_db() -> Session:
    """FastAPI dependency that yields a database session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables that do not yet exist (useful for dev)."""
    Base.metadata.create_all(bind=get_engine())
