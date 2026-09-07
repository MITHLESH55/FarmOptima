from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.ai_grounding import validate_answer_is_grounded
from app.core.environmental_interpretation import interpret_ndvi
from app.core.insight_engine import (
    CropNotInRankingError,
    MissingCriterionScoresError,
    generate_comparison_insight,
    generate_environmental_insight,
    generate_recommendation_insight,
)
from app.models import Recommendation, User, Farm
from app.schemas.ai import CropRankEntry, FarmContext, ResourcePlanContext, ParetoPointSummary
from app.schemas.insight import CriterionContribution, FarmInsightBundle


def _build_context() -> FarmContext:
    entries = [
        CropRankEntry(
            crop="Maize",
            topsis_closeness=0.81,
            electre_net_outranking=4,
            rank=1,
            tie_break_applied=False,
            tie_break_reason=None,
            criteria_scores={
                "climate_suitability": 0.92,
                "soil_suitability": 0.78,
                "water_efficiency": 0.74,
                "market_value": 0.61,
            },
        ),
        CropRankEntry(
            crop="Groundnut",
            topsis_closeness=0.80,
            electre_net_outranking=3,
            rank=2,
            tie_break_applied=True,
            tie_break_reason="dominant_criterion:climate_suitability",
            criteria_scores={
                "climate_suitability": 0.89,
                "soil_suitability": 0.76,
                "water_efficiency": 0.72,
                "market_value": 0.60,
            },
        ),
    ]
    context = FarmContext(
        recommendation_id=123,
        generated_at="2026-08-15T00:00:00Z",
        recommendation_status="complete",
        data_completeness_weather="live",
        data_completeness_soil="live",
        data_completeness_satellite="live",
        data_completeness_market="csv",
        satellite_source="gee-sentinel2",
        weather_source="nasa-power",
        soil_source="soilgrids",
        market_source="csv",
        latitude=18.52,
        longitude=73.86,
        ndvi={
            "value": 0.55,
            "source": "gee-sentinel2",
            "scene_date": "2026-07-15",
            "status": "dense vegetation",
            "is_live": True,
        },
        ndvi_available=True,
        satellite_scene_date="2026-07-15",
        rainfall_mm_last_30d=90.0,
        avg_temp_c=28.0,
        humidity_pct=62.0,
        solar_radiation_mj_m2=19.0,
        wind_speed_m_s=2.2,
        soil_ph=6.4,
        soil_moisture_pct=28.0,
        soil_nitrogen_mg_kg=42.0,
        soil_organic_carbon_g_kg=16.0,
        soil_sand_pct=32.0,
        soil_clay_pct=27.0,
        ahp_weights={
            "climate_suitability": 0.45,
            "soil_suitability": 0.25,
            "water_efficiency": 0.15,
            "market_value": 0.15,
        },
        ahp_consistency_ratio=0.03,
        ahp_is_consistent=True,
        ahp_method="fuzzy-ahp-chang-extent-analysis",
        crop_ranking=entries,
        crop_names_in_ranking=["Maize", "Groundnut"],
        resource_plan=ResourcePlanContext(
            water_liters_per_week=1200.0,
            fertilizer_kg_per_acre=45.0,
            optimizer_best_fitness=0.012,
            optimizer_generations_run=40,
            irrigation_schedule="Every 3 days",
            optimizer_method="nsga2-multiobjective",
            pareto_front=[
                ParetoPointSummary(
                    water_liters_per_week=1200.0,
                    fertilizer_kg_per_acre=45.0,
                    resource_cost=0.012,
                )
            ],
        ),
        ai_explanation="Top crop explanation.",
    )
    return context


def test_generate_recommendation_insight_sorted_and_tie_break_context():
    context = _build_context()
    insight = generate_recommendation_insight(context)

    assert insight.top_crop == "Maize"
    assert [item.criterion for item in insight.top_contributing_criteria] == [
        "climate_suitability",
        "soil_suitability",
        "water_efficiency",
        "market_value",
    ]
    assert insight.weakest_criterion.criterion == "market_value"
    assert insight.tie_break_context is None


def test_recommendation_insight_is_deterministic():
    context = _build_context()
    first = generate_recommendation_insight(context)
    second = generate_recommendation_insight(context)
    assert first.model_dump_json() == second.model_dump_json()


def test_generate_comparison_insight_missing_crop_raises():
    context = _build_context()
    with pytest.raises(CropNotInRankingError):
        generate_comparison_insight(context, "Maize", "Rice")


def test_generate_comparison_insight_computes_factors():
    context = _build_context()
    comp = generate_comparison_insight(context, "Maize", "Groundnut")

    assert comp.crop_a == "Maize"
    assert comp.crop_b == "Groundnut"
    assert comp.winning_factors == ["climate_suitability"]
    assert comp.losing_factors == ["market_value", "soil_suitability", "water_efficiency"]
    assert comp.criteria_comparison[0].criterion == "climate_suitability"
    assert comp.criteria_comparison[0].weighted_diff == pytest.approx(0.45 * (0.92 - 0.89))


def test_generate_environmental_insight_uses_crop_database_thresholds_and_no_reference_values():
    context = _build_context()
    env = generate_environmental_insight(context, "Maize")

    temp_factor = next(f for f in env.factors if f.field == "avg_temp_c")
    rainfall_factor = next(f for f in env.factors if f.field == "rainfall_mm_last_30d")
    ph_factor = next(f for f in env.factors if f.field == "soil_ph")
    moisture_factor = next(f for f in env.factors if f.field == "soil_moisture_pct")

    assert temp_factor.preferred_min == 18.0
    assert temp_factor.preferred_max == 32.0
    assert temp_factor.status == "within_preferred_range"
    assert rainfall_factor.preferred_min == 60.0
    assert rainfall_factor.preferred_max == 150.0
    assert ph_factor.preferred_min == 5.8
    assert ph_factor.preferred_max == 7.2
    assert moisture_factor.status == "no_reference_configured"
    assert moisture_factor.preferred_min is None
    assert moisture_factor.preferred_max is None


def test_missing_criterion_scores_raise_controlled_error():
    context = _build_context()
    context.crop_ranking[0].criteria_scores = {}

    with pytest.raises(MissingCriterionScoresError):
        generate_recommendation_insight(context)


def test_ndvi_single_source_of_truth_and_no_duplicate_interpretation(monkeypatch, client, auth_headers):
    import app.api.routes.recommend as recommend_route
    from app.services.ai.context_loader import get_context_for_recommendation

    spy = {"calls": 0}
    original = recommend_route.interpret_ndvi

    def counted(value):
        spy["calls"] += 1
        return original(value)

    monkeypatch.setattr(recommend_route, "interpret_ndvi", counted)

    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: type("W", (), {"rainfall_mm_last_30d": 90.0, "avg_temp_c": 28.0, "humidity_pct": 62.0, "solar_radiation_mj_m2": 19.0, "wind_speed_m_s": 2.2, "source": "nasa-power"})())
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: type("S", (), {"ph": 6.4, "clay_pct": 27.0, "sand_pct": 32.0, "soil_moisture_pct": 28.0, "nitrogen_total_mg_kg": 42.0, "organic_carbon_g_kg": 16.0, "source": "soilgrids"})())
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: type("N", (), {"ndvi": 0.55, "source": "gee-sentinel2", "scene_date": "2026-07-15"})())

    resp = client.post("/api/recommend", json={"lat": 18.52, "lon": 73.86}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    recommendation = resp.json()
    assert recommendation["ndvi_status"] == "dense vegetation"

    override_get_db = next(iter(client.app.dependency_overrides.values()))
    db = next(override_get_db())
    try:
        context = get_context_for_recommendation(recommendation["id"], db)
    finally:
        db.close()

    assert spy["calls"] == 1
    assert recommendation["ndvi_status"] == context.ndvi.status

    insight = generate_environmental_insight(context, context.crop_ranking[0].crop)
    ndvi_factor = next(f for f in insight.factors if f.field == "ndvi")
    assert spy["calls"] == 1
    assert recommendation["ndvi_status"] == context.ndvi.status == ndvi_factor.status


def test_environmental_ndvi_status_matches_single_source_truth():
    context = _build_context()
    env = generate_environmental_insight(context, "Maize")
    ndvi_factor = next(f for f in env.factors if f.field == "ndvi")
    assert ndvi_factor.status == interpret_ndvi(0.55)


def test_ai_grounding_accepts_real_criterion_and_rejects_invented_criterion():
    context = _build_context()
    bundle = FarmInsightBundle(
        recommendation=generate_recommendation_insight(context),
        environmental=generate_environmental_insight(context, "Maize"),
        comparisons=[],
    )
    context.insight_bundle = bundle

    assert validate_answer_is_grounded(
        "Maize is favoured because climate_suitability had the strongest weighted contribution.",
        context,
    ).passed is True

    assert validate_answer_is_grounded(
        "Maize is favoured because market_price had the strongest weighted contribution.",
        context,
    ).passed is False


def test_insight_route_requires_auth_and_ownership(client, auth_headers, monkeypatch):
    import app.api.routes.recommend as recommend_route
    from app.services.ai.context_loader import get_context_for_recommendation

    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: type("W", (), {"rainfall_mm_last_30d": 90.0, "avg_temp_c": 28.0, "humidity_pct": 62.0, "solar_radiation_mj_m2": 19.0, "wind_speed_m_s": 2.2, "source": "nasa-power"})())
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: type("S", (), {"ph": 6.4, "clay_pct": 27.0, "sand_pct": 32.0, "soil_moisture_pct": 28.0, "nitrogen_total_mg_kg": 42.0, "organic_carbon_g_kg": 16.0, "source": "soilgrids"})())
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: type("N", (), {"ndvi": 0.55, "source": "gee-sentinel2", "scene_date": "2026-07-15"})())

    resp = client.post("/api/recommend", json={"lat": 18.52, "lon": 73.86}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    rec_id = resp.json()["id"]

    insight_resp = client.get(f"/api/recommendations/{rec_id}/insight", headers=auth_headers)
    assert insight_resp.status_code == 200, insight_resp.text
    body = insight_resp.json()
    assert body["recommendation"]["top_crop"] == resp.json()["crop_ranking"][0]["crop"]

    other_headers = {"Authorization": "Bearer invalid"}
    other_resp = client.get(f"/api/recommendations/{rec_id}/insight", headers=other_headers)
    assert other_resp.status_code in {401, 403}

    missing = client.get("/api/recommendations/999999/insight", headers=auth_headers)
    assert missing.status_code == 404


def test_no_mcdm_recalculation_during_insight_generation(monkeypatch):
    import app.core.mcdm as mcdm

    context = _build_context()
    calls = {"topsis": 0, "electre": 0, "ahp": 0}

    def topsis_spy(*args, **kwargs):
        calls["topsis"] += 1
        return []

    def electre_spy(*args, **kwargs):
        calls["electre"] += 1
        return {}

    def ahp_spy(*args, **kwargs):
        calls["ahp"] += 1
        return type("X", (), {"is_consistent": True, "consistency_ratio": 0.03})()

    monkeypatch.setattr(mcdm, "topsis", topsis_spy)
    monkeypatch.setattr(mcdm, "electre_i", electre_spy)
    monkeypatch.setattr(mcdm, "ahp_weights", ahp_spy)

    generate_recommendation_insight(context)
    generate_environmental_insight(context, "Maize")
    assert calls == {"topsis": 0, "electre": 0, "ahp": 0}
