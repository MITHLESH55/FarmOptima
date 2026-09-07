"""
tests/test_ai_foundation.py — Phase 2 Step 2.1

Tests for the AI assistant backend foundation.

Test design follows the project's existing conventions exactly:
  - Pure-logic functions (context_builder, ai_grounding) are tested with
    ZERO network access — no LLM API calls.
  - llm_client and assistant_service are tested with the LLM call MOCKED
    using monkeypatch, exactly as test_integration_api.py mocks weather/
    soil/satellite services.
  - All 7 required test cases are implemented plus additional edge cases.

Running:
    cd backend
    python -m pytest tests/test_ai_foundation.py -v

No LLM API calls are made anywhere in this file.  The full suite (including
these tests) must pass with no network access and no LLM_API_KEY set.
"""

from __future__ import annotations

import os
import tempfile
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base

# ---------------------------------------------------------------------------
# Shared test data — a realistic RecommendationResponse-like payload
# ---------------------------------------------------------------------------

from app.schemas.recommendation import (
    RecommendationResponse,
    CropScore,
    ResourcePlan,
    ParetoPoint,
    DataCompleteness,
)
from app.schemas.common import LocationRequest, DataProvenance

SAMPLE_RECOMMENDATION = RecommendationResponse(
    id=42,
    location=LocationRequest(lat=19.5, lon=73.5),
    generated_at="2026-08-14T10:00:00",
    provenance=DataProvenance(
        satellite_source="gee-sentinel2",
        weather_source="nasa-power",
        soil_source="soilgrids",
        market_source="csv",
    ),
    data_completeness=DataCompleteness(
        weather="live", soil="live", satellite="live", market="csv"
    ),
    recommendation_status="complete",
    partial_data_reason=None,
    ndvi=0.55,
    satellite_scene_date="2026-07-15",
    satellite_tile_url=None,
    # Weather
    rainfall_mm_last_30d=85.0,
    avg_temp_c=27.5,
    humidity_pct=60.0,
    solar_radiation_mj_m2=18.0,
    wind_speed_m_s=2.5,
    # Soil
    soil_ph=6.6,
    soil_moisture_pct=24.0,
    soil_nitrogen_mg_kg=42.0,
    soil_organic_carbon_g_kg=18.0,
    soil_sand_pct=35.0,
    soil_clay_pct=22.0,
    # AHP
    ahp_weights={
        "climate_suitability": 0.4495,
        "soil_suitability": 0.2596,
        "water_efficiency": 0.1707,
        "market_value": 0.1202,
    },
    ahp_consistency_ratio=0.0321,
    ahp_is_consistent=True,
    ahp_method="fuzzy-ahp-chang-extent-analysis",
    top_crop_reference_ranges=None,
    crop_ranking=[
        CropScore(crop="wheat", topsis_closeness=0.7123, electre_net_outranking=2, rank=1),
        CropScore(crop="rice", topsis_closeness=0.6204, electre_net_outranking=1, rank=2),
        CropScore(crop="maize", topsis_closeness=0.5100, electre_net_outranking=0, rank=3),
    ],
    resource_plan=ResourcePlan(
        water_liters_per_week=1200.0,
        fertilizer_kg_per_acre=45.5,
        optimizer_best_fitness=0.0123,
        optimizer_generations_run=60,
        irrigation_schedule="Every 3 days",
        pareto_front=[
            ParetoPoint(water_liters_per_week=1200.0, fertilizer_kg_per_acre=45.5, water_gap=0.1, fertilizer_gap=0.2, resource_cost=0.0123),
            ParetoPoint(water_liters_per_week=1150.0, fertilizer_kg_per_acre=48.0, water_gap=0.15, fertilizer_gap=0.18, resource_cost=0.0145),
        ],
        optimizer_method="nsga2-multiobjective",
    ),
    ai_explanation=(
        "Why wheat? Among the currently evaluated crops, wheat has the highest "
        "TOPSIS closeness score (0.712), so it is closest to the ideal solution."
    ),
)

# A recommendation with unavailable NDVI (satellite source = "unavailable")
SAMPLE_REC_NO_NDVI = SAMPLE_RECOMMENDATION.model_copy(
    update={
        "ndvi": 0.0,  # pipeline sentinel when unavailable
        "provenance": DataProvenance(
            satellite_source="unavailable",
            weather_source="nasa-power",
            soil_source="soilgrids",
            market_source="csv",
        ),
        "data_completeness": DataCompleteness(
            weather="live", soil="live", satellite="unavailable", market="csv"
        ),
        "satellite_scene_date": None,
    }
)


# ---------------------------------------------------------------------------
# Fixtures: isolated SQLite DB per test (mirrors conftest.py)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def ai_db():
    """Fresh in-memory SQLite session for AI tests — no dev DB pollution."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    yield db
    db.close()
    engine.dispose()
    os.close(db_fd)
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Test 1 — build_farm_context() correctly maps every field
# ---------------------------------------------------------------------------

class TestBuildFarmContext:

    def test_maps_all_fields_from_full_recommendation(self):
        """build_farm_context maps every field 1:1 from RecommendationResponse."""
        from app.services.ai.context_builder import build_farm_context

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)

        # Provenance
        assert ctx.recommendation_id == 42
        assert ctx.recommendation_status == "complete"
        assert ctx.satellite_source == "gee-sentinel2"
        assert ctx.weather_source == "nasa-power"
        assert ctx.soil_source == "soilgrids"

        # Location
        assert ctx.latitude == 19.5
        assert ctx.longitude == 73.5

        # NDVI — should be live
        assert ctx.ndvi_available is True
        assert ctx.ndvi == 0.55
        assert ctx.satellite_scene_date == "2026-07-15"

        # Weather
        assert ctx.rainfall_mm_last_30d == 85.0
        assert ctx.avg_temp_c == 27.5
        assert ctx.humidity_pct == 60.0
        assert ctx.solar_radiation_mj_m2 == 18.0
        assert ctx.wind_speed_m_s == 2.5

        # Soil
        assert ctx.soil_ph == 6.6
        assert ctx.soil_moisture_pct == 24.0
        assert ctx.soil_nitrogen_mg_kg == 42.0
        assert ctx.soil_organic_carbon_g_kg == 18.0
        assert ctx.soil_sand_pct == 35.0
        assert ctx.soil_clay_pct == 22.0

        # AHP
        assert abs(ctx.ahp_weights["climate_suitability"] - 0.4495) < 1e-6
        assert ctx.ahp_consistency_ratio == 0.0321
        assert ctx.ahp_is_consistent is True
        assert ctx.ahp_method == "fuzzy-ahp-chang-extent-analysis"

        # Crop ranking
        assert len(ctx.crop_ranking) == 3
        assert ctx.crop_ranking[0].crop == "wheat"
        assert ctx.crop_ranking[0].rank == 1
        assert ctx.crop_ranking[1].crop == "rice"
        assert ctx.crop_ranking[2].crop == "maize"
        assert ctx.crop_names_in_ranking == ["wheat", "rice", "maize"]

        # Resource plan
        assert ctx.resource_plan.water_liters_per_week == 1200.0
        assert ctx.resource_plan.fertilizer_kg_per_acre == 45.5
        assert ctx.resource_plan.optimizer_best_fitness == 0.0123
        assert ctx.resource_plan.optimizer_generations_run == 60
        assert ctx.resource_plan.irrigation_schedule == "Every 3 days"
        assert len(ctx.resource_plan.pareto_front) == 2

        # AI explanation pass-through
        assert "wheat" in ctx.ai_explanation

    def test_unavailable_ndvi_is_explicitly_preserved_in_context(self):
        """A present NDVI value remains in the structured block even when the source label says unavailable."""
        from app.services.ai.context_builder import build_farm_context

        ctx = build_farm_context(SAMPLE_REC_NO_NDVI)

        assert ctx.ndvi is not None
        assert ctx.ndvi.value == 0.0
        assert ctx.ndvi.source == "unavailable"
        assert ctx.ndvi.is_live is True
        assert ctx.ndvi_available is True
        assert ctx.satellite_scene_date is None

    def test_mock_satellite_source_preserves_value_but_marks_unverified(self):
        """A mock source still keeps the NDVI value in the structured block, but marks it as unverified."""
        from app.services.ai.context_builder import build_farm_context

        rec_mock = SAMPLE_RECOMMENDATION.model_copy(
            update={
                "provenance": DataProvenance(
                    satellite_source="mock",
                    weather_source="nasa-power",
                    soil_source="soilgrids",
                    market_source="csv",
                ),
            }
        )
        ctx = build_farm_context(rec_mock)
        assert ctx.ndvi is not None
        assert ctx.ndvi.value == pytest.approx(0.55)
        assert ctx.ndvi_available is False
        assert ctx.ndvi.is_live is False

    def test_live_ndvi_trumps_stale_unavailable_source_label(self):
        """A real NDVI value should remain usable even if a stale source label says 'unavailable'."""
        from app.services.ai.context_builder import build_farm_context

        rec = SAMPLE_RECOMMENDATION.model_copy(
            update={
                "ndvi": 0.229,
                "provenance": DataProvenance(
                    satellite_source="unavailable",
                    weather_source="nasa-power",
                    soil_source="soilgrids",
                    market_source="csv",
                ),
                "data_completeness": DataCompleteness(
                    weather="live", soil="live", satellite="live", market="csv"
                ),
                "satellite_scene_date": "2026-07-14",
            }
        )

        ctx = build_farm_context(rec)
        assert ctx.ndvi == 0.229
        assert ctx.ndvi_available is True
        assert ctx.satellite_scene_date == "2026-07-14"


# ---------------------------------------------------------------------------
# Test 2 — build_grounding_prompt includes all context values
# ---------------------------------------------------------------------------

class TestBuildGroundingPrompt:

    def test_prompt_contains_all_crop_names_from_ranking(self):
        """Every crop in the ranking must appear in the prompt for grounding."""
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import build_grounding_prompt

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)
        prompt = build_grounding_prompt(ctx, "What is the best crop?")

        for crop in ["wheat", "rice", "maize"]:
            assert crop in prompt, f"Crop '{crop}' missing from grounding prompt"

    def test_prompt_contains_key_numeric_values(self):
        """Key numeric values must be in the prompt so validate_answer_is_grounded can check them."""
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import build_grounding_prompt

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)
        prompt = build_grounding_prompt(ctx, "How much water?")

        # Resource plan values
        assert "1200" in prompt   # water_liters_per_week
        assert "45.5" in prompt or "45.50" in prompt   # fertilizer_kg_per_acre
        assert "85" in prompt     # rainfall
        assert "27.5" in prompt or "27.50" in prompt   # avg_temp_c
        assert "6.6" in prompt    # soil_ph

    def test_prompt_contains_unavailability_notice_when_ndvi_not_available(self):
        """When NDVI is unavailable, the prompt must say so — not a zero."""
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import build_grounding_prompt

        ctx = build_farm_context(SAMPLE_REC_NO_NDVI)
        prompt = build_grounding_prompt(ctx, "What is my NDVI?")

        assert "NOT AVAILABLE" in prompt or "unavailable" in prompt.lower()

    def test_prompt_contains_hard_grounding_instructions(self):
        """The prompt must include the grounding constraints for the LLM."""
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import build_grounding_prompt

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)
        prompt = build_grounding_prompt(ctx, "Any question")

        # The prompt must contain key grounding instructions
        assert "ONLY" in prompt
        assert "not available" in prompt.lower() or "NOT" in prompt
        assert "re-rank" in prompt.lower() or "DO NOT re-order" in prompt


# ---------------------------------------------------------------------------
# Test 3 — validate_answer_is_grounded PASSES for in-context claims
# ---------------------------------------------------------------------------

class TestGroundingValidatorPasses:

    def test_answer_citing_only_context_crops_and_values_passes(self):
        """An answer that only uses crop names and values from context must pass."""
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import validate_answer_is_grounded

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)
        good_answer = (
            "Based on your recommendation, wheat is the top-ranked crop with a "
            "TOPSIS closeness score of 0.7123. The resource plan recommends "
            "1200.0 L/week of water and 45.5 kg/acre of fertilizer."
        )
        result = validate_answer_is_grounded(good_answer, ctx)
        assert result.passed, (
            f"Expected PASS but got FAIL. "
            f"Ungrounded crops: {result.ungrounded_crop_claims}, "
            f"Ungrounded numbers: {result.ungrounded_numeric_claims}"
        )

    def test_answer_with_no_crops_or_numbers_passes(self):
        """A purely qualitative answer with no crop names or numbers is always safe."""
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import validate_answer_is_grounded

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)
        qualitative_answer = (
            "Your farm's recommendation is complete and based on live data from "
            "satellite, weather, and soil sources."
        )
        result = validate_answer_is_grounded(qualitative_answer, ctx)
        assert result.passed

    def test_answer_with_live_ndvi_and_real_topsis_values_passes(self):
        """A grounded answer that cites the valid NDVI and actual TOPSIS score should pass."""
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import validate_answer_is_grounded

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)
        answer = (
            "The NDVI is 0.5500 and wheat has the top TOPSIS closeness score of 0.7123."
        )
        result = validate_answer_is_grounded(answer, ctx)
        assert result.passed


# ---------------------------------------------------------------------------
# Test 4 — validate_answer_is_grounded FAILS for hallucinated claims
# ---------------------------------------------------------------------------

class TestGroundingValidatorFails:

    def test_answer_with_crop_not_in_ranking_fails(self):
        """
        If the answer mentions a crop that isn't in the ranking (e.g. 'cotton'
        when only wheat/rice/maize were ranked), it must fail.
        This is the primary patent-documentation grounding check.
        """
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import validate_answer_is_grounded

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)
        hallucinated_crop_answer = (
            "I recommend you grow cotton this season as it suits your soil perfectly."
        )
        result = validate_answer_is_grounded(hallucinated_crop_answer, ctx)
        assert not result.passed, "Expected FAIL for hallucinated crop 'cotton'"
        assert "cotton" in result.ungrounded_crop_claims, (
            f"Expected 'cotton' in ungrounded_crop_claims, got {result.ungrounded_crop_claims}"
        )

    def test_answer_with_fabricated_number_fails(self):
        """
        If the answer states a number that doesn't match any context value
        (e.g. fabricated yield of 5000 kg/acre), it must fail.
        """
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import validate_answer_is_grounded

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)
        fabricated_number_answer = (
            "Wheat will give you a yield of 5000 kg/acre this season."
        )
        result = validate_answer_is_grounded(fabricated_number_answer, ctx)
        assert not result.passed, "Expected FAIL for fabricated number 5000"
        assert "5000.0" in result.ungrounded_numeric_claims or "5000" in str(result.ungrounded_numeric_claims), (
            f"Expected 5000 in ungrounded_numeric_claims, got {result.ungrounded_numeric_claims}"
        )

    def test_answer_with_wrong_topsis_score_fails(self):
        """An answer that cites a TOPSIS score not in the context must fail."""
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import validate_answer_is_grounded

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)
        # wheat's real score is 0.7123; 0.9500 is fabricated
        wrong_score_answer = "Wheat has a TOPSIS score of 0.9500 making it ideal."
        result = validate_answer_is_grounded(wrong_score_answer, ctx)
        assert not result.passed, "Expected FAIL for wrong TOPSIS score 0.9500"


# ---------------------------------------------------------------------------
# Test 5 — answer_farm_question with hallucinated crop returns safe fallback
# ---------------------------------------------------------------------------

class TestAssistantServiceHallucination:

    def test_hallucinated_crop_name_returns_safe_fallback(self, monkeypatch, ai_db):
        """
        When the mocked LLM returns an answer containing a crop not in the
        ranking, answer_farm_question must NOT return that answer.  It must
        return either a corrected answer (from the second LLM call) or the
        explicit safe fallback — never the raw hallucination.
        """
        from app.services.ai.context_builder import build_farm_context
        import app.services.ai.llm_client as llm_module
        from app.services.ai.assistant_service import answer_farm_question

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)

        # Sequence of LLM responses: first hallucinated, then still hallucinated
        # → should trigger the safe fallback path
        responses = iter([
            "I recommend cotton as the best crop for your field.",   # hallucinated
            "Cotton is the top crop with yield 9999 kg/ha.",         # still hallucinated
        ])

        def mock_call_llm(system_prompt, user_message):
            return next(responses)

        monkeypatch.setattr(llm_module, "call_llm", mock_call_llm)

        result = answer_farm_question(ctx, "What crop should I grow?", ai_db)

        # The answer must NOT contain the hallucinated crop name
        assert "cotton" not in result.answer.lower(), (
            f"Hallucinated crop 'cotton' leaked into the answer: {result.answer!r}"
        )
        # The answer should be the safe fallback message
        assert "not available" in result.answer.lower() or "not returning" in result.answer.lower() or "cannot" in result.answer.lower() or "sorry" in result.answer.lower(), (
            f"Expected a safe fallback message, got: {result.answer!r}"
        )

    def test_hallucinated_crop_after_correction_gives_safe_answer(self, monkeypatch, ai_db):
        """When the correction LLM call produces a valid answer, that is returned."""
        from app.services.ai.context_builder import build_farm_context
        import app.services.ai.llm_client as llm_module
        from app.services.ai.assistant_service import answer_farm_question

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)

        # First call hallucinated; second call (correction) is grounded
        responses = iter([
            "I recommend cotton as the best crop.",   # hallucinated
            "Based on your recommendation, wheat is ranked first with 0.7123 TOPSIS score.",  # grounded
        ])

        def mock_call_llm(system_prompt, user_message):
            return next(responses)

        monkeypatch.setattr(llm_module, "call_llm", mock_call_llm)

        result = answer_farm_question(ctx, "What crop should I grow?", ai_db)

        # The corrected answer IS grounded — should be returned
        assert "wheat" in result.answer.lower()
        assert "cotton" not in result.answer.lower()


# ---------------------------------------------------------------------------
# Test 6 — answer_farm_question persists exactly one AIInteraction row
# ---------------------------------------------------------------------------

class TestAssistantServicePersistence:

    def test_successful_call_persists_one_interaction_row(self, monkeypatch, ai_db):
        """
        A successful answer_farm_question call must persist exactly one
        AIInteraction row with grounding_passed=True and the correct
        recommendation_id.
        """
        from app.services.ai.context_builder import build_farm_context
        import app.services.ai.llm_client as llm_module
        from app.services.ai.assistant_service import answer_farm_question
        from app.models.ai_interaction import AIInteraction

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)

        def mock_call_llm(system_prompt, user_message):
            return (
                "Based on your recommendation, wheat is the top-ranked crop with "
                "a TOPSIS score of 0.7123. The water plan is 1200.0 L/week."
            )

        monkeypatch.setattr(llm_module, "call_llm", mock_call_llm)

        answer_farm_question(ctx, "What is the best crop for my farm?", ai_db)

        rows = ai_db.query(AIInteraction).all()
        assert len(rows) == 1, f"Expected exactly 1 AIInteraction row, got {len(rows)}"

        row = rows[0]
        assert row.recommendation_id == 42   # from SAMPLE_RECOMMENDATION.id
        assert row.grounding_passed is True
        assert "wheat" in row.answer.lower()
        assert row.question == "What is the best crop for my farm?"

    def test_failed_grounding_persists_row_with_grounding_passed_false(self, monkeypatch, ai_db):
        """Even when grounding fails and safe fallback is used, one row is persisted."""
        from app.services.ai.context_builder import build_farm_context
        import app.services.ai.llm_client as llm_module
        from app.services.ai.assistant_service import answer_farm_question
        from app.models.ai_interaction import AIInteraction

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)

        # Both LLM calls return hallucinated content
        def mock_call_llm(system_prompt, user_message):
            return "I recommend cotton with a yield of 9999 kg/ha."

        monkeypatch.setattr(llm_module, "call_llm", mock_call_llm)

        answer_farm_question(ctx, "What should I grow?", ai_db)

        rows = ai_db.query(AIInteraction).all()
        assert len(rows) == 1
        assert rows[0].grounding_passed is False

    def test_two_calls_persist_two_rows(self, monkeypatch, ai_db):
        """Each call to answer_farm_question creates its own audit row."""
        from app.services.ai.context_builder import build_farm_context
        import app.services.ai.llm_client as llm_module
        from app.services.ai.assistant_service import answer_farm_question
        from app.models.ai_interaction import AIInteraction

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)

        def mock_call_llm(system_prompt, user_message):
            return (
                "Wheat is ranked 1st. Water plan: 1200.0 L/week, fertilizer: 45.5 kg/acre."
            )

        monkeypatch.setattr(llm_module, "call_llm", mock_call_llm)

        answer_farm_question(ctx, "Question one?", ai_db)
        answer_farm_question(ctx, "Question two?", ai_db)

        rows = ai_db.query(AIInteraction).all()
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# NDVI interpretation contract tests
# ---------------------------------------------------------------------------

class TestNDVIInterpretation:

    def test_interpret_ndvi_band_labels_are_deterministic(self):
        from app.core.environmental_interpretation import interpret_ndvi

        assert interpret_ndvi(-0.2) == "water / non-vegetated surface"
        assert interpret_ndvi(0.0) == "bare soil / very sparse vegetation"
        assert interpret_ndvi(0.15) == "sparse vegetation"
        assert interpret_ndvi(0.25) == "moderate vegetation"
        assert interpret_ndvi(0.5) == "dense vegetation"
        assert interpret_ndvi(0.6) == "very dense vegetation"

    def test_live_ndvi_context_builds_expected_block(self):
        from app.services.ai.context_builder import build_farm_context

        rec = SAMPLE_RECOMMENDATION.model_copy(
            update={
                "ndvi": 0.229,
                "provenance": DataProvenance(
                    satellite_source="gee-sentinel2",
                    weather_source="nasa-power",
                    soil_source="soilgrids",
                    market_source="csv",
                ),
                "satellite_scene_date": "2026-07-14",
            }
        )

        ctx = build_farm_context(rec)
        assert ctx.ndvi is not None
        assert ctx.ndvi.value == pytest.approx(0.229)
        assert ctx.ndvi.is_live is True
        assert ctx.ndvi.status == "moderate vegetation"

    def test_mock_ndvi_context_preserves_value_but_marks_unverified(self):
        from app.services.ai.context_builder import build_farm_context

        rec = SAMPLE_RECOMMENDATION.model_copy(
            update={
                "ndvi": 0.229,
                "provenance": DataProvenance(
                    satellite_source="mock",
                    weather_source="nasa-power",
                    soil_source="soilgrids",
                    market_source="csv",
                ),
                "satellite_scene_date": "2026-07-14",
            }
        )

        ctx = build_farm_context(rec)
        assert ctx.ndvi is not None
        assert ctx.ndvi.value == pytest.approx(0.229)
        assert ctx.ndvi.is_live is False
        assert "mock" in ctx.ndvi.source.lower() or ctx.ndvi.source == "mock"

    def test_grounding_prompt_includes_live_ndvi_value_and_status(self):
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import build_grounding_prompt

        rec = SAMPLE_RECOMMENDATION.model_copy(
            update={
                "ndvi": 0.229,
                "provenance": DataProvenance(
                    satellite_source="gee-sentinel2",
                    weather_source="nasa-power",
                    soil_source="soilgrids",
                    market_source="csv",
                ),
                "satellite_scene_date": "2026-07-14",
            }
        )

        prompt = build_grounding_prompt(build_farm_context(rec), "What is the NDVI?")
        assert "0.2290" in prompt
        assert "moderate vegetation" in prompt.lower()
        assert "gee-sentinel2" in prompt.lower()

    def test_grounding_prompt_includes_mock_ndvi_value_and_status_warning(self):
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import build_grounding_prompt

        rec = SAMPLE_RECOMMENDATION.model_copy(
            update={
                "ndvi": 0.229,
                "provenance": DataProvenance(
                    satellite_source="mock",
                    weather_source="nasa-power",
                    soil_source="soilgrids",
                    market_source="csv",
                ),
                "satellite_scene_date": "2026-07-14",
            }
        )

        prompt = build_grounding_prompt(build_farm_context(rec), "What is the NDVI?")
        assert "0.2290" in prompt
        assert "moderate vegetation" in prompt.lower()
        assert "MOCK/UNVERIFIED" in prompt or "illustrative only" in prompt.lower()


# ---------------------------------------------------------------------------
# Test 7 — call_llm raises AIServiceUnavailableError when API fails
# ---------------------------------------------------------------------------

class TestLLMClientError:

    def test_raises_ai_service_unavailable_when_api_fails(self, monkeypatch):
        """
        When the underlying OpenAI API call raises any exception,
        call_llm must raise AIServiceUnavailableError (NOT a silent fallback,
        NOT the raw openai exception).
        """
        import app.services.ai.llm_client as llm_module
        from app.utils.exceptions import AIServiceUnavailableError

        # Simulate the openai client raising an error
        class FakeOpenAI:
            def __init__(self, api_key):
                pass

            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        raise RuntimeError("Connection refused by upstream")

        # Patch both: the openai module import AND the api key presence
        import types
        fake_openai_mod = types.ModuleType("openai")
        fake_openai_mod.OpenAI = FakeOpenAI
        monkeypatch.setitem(__import__("sys").modules, "openai", fake_openai_mod)

        # Ensure api key is set so we don't hit the "no key" error first
        monkeypatch.setattr(llm_module.settings, "llm_api_key", "fake-key-for-test")
        monkeypatch.setattr(llm_module.settings, "llm_provider", "openai")

        with pytest.raises(AIServiceUnavailableError) as exc_info:
            llm_module.call_llm("system prompt", "user question")

        assert exc_info.value.status_code == 502
        assert exc_info.value.error_code == "ai_service_unavailable"

    def test_raises_ai_service_unavailable_when_no_api_key(self, monkeypatch):
        """Missing LLM_API_KEY raises AIServiceUnavailableError immediately."""
        import app.services.ai.llm_client as llm_module
        from app.utils.exceptions import AIServiceUnavailableError

        monkeypatch.setattr(llm_module.settings, "llm_api_key", None)
        monkeypatch.setattr(llm_module.settings, "llm_provider", "openai")

        with pytest.raises(AIServiceUnavailableError) as exc_info:
            llm_module.call_llm("system prompt", "user question")

        assert "LLM_API_KEY" in str(exc_info.value.message)
        assert exc_info.value.status_code == 502

    def test_supports_groq_provider_configuration(self, monkeypatch):
        """Groq-compatible configuration should initialize the OpenAI SDK with the Groq base URL."""
        import sys
        import types
        import app.services.ai.llm_client as llm_module

        captured = {}

        class FakeOpenAI:
            def __init__(self, api_key, base_url=None):
                captured["api_key"] = api_key
                captured["base_url"] = base_url

            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        captured["kwargs"] = kwargs

                        class Message:
                            content = "Groq works"

                        class Choice:
                            message = Message()

                        class Response:
                            choices = [Choice()]
                            usage = type("Usage", (), {"prompt_tokens": 1, "completion_tokens": 1})()

                        return Response()

        fake_openai_mod = types.ModuleType("openai")
        fake_openai_mod.OpenAI = FakeOpenAI
        monkeypatch.setitem(sys.modules, "openai", fake_openai_mod)

        monkeypatch.setattr(llm_module.settings, "llm_api_key", "groq-test-key")
        monkeypatch.setattr(llm_module.settings, "llm_provider", "groq")
        monkeypatch.setattr(llm_module.settings, "llm_base_url", "https://api.groq.com/openai/v1")

        result = llm_module.call_llm("system prompt", "user question")

        assert result == "Groq works"
        assert captured["api_key"] == "groq-test-key"
        assert captured["base_url"] == "https://api.groq.com/openai/v1"

    def test_raises_ai_service_unavailable_for_unsupported_provider(self, monkeypatch):
        """An unsupported llm_provider raises AIServiceUnavailableError."""
        import app.services.ai.llm_client as llm_module
        from app.utils.exceptions import AIServiceUnavailableError

        monkeypatch.setattr(llm_module.settings, "llm_provider", "unsupported-provider")

        with pytest.raises(AIServiceUnavailableError):
            llm_module.call_llm("system prompt", "user question")


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------

class TestGroundingPromptAndContextEdgeCases:

    def test_empty_crop_ranking_does_not_crash(self):
        """Context with no crops (all data unavailable) should not crash the builder."""
        from app.schemas.recommendation import RecommendationResponse
        from app.services.ai.context_builder import build_farm_context

        empty_rec = SAMPLE_RECOMMENDATION.model_copy(
            update={"crop_ranking": [], "recommendation_status": "unavailable"}
        )
        ctx = build_farm_context(empty_rec)
        assert ctx.crop_ranking == []
        assert ctx.crop_names_in_ranking == []

    def test_grounding_prompt_with_empty_crop_ranking_does_not_crash(self):
        """Prompt builder must handle empty crop_ranking gracefully."""
        from app.services.ai.context_builder import build_farm_context
        from app.core.ai_grounding import build_grounding_prompt

        empty_rec = SAMPLE_RECOMMENDATION.model_copy(
            update={"crop_ranking": [], "recommendation_status": "unavailable"}
        )
        ctx = build_farm_context(empty_rec)
        prompt = build_grounding_prompt(ctx, "What crops are available?")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_grounded_fields_used_is_populated_in_response(self, monkeypatch, ai_db):
        """AIAnswerResponse.grounded_fields_used should be a non-empty list for a crop answer."""
        from app.services.ai.context_builder import build_farm_context
        import app.services.ai.llm_client as llm_module
        from app.services.ai.assistant_service import answer_farm_question

        ctx = build_farm_context(SAMPLE_RECOMMENDATION)

        def mock_call_llm(system_prompt, user_message):
            return (
                "Your top crop is wheat (rank 1). Water: 1200.0 L/week, "
                "fertilizer: 45.5 kg/acre. TOPSIS closeness: 0.7123."
            )

        monkeypatch.setattr(llm_module, "call_llm", mock_call_llm)

        result = answer_farm_question(ctx, "Tell me about my top crop.", ai_db)

        assert isinstance(result.grounded_fields_used, list)
        # At minimum "crop_ranking" should be detected
        assert len(result.grounded_fields_used) > 0
