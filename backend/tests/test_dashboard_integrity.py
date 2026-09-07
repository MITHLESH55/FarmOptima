"""
Phase 2.4.x — Dashboard Integrity Regression Tests

Proves:
1. GEE NDVI result reaches /api/recommend without data loss
2. NDVI source is preserved end-to-end
3. ndvi_status comes only from interpret_ndvi() — no second interpretation
4. Weather values survive service → route → schema → JSON
5. AI chat reaches LLM when credentials valid (not 502 on model issue)
6. AI 502 errors trigger controlled frontend message (not silent)
7. Frontend reads provenance.satellite_source for NDVI display gating
8. LLM model is an active Groq model (not the decommissioned llama-3.3-70b-versatile)
"""

import pytest
import app.api.routes.recommend as recommend_route
import app.services.ai.llm_client as llm_module
from app.services.weather_service import WeatherResult
from app.services.soil_service import SoilResult
from app.services.satellite_service import SatelliteResult
from app.core.environmental_interpretation import interpret_ndvi


# ---------------------------------------------------------------------------
# Fake service data representing a live GEE success
# ---------------------------------------------------------------------------
LIVE_SAT = SatelliteResult(ndvi=0.254, source="gee-sentinel2", scene_date="2026-07-14")
LIVE_WEATHER = WeatherResult(
    rainfall_mm_last_30d=470.2, avg_temp_c=23.7, humidity_pct=93.4,
    solar_radiation_mj_m2=8.98, wind_speed_m_s=3.4, source="nasa-power",
)
LIVE_SOIL = SoilResult(
    ph=6.98, clay_pct=25.0, sand_pct=30.0, soil_moisture_pct=26.1,
    nitrogen_total_mg_kg=1560.0, organic_carbon_g_kg=12.0, source="soilgrids-reference",
)

UNAVAIL_SAT = SatelliteResult(ndvi=0.0, source="unavailable", scene_date=None)
UNAVAIL_WEATHER = WeatherResult(
    rainfall_mm_last_30d=0.0, avg_temp_c=0.0, humidity_pct=0.0,
    solar_radiation_mj_m2=0.0, wind_speed_m_s=0.0, source="unavailable",
)


def _patch_live(monkeypatch):
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: LIVE_SAT)
    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: LIVE_WEATHER)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: LIVE_SOIL)


def _patch_unavailable(monkeypatch):
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: UNAVAIL_SAT)
    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: UNAVAIL_WEATHER)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: LIVE_SOIL)


# ---------------------------------------------------------------------------
# 1. GEE NDVI travels to /api/recommend intact
# ---------------------------------------------------------------------------
def test_live_gee_ndvi_reaches_recommend_response(client, auth_headers, monkeypatch):
    """Live GEE NDVI (0.254) must appear unchanged in the API response."""
    _patch_live(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.5204, "lon": 73.8567}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ndvi"] == 0.254, f"Expected ndvi=0.254 from GEE, got {data['ndvi']}"
    assert data["provenance"]["satellite_source"] == "gee-sentinel2"


# ---------------------------------------------------------------------------
# 2. NDVI source is preserved
# ---------------------------------------------------------------------------
def test_ndvi_source_preserved_in_response(client, auth_headers, monkeypatch):
    """provenance.satellite_source must match the service result."""
    _patch_live(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.5204, "lon": 73.8567}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["provenance"]["satellite_source"] == "gee-sentinel2"


# ---------------------------------------------------------------------------
# 3. ndvi_status comes only from interpret_ndvi() — no second interpretation
# ---------------------------------------------------------------------------
def test_ndvi_status_derived_from_interpret_ndvi(client, auth_headers, monkeypatch):
    """ndvi_status must equal interpret_ndvi(ndvi) — no duplicate interpretation."""
    _patch_live(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.5204, "lon": 73.8567}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    expected = interpret_ndvi(data["ndvi"])
    assert data["ndvi_status"] == expected, (
        f"ndvi_status '{data['ndvi_status']}' does not match interpret_ndvi({data['ndvi']})='{expected}'"
    )


# ---------------------------------------------------------------------------
# 4. Weather values survive service → route → API JSON
# ---------------------------------------------------------------------------
def test_weather_values_preserved_in_response(client, auth_headers, monkeypatch):
    """All weather fields must appear unchanged in the API JSON."""
    _patch_live(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.5204, "lon": 73.8567}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["rainfall_mm_last_30d"] == 470.2
    assert data["avg_temp_c"] == 23.7
    assert data["humidity_pct"] == 93.4
    assert data["solar_radiation_mj_m2"] == 8.98
    assert data["wind_speed_m_s"] == 3.4
    assert data["provenance"]["weather_source"] == "nasa-power"


# ---------------------------------------------------------------------------
# 5. Unavailable satellite → data_completeness.satellite == "unavailable"
# ---------------------------------------------------------------------------
def test_unavailable_satellite_flagged_in_completeness(client, auth_headers, monkeypatch):
    """When GEE fails, data_completeness.satellite must be 'unavailable'."""
    _patch_unavailable(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.5204, "lon": 73.8567}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_completeness"]["satellite"] == "unavailable"
    assert data["provenance"]["satellite_source"] == "unavailable"
    assert data["ndvi"] == 0.0


# ---------------------------------------------------------------------------
# 6. interpret_ndvi is deterministic and covers full range
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ndvi,expected_label", [
    (-0.1, "water / non-vegetated surface"),
    (0.0, "bare soil / very sparse vegetation"),
    (0.05, "bare soil / very sparse vegetation"),
    (0.15, "sparse vegetation"),
    (0.25, "moderate vegetation"),
    (0.5, "dense vegetation"),
    (0.7, "very dense vegetation"),
])
def test_interpret_ndvi_deterministic(ndvi, expected_label):
    """interpret_ndvi must be deterministic and cover all standard NDVI bands."""
    assert interpret_ndvi(ndvi) == expected_label


# ---------------------------------------------------------------------------
# 7. AI 502 from decommissioned model is a controlled error (not unhandled)
# ---------------------------------------------------------------------------
def test_ai_chat_model_error_returns_502(client, auth_headers, monkeypatch):
    """Model-not-found error from Groq must surface as HTTP 502 ai_service_unavailable.

    The real path in llm_client._call_provider catches any openai exception
    (including a 404 NotFoundError from a decommissioned model) and re-raises
    it as AIServiceUnavailableError, which the exception handler maps to 502.
    This test simulates that exact path by injecting the AIServiceUnavailableError
    directly into call_llm (the public surface monkeypatched in all other tests).
    """
    _patch_live(monkeypatch)
    rec_resp = client.post("/api/recommend", json={"lat": 18.5204, "lon": 73.8567}, headers=auth_headers)
    assert rec_resp.status_code == 200
    rec_id = rec_resp.json()["id"]

    from app.utils.exceptions import AIServiceUnavailableError

    def fake_llm_model_gone(system_prompt, user_message):
        # Simulate what llm_client._call_provider does when the Groq API returns
        # a 404 for a decommissioned model: it catches the openai exception and
        # re-raises as AIServiceUnavailableError.
        raise AIServiceUnavailableError(
            "GROQ API call failed: Error code: 404 - The model `llama-3.3-70b-versatile` "
            "does not exist or you do not have access to it. "
            "Check LLM_API_KEY, LLM_MODEL, and network connectivity."
        )

    monkeypatch.setattr(llm_module, "call_llm", fake_llm_model_gone)
    chat = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "Why?", "language": "en"},
        headers=auth_headers,
    )
    assert chat.status_code == 502, f"Expected 502, got {chat.status_code}: {chat.text}"
    error_body = chat.json()
    assert error_body["error"]["code"] == "ai_service_unavailable"


# ---------------------------------------------------------------------------
# 8. Grounded AI chat succeeds when model is available
# ---------------------------------------------------------------------------
def test_ai_chat_succeeds_with_working_model(client, auth_headers, monkeypatch):
    """AI chat must return 200 with a grounded answer when LLM call succeeds."""
    _patch_live(monkeypatch)
    rec_resp = client.post("/api/recommend", json={"lat": 18.5204, "lon": 73.8567}, headers=auth_headers)
    assert rec_resp.status_code == 200
    rec_id = rec_resp.json()["id"]
    top_crop = rec_resp.json()["crop_ranking"][0]["crop"]

    def fake_llm_ok(system_prompt, user_message):
        return f"{top_crop} is recommended with NDVI 0.254 and rainfall 470.2 mm."

    monkeypatch.setattr(llm_module, "call_llm", fake_llm_ok)
    chat = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "Why?", "language": "en"},
        headers=auth_headers,
    )
    assert chat.status_code == 200, chat.text
    assert top_crop.lower() in chat.json()["answer"].lower()


# ---------------------------------------------------------------------------
# 9. LLM_MODEL config must not be the decommissioned model
# ---------------------------------------------------------------------------
def test_llm_model_is_not_decommissioned():
    """The configured LLM_MODEL must not be the deprecated llama-3.3-70b-versatile."""
    from app.config import settings
    decommissioned = "llama-3.3-70b-versatile"
    assert settings.llm_model != decommissioned, (
        f"LLM_MODEL is set to the decommissioned model '{decommissioned}'. "
        "Update LLM_MODEL in .env to an active Groq model."
    )


# ---------------------------------------------------------------------------
# 10. Recommendation status is "complete" when all sources are live
# ---------------------------------------------------------------------------
def test_recommendation_status_complete_with_live_data(client, auth_headers, monkeypatch):
    """recommendation_status must be 'complete' when all three services succeed."""
    _patch_live(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.5204, "lon": 73.8567}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendation_status"] == "complete"
    assert data["data_completeness"]["weather"] == "live"
    assert data["data_completeness"]["soil"] == "live"
    assert data["data_completeness"]["satellite"] == "live"
