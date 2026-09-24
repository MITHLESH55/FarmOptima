from pydantic import BaseModel, Field, model_validator
from app.schemas.common import LocationRequest, DataProvenance


class CropScore(BaseModel):
    crop: str
    topsis_closeness: float
    electre_net_outranking: int
    rank: int
    tie_break_applied: bool = False
    tie_break_reason: str | None = None
    criteria_scores: dict[str, float] = Field(default_factory=dict)


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
    convergence_history: list[float] = Field(default_factory=list)
    optimizer_method: str = "nsga2-multiobjective"


class DataCompleteness(BaseModel):
    weather: str  # "live" or "unavailable"
    soil: str     # "live" or "unavailable"
    satellite: str # "live" or "unavailable"
    market: str   # "csv" or "fallback-index"


class NutrientRequirements(BaseModel):
    nitrogen_kg_per_acre: float
    phosphorus_kg_per_acre: float
    potassium_kg_per_acre: float
    total_field_nitrogen_kg: float
    total_field_phosphorus_kg: float
    total_field_potassium_kg: float


class CommercialFertilizerItem(BaseModel):
    name: str
    composition: str
    quantity_kg_per_acre: float
    quantity_kg_total: float
    application_stage: str


class ApplicationStageItem(BaseModel):
    stage: str
    dap_kg: float
    urea_kg: float
    mop_kg: float
    total_kg: float


class FertilizerPlan(BaseModel):
    crop: str
    field_area_acres: float
    nutrient_requirements: NutrientRequirements
    commercial_fertilizers: list[CommercialFertilizerItem]
    application_schedule: list[ApplicationStageItem]
    explanation: str


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

    ndvi: float | None = None
    ndvi_status: str | None = None
    satellite_scene_date: str | None  # Scene acquisition date from Sentinel-2
    satellite_tile_url: str | None = None  # Tile URL for satellite visualization

    def model_copy(self, *, update=None, deep=False, **kwargs):
        """Keep NDVI status synchronized when a recommendation snapshot is copied."""
        data = self.model_dump(mode="python")
        if update:
            data.update(update)

        from app.core.environmental_interpretation import interpret_ndvi
        ndvi_val = data.get("ndvi")
        data["ndvi_status"] = interpret_ndvi(float(ndvi_val) if ndvi_val is not None else None)

        return self.__class__.model_validate(data)

    @model_validator(mode="before")
    @classmethod
    def _backfill_legacy_ndvi_status(cls, values):
        if isinstance(values, dict):
            from app.core.environmental_interpretation import interpret_ndvi
            ndvi_val = values.get("ndvi")
            expected_status = interpret_ndvi(float(ndvi_val) if ndvi_val is not None else None)
            values["ndvi_status"] = expected_status
        return values
    
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
    fertilizer_plan: FertilizerPlan | None = None
    ai_explanation: str

