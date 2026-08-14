from pydantic import BaseModel, Field


class LocationRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class DataProvenance(BaseModel):
    """Transparency block — tells the caller which fields are from a live
    data source vs. a mock fallback, so this is never silently ambiguous."""
    satellite_source: str
    weather_source: str
    soil_source: str
    market_source: str
