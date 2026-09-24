"""
Pre-submission hardening regression tests.
Verifies data-context consistency, scientific correctness, and terminology integrity.
"""

import pytest
from app.core.environmental_interpretation import interpret_factor_range, interpret_ndvi
from app.core.mcdm import electre_i, topsis, ahp_weights
from app.core.nsga2 import optimize_resources_multiobjective
from app.schemas.ai import FarmContext, ResourcePlanContext, CropRankEntry, NDVIContext
from app.core.ai_grounding import build_grounding_prompt, validate_answer_is_grounded


def test_environmental_factor_range_interpretation():
    """Verify single source of truth for factor range status."""
    # Within range
    assert interpret_factor_range(75.0, 50.0, 100.0) == "within_preferred_range"
    assert interpret_factor_range(50.0, 50.0, 100.0) == "within_preferred_range"
    assert interpret_factor_range(100.0, 50.0, 100.0) == "within_preferred_range"

    # Below range
    assert interpret_factor_range(30.0, 50.0, 100.0) == "below_preferred_range"

    # Above range
    assert interpret_factor_range(120.0, 50.0, 100.0) == "above_preferred_range"

    # Missing reference range
    assert interpret_factor_range(75.0, None, None) == "no_reference_configured"

    # Unavailable / non-finite value
    assert interpret_factor_range(None, 50.0, 100.0) == "unavailable"
    assert interpret_factor_range(float("nan"), 50.0, 100.0) == "unavailable"


def test_electre_net_outranking_properties():
    """Verify that ELECTRE net outranking is a net count difference."""
    matrix = [
        [0.8, 0.7, 0.9, 0.6],
        [0.5, 0.4, 0.6, 0.5],
        [0.9, 0.8, 0.8, 0.7],
    ]
    weights = [0.4, 0.3, 0.2, 0.1]
    is_benefit = [True, True, True, True]

    res = electre_i(matrix, weights, is_benefit)
    net_counts = res["net_outranking_count"]
    
    # Net counts sum to 0 in a tournament setting
    assert sum(net_counts) == 0
    # Best alternative has positive net outranking count
    assert net_counts[2] >= net_counts[1]


def test_nsga2_multi_objective_compromise():
    """Verify NSGA-II multi-objective outputs: water gap, fert gap, and compromise solution."""
    result = optimize_resources_multiobjective(
        crop_water_need_mm=450.0,
        crop_fert_need_kg_acre=48.0,
        rainfall_mm_30d=60.0,
        soil_moisture_pct=25.0,
        population_size=20,
        generations=15,
        seed=42,
    )
    assert len(result.pareto_front) > 0
    comp = result.compromise_solution
    assert comp.water_liters_per_week > 0
    assert comp.fertilizer_kg_per_acre > 0
    assert comp.water_gap >= 0.0
    assert comp.fertilizer_gap >= 0.0
    assert comp.resource_cost > 0.0


def test_ai_grounding_fertilizer_context_validation():
    """Verify AI grounding accepts structured fertilizer plan quantities."""
    ctx = FarmContext(
        generated_at="2026-09-24T12:00:00Z",
        recommendation_status="complete",
        data_completeness_weather="live",
        data_completeness_soil="live",
        data_completeness_satellite="live",
        data_completeness_market="csv",
        satellite_source="gee-sentinel2",
        weather_source="nasa-power",
        soil_source="soilgrids",
        market_source="agmarknet_historical_csv",
        latitude=28.7041,
        longitude=77.1025,
        ndvi=NDVIContext(value=0.55, source="gee-sentinel2", status="dense vegetation", is_live=True),
        rainfall_mm_last_30d=85.0,
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
            CropRankEntry(crop="Wheat", topsis_closeness=0.82, electre_net_outranking=2, rank=1),
            CropRankEntry(crop="Rice", topsis_closeness=0.65, electre_net_outranking=0, rank=2),
        ],
        crop_names_in_ranking=["Wheat", "Rice"],
        resource_plan=ResourcePlanContext(
            water_liters_per_week=28000.0,
            fertilizer_kg_per_acre=48.0,
            optimizer_best_fitness=0.045,
            optimizer_generations_run=60,
            irrigation_schedule="~4000 L/day, split across 2-3 waterings/week",
            optimizer_method="nsga2-multiobjective",
        ),
        fertilizer_plan={
            "crop": "Wheat",
            "field_area_acres": 2.0,
            "nutrient_requirements": {
                "nitrogen_kg_per_acre": 48.0,
                "phosphorus_kg_per_acre": 24.0,
                "potassium_kg_per_acre": 16.0,
                "total_field_nitrogen_kg": 96.0,
                "total_field_phosphorus_kg": 48.0,
                "total_field_potassium_kg": 32.0,
            },
            "commercial_fertilizers": [
                {"name": "DAP", "quantity_kg_per_acre": 52.17, "quantity_kg_total": 104.34},
                {"name": "Urea", "quantity_kg_per_acre": 83.93, "quantity_kg_total": 167.86},
                {"name": "MOP", "quantity_kg_per_acre": 26.67, "quantity_kg_total": 53.34},
            ],
            "application_schedule": [
                {"stage": "Basal", "dap_kg": 104.34, "urea_kg": 83.93, "mop_kg": 53.34, "total_kg": 241.61},
                {"stage": "Top Dressing 1", "dap_kg": 0.0, "urea_kg": 41.97, "mop_kg": 0.0, "total_kg": 41.97},
            ],
        },
        ai_explanation="Wheat has the highest TOPSIS score of 0.82.",
    )

    prompt = build_grounding_prompt(ctx, "What fertilizer is needed?")
    assert "Detailed Fertilizer Plan" in prompt
    assert "DAP" in prompt
    assert "Urea" in prompt

    answer = "For your 2.0 acres of Wheat, you need 96.0 kg of Nitrogen total, supplied via 104.34 kg of DAP and 167.86 kg of Urea."
    check = validate_answer_is_grounded(answer, ctx)
    assert check.passed is True
