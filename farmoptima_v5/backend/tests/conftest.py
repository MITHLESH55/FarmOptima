"""
Shared fixtures for integration tests.

Key design point: we override the app's `get_db` dependency to use a
fresh, isolated SQLite file per test session (not the real farmoptima.db),
so integration tests never touch or pollute your actual development
database. This is standard FastAPI testing practice, not a hack.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db


@pytest.fixture(scope="function")
def test_db_engine():
    """A fresh SQLite file per test function — fully isolated, auto-cleaned up."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def client(test_db_engine):
    """A TestClient with the real app, but pointed at the isolated test DB.

    The slowapi rate limiter uses in-memory storage keyed by remote address.
    TestClient always presents as "testclient", so without a reset the 20/min
    limit accumulates across the entire test session, causing spurious 429s on
    later tests.  We clear the limiter's storage on every test function to keep
    each test independent — this does NOT weaken production rate limiting.
    """
    from app.utils.rate_limit import limiter
    # Reset in-memory rate-limit counters so each test starts fresh.
    # limiter._storage is the MovingWindowRateLimiter / MemoryStorage backend.
    try:
        limiter._storage.reset()
    except AttributeError:
        # Older slowapi versions expose the storage differently; fall back safely.
        try:
            limiter.reset()
        except Exception:
            pass

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # raise_server_exceptions=False lets our registered exception handlers
    # actually run during tests (otherwise TestClient re-raises server
    # errors directly, bypassing the standardized error envelope).
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client):
    """Registers a fresh test user, logs in, and returns a ready-to-use Authorization header."""
    credentials = {"username": "test_user", "password": "testpassword123"}
    client.post("/api/auth/register", json=credentials)
    login_resp = client.post("/api/auth/login", json=credentials)
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
