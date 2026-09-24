import pytest
from app.core.criteria import build_decision_matrix, DEFAULT_AHP_PAIRWISE_MATRIX
from app.core.mcdm import topsis
from app.core.fuzzy_ahp import crisp_to_default_fuzzy, select_ahp_weights
from app.crop_database import CROP_DATABASE


def get_ranking_for_inputs(temp_c, rain_30d, ph, n_mg_kg, oc_g_kg, moisture_pct, market_prices=None):
    crop_names, matrix, is_benefit = build_decision_matrix(
        ndvi=None,
        soil_ph=ph,
        rainfall_mm_30d=rain_30d,
        avg_temp_c=temp_c,
        market_prices=market_prices,
        humidity_pct=60.0,
        soil_nitrogen_mg_kg=n_mg_kg,
        soil_organic_carbon_g_kg=oc_g_kg,
        soil_moisture_pct=moisture_pct,
        soil_source="soilgrids",
        weather_source="nasa-power",
        satellite_source="unavailable",
    )
    fuzzy_matrix = crisp_to_default_fuzzy(DEFAULT_AHP_PAIRWISE_MATRIX)
    weights, _ = select_ahp_weights(DEFAULT_AHP_PAIRWISE_MATRIX, fuzzy_matrix)
    topsis_ranked = topsis(matrix, weights, is_benefit)
    return [crop_names[r["index"]] for r in topsis_ranked], topsis_ranked, matrix, crop_names


def test_all_configured_crops_enter_decision_matrix():
    ranking, _, matrix, crop_names = get_ranking_for_inputs(25.0, 100.0, 6.5, 800.0, 15.0, 25.0)
    assert len(crop_names) == 8
    assert set(crop_names) == set(CROP_DATABASE.keys())
    assert len(matrix) == 8
    assert len(ranking) == 8


def test_dry_hot_climate_does_not_recommend_rice():
    ranking, topsis_ranked, _, _ = get_ranking_for_inputs(38.0, 15.0, 7.2, 400.0, 10.0, 10.0)
    assert ranking[0] != "Rice"
    assert ranking[0] in ["Cotton", "Sugarcane", "Chickpea"]


def test_cool_climate_recommends_chickpea_or_wheat():
    ranking, topsis_ranked, _, _ = get_ranking_for_inputs(12.0, 50.0, 6.5, 800.0, 15.0, 25.0)
    assert ranking[0] in ["Chickpea", "Wheat"]
    assert ranking[0] != "Rice"


def test_low_rainfall_recommends_dryland_crop():
    ranking, topsis_ranked, _, _ = get_ranking_for_inputs(25.0, 10.0, 6.5, 800.0, 15.0, 25.0)
    assert ranking[0] in ["Chickpea", "Wheat", "Groundnut"]
    assert ranking[0] != "Rice"


def test_market_price_difference_influences_rankings():
    high_cotton_prices = {"Cotton": 9500.0, "Rice": 2000.0, "Wheat": 2000.0}
    ranking_with_market, _, _, _ = get_ranking_for_inputs(28.0, 90.0, 7.0, 600.0, 15.0, 25.0, market_prices=high_cotton_prices)
    ranking_no_market, _, _, _ = get_ranking_for_inputs(28.0, 90.0, 7.0, 600.0, 15.0, 25.0, market_prices=None)
    
    # Cotton rank should improve when its market price is significantly higher
    cotton_rank_with = ranking_with_market.index("Cotton")
    cotton_rank_without = ranking_no_market.index("Cotton")
    assert cotton_rank_with <= cotton_rank_without
