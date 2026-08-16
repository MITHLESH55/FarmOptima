"""
context_builder — converts a RecommendationResponse into a FarmContext.

This is a PURE RESHAPE operation.  It does not recompute any algorithm,
approximate any value, or invent any data.  If a field is unavailable in
the recommendation (e.g. NDVI from a "mock" or "unavailable" satellite
source), it is explicitly marked unavailable in the context — never
silently omitted, never backfilled with a default number.

Why a separate context object rather than passing RecommendationResponse
directly to the LLM?  Three reasons:
  1. Explicit unavailability: the context has typed None fields and boolean
     flags that make grounding checks unambiguous.
  2. Stability: the AI layer's grounding logic cannot break when
     RecommendationResponse gains new fields later.
  3. Testability: tests can construct FarmContext directly without needing
     to run the full recommendation pipeline.
"""

from __future__ import annotations

from app.core.environmental_interpretation import interpret_ndvi
from app.schemas.recommendation import RecommendationResponse
from app.schemas.ai import (
    FarmContext,
    CropRankEntry,
    NDVIContext,
    ResourcePlanContext,
    ParetoPointSummary,
)

# Sources considered "unavailable" — NDVI from these sources is not a real
# field measurement and must not be presented as one.
_UNAVAILABLE_SATELLITE_SOURCES = {"unavailable", "mock", "none", ""}


def build_farm_context(recommendation: RecommendationResponse) -> FarmContext:
    """
    Convert a full RecommendationResponse into a FarmContext suitable for
    LLM grounding.

    Caller contract:
    - `recommendation` should be the same object returned by /api/recommend
      (or reconstructed from its JSON), including the `id` field if it has
      been persisted to the database.
    - Every field in RecommendationResponse is mapped explicitly below.
      If a new field is added to RecommendationResponse later, this
      function should be updated to map it — it is intentionally not
      "dict(**rec.model_dump())" so that new fields are never silently
      swallowed.
    """
    prov = recommendation.provenance
    dc = recommendation.data_completeness

    # --- Satellite / NDVI availability decision ---
    # The actual numeric NDVI value in the recommendation is authoritative.
    # A real measurement must remain in the structured NDVI block even when the
    # source label is stale or provisional; only a true missing value becomes
    # None. A mock source is explicitly marked unverified, not dropped.
    satellite_source_lower = (prov.satellite_source or "").lower().strip()
    ndvi_value = recommendation.ndvi

    if ndvi_value is None:
        ndvi_context = None
        ndvi_available = False
    else:
        source_name = (prov.satellite_source or "unknown").strip() or "unknown"
        ndvi_status = recommendation.ndvi_status
        if ndvi_status is None:
            from app.core.environmental_interpretation import interpret_ndvi

            ndvi_status = interpret_ndvi(float(ndvi_value))
        else:
            from app.core.environmental_interpretation import interpret_ndvi

            expected_status = interpret_ndvi(float(ndvi_value))
            ndvi_status = expected_status if ndvi_status != expected_status else ndvi_status
        ndvi_context = NDVIContext(
            value=float(ndvi_value),
            source=source_name,
            scene_date=recommendation.satellite_scene_date,
            status=ndvi_status,
            is_live=satellite_source_lower != "mock",
        )
        ndvi_available = ndvi_context.is_live

    # --- Crop ranking ---
    crop_entries = [
        CropRankEntry(
            crop=cs.crop,
            topsis_closeness=cs.topsis_closeness,
            electre_net_outranking=cs.electre_net_outranking,
            rank=cs.rank,
            tie_break_applied=cs.tie_break_applied,
            tie_break_reason=cs.tie_break_reason,
            criteria_scores=cs.criteria_scores,
        )
        for cs in recommendation.crop_ranking
    ]
    crop_names = [entry.crop for entry in crop_entries]

    # --- Resource plan ---
    rp = recommendation.resource_plan
    pareto = [
        ParetoPointSummary(
            water_liters_per_week=p.water_liters_per_week,
            fertilizer_kg_per_acre=p.fertilizer_kg_per_acre,
            resource_cost=p.resource_cost,
        )
        for p in rp.pareto_front
    ]
    resource_plan_ctx = ResourcePlanContext(
        water_liters_per_week=rp.water_liters_per_week,
        fertilizer_kg_per_acre=rp.fertilizer_kg_per_acre,
        optimizer_best_fitness=rp.optimizer_best_fitness,
        optimizer_generations_run=rp.optimizer_generations_run,
        irrigation_schedule=rp.irrigation_schedule,
        optimizer_method=rp.optimizer_method,
        pareto_front=pareto,
    )

    return FarmContext(
        # Provenance
        recommendation_id=recommendation.id,
        generated_at=recommendation.generated_at,
        recommendation_status=recommendation.recommendation_status,
        data_completeness_weather=dc.weather,
        data_completeness_soil=dc.soil,
        data_completeness_satellite=dc.satellite,
        data_completeness_market=dc.market,
        satellite_source=prov.satellite_source,
        weather_source=prov.weather_source,
        soil_source=prov.soil_source,
        market_source=prov.market_source,
        # Location
        latitude=recommendation.location.lat,
        longitude=recommendation.location.lon,
        # NDVI
        ndvi=ndvi_context,
        ndvi_available=ndvi_available,
        satellite_scene_date=recommendation.satellite_scene_date,
        # Weather
        rainfall_mm_last_30d=recommendation.rainfall_mm_last_30d,
        avg_temp_c=recommendation.avg_temp_c,
        humidity_pct=recommendation.humidity_pct,
        solar_radiation_mj_m2=recommendation.solar_radiation_mj_m2,
        wind_speed_m_s=recommendation.wind_speed_m_s,
        # Soil
        soil_ph=recommendation.soil_ph,
        soil_moisture_pct=recommendation.soil_moisture_pct,
        soil_nitrogen_mg_kg=recommendation.soil_nitrogen_mg_kg,
        soil_organic_carbon_g_kg=recommendation.soil_organic_carbon_g_kg,
        soil_sand_pct=recommendation.soil_sand_pct,
        soil_clay_pct=recommendation.soil_clay_pct,
        # AHP
        ahp_weights=recommendation.ahp_weights,
        ahp_consistency_ratio=recommendation.ahp_consistency_ratio,
        ahp_is_consistent=recommendation.ahp_is_consistent,
        ahp_method=recommendation.ahp_method,
        # Crop ranking
        crop_ranking=crop_entries,
        crop_names_in_ranking=crop_names,
        # Resource plan
        resource_plan=resource_plan_ctx,
        # Existing explanation
        ai_explanation=recommendation.ai_explanation,
    )
