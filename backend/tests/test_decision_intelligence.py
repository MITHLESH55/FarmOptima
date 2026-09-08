"""
Dedicated test suite for FarmOptima Decision Intelligence pipeline.

Tests:
- Location changes drive weather-dependent MCDM rankings
- Soil parameter variations alter crop suitability profiles
- Data completeness tracking preserves honest missing markers
- End-to-end recommendation flow execution
"""

import pytest
from app.core.criteria import build_decision_matrix
from app.core.mcdm import topsis, ahp_weights
from app.services.fertilizer_service import calculate_fertilizer_plan


def test_location_and_weather_changes_alter_ranking():
    """Verify that different environmental inputs (weather/soil) produce different TOPSIS rankings."""
    # Scenario A: Cold, high rainfall climate (cool crop favorable)
    crop_names_a, matrix_a, is_benefit_a = build_decision_matrix(
        ndvi=0.65,
        soil_ph=6.5,
        rainfall_mm_30d=180.0,
        avg_temp_c=14.0,
        humidity_pct=75.0,
        soil_nitrogen_mg_kg=400.0,
        soil_organic_carbon_g_kg=18.0,
        soil_moisture_pct=35.0,
    )
    weights = [0.35, 0.30, 0.20, 0.15]
    ranking_a = topsis(matrix_a, weights, is_benefit_a)
    top_crop_a = crop_names_a[ranking_a[0]["index"]]

    # Scenario B: Warm, moderate rainfall climate (warm crop favorable)
    crop_names_b, matrix_b, is_benefit_b = build_decision_matrix(
        ndvi=0.65,
        soil_ph=6.5,
        rainfall_mm_30d=60.0,
        avg_temp_c=30.0,
        humidity_pct=50.0,
        soil_nitrogen_mg_kg=400.0,
        soil_organic_carbon_g_kg=18.0,
        soil_moisture_pct=25.0,
    )
    ranking_b = topsis(matrix_b, weights, is_benefit_b)
    top_crop_b = crop_names_b[ranking_b[0]["index"]]

    # Cool climate (Scenario A) and warm climate (Scenario B) must yield distinct top recommendations
    assert top_crop_a != top_crop_b


def test_soil_ph_variation_affects_suitability():
    """Test that extreme soil pH reduces soil suitability score compared to optimal pH."""
    crop_names, matrix_optimal, _ = build_decision_matrix(
        ndvi=0.6, soil_ph=6.8, rainfall_mm_30d=50.0, avg_temp_c=22.0
    )
    _, matrix_acidic, _ = build_decision_matrix(
        ndvi=0.6, soil_ph=4.2, rainfall_mm_30d=50.0, avg_temp_c=22.0
    )

    # Index 0 is Wheat (optimal pH 6.0-7.5)
    # Column 1 is soil_suitability
    wheat_optimal_soil = matrix_optimal[0][1]
    wheat_acidic_soil = matrix_acidic[0][1]

    assert wheat_optimal_soil > wheat_acidic_soil


def test_missing_data_uses_neutral_baseline_without_crash():
    """Verify that unavailable data sources populate neutral 0.5 scores without silently returning zero or crashing."""
    crop_names, matrix, is_benefit = build_decision_matrix(
        ndvi=0.0,
        soil_ph=0.0,
        rainfall_mm_30d=0.0,
        avg_temp_c=0.0,
        soil_source="unavailable",
        weather_source="unavailable",
        satellite_source="unavailable",
    )
    assert len(matrix) == len(crop_names)
    for row in matrix:
        # Climate and soil scores should be neutral baseline (0.5), not 0.0
        assert row[0] == 0.5
        assert row[1] == 0.5
