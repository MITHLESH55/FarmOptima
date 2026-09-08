"""
Weather service — real NASA POWER Daily Point API integration with Data Provenance tracking.

Docs: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
Endpoint used: /api/temporal/daily/point
No API key required.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta

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
    source: str  # "nasa-power", "nasa-power-cached", or "unavailable"
    source_type: str = "LIVE_API"  # "LIVE_API", "CACHED_API", "MOCK/FALLBACK"
    observation_date: str | None = None
    retrieved_at: str = ""
    is_stale: bool = False
    quality_status: str = "good"  # "good", "stale", "unavailable"

    def __post_init__(self):
        if not self.retrieved_at:
            self.retrieved_at = datetime.now(timezone.utc).isoformat()


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

        now_iso = datetime.now(timezone.utc).isoformat()
        obs_date = f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"

        return WeatherResult(
            rainfall_mm_last_30d=round(sum(rainfall_vals), 1),
            avg_temp_c=round(sum(temp_vals) / len(temp_vals), 1) if temp_vals else 0.0,
            humidity_pct=round(sum(humidity_vals) / len(humidity_vals), 1) if humidity_vals else 0.0,
            solar_radiation_mj_m2=round(sum(solar_vals) / len(solar_vals), 2) if solar_vals else 0.0,
            wind_speed_m_s=round(sum(wind_vals) / len(wind_vals), 2) if wind_vals else 0.0,
            source="nasa-power",
            source_type="LIVE_API",
            observation_date=obs_date,
            retrieved_at=now_iso,
            is_stale=False,
            quality_status="good",
        )
    except Exception as e:
        logger.warning("NASA POWER request failed for (%s, %s): %s", lat, lon, e)
        return None


def get_weather_for_location(lat: float, lon: float, db: any = None) -> WeatherResult:
    """
    Fetch weather data from NASA POWER for the given location.
    If NASA POWER is unreachable, queries DB cache for last stored reading (marked CACHED_API with is_stale=true).
    If no cache exists, returns explicit unavailable marker.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    result = _fetch_via_nasa_power(lat, lon)
    if result is not None:
        return result
    
    # NASA POWER API failed — check DB cache for last valid observation
    if db is not None:
        try:
            from app.models.recommendation import Recommendation
            cached_rec = db.query(Recommendation).filter(
                (Recommendation.latitude == lat) & (Recommendation.longitude == lon)
            ).order_by(Recommendation.id.desc()).first()
            if cached_rec and cached_rec.avg_temp_c is not None and cached_rec.avg_temp_c > 0:
                logger.info("Preserving last valid cached weather observation for (%.4f, %.4f)", lat, lon)
                return WeatherResult(
                    rainfall_mm_last_30d=cached_rec.rainfall_mm_last_30d or 0.0,
                    avg_temp_c=cached_rec.avg_temp_c or 0.0,
                    humidity_pct=cached_rec.humidity_pct or 0.0,
                    solar_radiation_mj_m2=cached_rec.solar_radiation_mj_m2 or 0.0,
                    wind_speed_m_s=cached_rec.wind_speed_m_s or 0.0,
                    source="nasa-power-cached",
                    source_type="CACHED_API",
                    observation_date=cached_rec.created_at.isoformat()[:10] if cached_rec.created_at else None,
                    retrieved_at=now_iso,
                    is_stale=True,
                    quality_status="stale",
                )
        except Exception as e:
            logger.warning("Error querying cached weather reading: %s", e)

    # NASA POWER API failed or is unreachable & no cache — return unavailable marker
    logger.warning("Weather data unavailable for (%.4f, %.4f) — NASA POWER API unreachable", lat, lon)
    return WeatherResult(
        rainfall_mm_last_30d=0.0,
        avg_temp_c=0.0,
        humidity_pct=0.0,
        solar_radiation_mj_m2=0.0,
        wind_speed_m_s=0.0,
        source="unavailable",
        source_type="MOCK/FALLBACK",
        observation_date=None,
        retrieved_at=now_iso,
        is_stale=True,
        quality_status="unavailable",
    )
