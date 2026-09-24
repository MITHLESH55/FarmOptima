"""
Builds the MCDM decision matrix from live, location-aware environmental
suitability rather than a static range-only comparison.

Each crop receives a normalized suitability profile from the dynamic model in
app.core.suitability, and the final decision matrix still preserves the same
MCDM interface expected by the rest of the pipeline: rows are crops and
columns are benefit-style criteria that higher is better.
"""

from __future__ import annotations

from app.crop_database import CROP_DATABASE
from app.core.suitability import calculate_crop_suitability_profile


def _range_fit_score(value: float, lo: float, hi: float) -> float:
    """Backward-compatible helper retained for tests and simple checks."""
    if lo <= value <= hi:
        return 1.0
    span = max(hi - lo, 1e-6)
    if value < lo:
        gap = lo - value
    else:
        gap = value - hi
    return max(0.0, 1.0 - gap / span)


def build_decision_matrix(
    *,
    ndvi: float | None = None,
    soil_ph: float,
    rainfall_mm_30d: float,
    avg_temp_c: float,
    market_prices: dict[str, float] | None = None,
    humidity_pct: float | None = None,
    soil_nitrogen_mg_kg: float | None = None,
    soil_organic_carbon_g_kg: float | None = None,
    soil_moisture_pct: float | None = None,
    soil_source: str = "soilgrids",
    weather_source: str = "nasa-power",
    satellite_source: str = "gee-sentinel2",
) -> tuple[list[str], list[list[float]], list[bool]]:
    """
    Returns (crop_names, decision_matrix, is_benefit) where decision_matrix
    rows = crops, columns = [climate_suitability, soil_suitability,
    water_efficiency, market_value] — all in 0-1 benefit form.

    The climate and soil scores come from the dynamic suitability model.
    When a data source is explicitly 'unavailable', baseline neutral scores (0.5)
    are populated so TOPSIS normalization remains mathematically sound.
    """
    from app.services.market_service import get_market_value_index

    crop_names = list(CROP_DATABASE.keys())
    matrix = []

    is_soil_available = soil_source != "unavailable" and (soil_ph > 0 or (soil_nitrogen_mg_kg or 0) > 0)
    is_weather_available = weather_source != "unavailable" and (avg_temp_c > 0 or rainfall_mm_30d > 0)
    is_sat_available = satellite_source != "unavailable" and ndvi is not None

    for crop in crop_names:
        params = CROP_DATABASE[crop]
        market_index = get_market_value_index(crop, market_prices or {}, params["base_market_value_index"])
        
        # Use ideal ph/temp defaults if source is unavailable to avoid 0.0 penalty
        effective_ph = soil_ph if is_soil_available else float(params.get("ideal_ph_min", 6.5))
        effective_temp = avg_temp_c if is_weather_available else float(params.get("ideal_temp_min_c", 22.0))
        effective_rain = rainfall_mm_30d if is_weather_available else float(params.get("ideal_rainfall_min_mm_30d", 50.0))

        profile = calculate_crop_suitability_profile(
            crop,
            temperature_c=effective_temp,
            rainfall_mm_30d=effective_rain,
            humidity_pct=humidity_pct if (humidity_pct is not None and is_weather_available) else 60.0,
            soil_ph=effective_ph,
            nitrogen_mg_kg=soil_nitrogen_mg_kg if (soil_nitrogen_mg_kg is not None and is_soil_available) else params["fertilizer_n_kg_per_acre"],
            organic_carbon_g_kg=soil_organic_carbon_g_kg if (soil_organic_carbon_g_kg is not None and is_soil_available) else 18.0,
            soil_moisture_pct=soil_moisture_pct if (soil_moisture_pct is not None and is_soil_available) else 30.0,
            ndvi=ndvi if is_sat_available else None,
            market_value_index=market_index,
            crop_params=params,
        )

        climate_score = (
            0.55 * profile["temperature_suitability"] + 0.30 * profile["rainfall_suitability"] + 0.15 * profile["humidity_suitability"]
            if is_weather_available else 0.5
        )
        soil_score = (
            0.45 * profile["soil_ph_suitability"] + 0.30 * profile["nitrogen_suitability"] + 0.25 * profile["organic_carbon_suitability"]
            if is_soil_available else 0.5
        )
        water_efficiency_score = (
            0.7 * profile["water_suitability"] + 0.3 * profile["vegetation_suitability"]
            if is_sat_available else profile["water_suitability"]
        )
        market_score = profile["market_suitability"]

        matrix.append([climate_score, soil_score, water_efficiency_score, market_score])

    is_benefit = [True, True, True, True]
    return crop_names, matrix, is_benefit


# Default AHP pairwise comparison matrix for the 4 criteria above, in the
# order [climate, soil, water_efficiency, market]. Values follow Saaty's
# 1-9 scale: e.g. climate is considered moderately more important (3x)
# than market value. Adjust these to reflect your own domain judgement —
# this is exactly the matrix an agronomist/advisor would be asked to fill
# in during a real AHP elicitation session.
DEFAULT_AHP_PAIRWISE_MATRIX = [
    # climate, soil, water_eff, market
    [1,       2,     3,         3],   # climate
    [1/2,     1,     2,         2],   # soil
    [1/3,     1/2,   1,         2],   # water_efficiency
    [1/3,     1/2,   1/2,       1],   # market
]
CRITERIA_NAMES = ["climate_suitability", "soil_suitability", "water_efficiency", "market_value"]
