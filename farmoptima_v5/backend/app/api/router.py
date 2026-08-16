from fastapi import APIRouter

from app.api.routes import weather, soil, satellite, recommend, farms, auth, ai

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(weather.router)
api_router.include_router(soil.router)
api_router.include_router(satellite.router)
api_router.include_router(recommend.router)
api_router.include_router(recommend.insight_router)
api_router.include_router(farms.router)
api_router.include_router(ai.router)
