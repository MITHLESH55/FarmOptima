"""
Database connection layer.

Uses SQLite by default (zero setup, file-based — perfect for a solo
final-year project and for demoing without a running Postgres server).
Switching to PostgreSQL later is a one-line change: set DATABASE_URL in
.env to a postgres:// connection string — nothing else in the codebase
needs to change, since all queries go through SQLAlchemy's ORM layer.
"""

from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# check_same_thread=False is required for SQLite when used with FastAPI's
# threaded request handling; it's a no-op / ignored for other databases.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and guarantees it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't already exist. Called on app startup."""
    from app import models  # noqa: F401 (ensures models are registered on Base)
    Base.metadata.create_all(bind=engine)
