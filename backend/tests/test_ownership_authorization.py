"""
Integration tests for Phase 2.3A Ownership & Authorization prerequisite.
"""

import pytest
from app.models import Farm, Recommendation, User
from app.api.deps import get_authorized_recommendation
from app.utils.exceptions import RecommendationNotFoundError

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------
def register_and_login(client, username, password):
    client.post("/api/auth/register", json={"username": username, "password": password})
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def get_user_by_username(db, username):
    return db.query(User).filter(User.username == username).first()


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

def test_farm_creation_ownership(client, auth_headers, test_db_engine):
    """TEST 1: Farm creation ownership."""
    # Test user is created by auth_headers fixture ("test_user")
    from sqlalchemy.orm import Session
    
    resp = client.post("/api/farms", json={"lat": 18.52, "lon": 73.85}, headers=auth_headers)
    assert resp.status_code == 200
    farm_id = resp.json()["id"]

    with Session(test_db_engine) as db:
        user = get_user_by_username(db, "test_user")
        farm = db.query(Farm).filter(Farm.id == farm_id).first()
        assert farm.user_id == user.id


def test_user_can_access_own_farm(client, auth_headers):
    """TEST 2: User A can access own farm."""
    client.post("/api/farms", json={"lat": 19.0, "lon": 72.0}, headers=auth_headers)
    resp = client.get("/api/farms", headers=auth_headers)
    assert resp.status_code == 200
    farms = resp.json()
    assert len(farms) >= 1
    assert any(f["latitude"] == 19.0 for f in farms)


def test_user_cannot_access_others_farm(client, test_db_engine):
    """TEST 3: User B cannot access User A's farm."""
    token_a = register_and_login(client, "user_a", "password123")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    token_b = register_and_login(client, "user_b", "password123")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    client.post("/api/farms", json={"lat": 20.0, "lon": 74.0}, headers=headers_a)

    resp_b = client.get("/api/farms", headers=headers_b)
    assert resp_b.status_code == 200
    farms = resp_b.json()
    assert len(farms) == 0


def test_recommendation_owned_by_farm_and_user(client, auth_headers, test_db_engine):
    """TEST 4: Recommendation is owned by Farm."""
    from sqlalchemy.orm import Session
    
    resp = client.post("/api/recommend", json={"lat": 21.0, "lon": 75.0}, headers=auth_headers)
    assert resp.status_code == 200
    rec_id = resp.json()["id"]

    with Session(test_db_engine) as db:
        user = get_user_by_username(db, "test_user")
        rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
        assert rec is not None
        farm = db.query(Farm).filter(Farm.id == rec.farm_id).first()
        
        assert farm is not None
        assert farm.user_id == user.id


def test_user_can_access_own_recommendation(client, auth_headers, test_db_engine):
    """TEST 5: User A can access own recommendation."""
    from sqlalchemy.orm import Session
    
    resp = client.post("/api/recommend", json={"lat": 21.5, "lon": 75.5}, headers=auth_headers)
    assert resp.status_code == 200
    rec_id = resp.json()["id"]

    with Session(test_db_engine) as db:
        user = get_user_by_username(db, "test_user")
        # Direct helper check
        rec = get_authorized_recommendation(rec_id, user, db)
        assert rec.id == rec_id


def test_user_cannot_access_others_recommendation(client, test_db_engine):
    """TEST 6: User B cannot access User A's recommendation."""
    from sqlalchemy.orm import Session
    
    token_a = register_and_login(client, "user_c", "password123")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    resp = client.post("/api/recommend", json={"lat": 22.0, "lon": 76.0}, headers=headers_a)
    assert resp.status_code == 200
    rec_id = resp.json()["id"]

    token_b = register_and_login(client, "user_d", "password123")

    with Session(test_db_engine) as db:
        user_b = get_user_by_username(db, "user_d")
        
        with pytest.raises(RecommendationNotFoundError):
            get_authorized_recommendation(rec_id, user_b, db)


def test_chat_prerequisite_authorization(client, test_db_engine):
    """TEST 7: Chat prerequisite authorization.

    Directly exercises both directions of get_authorized_recommendation()
    — the same primitive Phase 2.3 will call from POST /api/ai/chat.

    CASE A — legitimate owner is ALLOWED.
    CASE B — non-owner is DENIED with RecommendationNotFoundError,
              which means no AI/LLM processing could ever proceed.
    """
    from sqlalchemy.orm import Session

    # --- Setup User A with a real recommendation ---
    token_a = register_and_login(client, "chat_prereq_user_a", "password123")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    resp = client.post("/api/recommend", json={"lat": 17.5, "lon": 78.5}, headers=headers_a)
    assert resp.status_code == 200, f"Recommendation creation failed: {resp.text}"
    rec_id = resp.json()["id"]

    # --- Setup User B (no farms, no recommendations) ---
    register_and_login(client, "chat_prereq_user_b", "password123")

    with Session(test_db_engine) as db:
        user_a = get_user_by_username(db, "chat_prereq_user_a")
        user_b = get_user_by_username(db, "chat_prereq_user_b")

        # CASE A — owner is authorized
        authorized_rec = get_authorized_recommendation(rec_id, user_a, db)
        assert authorized_rec.id == rec_id, (
            "Owner should be granted access to their own recommendation."
        )

        # CASE B — non-owner is denied BEFORE any AI/LLM operation could occur
        with pytest.raises(RecommendationNotFoundError):
            get_authorized_recommendation(rec_id, user_b, db)



def test_missing_recommendation_handling(client, auth_headers, test_db_engine):
    """TEST 8: Missing recommendation."""
    from sqlalchemy.orm import Session
    with Session(test_db_engine) as db:
        user = get_user_by_username(db, "test_user")
        
        with pytest.raises(RecommendationNotFoundError):
            get_authorized_recommendation(999999, user, db)


def test_user_id_cannot_be_spoofed(client, auth_headers, test_db_engine):
    """TEST 9: User ID cannot be spoofed."""
    from sqlalchemy.orm import Session
    
    # We pass user_id = 9999 in the body to try and spoof it
    resp = client.post("/api/farms", json={"lat": 23.0, "lon": 77.0, "user_id": 9999}, headers=auth_headers)
    assert resp.status_code == 200
    farm_id = resp.json()["id"]

    with Session(test_db_engine) as db:
        user = get_user_by_username(db, "test_user")
        farm = db.query(Farm).filter(Farm.id == farm_id).first()
        
        assert farm.user_id == user.id
        assert farm.user_id != 9999
