from pydantic import BaseModel
from app.schemas.common import LocationRequest, DataProvenance


class CropScore(BaseModel):
    crop: str
    topsis_closeness: float
    electre_net_outranking: int
    rank: int


class ParetoPoint(BaseModel):
    water_liters_per_week: float
    fertilizer_kg_per_acre: float
    water_gap: float
    fertilizer_gap: float
    resource_cost: float


class ResourcePlan(BaseModel):
    water_liters_per_week: float
    fertilizer_kg_per_acre: float
    optimizer_best_fitness: float
    optimizer_generations_run: int
    irrigation_schedule: str
    pareto_front: list[ParetoPoint] = []
    optimizer_method: str = "nsga2-multiobjective"


class DataCompleteness(BaseModel):
    weather: str  # "live" or "unavailable"
    soil: str     # "live" or "unavailable"
    satellite: str # "live" or "unavailable"
    market: str   # "csv" or "fallback-index"


class RecommendationResponse(BaseModel):
    id: int | None = None  # DB row id, once persisted
    location: LocationRequest
    generated_at: str
    provenance: DataProvenance
    data_completeness: DataCompleteness = DataCompleteness(
        weather="live", soil="live", satellite="live", market="csv"
    )
    recommendation_status: str = "complete"  # "complete" | "partial" | "unavailable"
    partial_data_reason: str | None = None

    ndvi: float
    satellite_scene_date: str | None  # Scene acquisition date from Sentinel-2
    satellite_tile_url: str | None = None  # Tile URL for satellite visualization
    
    # Weather data
    rainfall_mm_last_30d: float
    avg_temp_c: float
    humidity_pct: float
    solar_radiation_mj_m2: float  # MJ/m² (megajoules per square meter)
    wind_speed_m_s: float  # m/s (meters per second)
    
    # Soil data
    soil_ph: float
    soil_moisture_pct: float
    soil_nitrogen_mg_kg: float  # Total nitrogen from SoilGrids nitrogen_total property
    soil_organic_carbon_g_kg: float  # Soil organic carbon from SoilGrids soc property
    soil_sand_pct: float  # Sand percentage (%)
    soil_clay_pct: float  # Clay percentage (%)

    ahp_weights: dict[str, float]
    ahp_consistency_ratio: float
    ahp_is_consistent: bool
    ahp_method: str = "fuzzy-ahp-chang-extent-analysis"

    top_crop_reference_ranges: dict[str, dict[str, float]] | None = None
    crop_ranking: list[CropScore]
    resource_plan: ResourcePlan
    ai_explanation: str

