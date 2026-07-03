"""SQLAlchemy engine/session — Postgres in prod, SQLite fallback locally."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_url = _settings.effective_database_url

# SQLite needs check_same_thread=False for FastAPI's threadpool.
_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}

engine = create_engine(_url, connect_args=_connect_args, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create tables if they don't exist (dev convenience; use Alembic in prod)."""
    from app.db import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)


def get_session():
    """FastAPI dependency yielding a session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
