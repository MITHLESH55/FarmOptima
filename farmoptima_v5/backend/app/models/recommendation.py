"""
Recommendation — a persisted record of every /recommend run.

Storing every run (inputs, provenance, and outputs) is what makes Chapter 7
validation and reproducibility possible later: you can query this table to
show "here are N runs, here's what data source each used, here's what was
recommended" as evidence for your report/patent documentation, rather than
relying on screenshots alone.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True, index=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Raw environmental readings at the time of this run
    ndvi = Column(Float)
    ndvi_status = Column(String(40))
    satellite_scene_date = Column(String(30))

    # Weather readings
    soil_ph = Column(Float)
    soil_moisture_pct = Column(Float)
    soil_sand_pct = Column(Float)
    soil_clay_pct = Column(Float)
    soil_nitrogen_mg_kg = Column(Float)
    soil_organic_carbon_g_kg = Column(Float)
    
    rainfall_mm_last_30d = Column(Float)
    avg_temp_c = Column(Float)
    humidity_pct = Column(Float)
    solar_radiation_mj_m2 = Column(Float)
    wind_speed_m_s = Column(Float)

    satellite_source = Column(String(30))
    weather_source = Column(String(30))
    soil_source = Column(String(30))
    market_source = Column(String(30))

    top_crop = Column(String(60))
    ahp_consistency_ratio = Column(Float)

    # Full structured result kept as JSON for complete traceability/audit
    full_result = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
