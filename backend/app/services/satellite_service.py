"""
Satellite service — NDVI computation from Sentinel-2 bands via Google Earth
Engine (GEE).

NDVI math here is real: NDVI = (NIR - Red) / (NIR + Red), operating on
actual band reflectance arrays. The GEE *retrieval* call requires you to
have registered a Google Cloud project for Earth Engine access (see
project README) — until GEE_PROJECT is configured in your environment,
this service transparently falls back to a clearly-flagged synthetic mode
so the rest of the pipeline can still be developed/demoed.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass

from app.config import settings


@dataclass
class SatelliteResult:
    ndvi: float
    source: str          # "gee-sentinel2" or "mock"
    scene_date: str | None


def compute_ndvi(nir_band: "list[float] | any", red_band: "list[float] | any") -> float:
    """
    Real NDVI formula applied to arrays of NIR and Red reflectance values
    (e.g. flattened Sentinel-2 B8 and B4 band pixel arrays for the field's
    footprint). Returns the mean NDVI across all provided pixels.
    """
    import numpy as np
    nir = np.array(nir_band, dtype=float)
    red = np.array(red_band, dtype=float)
    denom = nir + red
    denom[denom == 0] = 1e-9
    ndvi_pixels = (nir - red) / denom
    return float(np.clip(ndvi_pixels, -1, 1).mean())


def _fetch_via_gee(lat: float, lon: float) -> SatelliteResult | None:
    """
    Real Google Earth Engine retrieval path for Sentinel-2 NDVI.
    Query: COPERNICUS/S2_SR_HARMONIZED
    NDVI: (B8 - B4) / (B8 + B4)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not settings.gee_project:
        logger.warning("GEE_PROJECT not configured in settings")
        return None
    
    try:
        import ee
        ee.Initialize(project=settings.gee_project)

        point = ee.Geometry.Point([lon, lat])
        
        # Try configured lookback window first; if no scenes found, extend to 365 days
        start_date = settings.satellite_lookback_start
        end_date = settings.satellite_lookback_end
        
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(point)
            .filterDate(start_date, end_date)
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )
        
        # If collection is empty for 60-day window, fallback to 1-year lookback
        image = collection.first()
        try:
            image_id = image.get("system:id").getInfo()
            if not image_id:
                from datetime import date, timedelta
                fallback_start = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
                collection = (
                    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                    .filterBounds(point)
                    .filterDate(fallback_start, end_date)
                    .sort("CLOUDY_PIXEL_PERCENTAGE")
                )
                image = collection.first()
                image_id = image.get("system:id").getInfo()
        except Exception:
            from datetime import date, timedelta
            fallback_start = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(point)
                .filterDate(fallback_start, end_date)
                .sort("CLOUDY_PIXEL_PERCENTAGE")
            )
            image = collection.first()

        if not image:
            logger.warning(f"No Sentinel-2 image found for point ({lat}, {lon})")
            return None

        # Compute NDVI via normalizedDifference on B8 (NIR) and B4 (Red)
        ndvi_image = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        
        # Compute mean NDVI across 1000m buffer footprint
        stats = ndvi_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point.buffer(1000),
            scale=10,
            maxPixels=1e9
        )
        
        ndvi_value = stats.get("NDVI").getInfo()
        if ndvi_value is None:
            # Try 100m buffer if 1000m buffer returned None
            stats = ndvi_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point.buffer(100),
                scale=10,
                maxPixels=1e9
            )
            ndvi_value = stats.get("NDVI").getInfo()

        if ndvi_value is None:
            logger.warning(f"NDVI mean reduction returned None for point ({lat}, {lon})")
            return None

        scene_date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd").getInfo()

        return SatelliteResult(
            ndvi=round(float(ndvi_value), 3),
            source="gee-sentinel2",
            scene_date=scene_date
        )
    except Exception as e:
        logger.error(f"Error in _fetch_via_gee: {type(e).__name__}: {e}", exc_info=True)
        return None


def _mock_ndvi(lat: float, lon: float) -> SatelliteResult:
    """
    Deterministic (not random-per-call) synthetic NDVI, seeded from the
    coordinates so the same location always yields the same mock value
    during development without GEE access configured yet.
    """
    seed_str = f"{round(lat, 3)}:{round(lon, 3)}"
    h = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
    ndvi = 0.2 + (h % 6000) / 10000.0  # spread across 0.2 - 0.8
    return SatelliteResult(ndvi=round(ndvi, 3), source="mock", scene_date=None)


def get_ndvi_for_location(lat: float, lon: float) -> SatelliteResult:
    """
    Get NDVI for a location from Sentinel-2 via Google Earth Engine.
    
    Returns:
      - SatelliteResult with source="gee-sentinel2" if GEE API succeeds
      - SatelliteResult with source="unavailable" if GEE is not configured or fails
    
    To enable: Set GEE_PROJECT environment variable and run 'earthengine authenticate'
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[NDVI_DIAGNOSTIC] get_ndvi_for_location called: lat={lat}, lon={lon}, gee_project={settings.gee_project}")
    
    result = _fetch_via_gee(lat, lon)
    if result is not None:
        logger.info(f"[NDVI_DIAGNOSTIC] GEE fetch succeeded: {result}")
        return result
    
    # GEE not configured or failed — return unavailable marker
    if not settings.gee_project:
        logger.warning("[NDVI_DIAGNOSTIC] GEE_PROJECT not set in .env — Earth Engine integration unavailable")
    else:
        logger.warning(f"[NDVI_DIAGNOSTIC] Earth Engine request failed for ({lat}, {lon}) — check authentication")
    
    unavailable_result = SatelliteResult(ndvi=0.0, source="unavailable", scene_date=None)
    logger.info(f"[NDVI_DIAGNOSTIC] Returning unavailable result: {unavailable_result}")
    return unavailable_result


def get_satellite_map_url(lat: float, lon: float, zoom: int = 12) -> str:
    """
    Generate a satellite map URL for displaying the location.
    Uses public tile services (Sentinel-2 tiles or OSM Satellite).
    
    Returns a Leaflet-compatible tile URL that can be used in frontend mapping.
    For production, consider:
    - Google Maps Static API (requires API key)
    - Mapbox Static API (requires API key)
    - USGS LandSat public tiles
    - Copernicus Sentinel-2 public tiles
    """
    # Use USGS Sentinel-2 public tiles (level-2A, 10m resolution)
    # These tiles are freely available and don't require API keys
    # Tile service: https://sentinel.ga.gov.au/
    # Alternative: https://tiles.sentinel-hub.com/
    
    # For now, return a URL to display satellite imagery via a public tile service
    # This returns a Leaflet tile URL pattern that can be embedded in a frontend map
    url = f"https://tiles.sentinel-hub.com/wms/{{z}}/{{x}}/{{y}}?layers=TRUE_COLOR&showlogo=false"
    return url

