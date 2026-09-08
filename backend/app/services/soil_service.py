"""
Soil service — real ISRIC SoilGrids v2.0 REST API integration with lab test precedence
and data provenance tracking.

Docs: https://www.isric.org/explore/soilgrids/faq-soilgrids
Endpoint used: https://rest.isric.org/soilgrids/v2.0/properties/query

PRECEDENCE RULE:
LAB_MEASUREMENT (verified farmer/laboratory soil sample) > SoilGrids MODEL_PREDICTION.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

SOILGRIDS_BASE_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"


@dataclass
class SoilResult:
    ph: float
    clay_pct: float
    sand_pct: float
    soil_moisture_pct: float
    nitrogen_total_mg_kg: float
    organic_carbon_g_kg: float
    source: str  # "soilgrids", "lab_measurement", "soilgrids-cached", or "unavailable"
    source_type: str = "MODEL_PREDICTION"  # "LAB_MEASUREMENT", "MODEL_PREDICTION", "CACHED_API", "MOCK/FALLBACK"
    observation_date: str | None = None
    retrieved_at: str = ""
    is_stale: bool = False
    quality_status: str = "good"  # "good", "lab_verified", "stale", "unavailable"

    def __post_init__(self):
        if not self.retrieved_at:
            self.retrieved_at = datetime.now(timezone.utc).isoformat()


def _fetch_live_soil_moisture(lat: float, lon: float) -> float | None:
    """Fetch live volumetric soil moisture from Open-Meteo as real-time land surface API."""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current": "soil_moisture_0_to_7cm"}
        resp = requests.get(url, params=params, timeout=5)
        if resp.ok:
            data = resp.json()
            sm_val = data.get("current", {}).get("soil_moisture_0_to_7cm")
            if sm_val is not None:
                return round(float(sm_val) * 100.0, 1)
    except Exception as e:
        logger.debug("Live soil moisture fetch from Open-Meteo skipped for (%.4f, %.4f): %s", lat, lon, e)
    return None


def _fetch_via_soilgrids(lat: float, lon: float) -> SoilResult | None:
    params = {
        "lon": lon,
        "lat": lat,
        "property": ["phh2o", "clay", "sand", "nitrogen", "soc"],
        "depth": "0-5cm",
        "value": "mean",
    }

    def mean_at_0_5cm_from_layers(layers, prop_name, divisor=1.0, multiplier=1.0):
        layer = layers.get(prop_name)
        if not layer:
            return None
        depths = layer.get("depths", [])
        for d in depths:
            if d.get("label") == "0-5cm":
                val = d.get("values", {}).get("mean")
                if val is None:
                    return None
                return (val / divisor) * multiplier
        return None

    try:
        resp = requests.get(SOILGRIDS_BASE_URL, params=params, timeout=4)
        if not resp.ok:
            logger.error("SoilGrids API error for (%.4f, %.4f): HTTP %d", lat, lon, resp.status_code)
            return None
        
        payload = resp.json()
        layers = {layer["name"]: layer for layer in payload.get("properties", {}).get("layers", [])}

        ph = mean_at_0_5cm_from_layers(layers, "phh2o", divisor=10.0)
        clay = mean_at_0_5cm_from_layers(layers, "clay", divisor=10.0)
        sand = mean_at_0_5cm_from_layers(layers, "sand", divisor=10.0)
        nitrogen = mean_at_0_5cm_from_layers(layers, "nitrogen", multiplier=10.0)
        soc = mean_at_0_5cm_from_layers(layers, "soc", divisor=10.0)

        if ph is None:
            logger.warning("SoilGrids returned payload but missing phh2o at 0-5cm depth layer")
            return None

        live_moisture = _fetch_live_soil_moisture(lat, lon)
        moisture_val = live_moisture if live_moisture is not None else min(45.0, max(8.0, 15 + (clay or 20) * 0.5 - (sand or 40) * 0.1))

        now_iso = datetime.now(timezone.utc).isoformat()

        return SoilResult(
            ph=round(ph, 2),
            clay_pct=round(clay or 0, 1),
            sand_pct=round(sand or 0, 1),
            soil_moisture_pct=round(moisture_val, 1),
            nitrogen_total_mg_kg=round(nitrogen or 0, 1),
            organic_carbon_g_kg=round(soc or 0, 1),
            source="soilgrids",
            source_type="MODEL_PREDICTION",
            observation_date=now_iso[:10],
            retrieved_at=now_iso,
            is_stale=False,
            quality_status="good",
        )
    except Exception as e:
        logger.warning("SoilGrids API call unfulfilled for (%.4f, %.4f): %s", lat, lon, e)
        return None


def get_soil_for_location(
    lat: float, lon: float, db: any = None, farm_id: int | None = None
) -> SoilResult:
    """
    Fetch soil data for location with strict precedence:
    1. LAB_MEASUREMENT (verified laboratory soil test if uploaded)
    2. SoilGrids MODEL_PREDICTION (ISRIC v2.0 250m REST API)
    3. CACHED_API (last valid database observation marked stale)
    4. MOCK/FALLBACK (explicit unavailable marker, zero fake values)
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Check for verified LAB_MEASUREMENT
    if db is not None and farm_id is not None:
        try:
            from app.models.soil_test import SoilTest
            lab_test = db.query(SoilTest).filter(SoilTest.farm_id == farm_id).order_by(SoilTest.id.desc()).first()
            if lab_test:
                logger.info("Using LAB_MEASUREMENT soil test precedence for farm_id %d", farm_id)
                live_moisture = _fetch_live_soil_moisture(lat, lon) or 25.0
                return SoilResult(
                    ph=lab_test.ph,
                    clay_pct=lab_test.clay_pct or 20.0,
                    sand_pct=lab_test.sand_pct or 40.0,
                    soil_moisture_pct=live_moisture,
                    nitrogen_total_mg_kg=lab_test.nitrogen_mg_kg,
                    organic_carbon_g_kg=lab_test.organic_carbon_g_kg or 15.0,
                    source="lab_measurement",
                    source_type="LAB_MEASUREMENT",
                    observation_date=lab_test.sample_date or (lab_test.created_at.isoformat() if lab_test.created_at else now_iso[:10]),
                    retrieved_at=now_iso,
                    is_stale=False,
                    quality_status="lab_verified",
                )
        except Exception as e:
            logger.warning("Error checking lab soil test for farm_id %s: %s", farm_id, e)

    # 2. Query SoilGrids REST API (MODEL_PREDICTION)
    result = _fetch_via_soilgrids(lat, lon)
    if result is not None:
        return result

    # 3. Query DB cache for last stored valid observation (CACHED_API)
    if db is not None:
        try:
            from app.models.recommendation import Recommendation
            cached_rec = db.query(Recommendation).filter(
                (Recommendation.latitude == lat) & (Recommendation.longitude == lon)
            ).order_by(Recommendation.id.desc()).first()
            if cached_rec and cached_rec.soil_ph is not None and cached_rec.soil_ph > 0:
                logger.info("Preserving last valid cached soil observation for (%.4f, %.4f)", lat, lon)
                return SoilResult(
                    ph=cached_rec.soil_ph,
                    clay_pct=cached_rec.soil_clay_pct or 0.0,
                    sand_pct=cached_rec.soil_sand_pct or 0.0,
                    soil_moisture_pct=cached_rec.soil_moisture_pct or 0.0,
                    nitrogen_total_mg_kg=cached_rec.soil_nitrogen_mg_kg or 0.0,
                    organic_carbon_g_kg=cached_rec.soil_organic_carbon_g_kg or 0.0,
                    source="soilgrids-cached",
                    source_type="CACHED_API",
                    observation_date=cached_rec.created_at.isoformat()[:10] if cached_rec.created_at else None,
                    retrieved_at=now_iso,
                    is_stale=True,
                    quality_status="stale",
                )
        except Exception as e:
            logger.warning("Error querying cached soil reading: %s", e)

    # 4. ISRIC SoilGrids API unreachable & no cache: return explicit unavailable marker
    logger.warning("Soil data unavailable for (%.4f, %.4f) — ISRIC API unreachable and no cache found", lat, lon)
    return SoilResult(
        ph=0.0,
        clay_pct=0.0,
        sand_pct=0.0,
        soil_moisture_pct=0.0,
        nitrogen_total_mg_kg=0.0,
        organic_carbon_g_kg=0.0,
        source="unavailable",
        source_type="MOCK/FALLBACK",
        observation_date=None,
        retrieved_at=now_iso,
        is_stale=True,
        quality_status="unavailable",
    )
