from pydantic import BaseModel
from datetime import datetime


class FarmOut(BaseModel):
    id: int
    name: str | None
    latitude: float
    longitude: float
    created_at: datetime

    class Config:
        from_attributes = True


class WeatherOut(BaseModel):
    rainfall_mm_last_30d: float
    avg_temp_c: float
    humidity_pct: float
    source: str


class SoilOut(BaseModel):
    ph: float
    clay_pct: float
    sand_pct: float
    soil_moisture_pct: float
    source: str


class SatelliteOut(BaseModel):
    ndvi: float
    source: str
    scene_date: str | None
