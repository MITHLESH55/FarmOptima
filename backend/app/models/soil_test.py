"""SoilTest — laboratory soil analysis results uploaded for a farm."""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class SoilTest(Base):
    __tablename__ = "soil_tests"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sample_date = Column(String(30), nullable=True)
    lab_name = Column(String(120), nullable=True)
    
    # Measured properties
    ph = Column(Float, nullable=False)
    nitrogen_mg_kg = Column(Float, nullable=False)
    organic_carbon_g_kg = Column(Float, nullable=True)
    sand_pct = Column(Float, nullable=True)
    clay_pct = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
