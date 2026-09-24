import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user
from app.models.user import User


@pytest.fixture
def client():
    mock_user = User(id=1, username="testuser", hashed_password="fake")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def test_recommendation_api_runtime_contract_unavailable_satellite(client):
    payload = {"lat": 18.6116, "lon": 73.9553}
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "crop_ranking" in data
    assert len(data["crop_ranking"]) == 8
    
    prov = data.get("provenance", {})
    sat_source = prov.get("satellite_source")
    if sat_source == "unavailable":
        assert data["ndvi"] is None
        assert data["ndvi_status"] == "unavailable"
    else:
        assert data["ndvi"] is not None
        assert isinstance(data["ndvi"], float)


def test_recommendation_api_ranking_integrity(client):
    payload = {"lat": 18.6116, "lon": 73.9553}
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    ranking = data["crop_ranking"]
    # Verify ranking is strictly sorted by TOPSIS closeness coefficient descending
    closeness_scores = [c["topsis_closeness"] for c in ranking]
    assert closeness_scores == sorted(closeness_scores, reverse=True)
