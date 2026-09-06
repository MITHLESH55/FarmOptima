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


def _ensure_farms_user_id_column(conn) -> None:
    """Idempotent Phase 2.3A migration: add user_id to farms if absent.

    Inspects the actual schema using PRAGMA table_info before attempting
    ALTER TABLE. This avoids:
    - Swallowing unrelated database errors.
    - Duplicate-column errors on subsequent startups.
    - Any assumption about the column's presence.

    SQLite ADD COLUMN restrictions mean the new column must be nullable
    (which matches our design: legacy rows have NULL ownership).
    """
    from sqlalchemy import text

    # PRAGMA table_info returns one row per column: (cid, name, type, ...)
    result = conn.execute(text("PRAGMA table_info(farms)"))
    existing_columns = {row[1] for row in result}

    if "user_id" not in existing_columns:
        import logging
        logging.getLogger("farmoptima").info(
            "Migration: adding user_id column to farms table (Phase 2.3A)."
        )
        conn.execute(
            text("ALTER TABLE farms ADD COLUMN user_id INTEGER REFERENCES users(id)")
        )
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
        _ensure_farms_user_id_column(conn)
        _ensure_recommendation_columns(conn)

