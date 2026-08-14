"""Pure suitability scores for environmental and agronomic suitability.

This module intentionally contains no HTTP calls, database access, or Earth
Engine calls. All functions are deterministic and work only on the numeric
values passed in by the caller.

The objective is to convert raw measured and model-derived values into smooth,
normalized suitability scores in the [0, 1] range. This is used as the
"environmental suitability" layer that feeds the existing MCDM pipeline.
"""

from __future__ import annotations

import math

from app.crop_database import CROP_DATABASE


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _smooth_band_score(value: float, opt_min: float, opt_max: float) -> float:
    """Return a continuous score in [0,1].

    A value inside the optimal interval scores 1.0; moving away from the band
    gradually reduces the score until it approaches zero. The decay is linear,
    which keeps the function transparent and deterministic.
    """
    if not math.isfinite(value):
        return 0.0
    if opt_min is None or opt_max is None:
        return 0.0
    if opt_min <= value <= opt_max:
        return 1.0
    span = max(opt_max - opt_min, 1.0)
    if value < opt_min:
        gap = opt_min - value
    else:
        gap = value - opt_max
    return clamp01(1.0 - gap / span)


def temperature_suitability(value: float, opt_min: float, opt_max: float) -> float:
    return _smooth_band_score(value, opt_min, opt_max)


def rainfall_suitability(value: float, opt_min: float, opt_max: float) -> float:
    return _smooth_band_score(value, opt_min, opt_max)


def humidity_suitability(value: float, opt_min: float = 35.0, opt_max: float = 80.0, temperature_c: float | None = None) -> float:
    """Humidity suitability.

    In the absence of a crop-specific humidity target, a practical default is
    the middle range of moderate humidity. When temperature is also available,
    the function can use a vapour pressure deficit (VPD) proxy to sharpen the
    suitability estimate.
    """
    if temperature_c is not None:
        vpd_kpa = _vapour_pressure_deficit_kpa(temperature_c, value)
        return _smooth_band_score(vpd_kpa, 0.8, 1.6)
    return _smooth_band_score(value, opt_min, opt_max)


def soil_ph_suitability(value: float, opt_min: float, opt_max: float) -> float:
    return _smooth_band_score(value, opt_min, opt_max)


def nitrogen_suitability(value: float, target_value: float = 40.0, tolerance: float = 25.0) -> float:
    """Normalized nutrient adequacy score.

    The score is highest near a biologically relevant target and declines as the
    value becomes deficient or excessively high. It is intentionally smooth and
    not a hard pass-fail threshold.
    """
    if not math.isfinite(value):
        return 0.0
    lower = max(0.0, target_value - tolerance)
    upper = target_value + tolerance
    return _smooth_band_score(value, lower, upper)


def organic_carbon_suitability(value: float, target_value: float = 18.0, tolerance: float = 12.0) -> float:
    """Soil carbon suitability used as a moderated soil-quality indicator."""
    if not math.isfinite(value):
        return 0.0
    lower = max(0.0, target_value - tolerance)
    upper = target_value + tolerance
    return _smooth_band_score(value, lower, upper)


def soil_moisture_suitability(value: float, opt_min: float = 20.0, opt_max: float = 50.0) -> float:
    """Soil moisture suitability based on a broad available-water range.

    SoilGrids' water-content properties, when available, can be converted to a
    water-holding/availability estimate. For Phase 1, this function treats the
    observed volumetric soil moisture percentage as a normalized availability
    indicator on a broad agronomic band.
    """
    return _smooth_band_score(value, opt_min, opt_max)


def vegetation_suitability(value: float, opt_min: float = 0.45, opt_max: float = 0.75) -> float:
    return _smooth_band_score(value, opt_min, opt_max)


def market_suitability(value: float, opt_min: float = 1.0, opt_max: float = 10.0) -> float:
    return _smooth_band_score(value, opt_min, opt_max)


def _vapour_pressure_deficit_kpa(temperature_c: float, relative_humidity_pct: float) -> float:
    """Approximate VPD in kPa from temperature and relative humidity.

    This is a standard agronomic proxy used to reason about atmospheric water
    stress, not a direct crop-specific measurement.
    """
    if not math.isfinite(temperature_c) or not math.isfinite(relative_humidity_pct):
        return 0.0
    temp_c = max(temperature_c, 0.0)
    rh = clamp01(relative_humidity_pct / 100.0)
    sat_vp = 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    actual_vp = sat_vp * rh
    vpd = max(0.0, sat_vp - actual_vp) / 10.0
    return min(vpd, 5.0)


def estimate_et0_mm_day(temperature_c: float, solar_radiation_mj_m2: float, relative_humidity_pct: float, wind_speed_m_s: float) -> float:
    """Approximate reference evapotranspiration using a conservative method.

    This is intentionally simple and is used only for Phase 1 water-balance
    reasoning. It is not a replacement for a full FAO Penman-Monteith run.
    """
    if not all(math.isfinite(x) for x in (temperature_c, solar_radiation_mj_m2, relative_humidity_pct, wind_speed_m_s)):
        return 0.0
    ra = max(0.0, solar_radiation_mj_m2) / 10.0
    temp_term = (temperature_c + 17.8) ** 2
    humidity_term = 1.0 - (relative_humidity_pct / 100.0)
    wind_term = 1.0 + max(0.0, wind_speed_m_s) * 0.1
    eto = 0.0023 * temp_term * ra * humidity_term * wind_term
    return max(0.0, round(eto, 3))


def crop_water_requirement_mm_period(eto_mm_day: float, kc_mid: float, growth_stage_days: int = 120) -> float:
    """Very small FAO-style crop water demand approximation for a growth stage."""
    if not math.isfinite(eto_mm_day) or growth_stage_days <= 0:
        return 0.0
    return max(0.0, eto_mm_day * kc_mid * growth_stage_days)


def water_efficiency_suitability(rainfall_mm_30d: float, crop_water_need_mm: float, *, et0_mm_day: float | None = None, kc: float = 1.0) -> float:
    """Water adequacy score relative to crop water demand.

    The score balances current rainfall against the crop's approximate seasonal
    demand. If a crop requires substantial water, a rainfall amount that is
    proportionally low will reduce the suitability smoothly. This is not a
    binary irrigation/no-irrigation rule; it is a normalized adequacy signal.
    """
    if not math.isfinite(rainfall_mm_30d) or not math.isfinite(crop_water_need_mm):
        return 0.0
    demand = max(crop_water_need_mm, 1.0)
    ratio = rainfall_mm_30d / demand
    # Reasonable agronomic balance: around 0.75-1.2 of the crop demand gives a
    # strong water adequacy score; values below/above this taper smoothly.
    if 0.7 <= ratio <= 1.2:
        return 1.0
    if ratio < 0.7:
        return clamp01(1.0 - ((0.7 - ratio) / 0.7))
    return clamp01(1.0 - ((ratio - 1.2) / 1.2))


def calculate_crop_suitability_profile(
    crop_name: str,
    *,
    temperature_c: float,
    rainfall_mm_30d: float,
    humidity_pct: float,
    soil_ph: float,
    nitrogen_mg_kg: float,
    organic_carbon_g_kg: float,
    soil_moisture_pct: float,
    ndvi: float,
    market_value_index: float = 5.0,
    crop_params: dict | None = None,
) -> dict[str, float]:
    params = crop_params or CROP_DATABASE.get(crop_name, {})
    if not params:
        return {
            "temperature_suitability": 0.0,
            "rainfall_suitability": 0.0,
            "humidity_suitability": 0.0,
            "soil_ph_suitability": 0.0,
            "nitrogen_suitability": 0.0,
            "organic_carbon_suitability": 0.0,
            "soil_moisture_suitability": 0.0,
            "vegetation_suitability": 0.0,
            "water_suitability": 0.0,
            "market_suitability": 0.0,
            "overall_environmental_score": 0.0,
        }

    temp_score = temperature_suitability(temperature_c, params.get("ideal_temp_min_c", 15.0), params.get("ideal_temp_max_c", 30.0))
    rainfall_score = rainfall_suitability(rainfall_mm_30d, params.get("ideal_rainfall_min_mm_30d", 30.0), params.get("ideal_rainfall_max_mm_30d", 150.0))
    humidity_score = humidity_suitability(humidity_pct, 35.0, 80.0, temperature_c=temperature_c)
    ph_score = soil_ph_suitability(soil_ph, params.get("ideal_ph_min", 5.5), params.get("ideal_ph_max", 7.5))
    nitrogen_target = max(10.0, float(params.get("fertilizer_n_kg_per_acre", 30.0)) * 0.8)
    nitrogen_score = nitrogen_suitability(nitrogen_mg_kg, target_value=nitrogen_target, tolerance=max(12.0, nitrogen_target * 0.7))
    carbon_target = 18.0
    carbon_score = organic_carbon_suitability(organic_carbon_g_kg, target_value=carbon_target, tolerance=12.0)
    moisture_score = soil_moisture_suitability(soil_moisture_pct, 20.0, 50.0)
    vegetation_score = vegetation_suitability(ndvi, 0.4, 0.75)
    water_score = water_efficiency_suitability(rainfall_mm_30d, float(params.get("water_need_mm_season", 500.0)))
    market_score = market_suitability(market_value_index, 1.0, 10.0)

    climate_score = 0.55 * temp_score + 0.30 * rainfall_score + 0.15 * humidity_score
    soil_score = 0.45 * ph_score + 0.30 * nitrogen_score + 0.25 * carbon_score
    overall_environmental_score = 0.35 * climate_score + 0.30 * soil_score + 0.20 * moisture_score + 0.15 * vegetation_score

    return {
        "temperature_suitability": clamp01(temp_score),
        "rainfall_suitability": clamp01(rainfall_score),
        "humidity_suitability": clamp01(humidity_score),
        "soil_ph_suitability": clamp01(ph_score),
        "nitrogen_suitability": clamp01(nitrogen_score),
        "organic_carbon_suitability": clamp01(carbon_score),
        "soil_moisture_suitability": clamp01(moisture_score),
        "vegetation_suitability": clamp01(vegetation_score),
        "water_suitability": clamp01(water_score),
        "market_suitability": clamp01(market_score),
        "overall_environmental_score": clamp01(overall_environmental_score),
    }
