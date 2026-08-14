from fastapi import APIRouter
from app.schemas import SatelliteOut
from app.services.satellite_service import get_ndvi_for_location

router = APIRouter(prefix="/satellite", tags=["satellite"])


@router.get("", response_model=SatelliteOut)
def get_satellite(lat: float, lon: float):
    result = get_ndvi_for_location(lat, lon)
    return SatelliteOut(ndvi=result.ndvi, source=result.source, scene_date=result.scene_date)
