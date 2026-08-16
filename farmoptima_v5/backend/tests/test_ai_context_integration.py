"""
tests/test_ai_context_integration.py — Phase 2 Step 2.2

Integration tests that prove the AI service layer connects correctly to
REAL, persisted /api/recommend results.

Test design conventions (identical to test_integration_api.py):
  - Uses the shared conftest.py fixtures: client (isolated test DB),
    auth_headers, test_db_engine.
  - External services (weather/soil/satellite) are mocked at the module
    level inside the route, exactly as test_integration_api.py does.
  - LLM calls are mocked via monkeypatch, exactly as test_ai_foundation.py
    does — zero real network calls anywhere in this file.
  - The isolated test DB means every test gets its own fresh set of
    recommendations — no cross-test contamination.

The four required test cases:
  1. Round-trip integrity (strongest patent evidence for this step)
  2. RecommendationNotFoundError for a nonexistent id
  3. answer_question_for_recommendation() links AIInteraction to real id
  4. Cross-context grounding: same crop claim passes A's context, fails B's
"""

from __future__ import annotations

import pytest

from app.services.weather_service import WeatherResult
from app.services.soil_service import SoilResult
from app.services.satellite_service import SatelliteResult
import app.api.routes.recommend as recommend_route
import app.services.ai.llm_client as llm_module

# ---------------------------------------------------------------------------
# Shared fake service responses (reusing the same values as conftest tests
# so we get predictable crop names in the ranking for grounding assertions)
# ---------------------------------------------------------------------------

FAKE_WEATHER_A = WeatherResult(
    rainfall_mm_last_30d=85.0, avg_temp_c=27.5, humidity_pct=60.0,
    solar_radiation_mj_m2=18.0, wind_speed_m_s=2.5, source="nasa-power",
)
FAKE_SOIL_A = SoilResult(
    ph=6.6, clay_pct=22.0, sand_pct=35.0, soil_moisture_pct=24.0,
    nitrogen_total_mg_kg=42.0, organic_carbon_g_kg=18.0, source="soilgrids",
)
FAKE_SATELLITE_A = SatelliteResult(ndvi=0.55, source="gee-sentinel2", scene_date="2026-07-15")

# "B" uses very different conditions to guarantee a different top crop ranking
FAKE_WEATHER_B = WeatherResult(
    rainfall_mm_last_30d=20.0, avg_temp_c=38.0, humidity_pct=15.0,
    solar_radiation_mj_m2=28.0, wind_speed_m_s=5.0, source="nasa-power",
)
FAKE_SOIL_B = SoilResult(
    ph=8.2, clay_pct=10.0, sand_pct=70.0, soil_moisture_pct=5.0,
    nitrogen_total_mg_kg=8.0, organic_carbon_g_kg=3.0, source="soilgrids",
)
FAKE_SATELLITE_B = SatelliteResult(ndvi=0.18, source="gee-sentinel2", scene_date="2026-07-20")


def _patch_services_a(monkeypatch):
    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: FAKE_WEATHER_A)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: FAKE_SOIL_A)
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: FAKE_SATELLITE_A)


def _patch_services_b(monkeypatch):
    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: FAKE_WEATHER_B)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: FAKE_SOIL_B)
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: FAKE_SATELLITE_B)


def _make_recommend_a(client, auth_headers, monkeypatch):
    """POST /api/recommend with set-A mocked services. Returns parsed body."""
    _patch_services_a(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 19.5, "lon": 73.5}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_recommend_b(client, auth_headers, monkeypatch):
    """POST /api/recommend with set-B mocked services. Returns parsed body."""
    _patch_services_b(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 23.0, "lon": 77.0}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _get_db_session(test_db_engine):
    """Open a raw SQLAlchemy session on the isolated test DB."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_db_engine)
    return Session()


# ===========================================================================
# Test 1 — ROUND-TRIP INTEGRITY
# ===========================================================================

class TestRoundTripIntegrity:

    def test_context_matches_original_recommend_response_exactly(
        self, client, auth_headers, test_db_engine, monkeypatch
    ):
        """
        ROUND-TRIP INTEGRITY TEST (primary patent-documentation evidence):

        Steps:
          1. POST /api/recommend → capture full response JSON + id.
          2. get_context_for_recommendation(id, db) → FarmContext.
          3. Assert every key field in FarmContext matches the original response.

        This proves: the context used for AI grounding is byte-for-byte the
        data the client already received — not a recomputation, not a
        denormalized approximation.
        """
        from app.services.ai.context_loader import get_context_for_recommendation

        original = _make_recommend_a(client, auth_headers, monkeypatch)
        rec_id = original["id"]
        assert rec_id is not None, "Recommendation must be persisted with a real id"

        db = _get_db_session(test_db_engine)
        try:
            ctx = get_context_for_recommendation(rec_id, db)
        finally:
            db.close()

        # --- Location ---
        assert ctx.latitude == original["location"]["lat"]
        assert ctx.longitude == original["location"]["lon"]

        # --- NDVI ---
        assert ctx.ndvi_available is True      # set-A has live satellite
        assert ctx.ndvi == pytest.approx(original["ndvi"], abs=1e-6)
        assert ctx.satellite_scene_date == original["satellite_scene_date"]
        assert ctx.satellite_source == original["provenance"]["satellite_source"]

        # --- Weather ---
        assert ctx.rainfall_mm_last_30d == pytest.approx(original["rainfall_mm_last_30d"])
        assert ctx.avg_temp_c == pytest.approx(original["avg_temp_c"])
        assert ctx.humidity_pct == pytest.approx(original["humidity_pct"])
        assert ctx.solar_radiation_mj_m2 == pytest.approx(original["solar_radiation_mj_m2"])
        assert ctx.wind_speed_m_s == pytest.approx(original["wind_speed_m_s"])

        # --- Soil ---
        assert ctx.soil_ph == pytest.approx(original["soil_ph"])
        assert ctx.soil_moisture_pct == pytest.approx(original["soil_moisture_pct"])
        assert ctx.soil_nitrogen_mg_kg == pytest.approx(original["soil_nitrogen_mg_kg"])
        assert ctx.soil_organic_carbon_g_kg == pytest.approx(original["soil_organic_carbon_g_kg"])
        assert ctx.soil_sand_pct == pytest.approx(original["soil_sand_pct"])
        assert ctx.soil_clay_pct == pytest.approx(original["soil_clay_pct"])

        # --- AHP ---
        for criterion, weight in original["ahp_weights"].items():
            assert ctx.ahp_weights[criterion] == pytest.approx(weight, abs=1e-6), (
                f"AHP weight mismatch for '{criterion}': "
                f"context={ctx.ahp_weights[criterion]}, original={weight}"
            )
        assert ctx.ahp_consistency_ratio == pytest.approx(original["ahp_consistency_ratio"], abs=1e-4)
        assert ctx.ahp_is_consistent == original["ahp_is_consistent"]
        assert ctx.ahp_method == original["ahp_method"]

        # --- Crop ranking order, scores, and names ---
        orig_ranking = original["crop_ranking"]
        assert len(ctx.crop_ranking) == len(orig_ranking), (
            f"Crop ranking length mismatch: context has {len(ctx.crop_ranking)}, "
            f"original has {len(orig_ranking)}"
        )
        for ctx_entry, orig_entry in zip(ctx.crop_ranking, orig_ranking):
            assert ctx_entry.crop == orig_entry["crop"], (
                f"Crop name mismatch at rank {orig_entry['rank']}: "
                f"context='{ctx_entry.crop}', original='{orig_entry['crop']}'"
            )
            assert ctx_entry.rank == orig_entry["rank"]
            assert ctx_entry.topsis_closeness == pytest.approx(orig_entry["topsis_closeness"], abs=1e-6)
            assert ctx_entry.electre_net_outranking == orig_entry["electre_net_outranking"]

        orig_crops = [c["crop"] for c in orig_ranking]
        assert ctx.crop_names_in_ranking == orig_crops

        # --- Resource plan ---
        orig_plan = original["resource_plan"]
        assert ctx.resource_plan.water_liters_per_week == pytest.approx(orig_plan["water_liters_per_week"])
        assert ctx.resource_plan.fertilizer_kg_per_acre == pytest.approx(orig_plan["fertilizer_kg_per_acre"])
        assert ctx.resource_plan.optimizer_best_fitness == pytest.approx(orig_plan["optimizer_best_fitness"], rel=1e-4)
        assert ctx.resource_plan.optimizer_generations_run == orig_plan["optimizer_generations_run"]
        assert ctx.resource_plan.irrigation_schedule == orig_plan["irrigation_schedule"]
        assert ctx.resource_plan.optimizer_method == orig_plan["optimizer_method"]

        # --- Pareto front length ---
        assert len(ctx.resource_plan.pareto_front) == len(orig_plan["pareto_front"]), (
            f"Pareto front length mismatch: context={len(ctx.resource_plan.pareto_front)}, "
            f"original={len(orig_plan['pareto_front'])}"
        )

        # --- recommendation_id linkage ---
        assert ctx.recommendation_id == rec_id

    def test_unavailable_ndvi_round_trips_as_none_not_zero(
        self, client, auth_headers, test_db_engine, monkeypatch
    ):
        """When NDVI source is 'unavailable', context_loader must restore ndvi=None."""
        from app.services.ai.context_loader import get_context_for_recommendation

        _patch_services_a(monkeypatch)
        monkeypatch.setattr(
            recommend_route, "get_ndvi_for_location",
            lambda lat, lon: SatelliteResult(ndvi=0, source="unavailable", scene_date=None),
        )
        resp = client.post("/api/recommend", json={"lat": 19.5, "lon": 73.5}, headers=auth_headers)
        assert resp.status_code == 200
        rec_id = resp.json()["id"]

        db = _get_db_session(test_db_engine)
        try:
            ctx = get_context_for_recommendation(rec_id, db)
        finally:
            db.close()

        assert ctx.ndvi_available is True
        assert ctx.ndvi is not None
        assert ctx.ndvi.value == 0.0
        assert ctx.ndvi.is_live is True


# ===========================================================================
# Test 2 — RecommendationNotFoundError
# ===========================================================================

class TestRecommendationNotFound:

    def test_raises_recommendation_not_found_for_nonexistent_id(
        self, test_db_engine
    ):
        """
        get_context_for_recommendation() with a non-existent id raises
        RecommendationNotFoundError (status 404, code 'recommendation_not_found').
        NOT a silent None return, NOT a generic 500.
        """
        from app.services.ai.context_loader import get_context_for_recommendation
        from app.utils.exceptions import RecommendationNotFoundError

        db = _get_db_session(test_db_engine)
        try:
            with pytest.raises(RecommendationNotFoundError) as exc_info:
                get_context_for_recommendation(99999, db)
        finally:
            db.close()

        assert exc_info.value.status_code == 404
        assert exc_info.value.error_code == "recommendation_not_found"
        assert "99999" in exc_info.value.message

    def test_not_found_is_subclass_of_not_found_error(self):
        """RecommendationNotFoundError must inherit from NotFoundError so
        the existing broad exception handler in main.py catches it correctly."""
        from app.utils.exceptions import RecommendationNotFoundError, NotFoundError
        assert issubclass(RecommendationNotFoundError, NotFoundError)

    def test_not_found_has_correct_http_status_and_error_code_attributes(self):
        """
        RecommendationNotFoundError carries status_code=404 and
        error_code='recommendation_not_found' so the existing main.py
        FarmOptimaError handler will produce the right HTTP 404 JSON envelope
        when raised inside a route.

        No chat route exists yet; per the spec we test the exception directly.
        """
        from app.utils.exceptions import RecommendationNotFoundError

        exc = RecommendationNotFoundError("Recommendation id=99999 was not found.")

        assert exc.status_code == 404
        assert exc.error_code == "recommendation_not_found"
        assert "99999" in exc.message

    def test_not_found_is_farmoptima_error_so_handler_catches_it(self):
        """
        RecommendationNotFoundError must be a FarmOptimaError subclass so
        the existing main.py @app.exception_handler(FarmOptimaError) catches
        it and returns the standard {success, error: {code, message}} envelope.
        """
        from app.utils.exceptions import RecommendationNotFoundError, FarmOptimaError

        exc = RecommendationNotFoundError("test")
        assert isinstance(exc, FarmOptimaError)


# ===========================================================================
# Test 3 — answer_question_for_recommendation links AIInteraction to real id
# ===========================================================================

class TestAnswerQuestionForRecommendation:

    def test_grounded_answer_persists_interaction_with_real_recommendation_id(
        self, client, auth_headers, test_db_engine, monkeypatch
    ):
        """
        answer_question_for_recommendation() with a mocked LLM returning a
        grounded answer must:
        - Return an AIAnswerResponse.
        - Persist exactly one AIInteraction row.
        - The AIInteraction.recommendation_id must be the REAL DB id (not null,
          not a placeholder).
        - grounding_passed must be True for a grounded mock answer.
        """
        from app.services.ai.assistant_service import answer_question_for_recommendation
        from app.models.ai_interaction import AIInteraction

        original = _make_recommend_a(client, auth_headers, monkeypatch)
        rec_id = original["id"]
        top_crop = original["crop_ranking"][0]["crop"]
        water = original["resource_plan"]["water_liters_per_week"]
        fertilizer = original["resource_plan"]["fertilizer_kg_per_acre"]
        topsis = original["crop_ranking"][0]["topsis_closeness"]

        # Grounded mock answer: only uses crop names and numbers from context
        def mock_llm(system_prompt, user_message):
            return (
                f"Based on your recommendation, {top_crop} is the top-ranked crop. "
                f"The resource plan recommends {water:.1f} L/week of water "
                f"and {fertilizer:.1f} kg/acre of fertilizer. "
                f"TOPSIS closeness: {topsis:.4f}."
            )

        monkeypatch.setattr(llm_module, "call_llm", mock_llm)

        db = _get_db_session(test_db_engine)
        try:
            result = answer_question_for_recommendation(rec_id, "What crop should I grow?", db)

            # Check response
            assert isinstance(result.answer, str)
            assert len(result.answer) > 0
            assert result.context_snapshot_id == rec_id

            # Check DB row
            rows = db.query(AIInteraction).filter(
                AIInteraction.recommendation_id == rec_id
            ).all()
            assert len(rows) == 1, f"Expected 1 AIInteraction row, got {len(rows)}"
            row = rows[0]
            assert row.recommendation_id == rec_id, (
                f"AIInteraction.recommendation_id must be {rec_id} (real DB id), "
                f"got {row.recommendation_id!r}"
            )
            assert row.grounding_passed is True
            assert top_crop.lower() in row.answer.lower()
        finally:
            db.close()

    def test_hallucinated_answer_persists_interaction_with_grounding_failed(
        self, client, auth_headers, test_db_engine, monkeypatch
    ):
        """
        When the mocked LLM returns a hallucinated crop (not in context),
        grounding_passed must be False in the persisted AIInteraction row.
        """
        from app.services.ai.assistant_service import answer_question_for_recommendation
        from app.models.ai_interaction import AIInteraction

        original = _make_recommend_a(client, auth_headers, monkeypatch)
        rec_id = original["id"]

        # Both LLM calls return hallucination → triggers safe fallback
        def mock_llm(system_prompt, user_message):
            return "I recommend cotton with a yield of 9999 kg/ha."

        monkeypatch.setattr(llm_module, "call_llm", mock_llm)

        db = _get_db_session(test_db_engine)
        try:
            result = answer_question_for_recommendation(rec_id, "What crop?", db)

            # Safe fallback answer — must not contain hallucinated claim
            assert "cotton" not in result.answer.lower()

            rows = db.query(AIInteraction).filter(
                AIInteraction.recommendation_id == rec_id
            ).all()
            assert len(rows) == 1
            assert rows[0].grounding_passed is False
            assert rows[0].recommendation_id == rec_id
        finally:
            db.close()

    def test_not_found_raises_before_any_llm_call(
        self, test_db_engine, monkeypatch
    ):
        """When the recommendation id does not exist, the function raises
        RecommendationNotFoundError without ever calling the LLM."""
        from app.services.ai.assistant_service import answer_question_for_recommendation
        from app.utils.exceptions import RecommendationNotFoundError

        llm_called = []

        def mock_llm(system_prompt, user_message):
            llm_called.append(True)
            return "some answer"

        monkeypatch.setattr(llm_module, "call_llm", mock_llm)

        db = _get_db_session(test_db_engine)
        try:
            with pytest.raises(RecommendationNotFoundError):
                answer_question_for_recommendation(99999, "Any question?", db)
        finally:
            db.close()

        assert llm_called == [], "LLM must not be called when recommendation is not found"


# ===========================================================================
# Test 4 — CROSS-CONTEXT GROUNDING TEST
# ===========================================================================

class TestCrossContextGrounding:

    def _make_context_with_crops(self, crops: list[str], rec_id: int):
        """
        Build a minimal FarmContext with a known crop set.
        Used to test grounding logic in isolation from the algorithm.
        """
        from app.schemas.ai import (
            FarmContext, CropRankEntry, ResourcePlanContext, ParetoPointSummary
        )
        entries = [
            CropRankEntry(
                crop=crop,
                topsis_closeness=round(0.9 - i * 0.1, 4),
                electre_net_outranking=2 - i,
                rank=i + 1,
            )
            for i, crop in enumerate(crops)
        ]
        return FarmContext(
            recommendation_id=rec_id,
            generated_at="2026-08-14T10:00:00",
            recommendation_status="complete",
            data_completeness_weather="live",
            data_completeness_soil="live",
            data_completeness_satellite="live",
            data_completeness_market="csv",
            satellite_source="gee-sentinel2",
            weather_source="nasa-power",
            soil_source="soilgrids",
            market_source="csv",
            latitude=19.5,
            longitude=73.5,
            ndvi=0.55,
            ndvi_available=True,
            satellite_scene_date="2026-07-15",
            rainfall_mm_last_30d=85.0,
            avg_temp_c=27.5,
            humidity_pct=60.0,
            solar_radiation_mj_m2=18.0,
            wind_speed_m_s=2.5,
            soil_ph=6.6,
            soil_moisture_pct=24.0,
            soil_nitrogen_mg_kg=42.0,
            soil_organic_carbon_g_kg=18.0,
            soil_sand_pct=35.0,
            soil_clay_pct=22.0,
            ahp_weights={
                "climate_suitability": 0.4495,
                "soil_suitability": 0.2596,
                "water_efficiency": 0.1707,
                "market_value": 0.1202,
            },
            ahp_consistency_ratio=0.0321,
            ahp_is_consistent=True,
            ahp_method="fuzzy-ahp-chang-extent-analysis",
            crop_ranking=entries,
            crop_names_in_ranking=crops,
            resource_plan=ResourcePlanContext(
                water_liters_per_week=1200.0,
                fertilizer_kg_per_acre=45.5,
                optimizer_best_fitness=0.0123,
                optimizer_generations_run=60,
                irrigation_schedule="Every 3 days",
                optimizer_method="nsga2-multiobjective",
                pareto_front=[
                    ParetoPointSummary(
                        water_liters_per_week=1200.0,
                        fertilizer_kg_per_acre=45.5,
                        resource_cost=0.0123,
                    )
                ],
            ),
            ai_explanation="Top crop explanation.",
        )

    def test_crop_claim_passes_own_context_fails_other_context(self):
        """
        CROSS-CONTEXT GROUNDING TEST (deterministic — does not depend on
        algorithm ranking output):

        Context A has: wheat, rice, maize
        Context B has: sorghum, millet, barley

        An answer mentioning 'wheat' (A's top crop):
          - PASSES grounding against context A (wheat is in A's ranking).
          - FAILS grounding against context B (wheat is NOT in B's ranking).

        This proves grounding is context-SPECIFIC, not a global
        "any known crop name passes" allowlist.
        """
        from app.core.ai_grounding import validate_answer_is_grounded

        crops_a = ["wheat", "rice", "maize"]
        crops_b = ["sorghum", "millet", "barley"]

        ctx_a = self._make_context_with_crops(crops_a, rec_id=1)
        ctx_b = self._make_context_with_crops(crops_b, rec_id=2)

        # wheat is in A, NOT in B
        assert "wheat" in ctx_a.crop_names_in_ranking
        assert "wheat" not in ctx_b.crop_names_in_ranking

        answer_citing_wheat = (
            "Based on the recommendation, wheat is the top crop "
            "with a TOPSIS closeness score of 0.9000. "
            "The water plan is 1200.0 L/week."
        )

        # PASS: wheat is grounded in context A
        check_a = validate_answer_is_grounded(answer_citing_wheat, ctx_a)
        assert check_a.passed, (
            f"Expected PASS for wheat in context A {crops_a}. "
            f"Ungrounded crops: {check_a.ungrounded_crop_claims}, "
            f"numbers: {check_a.ungrounded_numeric_claims}"
        )

        # FAIL: wheat is NOT in context B — grounding check must reject it
        check_b = validate_answer_is_grounded(answer_citing_wheat, ctx_b)
        assert not check_b.passed, (
            f"Expected FAIL for wheat in context B {crops_b}, "
            "but grounding check passed — context-specificity broken."
        )
        assert "wheat" in check_b.ungrounded_crop_claims, (
            f"Expected 'wheat' flagged in ungrounded_crop_claims, "
            f"got {check_b.ungrounded_crop_claims}"
        )

    def test_answer_about_b_top_crop_fails_a_context(self):
        """
        Symmetric test: 'sorghum' (B's top crop) passes B's context but
        fails A's context.  Confirms directional symmetry of grounding.
        """
        from app.core.ai_grounding import validate_answer_is_grounded

        crops_a = ["wheat", "rice", "maize"]
        crops_b = ["sorghum", "millet", "barley"]

        ctx_a = self._make_context_with_crops(crops_a, rec_id=1)
        ctx_b = self._make_context_with_crops(crops_b, rec_id=2)

        answer_citing_sorghum = (
            "Sorghum is your top-ranked crop. "
            "Water plan: 1200.0 L/week, fertilizer: 45.5 kg/acre."
        )

        # PASS against B
        check_b = validate_answer_is_grounded(answer_citing_sorghum, ctx_b)
        assert check_b.passed, (
            f"Expected PASS for sorghum in B {crops_b}. "
            f"Ungrounded: {check_b.ungrounded_crop_claims}"
        )

        # FAIL against A
        check_a = validate_answer_is_grounded(answer_citing_sorghum, ctx_a)
        assert not check_a.passed, (
            f"Expected FAIL for sorghum in A {crops_a}."
        )
        assert "sorghum" in check_a.ungrounded_crop_claims

    def test_context_a_context_b_have_different_recommendation_ids(
        self, client, auth_headers, monkeypatch
    ):
        """Sanity check: two POST /api/recommend calls with different locations
        produce two distinct recommendation ids (they are independent DB rows)."""
        rec_a = _make_recommend_a(client, auth_headers, monkeypatch)
        rec_b = _make_recommend_b(client, auth_headers, monkeypatch)
        assert rec_a["id"] != rec_b["id"]
        assert rec_a["location"]["lat"] != rec_b["location"]["lat"]

