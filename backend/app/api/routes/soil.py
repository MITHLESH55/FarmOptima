from fastapi import APIRouter
from app.schemas import SoilOut
from app.services.soil_service import get_soil_for_location

router = APIRouter(prefix="/soil", tags=["soil"])


@router.get("", response_model=SoilOut)
def get_soil(lat: float, lon: float):
    result = get_soil_for_location(lat, lon)
    return SoilOut(
        ph=result.ph, clay_pct=result.clay_pct, sand_pct=result.sand_pct,
        soil_moisture_pct=result.soil_moisture_pct, source=result.source,
    )
