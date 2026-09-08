from pydantic import BaseModel, Field
from typing import Any


class LocationRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    field_area_acres: float = Field(1.0, gt=0, le=1000)
    polygon_geojson: dict[str, Any] | list[Any] | None = None


class ProvenanceItem(BaseModel):
    source_name: str
    source_type: str  # LIVE_API, MODEL_PREDICTION, LAB_MEASUREMENT, SATELLITE_OBSERVATION, STATIC_DATASET, CACHED_API, MOCK/FALLBACK
    observation_date: str | None = None
    retrieved_at: str
    is_stale: bool = False
    quality_status: str = "good"  # "good" | "stale" | "unavailable" | "lab_verified"
    endpoint_reference: str | None = None


class DataProvenance(BaseModel):
    """Transparency block — tells the caller which fields are from a live
    data source vs. a mock fallback or lab test, so this is never silently ambiguous."""
    satellite_source: str
    weather_source: str
    soil_source: str
    market_source: str
    
    # Structured Data Provenance Details
    weather_provenance: ProvenanceItem | None = None
    soil_provenance: ProvenanceItem | None = None
    satellite_provenance: ProvenanceItem | None = None
    market_provenance: ProvenanceItem | None = None
