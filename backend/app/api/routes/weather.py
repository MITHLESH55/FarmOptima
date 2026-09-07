from fastapi import APIRouter, Depends
from app.schemas import WeatherOut
from app.services.weather_service import get_weather_for_location

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("", response_model=WeatherOut)
def get_weather(lat: float, lon: float):
    result = get_weather_for_location(lat, lon)
    return WeatherOut(
        rainfall_mm_last_30d=result.rainfall_mm_last_30d,
        avg_temp_c=result.avg_temp_c,
        humidity_pct=result.humidity_pct,
        source=result.source,
    )
