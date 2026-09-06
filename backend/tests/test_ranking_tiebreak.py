from __future__ import annotations

from app.core.ai_grounding import validate_answer_is_grounded
from app.core.ranking_tiebreak import resolve_tie_break_order, TOPSIS_TIE_EPSILON
from app.schemas.ai import (
    CropRankEntry,
    FarmContext,
    ParetoPointSummary,
    ResourcePlanContext,
)


def _build_context_from_ranking(entries, *, ahp_weights=None, recommendation_id=1):
    ahp_weights = ahp_weights or {"climate_suitability": 0.45, "soil_suitability": 0.25, "water_efficiency": 0.15, "market_value": 0.15}
    return FarmContext(
        recommendation_id=recommendation_id,
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
        ndvi={"value": 0.55, "source": "gee-sentinel2", "scene_date": "2026-07-15", "status": "dense vegetation", "is_live": True},
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
        ahp_weights=ahp_weights,
        ahp_consistency_ratio=0.0321,
        ahp_is_consistent=True,
        ahp_method="fuzzy-ahp-chang-extent-analysis",
        crop_ranking=entries,
        crop_names_in_ranking=[e.crop for e in entries],
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


def test_non_tied_topsis_keeps_no_tie_break():
    entries = [
        CropRankEntry(crop="Maize", topsis_closeness=0.91, electre_net_outranking=3, rank=1, tie_break_applied=False, tie_break_reason=None),
        CropRankEntry(crop="Groundnut", topsis_closeness=0.72, electre_net_outranking=1, rank=2, tie_break_applied=False, tie_break_reason=None),
    ]
    result = resolve_tie_break_order(entries, {"climate_suitability": 0.45, "soil_suitability": 0.25, "water_efficiency": 0.15, "market_value": 0.15}, [[0.80, 0.70, 0.75, 0.60], [0.55, 0.50, 0.65, 0.40]])
    assert result[0].tie_break_applied is False
    assert result[0].tie_break_reason is None
    assert [item.crop for item in result] == ["Maize", "Groundnut"]


def test_topsis_tie_uses_electre():
    entries = [
        CropRankEntry(crop="Maize", topsis_closeness=0.80, electre_net_outranking=2, rank=1, tie_break_applied=False, tie_break_reason=None),
        CropRankEntry(crop="Groundnut", topsis_closeness=0.80, electre_net_outranking=5, rank=2, tie_break_applied=False, tie_break_reason=None),
    ]
    result = resolve_tie_break_order(entries, {"climate_suitability": 0.45, "soil_suitability": 0.25, "water_efficiency": 0.15, "market_value": 0.15}, [[0.70, 0.60, 0.80, 0.55], [0.65, 0.62, 0.72, 0.40]])
    assert result[0].crop == "Groundnut"
    assert result[0].tie_break_applied is True
    assert result[0].tie_break_reason == "electre_net_outranking"


def test_topsis_tie_uses_dominant_criterion_when_electre_tied():
    entries = [
        CropRankEntry(crop="Maize", topsis_closeness=0.80, electre_net_outranking=2, rank=1, tie_break_applied=False, tie_break_reason=None),
        CropRankEntry(crop="Groundnut", topsis_closeness=0.80, electre_net_outranking=2, rank=2, tie_break_applied=False, tie_break_reason=None),
    ]
    result = resolve_tie_break_order(entries, {"climate_suitability": 0.45, "soil_suitability": 0.30, "water_efficiency": 0.15, "market_value": 0.10}, [[0.90, 0.60, 0.70, 0.40], [0.70, 0.62, 0.72, 0.50]])
    assert result[0].crop == "Maize"
    assert result[0].tie_break_applied is True
    assert result[0].tie_break_reason == "dominant_criterion:climate_suitability"


def test_topsis_tie_falls_back_to_alphabetical_order():
    entries = [
        CropRankEntry(crop="Maize", topsis_closeness=0.80, electre_net_outranking=2, rank=1, tie_break_applied=False, tie_break_reason=None),
        CropRankEntry(crop="Cotton", topsis_closeness=0.80, electre_net_outranking=2, rank=2, tie_break_applied=False, tie_break_reason=None),
        CropRankEntry(crop="Groundnut", topsis_closeness=0.80, electre_net_outranking=2, rank=3, tie_break_applied=False, tie_break_reason=None),
    ]
    result = resolve_tie_break_order(entries, {"climate_suitability": 0.25, "soil_suitability": 0.25, "water_efficiency": 0.25, "market_value": 0.25}, [[0.50, 0.50, 0.50, 0.50]] * 3)
    assert [item.crop for item in result] == ["Cotton", "Groundnut", "Maize"]
    assert result[0].tie_break_applied is True
    assert result[0].tie_break_reason == "alphabetical_fallback"


def test_grounding_rejects_wrong_tiebreak_reason_and_accepts_actual_reason():
    entries = [
        CropRankEntry(crop="Maize", topsis_closeness=0.80, electre_net_outranking=5, rank=1, tie_break_applied=True, tie_break_reason="electre_net_outranking"),
        CropRankEntry(crop="Groundnut", topsis_closeness=0.80, electre_net_outranking=2, rank=2, tie_break_applied=False, tie_break_reason=None),
    ]
    context = _build_context_from_ranking(entries)

    wrong = validate_answer_is_grounded("Maize was ranked above Groundnut because climate suitability was better.", context)
    assert wrong.passed is False

    right = validate_answer_is_grounded("Maize was ranked above Groundnut because the ELECTRE net outranking result broke the TOPSIS tie.", context)
    assert right.passed is True


def test_why_not_groundnut_requires_actual_tie_break_reason():
    entries = [
        CropRankEntry(crop="Maize", topsis_closeness=0.80, electre_net_outranking=3, rank=1, tie_break_applied=True, tie_break_reason="dominant_criterion:climate_suitability"),
        CropRankEntry(crop="Groundnut", topsis_closeness=0.80, electre_net_outranking=3, rank=2, tie_break_applied=False, tie_break_reason=None),
    ]
    context = _build_context_from_ranking(entries)

    unsupported = validate_answer_is_grounded("Maize was ranked above Groundnut because of overall suitability.", context)
    assert unsupported.passed is False

    actual = validate_answer_is_grounded(
        "Maize and Groundnut had tied TOPSIS and ELECTRE results, and the tie was resolved using the dominant AHP criterion, climate_suitability.",
        context,
    )
    assert actual.passed is True


def test_topsis_tie_epsilon_is_applied_to_raw_scores():
    assert abs(0.8000000000001 - 0.8) <= TOPSIS_TIE_EPSILON
    assert abs(0.8000001 - 0.8) > TOPSIS_TIE_EPSILON
