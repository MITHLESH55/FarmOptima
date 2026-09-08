"""
Soil Test route — Allows uploading verified laboratory soil analysis measurements
for a farm location (LAB_MEASUREMENT).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Farm, SoilTest
from app.api.deps import get_current_user


router = APIRouter(prefix="/farms", tags=["soil_tests"])


class SoilTestCreate(BaseModel):
    ph: float = Field(..., ge=0, le=14)
    nitrogen_mg_kg: float = Field(..., ge=0)
    organic_carbon_g_kg: float | None = Field(None, ge=0)
    sand_pct: float | None = Field(None, ge=0, le=100)
    clay_pct: float | None = Field(None, ge=0, le=100)
    sample_date: str | None = None
    lab_name: str | None = None


class SoilTestResponse(BaseModel):
    id: int
    farm_id: int
    user_id: int
    ph: float
    nitrogen_mg_kg: float
    organic_carbon_g_kg: float | None
    sand_pct: float | None
    clay_pct: float | None
    sample_date: str | None
    lab_name: str | None
    created_at: str


@router.post("/{farm_id}/soil-tests", response_model=SoilTestResponse)
def create_soil_test(
    farm_id: int,
    req: SoilTestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    farm = db.query(Farm).filter((Farm.id == farm_id) & (Farm.user_id == current_user.id)).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or unauthorized")

    record = SoilTest(
        farm_id=farm.id,
        user_id=current_user.id,
        ph=req.ph,
        nitrogen_mg_kg=req.nitrogen_mg_kg,
        organic_carbon_g_kg=req.organic_carbon_g_kg,
        sand_pct=req.sand_pct,
        clay_pct=req.clay_pct,
        sample_date=req.sample_date,
        lab_name=req.lab_name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return SoilTestResponse(
        id=record.id,
        farm_id=record.farm_id,
        user_id=record.user_id,
        ph=record.ph,
        nitrogen_mg_kg=record.nitrogen_mg_kg,
        organic_carbon_g_kg=record.organic_carbon_g_kg,
        sand_pct=record.sand_pct,
        clay_pct=record.clay_pct,
        sample_date=record.sample_date,
        lab_name=record.lab_name,
        created_at=record.created_at.isoformat() if record.created_at else "",
    )
