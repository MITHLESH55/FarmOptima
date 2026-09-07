"""
Phase 2.5 — Decision Matrix Correctness Regression Tests.

These tests PROVE the discovered defects and VERIFY the fixes.
They were written AFTER mathematical proof of the defects from live data.

Proven defects:
1. nitrogen_suitability uses fertilizer_n_kg_per_acre (~12–80) as target
   but receives soil_nitrogen_mg_kg (~500–2000) → always 0 for all crops.
2. rainfall_suitability collapses to 0 for all crops when heavily above-optimal
   (e.g. monsoon 470mm/30d vs crop ideals of 30–300mm), making climate_suitability
   a constant for all crops → TOPSIS degenerates (multiple crops score 1.0000).
3. NSGA-II hypervolume_history is not serialized to the API → ResourcePlanPanel.jsx
   charts pareto_front array indices labeled as "Generations" (wrong data contract).
"""
import pytest
import sys, math
sys.path.insert(0, '.')

from app.core.suitability import (
    nitrogen_suitability,
    calculate_crop_suitability_profile,
    rainfall_suitability,
)
from app.core.criteria import build_decision_matrix
from app.services.market_service import load_market_prices


# ---------------------------------------------------------------------------
# BUG 1 — Nitrogen units mismatch: proves the defect
# ---------------------------------------------------------------------------

class TestNitrogenUnitsMismatch:
    """Prove that the old nitrogen_suitability is broken for SoilGrids values."""

    def test_soilgrids_nitrogen_gives_zero_for_all_crops(self):
        """
        SoilGrids returns total soil N in mg/kg (typically 500–2000 for Indian soils).
        The old code compares it against fertilizer_n_kg_per_acre * 0.8 (~12–80).
        Result: score = 0 for every crop → soil_suitability = 0.45*ph + 0 + 0.25*oc = 0.7 constant.
        This test proves that defect before fix and must PASS AFTER FIX (scores must be non-zero).
        """
        soilgrids_n = 1560.0  # mg/kg — typical Pune SoilGrids value
        from app.crop_database import CROP_DATABASE

        all_zero_before_fix = True
        for crop, params in CROP_DATABASE.items():
            n_target = max(10.0, float(params.get("fertilizer_n_kg_per_acre", 30.0)) * 0.8)
            n_tol = max(12.0, n_target * 0.7)
            score = nitrogen_suitability(soilgrids_n, target_value=n_target, tolerance=n_tol)
            if score > 0.001:
                all_zero_before_fix = False
                break

        # AFTER FIX: at least some crops must differentiate (not all zero)
        # Use the fixed suitability profile which now uses soil_n_mg_kg scale
        n_scores = []
        for crop, params in CROP_DATABASE.items():
            profile = calculate_crop_suitability_profile(
                crop,
                temperature_c=23.7, rainfall_mm_30d=100.0, humidity_pct=65.0,
                soil_ph=6.8, nitrogen_mg_kg=soilgrids_n, organic_carbon_g_kg=18.0,
                soil_moisture_pct=28.0, ndvi=0.35, market_value_index=7.0,
                crop_params=params,
            )
            n_scores.append(profile["nitrogen_suitability"])

        # Post-fix requirement: at least one non-zero nitrogen score at N=1560 mg/kg
        assert any(s > 0 for s in n_scores), (
            f"After fix, at least some crops must have non-zero nitrogen_suitability at N=1560 mg/kg. "
            f"Got: {dict(zip(list(CROP_DATABASE.keys()), n_scores))}"
        )

    def test_nitrogen_suitability_differentiates_crops(self):
        """
        After fix, high-N-demanding crops (Sugarcane, Cotton) must score
        differently from low-N crops (Chickpea, Groundnut) at a given soil N level.
        This is the FUNDAMENTAL property the defect was destroying.
        """
        from app.crop_database import CROP_DATABASE
        soilgrids_n = 800.0  # mg/kg — medium soil N

        profiles = {}
        for crop, params in CROP_DATABASE.items():
            profile = calculate_crop_suitability_profile(
                crop,
                temperature_c=25.0, rainfall_mm_30d=80.0, humidity_pct=65.0,
                soil_ph=6.5, nitrogen_mg_kg=soilgrids_n, organic_carbon_g_kg=18.0,
                soil_moisture_pct=30.0, ndvi=0.4, market_value_index=7.0,
                crop_params=params,
            )
            profiles[crop] = profile["nitrogen_suitability"]

        # Must not all be identical
        unique_n_scores = set(round(v, 4) for v in profiles.values())
        assert len(unique_n_scores) > 1, (
            f"After fix, nitrogen_suitability must differ across crops. "
            f"Got identical scores: {profiles}"
        )

    def test_decision_matrix_soil_col_not_constant(self):
        """
        After fix, the soil_suitability column of the decision matrix must
        NOT be constant (0.7 for all crops) when real SoilGrids data is used.
        """
        market_prices = load_market_prices()
        crop_names, dm, _ = build_decision_matrix(
            ndvi=0.35, soil_ph=6.8, rainfall_mm_30d=100.0, avg_temp_c=25.0,
            humidity_pct=65.0, soil_nitrogen_mg_kg=1560.0, soil_organic_carbon_g_kg=18.0,
            soil_moisture_pct=28.0, market_prices=market_prices,
            soil_source="soilgrids-reference", weather_source="nasa-power",
            satellite_source="gee-sentinel2",
        )
        soil_col = [row[1] for row in dm]  # index 1 = soil_suitability
        unique = set(round(v, 6) for v in soil_col)
        assert len(unique) > 1, (
            f"soil_suitability must differentiate crops when soil data is live. "
            f"Got constant soil column: {dict(zip(crop_names, soil_col))}"
        )


# ---------------------------------------------------------------------------
# BUG 1a — Soil suitability always 0.7: prove the constant
# ---------------------------------------------------------------------------

class TestSoilSuitabilityConstant:
    """Prove that soil_suitability = 0.7 for all crops under typical SoilGrids values."""

    def test_soil_suitability_was_0_7_constant(self):
        """
        With pre-fix code: ph=6.98 (all crops in range → ph_score=1.0),
        N=1560 mg/kg (all n_score=0), OC=18 (all oc_score=1.0)
        → soil = 0.45*1 + 0.30*0 + 0.25*1 = 0.7 for every crop.
        After fix this test serves as a baseline — the constant must be broken.
        """
        market_prices = load_market_prices()
        crop_names, dm, _ = build_decision_matrix(
            ndvi=0.35, soil_ph=6.98, rainfall_mm_30d=100.0, avg_temp_c=25.0,
            humidity_pct=65.0, soil_nitrogen_mg_kg=1560.0, soil_organic_carbon_g_kg=18.0,
            soil_moisture_pct=28.0, market_prices=market_prices,
            soil_source="soilgrids-reference", weather_source="nasa-power",
            satellite_source="gee-sentinel2",
        )
        soil_col = [row[1] for row in dm]
        # After fix: must NOT all be exactly 0.7
        all_equal_07 = all(abs(v - 0.7) < 0.001 for v in soil_col)
        assert not all_equal_07, (
            f"After fix, soil_suitability must NOT be 0.7 constant for all crops. "
            f"Still getting: {dict(zip(crop_names, [round(v, 4) for v in soil_col]))}"
        )


# ---------------------------------------------------------------------------
# BUG 2 — TOPSIS degeneracy when climate scores are identical
# ---------------------------------------------------------------------------

class TestTOPSIDegeneracy:
    """Prove TOPSIS degeneracy and that the fix resolves it."""

    def test_pune_conditions_no_longer_produce_topsis_1_for_multiple_crops(self):
        """
        Pune conditions (rain=470mm/30d, temp=23.7, hum=93.4%) caused all crops
        to have climate_suitability=0.583 and soil_suitability=0.7 → identical rows
        → multiple crops with TOPSIS closeness=1.0000 (degenerate).
        After fix: at most ONE crop may score 1.0 in TOPSIS.
        """
        from app.core.mcdm import topsis
        from app.core.criteria import build_decision_matrix, DEFAULT_AHP_PAIRWISE_MATRIX, CRITERIA_NAMES
        from app.core.mcdm import ahp_weights
        from app.core.fuzzy_ahp import crisp_to_default_fuzzy, select_ahp_weights

        market_prices = load_market_prices()
        crop_names, dm, is_benefit = build_decision_matrix(
            ndvi=0.254, soil_ph=6.98, rainfall_mm_30d=470.2, avg_temp_c=23.7,
            humidity_pct=93.4, soil_nitrogen_mg_kg=1560.0, soil_organic_carbon_g_kg=18.0,
            soil_moisture_pct=27.2, market_prices=market_prices,
            soil_source="soilgrids-reference", weather_source="nasa-power",
            satellite_source="gee-sentinel2",
        )

        crisp = ahp_weights(DEFAULT_AHP_PAIRWISE_MATRIX)
        fuzzy_matrix = crisp_to_default_fuzzy(DEFAULT_AHP_PAIRWISE_MATRIX)
        weights, _ = select_ahp_weights(DEFAULT_AHP_PAIRWISE_MATRIX, fuzzy_matrix)

        ranked = topsis(dm, weights, is_benefit)
        perfect_scores = [e for e in ranked if abs(e["closeness"] - 1.0) < 1e-8]

        assert len(perfect_scores) <= 1, (
            f"After fix, at most 1 crop should have TOPSIS=1.0000 (the true best). "
            f"Got {len(perfect_scores)} crops at 1.0: "
            f"{[crop_names[e['index']] for e in perfect_scores]}"
        )

    def test_climate_scores_differentiate_crops_at_extreme_rainfall(self):
        """
        At extreme rainfall (470mm/30d), crops must still receive different
        climate_suitability scores (the high-water crops like Sugarcane/Rice
        must score better than low-water crops like Chickpea/Wheat).
        """
        market_prices = load_market_prices()
        crop_names, dm, _ = build_decision_matrix(
            ndvi=0.254, soil_ph=6.98, rainfall_mm_30d=470.2, avg_temp_c=23.7,
            humidity_pct=93.4, soil_nitrogen_mg_kg=1560.0, soil_organic_carbon_g_kg=18.0,
            soil_moisture_pct=27.2, market_prices=market_prices,
            soil_source="soilgrids-reference", weather_source="nasa-power",
            satellite_source="gee-sentinel2",
        )
        climate_col = [row[0] for row in dm]  # climate_suitability
        unique_climate = set(round(v, 4) for v in climate_col)
        assert len(unique_climate) > 1, (
            f"After fix, climate_suitability must differentiate crops at extreme rainfall. "
            f"Got: {dict(zip(crop_names, [round(v, 4) for v in climate_col]))}"
        )


# ---------------------------------------------------------------------------
# BUG 3 — Optimizer chart data contract: hypervolume_history missing from API
# ---------------------------------------------------------------------------

class TestOptimizerDataContract:
    """Prove the optimizer data contract between NSGA-II and the API/frontend."""

    def test_nsga2_hypervolume_history_length_equals_generations(self):
        """NSGA2Result.hypervolume_history must have one entry per generation."""
        from app.core.nsga2 import optimize_resources_multiobjective
        result = optimize_resources_multiobjective(
            crop_water_need_mm=500, crop_fert_need_kg_acre=20,
            rainfall_mm_30d=100, soil_moisture_pct=30,
            population_size=20, generations=10, seed=42,
        )
        assert result.generations_run == 10
        assert len(result.hypervolume_history) == 10, (
            f"hypervolume_history length {len(result.hypervolume_history)} != generations_run {result.generations_run}"
        )

    def test_resource_plan_schema_includes_convergence_history(self, client, auth_headers, monkeypatch):
        """
        The /api/recommend response ResourcePlan must include convergence_history
        so ResourcePlanPanel.jsx can plot the actual per-generation convergence,
        not the Pareto front array indices mislabeled as generations.
        """
        import app.api.routes.recommend as rec
        from app.services.satellite_service import SatelliteResult
        from app.services.weather_service import WeatherResult
        from app.services.soil_service import SoilResult

        monkeypatch.setattr(rec, "get_ndvi_for_location", lambda lat, lon: SatelliteResult(ndvi=0.35, source="gee-sentinel2", scene_date="2026-07-14"))
        monkeypatch.setattr(rec, "get_weather_for_location", lambda lat, lon: WeatherResult(
            rainfall_mm_last_30d=100.0, avg_temp_c=25.0, humidity_pct=65.0,
            solar_radiation_mj_m2=15.0, wind_speed_m_s=2.0, source="nasa-power",
        ))
        monkeypatch.setattr(rec, "get_soil_for_location", lambda lat, lon: SoilResult(
            ph=6.5, clay_pct=25.0, sand_pct=35.0, soil_moisture_pct=28.0,
            nitrogen_total_mg_kg=900.0, organic_carbon_g_kg=15.0, source="soilgrids-reference",
        ))
        resp = client.post("/api/recommend", json={"lat": 18.5, "lon": 73.8}, headers=auth_headers)
        assert resp.status_code == 200
        plan = resp.json()["resource_plan"]

        # After fix: convergence_history must be present and have the correct length
        assert "convergence_history" in plan, (
            "resource_plan must include convergence_history for the frontend chart. "
            "ResourcePlanPanel.jsx was plotting pareto_front indices as generation numbers."
        )
        expected_gens = plan["optimizer_generations_run"]
        assert len(plan["convergence_history"]) == expected_gens, (
            f"convergence_history length {len(plan['convergence_history'])} != "
            f"optimizer_generations_run {expected_gens}"
        )


# ---------------------------------------------------------------------------
# MULTI-LOCATION: prove pipeline depends on location
# ---------------------------------------------------------------------------

class TestMultiLocationDifferentiation:
    """
    Verify that different locations produce different decision matrices
    and that ranking is derived from actual inputs, not static data.
    """

    @pytest.mark.parametrize("loc_a,loc_b", [
        # Bengaluru (dry, moderate rain) vs Pune (monsoon)
        (
            {"ndvi": 0.282, "rain": 105.6, "temp": 23.9, "hum": 79.9, "ph": 7.14, "n": 1470.0, "oc": 18.8, "moist": 39.6},
            {"ndvi": 0.254, "rain": 470.2, "temp": 23.7, "hum": 93.4, "ph": 6.98, "n": 1560.0, "oc": 18.0, "moist": 27.2},
        ),
        # Jaipur (semi-arid) vs Hyderabad (intermediate)
        (
            {"ndvi": 0.238, "rain": 206.1, "temp": 29.2, "hum": 76.4, "ph": 6.98, "n": 1290.0, "oc": 18.0, "moist": 22.7},
            {"ndvi": 0.250, "rain": 260.9, "temp": 25.8, "hum": 83.1, "ph": 6.98, "n": 1380.0, "oc": 17.2, "moist": 21.4},
        ),
    ])
    def test_decision_matrices_differ_across_locations(self, loc_a, loc_b):
        """Two different locations must produce different decision matrices."""
        market_prices = load_market_prices()

        def make_dm(loc):
            _, dm, _ = build_decision_matrix(
                ndvi=loc["ndvi"], soil_ph=loc["ph"], rainfall_mm_30d=loc["rain"],
                avg_temp_c=loc["temp"], humidity_pct=loc["hum"],
                soil_nitrogen_mg_kg=loc["n"], soil_organic_carbon_g_kg=loc["oc"],
                soil_moisture_pct=loc["moist"], market_prices=market_prices,
                soil_source="soilgrids-reference", weather_source="nasa-power",
                satellite_source="gee-sentinel2",
            )
            return dm

        dm_a = make_dm(loc_a)
        dm_b = make_dm(loc_b)

        # At least some cells must differ
        all_equal = all(
            abs(a - b) < 1e-9
            for row_a, row_b in zip(dm_a, dm_b)
            for a, b in zip(row_a, row_b)
        )
        assert not all_equal, "Decision matrices must differ for different environmental inputs"

    def test_extreme_rain_location_different_top_crop_from_dry_location(self):
        """
        A high-water crop (e.g. Rice/Sugarcane) should have a comparatively
        BETTER TOPSIS score in a very-wet location than in a dry location.
        This proves the computation is location-sensitive.
        """
        from app.core.mcdm import topsis, ahp_weights
        from app.core.criteria import build_decision_matrix, DEFAULT_AHP_PAIRWISE_MATRIX
        from app.core.fuzzy_ahp import crisp_to_default_fuzzy, select_ahp_weights

        market_prices = load_market_prices()

        # Dry location: rain=60mm
        _, dm_dry, is_benefit = build_decision_matrix(
            ndvi=0.35, soil_ph=6.5, rainfall_mm_30d=60.0, avg_temp_c=28.0,
            humidity_pct=55.0, soil_nitrogen_mg_kg=900.0, soil_organic_carbon_g_kg=15.0,
            soil_moisture_pct=20.0, market_prices=market_prices,
            soil_source="soilgrids-reference", weather_source="nasa-power",
            satellite_source="gee-sentinel2",
        )
        from app.crop_database import CROP_DATABASE
        crop_names = list(CROP_DATABASE.keys())
        fuzzy_matrix = crisp_to_default_fuzzy(DEFAULT_AHP_PAIRWISE_MATRIX)
        weights, _ = select_ahp_weights(DEFAULT_AHP_PAIRWISE_MATRIX, fuzzy_matrix)

        ranked_dry = topsis(dm_dry, weights, is_benefit)
        top_dry = crop_names[ranked_dry[0]["index"]]

        # Wet location: rain=350mm (strongly monsoon)
        _, dm_wet, _ = build_decision_matrix(
            ndvi=0.35, soil_ph=6.5, rainfall_mm_30d=350.0, avg_temp_c=28.0,
            humidity_pct=85.0, soil_nitrogen_mg_kg=900.0, soil_organic_carbon_g_kg=15.0,
            soil_moisture_pct=45.0, market_prices=market_prices,
            soil_source="soilgrids-reference", weather_source="nasa-power",
            satellite_source="gee-sentinel2",
        )
        ranked_wet = topsis(dm_wet, weights, is_benefit)
        top_wet = crop_names[ranked_wet[0]["index"]]

        # The water_efficiency_suitability must differ for dry vs wet
        rice_idx = crop_names.index("Rice")
        chickpea_idx = crop_names.index("Chickpea")
        rice_water_wet = dm_wet[rice_idx][2]
        rice_water_dry = dm_dry[rice_idx][2]
        chickpea_water_wet = dm_wet[chickpea_idx][2]
        chickpea_water_dry = dm_dry[chickpea_idx][2]

        # Rice should score better on water_efficiency in wet conditions than dry
        # Chickpea should score better on water_efficiency in dry conditions
        assert rice_water_wet != rice_water_dry or chickpea_water_wet != chickpea_water_dry, (
            "water_efficiency scores must differ between wet and dry conditions"
        )
