from app.services.satellite_service import compute_ndvi
from app.core.criteria import _range_fit_score, build_decision_matrix
from app.core.suitability import (
    temperature_suitability,
    rainfall_suitability,
    humidity_suitability,
    soil_ph_suitability,
    soil_moisture_suitability,
    vegetation_suitability,
)


def test_dynamic_suitability_scores_are_normalized():
    assert 0.0 <= temperature_suitability(27.0, 20.0, 30.0) <= 1.0
    assert 0.0 <= rainfall_suitability(80.0, 60.0, 140.0) <= 1.0
    assert 0.0 <= humidity_suitability(60.0, 35.0, 80.0) <= 1.0
    assert 0.0 <= soil_ph_suitability(6.8, 5.8, 7.2) <= 1.0
    assert 0.0 <= soil_moisture_suitability(28.0, 20.0, 40.0) <= 1.0
    assert 0.0 <= vegetation_suitability(0.62, 0.45, 0.8) <= 1.0


def test_ndvi_formula_known_values():
    # NDVI = (NIR - Red) / (NIR + Red). NIR=0.5, Red=0.1 -> (0.4)/(0.6) = 0.667
    ndvi = compute_ndvi(nir_band=[0.5], red_band=[0.1])
    assert abs(ndvi - 0.6667) < 0.001


def test_ndvi_zero_for_equal_bands():
    ndvi = compute_ndvi(nir_band=[0.3, 0.3], red_band=[0.3, 0.3])
    assert abs(ndvi - 0.0) < 1e-6


def test_ndvi_averages_across_multiple_pixels():
    ndvi = compute_ndvi(nir_band=[0.5, 0.3], red_band=[0.1, 0.3])
    # pixel 1: (0.4/0.6)=0.667, pixel 2: (0/0.6)=0 -> mean = 0.333
    assert abs(ndvi - 0.333) < 0.01


def test_range_fit_score_inside_range_is_one():
    assert _range_fit_score(20, 10, 30) == 1.0


def test_range_fit_score_decays_outside_range():
    score_near = _range_fit_score(31, 10, 30)   # just outside
    score_far = _range_fit_score(60, 10, 30)    # far outside
    assert 0 < score_near < 1.0
    assert score_far < score_near


def test_decision_matrix_has_correct_shape():
    crop_names, matrix, is_benefit = build_decision_matrix(
        ndvi=0.6, soil_ph=6.5, rainfall_mm_30d=80, avg_temp_c=25, market_prices={},
    )
    assert len(crop_names) == len(matrix)
    assert all(len(row) == 4 for row in matrix)
    assert all(is_benefit)
    assert all(0.0 <= val <= 1.0 for row in matrix for val in row)
