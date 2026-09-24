"""
AI assistant schemas.

These are the data-transfer objects for the AI service layer introduced in
Phase 2 Step 2.1.  They are deliberately separate from the existing
recommendation schemas — the AI layer depends on them, never the reverse.

FarmContext  — the grounding context fed to the LLM.  Every field that
               validate_answer_is_grounded() needs to check against is
               explicit here.  If a value was unavailable at recommendation
               time it MUST be None here, never back-filled.

AIQuestionRequest   — the incoming question (language field accepted for
                      forward-compat with step 2.5; unused this step).

AIAnswerResponse    — the answer plus audit fields.

GroundingCheckResult — internal result of the deterministic grounding check;
                       returned by core/ai_grounding.py, not exposed via HTTP.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.environmental_interpretation import interpret_ndvi
from app.schemas.insight import FarmInsightBundle


# ---------------------------------------------------------------------------
# Context object
# ---------------------------------------------------------------------------

class NDVIContext(BaseModel):
    """Structured NDVI block used for deterministic grounding and auditability."""
    value: float
    source: str
    scene_date: str | None = None
    status: str
    is_live: bool

    def __float__(self) -> float:
        return float(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"NDVIContext(value={self.value}, source={self.source!r}, status={self.status!r})"

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return abs(float(self.value) - float(other)) < 1e-9
        return super().__eq__(other)


class CropRankEntry(BaseModel):
    """One row from crop_ranking in RecommendationResponse."""
    crop: str
    topsis_closeness: float
    electre_net_outranking: int
    rank: int
    tie_break_applied: bool = False
    tie_break_reason: str | None = None
    criteria_scores: dict[str, float] = Field(default_factory=dict)


class ParetoPointSummary(BaseModel):
    """Lightweight pareto-front entry kept in context for grounding checks."""
    water_liters_per_week: float
    fertilizer_kg_per_acre: float
    resource_cost: float


class ResourcePlanContext(BaseModel):
    water_liters_per_week: float
    fertilizer_kg_per_acre: float
    optimizer_best_fitness: float
    optimizer_generations_run: int
    irrigation_schedule: str
    optimizer_method: str
    pareto_front: list[ParetoPointSummary] = []
    convergence_history: list[float] = Field(default_factory=list)


class FarmContext(BaseModel):
    """
    A fully explicit, grounding-safe snapshot of one FarmOptima recommendation
    run.  Used by the AI service layer only — never stored as a DB column
    directly (the underlying RecommendationResponse JSON covers that).

    Unavailability conventions:
    - ndvi: None when satellite source is "unavailable" / "mock".
    - All other numeric fields carry their live value; the caller must
      set data_completeness / recommendation_status to expose missing data.
    """

    # --- Provenance ---
    recommendation_id: int | None = None  # DB id if persisted
    generated_at: str
    recommendation_status: str  # "complete" | "partial" | "unavailable"
    data_completeness_weather: str
    data_completeness_soil: str
    data_completeness_satellite: str
    data_completeness_market: str
    satellite_source: str
    weather_source: str
    soil_source: str
    market_source: str

    # --- Location ---
    latitude: float
    longitude: float

    # --- Satellite / NDVI ---
    ndvi: NDVIContext | float | None = None  # canonical structured block; float is accepted for compatibility
    ndvi_available: bool = False             # legacy compatibility; mirrors whether a live NDVI is present
    satellite_scene_date: str | None = None

    @field_validator("ndvi", mode="before")
    @classmethod
    def coerce_ndvi(cls, value, info):
        if value is None or isinstance(value, NDVIContext):
            return value
        if isinstance(value, (int, float)):
            source = info.data.get("satellite_source", "unknown")
            source_name = str(source).strip() or "unknown"
            scene_date = info.data.get("satellite_scene_date")
            is_live = info.data.get("ndvi_available", source_name.lower() != "mock")
            return NDVIContext(
                value=float(value),
                source=source_name,
                scene_date=scene_date,
                status=interpret_ndvi(float(value)),
                is_live=bool(is_live),
            )
        return value

    @model_validator(mode="after")
    def sync_ndvi_availability(self):
        self.ndvi_available = self.ndvi is not None and self.ndvi.is_live if isinstance(self.ndvi, NDVIContext) else bool(self.ndvi_available)
        return self

    # --- Weather ---
    rainfall_mm_last_30d: float
    avg_temp_c: float
    humidity_pct: float
    solar_radiation_mj_m2: float
    wind_speed_m_s: float

    # --- Soil ---
    soil_ph: float
    soil_moisture_pct: float
    soil_nitrogen_mg_kg: float
    soil_organic_carbon_g_kg: float
    soil_sand_pct: float
    soil_clay_pct: float

    # --- AHP ---
    ahp_weights: dict[str, float]
    ahp_consistency_ratio: float
    ahp_is_consistent: bool
    ahp_method: str

    # --- Crop ranking ---
    crop_ranking: list[CropRankEntry]       # ordered rank 1..N
    crop_names_in_ranking: list[str]        # pre-extracted for fast lookup

    # --- Resource plan ---
    resource_plan: ResourcePlanContext

    # --- Structured Fertilizer Plan & Top Crop Reference Ranges ---
    fertilizer_plan: dict | None = None
    top_crop_reference_ranges: dict[str, dict[str, float]] | None = None

    # --- Existing template explanation (pass-through) ---
    ai_explanation: str

    # --- Optional structured insight bundle, produced by deterministic rules ---
    insight_bundle: FarmInsightBundle | None = None


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class AIQuestionRequest(BaseModel):
    """
    A farmer's natural-language question about a previous recommendation run.

    language is accepted for multilingual conversational support while the
    reasoning layer remains the same. Unsupported values are normalized to
    English and never crash the request.
    """
    question: str = Field(..., min_length=1, max_length=2000)
    language: Literal["en", "hi", "mr"] = "en"

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, value):
        if value is None:
            return "en"
        normalized = str(value).strip().lower()
        if normalized in {"en", "hi", "mr"}:
            return normalized
        return "en"


class AIAnswerResponse(BaseModel):
    """
    The grounded answer produced by the AI assistant.

    grounded_fields_used — names of the FarmContext fields the answer drew
    from (populated by validate_answer_is_grounded as a best-effort audit
    trail; empty list means the check could not determine field usage).

    context_snapshot_id — the recommendation_id the context was built from,
    for cross-referencing with the recommendations table.
    """
    answer: str
    grounded_fields_used: list[str] = []
    context_snapshot_id: int | None = None


class VoiceAnswerResponse(BaseModel):
    """
    The response produced by the Voice AI assistant (Phase 2.4).

    transcript — the exact text transcribed from the farmer's audio.
    answer — the grounded answer produced by the AI pipeline.
    grounded_fields_used — context fields referenced.
    context_snapshot_id — recommendation_id.
    audio_base64 — optional base64-encoded synthesized speech audio (MP3).
                   None if TTS is unconfigured or failed.
    """
    transcript: str
    answer: str
    grounded_fields_used: list[str] = []
    context_snapshot_id: int | None = None
    audio_base64: str | None = None


# ---------------------------------------------------------------------------
# Internal grounding check result (not exposed via HTTP)
# ---------------------------------------------------------------------------

class GroundingCheckResult(BaseModel):
    """
    Returned by validate_answer_is_grounded().  Used internally by
    assistant_service.answer_farm_question() to decide whether to accept,
    retry, or replace the model's answer.
    """
    passed: bool
    ungrounded_crop_claims: list[str] = []   # crop names in answer not in context
    ungrounded_numeric_claims: list[str] = [] # numbers in answer not matchable to context
    grounded_fields_used: list[str] = []      # context field names referenced
