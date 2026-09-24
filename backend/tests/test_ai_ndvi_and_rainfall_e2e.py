"""
End-to-End integration tests for NDVI AI Assistant and Rainfall Single-Source Reasoning.
"""

import pytest
from app.schemas.ai import FarmContext, NDVIContext, ResourcePlanContext, CropRankEntry
from app.core.ai_grounding import build_grounding_prompt, validate_answer_is_grounded
from app.core.environmental_interpretation import interpret_factor_range, interpret_ndvi
from app.services.ai.intent_resolver import resolve_question_intent, CanonicalIntent
from app.crop_database import CROP_DATABASE


def create_mock_context(
    *,
    ndvi_val: float | None = 0.52,
    satellite_source: str = "gee-sentinel2",
    rainfall: float = 85.0,
    top_crop: str = "Wheat",
) -> FarmContext:
    ndvi_ctx = None
    if ndvi_val is not None:
        ndvi_ctx = NDVIContext(
            value=ndvi_val,
            source=satellite_source,
            scene_date="2026-08-15",
            status=interpret_ndvi(ndvi_val),
            is_live=satellite_source != "mock",
        )

    return FarmContext(
        generated_at="2026-09-24T12:00:00Z",
        recommendation_status="complete",
        data_completeness_weather="live",
        data_completeness_soil="live",
        data_completeness_satellite="live" if ndvi_ctx and ndvi_ctx.is_live else "unavailable",
        data_completeness_market="csv",
        satellite_source=satellite_source,
        weather_source="nasa-power",
        soil_source="soilgrids",
        market_source="agmarknet_historical_csv",
        latitude=28.7041,
        longitude=77.1025,
        ndvi=ndvi_ctx,
        rainfall_mm_last_30d=rainfall,
        avg_temp_c=25.0,
        humidity_pct=60.0,
        solar_radiation_mj_m2=18.0,
        wind_speed_m_s=2.5,
        soil_ph=6.5,
        soil_moisture_pct=28.0,
        soil_nitrogen_mg_kg=35.0,
        soil_organic_carbon_g_kg=15.0,
        soil_sand_pct=40.0,
        soil_clay_pct=25.0,
        ahp_weights={"climate_suitability": 0.45, "soil_suitability": 0.25, "water_efficiency": 0.18, "market_value": 0.12},
        ahp_consistency_ratio=0.04,
        ahp_is_consistent=True,
        ahp_method="fuzzy-ahp",
        crop_ranking=[
            CropRankEntry(crop=top_crop, topsis_closeness=0.85, electre_net_outranking=3, rank=1),
            CropRankEntry(crop="Rice" if top_crop != "Rice" else "Wheat", topsis_closeness=0.65, electre_net_outranking=0, rank=2),
        ],
        crop_names_in_ranking=[top_crop, "Rice" if top_crop != "Rice" else "Wheat"],
        resource_plan=ResourcePlanContext(
            water_liters_per_week=28000.0,
            fertilizer_kg_per_acre=48.0,
            optimizer_best_fitness=0.045,
            optimizer_generations_run=60,
            irrigation_schedule="~4000 L/day, split across 2-3 waterings/week",
            optimizer_method="nsga2-multiobjective",
        ),
        fertilizer_plan={
            "crop": top_crop,
            "field_area_acres": 1.5,
            "nutrient_requirements": {"nitrogen_kg_per_acre": 48.0, "phosphorus_kg_per_acre": 24.0, "potassium_kg_per_acre": 16.0},
        },
        ai_explanation=f"{top_crop} achieved the highest TOPSIS score of 0.85.",
    )


# --- 1. NDVI AI Grounding End-to-End Tests ---

def test_ai_ndvi_query_with_live_observation():
    """Verify AI prompt contains live Sentinel-2 NDVI details and grounded answer passes."""
    ctx = create_mock_context(ndvi_val=0.52, satellite_source="gee-sentinel2")
    q = "What is my field's NDVI status?"
    resolved = resolve_question_intent(q, ctx)
    assert resolved.canonical_intent == CanonicalIntent.NDVI_SATELLITE

    prompt = build_grounding_prompt(ctx, q)
    assert "NDVI: 0.5200" in prompt
    assert "dense vegetation" in prompt
    assert "source: gee-sentinel2" in prompt

    answer = "Your field's NDVI value is 0.52, indicating dense vegetation from Copernicus Sentinel-2 observations."
    check = validate_answer_is_grounded(answer, ctx)
    assert check.passed is True


def test_ai_ndvi_query_with_mock_source():
    """Verify AI prompt marks unverified source explicitly when fallback is active."""
    ctx = create_mock_context(ndvi_val=0.45, satellite_source="mock")
    prompt = build_grounding_prompt(ctx, "What is the vegetation status?")
    assert "NDVI: 0.4500" in prompt
    assert "MOCK/UNVERIFIED" in prompt

    answer = "The calculated illustrative NDVI is 0.45, indicating moderate vegetation under illustrative mode."
    check = validate_answer_is_grounded(answer, ctx)
    assert check.passed is True


def test_ai_ndvi_query_when_unavailable():
    """Verify prompt explicitly marks NDVI as NOT AVAILABLE when data is missing."""
    ctx = create_mock_context(ndvi_val=None, satellite_source="unavailable")
    prompt = build_grounding_prompt(ctx, "What is the NDVI?")
    assert "NDVI: NOT AVAILABLE" in prompt


# --- 2. Rainfall Single-Source & Consistency Tests ---

def test_rainfall_within_optimal_crop_range():
    """Verify rainfall within range is evaluated consistently."""
    # Wheat ideal rainfall: 30 - 100 mm/30d
    wheat_params = CROP_DATABASE["Wheat"]
    min_r = float(wheat_params["ideal_rainfall_min_mm_30d"])
    max_r = float(wheat_params["ideal_rainfall_max_mm_30d"])

    status = interpret_factor_range(65.0, min_r, max_r)
    assert status == "within_preferred_range"

    ctx = create_mock_context(rainfall=65.0, top_crop="Wheat")
    prompt = build_grounding_prompt(ctx, "Is rainfall suitable for wheat?")
    assert "Rainfall: 65.00 mm" in prompt
    assert f"Optimal Rainfall: {int(min_r)}-{int(max_r)} mm/month" in prompt

    answer = "Your 30-day rainfall of 65.0 mm falls within the optimal range of 30 to 100 mm for Wheat."
    check = validate_answer_is_grounded(answer, ctx)
    assert check.passed is True


def test_rainfall_below_optimal_crop_range():
    """Verify rainfall below range is evaluated consistently."""
    # Rice ideal rainfall: 150 - 300 mm/30d
    rice_params = CROP_DATABASE["Rice"]
    min_r = float(rice_params["ideal_rainfall_min_mm_30d"])
    max_r = float(rice_params["ideal_rainfall_max_mm_30d"])

    status = interpret_factor_range(40.0, min_r, max_r)
    assert status == "below_preferred_range"

    ctx = create_mock_context(rainfall=40.0, top_crop="Rice")
    answer = "Recent 30-day rainfall of 40.0 mm is below the optimal 150 to 300 mm range for Rice."
    check = validate_answer_is_grounded(answer, ctx)
    assert check.passed is True


def test_rainfall_above_optimal_crop_range():
    """Verify rainfall above range is evaluated consistently."""
    # Chickpea ideal rainfall: 20 - 70 mm/30d
    chickpea_params = CROP_DATABASE["Chickpea"]
    min_r = float(chickpea_params["ideal_rainfall_min_mm_30d"])
    max_r = float(chickpea_params["ideal_rainfall_max_mm_30d"])

    status = interpret_factor_range(110.0, min_r, max_r)
    assert status == "above_preferred_range"


def test_rainfall_missing_reference_range():
    """Verify missing reference handled deterministically."""
    status = interpret_factor_range(80.0, None, None)
    assert status == "no_reference_configured"
