"""
Database connection layer.

Uses SQLite by default (zero setup, file-based — perfect for a solo
final-year project and for demoing without a running Postgres server).
Switching to PostgreSQL later is a one-line change: set DATABASE_URL in
.env to a postgres:// connection string — nothing else in the codebase
needs to change, since all queries go through SQLAlchemy's ORM layer.
"""

from __future__ import annotations
from sqlalchemy import create_engine, text
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


def _ensure_farms_columns(conn) -> None:
    """SQLite-safe migration for older farms tables.

    Fresh installs get the current schema from `create_all`, but legacy DBs can
    still exist from earlier app versions with a partial or stale table. The app
    should upgrade those tables in place instead of crashing on query/insert.
    """
    from sqlalchemy.dialects import sqlite
    from app.models.farm import Farm

    result = conn.execute(text("PRAGMA table_info(farms)"))
    existing_columns = {row[1] for row in result}

    for column in Farm.__table__.columns:
        if column.name in existing_columns:
            continue

        column_sql = column.type.compile(dialect=sqlite.dialect())
        sql = f"ALTER TABLE farms ADD COLUMN {column.name} {column_sql}"
        conn.execute(text(sql))

    conn.commit()


def _ensure_recommendation_columns(conn) -> None:
    """SQLite-safe migration for older recommendation tables.

    Fresh installs get the current schema from `create_all`, but legacy DBs can
    still exist from earlier app versions with a partial or stale table. The app
    should upgrade those tables in place instead of crashing on the first insert.
    """
    from sqlalchemy.dialects import sqlite

    from app.models.recommendation import Recommendation

    result = conn.execute(text("PRAGMA table_info(recommendations)"))
    existing_columns = {row[1] for row in result}

    for column in Recommendation.__table__.columns:
        if column.name in existing_columns:
            continue

        column_sql = column.type.compile(dialect=sqlite.dialect())
        sql = f"ALTER TABLE recommendations ADD COLUMN {column.name} {column_sql}"
        conn.execute(text(sql))

    conn.commit()


def init_db():
    """Create all tables if they don't already exist. Called on app startup."""
    from app import models  # noqa: F401 (ensures models are registered on Base)
    Base.metadata.create_all(bind=engine)

    # Phase 2.3A ownership migration — idempotent, SQLite-compatible.
    # Only silences the case where farms doesn't exist yet (fresh DB where
    # create_all just ran and the column will be present from the model).
    with engine.connect() as conn:
        _ensure_farms_columns(conn)
        _ensure_recommendation_columns(conn)


