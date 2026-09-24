"""
Satellite service — NDVI computation from Sentinel-2 bands via Google Earth Engine (GEE)
with Data Provenance tracking and Field Polygon geometry support.

NDVI formula: (NIR - Red) / (NIR + Red) applied to Copernicus Sentinel-2 Level-2A imagery.
"""

from __future__ import annotations
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SatelliteResult:
    ndvi: float | None
    source: str  # "gee-sentinel2", "gee-cached", or "unavailable"
    scene_date: str | None
    source_type: str = "SATELLITE_OBSERVATION"  # "SATELLITE_OBSERVATION", "CACHED_API", "MOCK/FALLBACK"
    retrieved_at: str = ""
    is_stale: bool = False
    quality_status: str = "good"  # "good", "stale", "unavailable"

    def __post_init__(self):
        if not self.retrieved_at:
            self.retrieved_at = datetime.now(timezone.utc).isoformat()


def compute_ndvi(nir_band: "list[float] | any", red_band: "list[float] | any") -> float:
    """
    Real NDVI formula applied to arrays of NIR and Red reflectance values
    (e.g. Sentinel-2 B8 and B4 band pixel arrays for the field's footprint).
    """
    import numpy as np
    nir = np.array(nir_band, dtype=float)
    red = np.array(red_band, dtype=float)
    denom = nir + red
    denom[denom == 0] = 1e-9
    ndvi_pixels = (nir - red) / denom
    return float(np.clip(ndvi_pixels, -1, 1).mean())


def _fetch_via_gee(lat: float, lon: float, polygon_geojson: dict[str, Any] | list[Any] | None = None) -> SatelliteResult | None:
    """
    Real Google Earth Engine retrieval path for Sentinel-2 NDVI.
    Query: COPERNICUS/S2_SR_HARMONIZED
    NDVI: (B8 - B4) / (B8 + B4)
    Supports field boundary polygon geometry reduction when polygon_geojson is provided.
    """
    if not settings.gee_project:
        logger.warning("GEE_PROJECT not configured in settings")
        return None
    
    try:
        import ee
        ee.Initialize(project=settings.gee_project)

        # Build GEE geometry: Polygon if provided, or Point
        if polygon_geojson and isinstance(polygon_geojson, (dict, list)):
            try:
                if isinstance(polygon_geojson, dict) and polygon_geojson.get("coordinates"):
                    gee_geometry = ee.Geometry.Polygon(polygon_geojson.get("coordinates"))
                elif isinstance(polygon_geojson, list):
                    gee_geometry = ee.Geometry.Polygon(polygon_geojson)
                else:
                    gee_geometry = ee.Geometry.Point([lon, lat])
            except Exception as e:
                logger.warning("Error building GEE polygon geometry, falling back to point: %s", e)
                gee_geometry = ee.Geometry.Point([lon, lat])
        else:
            gee_geometry = ee.Geometry.Point([lon, lat])
        
        start_date = settings.satellite_lookback_start
        end_date = settings.satellite_lookback_end
        
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(gee_geometry)
            .filterDate(start_date, end_date)
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )
        
        image = collection.first()
        try:
            image_id = image.get("system:id").getInfo()
            if not image_id:
                from datetime import date, timedelta
                fallback_start = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
                collection = (
                    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                    .filterBounds(gee_geometry)
                    .filterDate(fallback_start, end_date)
                    .sort("CLOUDY_PIXEL_PERCENTAGE")
                )
                image = collection.first()
        except Exception:
            pass

        if not image:
            logger.warning(f"No Sentinel-2 image found for ({lat}, {lon})")
            return None

        # Compute NDVI via normalizedDifference on B8 (NIR) and B4 (Red)
        ndvi_image = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        
        # Reduce region over polygon or point buffer
        target_region = gee_geometry if gee_geometry.type().getInfo() == "Polygon" else gee_geometry.buffer(1000)
        
        stats = ndvi_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=target_region,
            scale=10,
            maxPixels=1e9
        )
        
        ndvi_value = stats.get("NDVI").getInfo()
        if ndvi_value is None and gee_geometry.type().getInfo() != "Polygon":
            stats = ndvi_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=gee_geometry.buffer(100),
                scale=10,
                maxPixels=1e9
            )
            ndvi_value = stats.get("NDVI").getInfo()

        if ndvi_value is None:
            logger.warning(f"NDVI mean reduction returned None for ({lat}, {lon})")
            return None

        scene_date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd").getInfo()
        now_iso = datetime.now(timezone.utc).isoformat()

        return SatelliteResult(
            ndvi=round(float(ndvi_value), 3),
            source="gee-sentinel2",
            source_type="SATELLITE_OBSERVATION",
            scene_date=scene_date,
            retrieved_at=now_iso,
            is_stale=False,
            quality_status="good",
        )
    except Exception as e:
        logger.error(f"Error in _fetch_via_gee: {type(e).__name__}: {e}")
        return None


def get_ndvi_for_location(
    lat: float, lon: float, polygon_geojson: dict[str, Any] | list[Any] | None = None, db: any = None
) -> SatelliteResult:
    """
    Get NDVI for a location from Sentinel-2 via Google Earth Engine.
    
    Returns:
      - SatelliteResult with source_type="SATELLITE_OBSERVATION" if GEE API succeeds
      - SatelliteResult with source_type="CACHED_API" and is_stale=True if last DB observation is used
      - SatelliteResult with source_type="MOCK/FALLBACK" and source="unavailable" if GEE API fails and no cache exists
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    result = _fetch_via_gee(lat, lon, polygon_geojson=polygon_geojson)
    if result is not None:
        return result
    
    # Check DB cache for last stored observation
    if db is not None:
        try:
            from app.models.recommendation import Recommendation
            cached_rec = db.query(Recommendation).filter(
                (Recommendation.latitude == lat) & (Recommendation.longitude == lon)
            ).order_by(Recommendation.id.desc()).first()
            if cached_rec and cached_rec.ndvi is not None and cached_rec.ndvi > 0:
                logger.info("Preserving last valid cached satellite observation for (%.4f, %.4f)", lat, lon)
                return SatelliteResult(
                    ndvi=cached_rec.ndvi,
                    source="gee-cached",
                    source_type="CACHED_API",
                    scene_date=cached_rec.satellite_scene_date,
                    retrieved_at=now_iso,
                    is_stale=True,
                    quality_status="stale",
                )
        except Exception as e:
            logger.warning("Error querying cached satellite reading: %s", e)

    # GEE not configured or failed & no cache — return explicit unavailable marker
    return SatelliteResult(
        ndvi=None,
        source="unavailable",
        source_type="MOCK/FALLBACK",
        scene_date=None,
        retrieved_at=now_iso,
        is_stale=True,
        quality_status="unavailable",
    )


def get_satellite_map_url(lat: float, lon: float, zoom: int = 12) -> str:
    """Generate Leaflet satellite tile URL for displaying imagery."""
    return f"https://tiles.sentinel-hub.com/wms/{{z}}/{{x}}/{{y}}?layers=TRUE_COLOR&showlogo=false"
