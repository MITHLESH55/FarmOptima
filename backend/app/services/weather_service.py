"""
Weather service — real NASA POWER Daily Point API integration.

Docs: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
Endpoint used: /api/temporal/daily/point
No API key required. Falls back to a deterministic mock only if the
request fails (no network, rate limit, etc.) — the failure is logged and
flagged in the response, never silently swapped in.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import date, timedelta

import requests

logger = logging.getLogger(__name__)

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


@dataclass
class WeatherResult:
    rainfall_mm_last_30d: float
    avg_temp_c: float
    humidity_pct: float
    solar_radiation_mj_m2: float
    wind_speed_m_s: float
    source: str  # "nasa-power" or "mock"


def _fetch_via_nasa_power(lat: float, lon: float, lookback_days: int = 30) -> WeatherResult | None:
    end = date.today()
    start = end - timedelta(days=lookback_days)
    params = {
        "parameters": "PRECTOTCORR,T2M,RH2M,ALLSKY_SFC_SW_DWN,WS2M",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    try:
        resp = requests.get(NASA_POWER_BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        params_data = payload["properties"]["parameter"]

        rainfall_series = params_data["PRECTOTCORR"]
        temp_series = params_data["T2M"]
        humidity_series = params_data["RH2M"]
        solar_series = params_data["ALLSKY_SFC_SW_DWN"]
        wind_series = params_data["WS2M"]

        # NASA POWER uses -999 as a fill value for missing days — exclude them.
        rainfall_vals = [v for v in rainfall_series.values() if v > -900]
        temp_vals = [v for v in temp_series.values() if v > -900]
        humidity_vals = [v for v in humidity_series.values() if v > -900]
        solar_vals = [v for v in solar_series.values() if v > -900]
        wind_vals = [v for v in wind_series.values() if v > -900]

        return WeatherResult(
            rainfall_mm_last_30d=round(sum(rainfall_vals), 1),
            avg_temp_c=round(sum(temp_vals) / len(temp_vals), 1) if temp_vals else 0.0,
            humidity_pct=round(sum(humidity_vals) / len(humidity_vals), 1) if humidity_vals else 0.0,
            solar_radiation_mj_m2=round(sum(solar_vals) / len(solar_vals), 2) if solar_vals else 0.0,
            wind_speed_m_s=round(sum(wind_vals) / len(wind_vals), 2) if wind_vals else 0.0,
            source="nasa-power",
        )
    except Exception as e:
        logger.warning("NASA POWER request failed for (%s, %s): %s", lat, lon, e)
        return None


def get_weather_for_location(lat: float, lon: float) -> WeatherResult:
    """
    Fetch weather data from NASA POWER for the given location.
    
    Returns:
        - WeatherResult with source="nasa-power" if API succeeds
        - WeatherResult with source="unavailable" and zero values if API fails
    
    IMPORTANT: This function does NOT fall back to synthetic mock data.
    If NASA POWER is unreachable or returns an error, the caller receives
    an explicit unavailable marker, not a fake live value.
    """
    result = _fetch_via_nasa_power(lat, lon)
    if result is not None:
        return result
    
    # NASA POWER API failed or is unreachable — return unavailable marker
    logger.warning("Weather data unavailable for (%.4f, %.4f) — NASA POWER API unreachable", lat, lon)
    return WeatherResult(
        rainfall_mm_last_30d=0.0,
        avg_temp_c=0.0,
        humidity_pct=0.0,
        solar_radiation_mj_m2=0.0,
        wind_speed_m_s=0.0,
        source="unavailable",
    )
