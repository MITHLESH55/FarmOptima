import pytest
from app.services.satellite_service import SatelliteResult, get_ndvi_for_location
from app.core.environmental_interpretation import interpret_ndvi
from app.core.suitability import calculate_crop_suitability_profile
from app.core.criteria import build_decision_matrix


def test_interpret_ndvi_handles_none_as_unavailable():
    assert interpret_ndvi(None) == "unavailable"


def test_interpret_ndvi_handles_valid_observations():
    assert interpret_ndvi(0.63) == "very dense vegetation"
    assert interpret_ndvi(0.0) == "bare soil / very sparse vegetation"
    assert interpret_ndvi(0.15) == "sparse vegetation"
    assert interpret_ndvi(-0.2) == "water / non-vegetated surface"


def test_gee_unavailable_returns_none_ndvi():
    # Calling get_ndvi_for_location when GEE is unconfigured/unavailable
    res = get_ndvi_for_location(0.0, 0.0)
    assert res.source == "unavailable"
    assert res.ndvi is None
    assert res.quality_status == "unavailable"


def test_unavailable_ndvi_does_not_score_as_zero_biomass():
    # Test that ndvi=None gives neutral vegetation suitability (0.5)
    profile_none = calculate_crop_suitability_profile(
        "Wheat",
        temperature_c=22.0,
        rainfall_mm_30d=50.0,
        humidity_pct=60.0,
        soil_ph=6.5,
        nitrogen_mg_kg=800.0,
        organic_carbon_g_kg=15.0,
        soil_moisture_pct=25.0,
        ndvi=None,
    )
    assert profile_none["vegetation_suitability"] == 0.5


def test_criteria_build_matrix_handles_unavailable_satellite():
    crop_names, matrix, is_benefit = build_decision_matrix(
        ndvi=None,
        soil_ph=6.5,
        rainfall_mm_30d=50.0,
        avg_temp_c=22.0,
        satellite_source="unavailable",
    )
    assert len(matrix) == len(crop_names)
    for row in matrix:
        assert len(row) == 4
        # Matrix values should all be finite numbers between 0 and 1
        for score in row:
            assert 0.0 <= score <= 1.0
