"""
tests/test_ai_chat_api.py — Phase 2.3

Integration tests for POST /api/ai/chat.

Design conventions (same as existing test files):
  - Isolated SQLite DB per test (conftest.py fixtures).
  - External services (weather/soil/satellite) mocked via monkeypatch
    at the recommend_route module level — no real network calls.
  - LLM calls mocked via monkeypatch on llm_module.call_llm — no real
    OpenAI calls.
  - The HTTP route, authorization layer, Phase 2.2 context loader,
    and Phase 2.1 grounding pipeline all execute for real.
"""

from __future__ import annotations

import pytest

from app.services.weather_service import WeatherResult
from app.services.soil_service import SoilResult
from app.services.satellite_service import SatelliteResult
import app.api.routes.recommend as recommend_route
import app.services.ai.llm_client as llm_module
from app.models import AIInteraction, Recommendation

# ---------------------------------------------------------------------------
# Shared fake service data
# ---------------------------------------------------------------------------

FAKE_WEATHER = WeatherResult(
    rainfall_mm_last_30d=80.0, avg_temp_c=26.0, humidity_pct=62.0,
    solar_radiation_mj_m2=17.0, wind_speed_m_s=2.0, source="nasa-power",
)
FAKE_SOIL = SoilResult(
    ph=6.5, clay_pct=25.0, sand_pct=30.0, soil_moisture_pct=28.0,
    nitrogen_total_mg_kg=40.0, organic_carbon_g_kg=16.0, source="soilgrids",
)
FAKE_SAT = SatelliteResult(ndvi=0.55, source="gee-sentinel2", scene_date="2026-07-10")

# Different conditions to produce a clearly different crop ranking
FAKE_WEATHER_B = WeatherResult(
    rainfall_mm_last_30d=12.0, avg_temp_c=40.0, humidity_pct=10.0,
    solar_radiation_mj_m2=30.0, wind_speed_m_s=6.0, source="nasa-power",
)
FAKE_SOIL_B = SoilResult(
    ph=8.3, clay_pct=8.0, sand_pct=75.0, soil_moisture_pct=4.0,
    nitrogen_total_mg_kg=5.0, organic_carbon_g_kg=2.0, source="soilgrids",
)
FAKE_SAT_B = SatelliteResult(ndvi=0.15, source="gee-sentinel2", scene_date="2026-07-20")


def _patch_services(monkeypatch, weather=FAKE_WEATHER, soil=FAKE_SOIL, sat=FAKE_SAT):
    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: weather)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: soil)
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: sat)


def _make_recommendation(client, auth_headers, monkeypatch, lat=18.0, lon=73.0,
                          weather=FAKE_WEATHER, soil=FAKE_SOIL, sat=FAKE_SAT):
    _patch_services(monkeypatch, weather=weather, soil=soil, sat=sat)
    resp = client.post("/api/recommend", json={"lat": lat, "lon": lon}, headers=auth_headers)
    assert resp.status_code == 200, f"Recommendation failed: {resp.text}"
    return resp.json()


def _register_and_login(client, username, password="password123"):
    client.post("/api/auth/register", json={"username": username, "password": password})
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_chat_defaults_to_english_when_language_missing(client, auth_headers, monkeypatch):
    """Missing language should be treated as English for backward compatibility."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    captured = {}

    def fake_call_llm(system_prompt, user_message):
        captured["prompt"] = system_prompt
        return "This crop is recommended because it has the highest TOPSIS score."

    monkeypatch.setattr(llm_module, "call_llm", fake_call_llm)

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "Why this crop?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert "Respond in English" in captured["prompt"]


def test_hindi_chat_uses_language_instruction(client, auth_headers, monkeypatch):
    """The same grounded AI flow should be instructed to answer in Hindi."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    captured = {}

    def fake_call_llm(system_prompt, user_message):
        captured["prompt"] = system_prompt
        return "यह फसल सबसे अधिक TOPSIS स्कोर के कारण सिफारिश की गई है।"

    monkeypatch.setattr(llm_module, "call_llm", fake_call_llm)

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "कौन सी फसल सिफारिश की गई है?", "language": "hi"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert "Respond in Hindi" in captured["prompt"]
    assert "यह फसल" in resp.json()["answer"]


def test_marathi_chat_uses_language_instruction(client, auth_headers, monkeypatch):
    """The same grounded AI flow should be instructed to answer in Marathi."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    captured = {}

    def fake_call_llm(system_prompt, user_message):
        captured["prompt"] = system_prompt
        return "ही फसल सर्वाधिक TOPSIS गुणांकामुळे शिफारस केली गेली आहे."

    monkeypatch.setattr(llm_module, "call_llm", fake_call_llm)

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "कोणती फसल शिफारस केली गेली आहे?", "language": "mr"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert "Respond in Marathi" in captured["prompt"]
    assert "ही फसल" in resp.json()["answer"]


def test_unsupported_language_falls_back_to_english(client, auth_headers, monkeypatch):
    """Unsupported language input should safely fall back to English without crashing."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    captured = {}

    def fake_call_llm(system_prompt, user_message):
        captured["prompt"] = system_prompt
        return "This crop is recommended because it has the highest TOPSIS score."

    monkeypatch.setattr(llm_module, "call_llm", fake_call_llm)

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "Why this crop?", "language": "fr"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert "Respond in English" in captured["prompt"]


def test_placeholder_llm_key_is_not_reported_as_configured(client, monkeypatch):
    """A placeholder value like sk-your_actual_api_key_here must not count as a valid key."""
    monkeypatch.setattr("app.config.settings.llm_api_key", "sk-your_actual_api_key_here")

    resp = client.get("/api/ai/health")
    assert resp.status_code == 200
    assert resp.json()["llm_configured"] is False


# ---------------------------------------------------------------------------
# TEST 1 — Authenticated owner can chat
# ---------------------------------------------------------------------------

def test_authenticated_owner_can_chat(client, auth_headers, monkeypatch):
    """Happy path: owner asks a question, gets a grounded answer."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    top_crop = rec["crop_ranking"][0]["crop"]

    monkeypatch.setattr(
        llm_module, "call_llm",
        lambda system_prompt, user_message: (
            f"Based on the recommendation, {top_crop} is the top crop."
        ),
    )

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "Why was this crop recommended?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "answer" in body
    assert len(body["answer"]) > 0
    assert body["context_snapshot_id"] == rec_id


# ---------------------------------------------------------------------------
# TEST 2 — Unauthenticated request is rejected
# ---------------------------------------------------------------------------

def test_unauthenticated_request_rejected(client, monkeypatch):
    """No token → authentication failure, LLM never called."""
    llm_called = []
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "x")

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": 1, "question": "Why?"},
    )
    assert resp.status_code == 401
    assert len(llm_called) == 0


# ---------------------------------------------------------------------------
# TEST 3 — Nonexistent recommendation → 404
# ---------------------------------------------------------------------------

def test_nonexistent_recommendation_returns_404(client, auth_headers, monkeypatch):
    """Recommendation 999999999 does not exist → safe not-found error."""
    llm_called = []
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "x")

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": 999999999, "question": "Why?"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "recommendation_not_found"
    assert len(llm_called) == 0


# ---------------------------------------------------------------------------
# TEST 4 — Cross-user access denied (most important security test)
# ---------------------------------------------------------------------------

def test_cross_user_access_denied(client, monkeypatch):
    """
    User B must NOT access User A's recommendation.
    Authorization must fire BEFORE context loading AND before any LLM call.
    """
    headers_a = _register_and_login(client, "chat_user_a_t4")
    headers_b = _register_and_login(client, "chat_user_b_t4")

    # User A creates a recommendation
    rec = _make_recommendation(client, headers_a, monkeypatch, lat=10.0, lon=76.0)
    rec_id_a = rec["id"]

    # Track whether context_loader and LLM are called
    context_loader_called = []
    llm_called = []

    import app.services.ai.context_loader as ctx_loader_module
    original_get_context = ctx_loader_module.get_context_for_recommendation

    def tracking_get_context(*args, **kwargs):
        context_loader_called.append(1)
        return original_get_context(*args, **kwargs)

    monkeypatch.setattr(ctx_loader_module, "get_context_for_recommendation", tracking_get_context)
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "x")

    # User B attempts to access User A's recommendation
    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id_a, "question": "What crop was recommended?"},
        headers=headers_b,
    )

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["error"]["code"] == "recommendation_not_found"
    assert len(context_loader_called) == 0, "context_loader must NOT be called if authorization fails"
    assert len(llm_called) == 0, "LLM must NOT be called if authorization fails"


# ---------------------------------------------------------------------------
# TEST 5 — Real persisted context is used
# ---------------------------------------------------------------------------

def test_real_persisted_context_is_used(client, auth_headers, monkeypatch, test_db_engine):
    """The FarmContext used must match the persisted recommendation fields."""
    from sqlalchemy.orm import Session

    rec = _make_recommendation(client, auth_headers, monkeypatch, lat=11.0, lon=77.0)
    rec_id = rec["id"]
    top_crop = rec["crop_ranking"][0]["crop"]
    persisted_ndvi = rec["ndvi"]

    captured_contexts = []

    import app.services.ai.assistant_service as svc
    original_answer = svc.answer_farm_question

    def capturing_answer(context, question, db):
        captured_contexts.append(context)
        return original_answer(context=context, question=question, db=db)

    monkeypatch.setattr(svc, "answer_farm_question", capturing_answer)
    monkeypatch.setattr(
        llm_module, "call_llm",
        lambda system_prompt, user_message: f"The top crop is {top_crop}.",
    )

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "What is the top crop?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text

    assert len(captured_contexts) == 1
    ctx = captured_contexts[0]
    assert ctx.recommendation_id == rec_id
    assert ctx.crop_ranking[0].crop == top_crop
    assert ctx.ndvi == persisted_ndvi
    assert ctx.ndvi_available is True


# ---------------------------------------------------------------------------
# TEST 6 — Grounded answer passes
# ---------------------------------------------------------------------------

def test_grounded_answer_passes(client, auth_headers, monkeypatch):
    """An answer referencing the actual top crop should have grounding_passed via context."""
    rec = _make_recommendation(client, auth_headers, monkeypatch, lat=12.0, lon=74.0)
    rec_id = rec["id"]
    top_crop = rec["crop_ranking"][0]["crop"]

    monkeypatch.setattr(
        llm_module, "call_llm",
        lambda system_prompt, user_message: (
            f"Based on the recommendation, {top_crop} is the top crop for your farm."
        ),
    )

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "What crop should I grow?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert top_crop.lower() in body["answer"].lower()


# ---------------------------------------------------------------------------
# TEST 7 — Hallucinated answer: grounding rejects then uses fallback
# ---------------------------------------------------------------------------

def test_hallucinated_answer_triggers_grounding_fallback(client, auth_headers, monkeypatch):
    """
    An answer containing a crop that isn't in the ranking should be rejected by
    Phase 2.1 grounding. The fallback message must be returned instead.
    """
    rec = _make_recommendation(client, auth_headers, monkeypatch, lat=13.0, lon=75.0)
    rec_id = rec["id"]

    # Return a crop name that is guaranteed not in the ranking
    monkeypatch.setattr(
        llm_module, "call_llm",
        lambda system_prompt, user_message: (
            "Durian is the absolute best crop for your farm with 99% yield increase."
        ),
    )

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "What crop should I grow?"},
        headers=auth_headers,
    )
    # The route must succeed (HTTP 200) — grounding uses safe fallback, not HTTP 500
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # The hallucinated crop name must NOT be in the final answer
    assert "Durian" not in body["answer"], "Hallucinated crop must not appear in final answer"


# ---------------------------------------------------------------------------
# TEST 8 — AIInteraction linkage
# ---------------------------------------------------------------------------

def test_ai_interaction_persists_real_recommendation_id(
    client, auth_headers, monkeypatch, test_db_engine
):
    """AIInteraction.recommendation_id must equal the requested recommendation_id."""
    from sqlalchemy.orm import Session

    rec = _make_recommendation(client, auth_headers, monkeypatch, lat=14.0, lon=76.0)
    rec_id = rec["id"]
    top_crop = rec["crop_ranking"][0]["crop"]

    monkeypatch.setattr(
        llm_module, "call_llm",
        lambda system_prompt, user_message: f"The top crop is {top_crop}.",
    )

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "What was recommended?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text

    with Session(test_db_engine) as db:
        interaction = (
            db.query(AIInteraction)
            .filter(AIInteraction.recommendation_id == rec_id)
            .order_by(AIInteraction.id.desc())
            .first()
        )
        assert interaction is not None, "AIInteraction must be persisted"
        assert interaction.recommendation_id == rec_id, (
            f"AIInteraction.recommendation_id ({interaction.recommendation_id}) "
            f"!= requested rec_id ({rec_id})"
        )
        assert interaction.recommendation_id is not None


# ---------------------------------------------------------------------------
# TEST 9 — Different recommendations produce different contexts
# ---------------------------------------------------------------------------

def test_different_recommendations_use_correct_contexts(
    client, auth_headers, monkeypatch, test_db_engine
):
    """
    Two recommendations with very different conditions must produce
    different FarmContexts — the endpoint must not reuse a cached/global
    recommendation.
    """
    # Recommendation A — lush conditions
    rec_a = _make_recommendation(
        client, auth_headers, monkeypatch, lat=15.0, lon=73.0,
        weather=FAKE_WEATHER, soil=FAKE_SOIL, sat=FAKE_SAT,
    )
    rec_id_a = rec_a["id"]
    top_crop_a = rec_a["crop_ranking"][0]["crop"]

    # Recommendation B — dry/harsh conditions, guaranteed different top crop
    rec_b = _make_recommendation(
        client, auth_headers, monkeypatch, lat=16.0, lon=73.0,
        weather=FAKE_WEATHER_B, soil=FAKE_SOIL_B, sat=FAKE_SAT_B,
    )
    rec_id_b = rec_b["id"]
    top_crop_b = rec_b["crop_ranking"][0]["crop"]

    captured = {}

    import app.services.ai.assistant_service as svc
    original_answer = svc.answer_farm_question

    def capturing_answer(context, question, db):
        captured[context.recommendation_id] = context
        return original_answer(context=context, question=question, db=db)

    monkeypatch.setattr(svc, "answer_farm_question", capturing_answer)

    # Mock LLM to mention the respective top crop for each request
    def dynamic_llm(system_prompt, user_message):
        if top_crop_a in system_prompt:
            return f"The top crop is {top_crop_a}."
        return f"The top crop is {top_crop_b}."

    monkeypatch.setattr(llm_module, "call_llm", dynamic_llm)

    client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id_a, "question": "What is the top crop?"},
        headers=auth_headers,
    )
    client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id_b, "question": "What is the top crop?"},
        headers=auth_headers,
    )

    assert rec_id_a in captured, "Context for rec A was not captured"
    assert rec_id_b in captured, "Context for rec B was not captured"
    assert captured[rec_id_a].crop_ranking[0].crop == top_crop_a
    assert captured[rec_id_b].crop_ranking[0].crop == top_crop_b


# ---------------------------------------------------------------------------
# TEST 10 — LLM failure is handled safely
# ---------------------------------------------------------------------------

def test_llm_failure_returns_safe_error(client, auth_headers, monkeypatch):
    """LLM provider failure → AIServiceUnavailableError (HTTP 502), no raw exception leak."""
    from app.utils.exceptions import AIServiceUnavailableError

    rec = _make_recommendation(client, auth_headers, monkeypatch, lat=17.0, lon=78.0)
    rec_id = rec["id"]

    def failing_llm(system_prompt, user_message):
        raise AIServiceUnavailableError("LLM provider connection refused.")

    monkeypatch.setattr(llm_module, "call_llm", failing_llm)

    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": rec_id, "question": "What crop?"},
        headers=auth_headers,
    )
    assert resp.status_code == 502, f"Expected 502, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["error"]["code"] == "ai_service_unavailable"
    # Ensure no API key or stack trace was leaked
    resp_text = resp.text
    assert "Traceback" not in resp_text
    assert "API_KEY" not in resp_text.upper()


# ---------------------------------------------------------------------------
# TEST 11 — Empty question validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_question", ["", "   ", "\n\t", "\t  \n"])
def test_empty_question_rejected(client, auth_headers, bad_question):
    """Whitespace-only or empty questions must be rejected with HTTP 422."""
    resp = client.post(
        "/api/ai/chat",
        json={"recommendation_id": 1, "question": bad_question},
        headers=auth_headers,
    )
    assert resp.status_code == 422
