"""
The main /recommend endpoint. This is the orchestration layer only — every
real computation lives in services/ (data retrieval) or core/ (algorithms).
Every run is persisted to the database (see models.Recommendation), which
is what lets you later query "show me every run and what it recommended"
as evidence for your report's validation chapter.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import LocationRequest, RecommendationResponse, DataProvenance, CropScore, ResourcePlan, ParetoPoint, DataCompleteness
from app.services.satellite_service import get_ndvi_for_location, get_satellite_map_url
from app.services.weather_service import get_weather_for_location
from app.services.soil_service import get_soil_for_location
from app.services.market_service import load_market_prices
from app.services.explanation_service import build_explanation
from app.core.criteria import build_decision_matrix, DEFAULT_AHP_PAIRWISE_MATRIX, CRITERIA_NAMES
from app.core.mcdm import ahp_weights, topsis, electre_i
from app.core.fuzzy_ahp import crisp_to_default_fuzzy, select_ahp_weights
from app.core.nsga2 import optimize_resources_multiobjective
from app.crop_database import CROP_DATABASE
from app.config import settings
from app.models import Recommendation, User, Farm
from app.utils.exceptions import InvalidLocationError
from app.api.deps import get_current_user
from app.utils.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommend", tags=["recommend"])

_market_prices_cache = load_market_prices()

SEASON_WEEKS = 16
ACRE_TO_LITERS_PER_MM = 4046.86


@router.post("", response_model=RecommendationResponse)
@limiter.limit(settings.recommend_rate_limit)
def recommend(
    request: Request, req: LocationRequest,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if req.lat == 0 and req.lon == 0:
        raise InvalidLocationError("Please select a real location on the map.")

    # 1-3: Data collection (each with real integration + honest fallback)
    sat = get_ndvi_for_location(req.lat, req.lon)
    weather = get_weather_for_location(req.lat, req.lon)
    soil = get_soil_for_location(req.lat, req.lon)

    # Calculate data completeness status
    completeness = DataCompleteness(
        weather="live" if weather.source != "unavailable" else "unavailable",
        soil="live" if soil.source != "unavailable" else "unavailable",
        satellite="live" if sat.source != "unavailable" else "unavailable",
        market="csv" if _market_prices_cache else "fallback-index",
    )

    missing_sources = []
    if completeness.soil == "unavailable":
        missing_sources.append("soil (SoilGrids)")
    if completeness.weather == "unavailable":
        missing_sources.append("weather (NASA POWER/Open-Meteo)")
    if completeness.satellite == "unavailable":
        missing_sources.append("vegetation (Sentinel-2 NDVI)")

    if len(missing_sources) == 3:
        recommendation_status = "unavailable"
        partial_data_reason = "All required environmental data sources are currently unreachable. Cannot compute valid MCDM ranking."
    elif len(missing_sources) > 0:
        recommendation_status = "partial"
        partial_data_reason = f"Data source(s) {', '.join(missing_sources)} unavailable — recommendation calculated using baseline suitability profiles."
    else:
        recommendation_status = "complete"
        partial_data_reason = None

    # 4: Build the real decision matrix from measured conditions
    crop_names, decision_matrix, is_benefit = build_decision_matrix(
        ndvi=sat.ndvi,
        soil_ph=soil.ph,
        rainfall_mm_30d=weather.rainfall_mm_last_30d,
        avg_temp_c=weather.avg_temp_c,
        humidity_pct=weather.humidity_pct,
        soil_nitrogen_mg_kg=soil.nitrogen_total_mg_kg,
        soil_organic_carbon_g_kg=soil.organic_carbon_g_kg,
        soil_moisture_pct=soil.soil_moisture_pct,
        market_prices=_market_prices_cache,
        soil_source=soil.source,
        weather_source=weather.source,
        satellite_source=sat.source,
    )

    # 5: Fuzzy AHP criteria weighting — handles genuine expert uncertainty via
    # triangular fuzzy numbers (Chang's extent analysis) instead of forcing a
    # single crisp Saaty-scale value. We still compute the crisp Consistency
    # Ratio on the underlying judgment matrix as a diagnostic (a standard,
    # well-understood check), even though the weights actually used come
    # from the fuzzy extension.
    crisp_diagnostic = ahp_weights(DEFAULT_AHP_PAIRWISE_MATRIX)
    fuzzy_matrix = crisp_to_default_fuzzy(DEFAULT_AHP_PAIRWISE_MATRIX)
    weights, used_fuzzy_weights = select_ahp_weights(DEFAULT_AHP_PAIRWISE_MATRIX, fuzzy_matrix)
    weights_dict = {name: float(w) for name, w in zip(CRITERIA_NAMES, weights)}
    if not crisp_diagnostic.is_consistent:
        logger.warning("Underlying crisp AHP matrix CR %.3f exceeds 0.10 — reconsider the matrix.",
                        crisp_diagnostic.consistency_ratio)
    if not used_fuzzy_weights:
        logger.warning("Fuzzy AHP produced a degenerate zero-weight solution; falling back to crisp AHP weights.")

    # 6: TOPSIS ranking + ELECTRE cross-check, using the decisive AHP weights
    topsis_ranked = topsis(decision_matrix, weights, is_benefit)
    electre_result = electre_i(decision_matrix, weights, is_benefit)

    crop_ranking = []
    if recommendation_status != "unavailable":
        for rank, entry in enumerate(topsis_ranked, start=1):
            idx = entry["index"]
            crop_ranking.append(CropScore(
                crop=crop_names[idx], topsis_closeness=round(entry["closeness"], 4),
                electre_net_outranking=electre_result["net_outranking_count"][idx], rank=rank,
            ))

    top_crop_name = crop_ranking[0].crop if crop_ranking else "Wheat"
    top_crop_params = CROP_DATABASE.get(top_crop_name, CROP_DATABASE["Wheat"])
    top_crop_reference_ranges = {
        "temperature_c": {"min": float(top_crop_params["ideal_temp_min_c"]), "max": float(top_crop_params["ideal_temp_max_c"])},
        "rainfall_mm_last_30d": {"min": float(top_crop_params["ideal_rainfall_min_mm_30d"]), "max": float(top_crop_params["ideal_rainfall_max_mm_30d"])},
        "soil_ph": {"min": float(top_crop_params["ideal_ph_min"]), "max": float(top_crop_params["ideal_ph_max"])},
    }

    # 7: NSGA-II multi-objective resource optimization — trades off water gap,
    # fertilizer gap, and resource cost simultaneously (a real Pareto front),
    # rather than a single scalarized fitness. Bounds scaled to the crop's own need.
    naive_weekly_water = top_crop_params["water_need_mm_season"] * ACRE_TO_LITERS_PER_MM / SEASON_WEEKS
    water_bounds = (naive_weekly_water * 0.2, naive_weekly_water * 2.0)
    fert_bounds = (
        top_crop_params["fertilizer_n_kg_per_acre"] * 0.3,
        top_crop_params["fertilizer_n_kg_per_acre"] * 2.0,
    )
    nsga2_result = optimize_resources_multiobjective(
        crop_water_need_mm=top_crop_params["water_need_mm_season"],
        crop_fert_need_kg_acre=top_crop_params["fertilizer_n_kg_per_acre"],
        rainfall_mm_30d=weather.rainfall_mm_last_30d, soil_moisture_pct=soil.soil_moisture_pct,
        season_weeks=SEASON_WEEKS, population_size=settings.gpo_population_size,
        generations=settings.gpo_generations, water_bounds=water_bounds, fert_bounds=fert_bounds,
        seed=hash((round(req.lat, 3), round(req.lon, 3))) % (2**31),
    )
    compromise = nsga2_result.compromise_solution
    resource_plan = ResourcePlan(
        water_liters_per_week=compromise.water_liters_per_week,
        fertilizer_kg_per_acre=compromise.fertilizer_kg_per_acre,
        optimizer_best_fitness=round(
            (compromise.water_gap ** 2 + compromise.fertilizer_gap ** 2) ** 0.5, 5
        ),
        optimizer_generations_run=nsga2_result.generations_run,
        irrigation_schedule=f"~{compromise.water_liters_per_week / 7:.0f} L/day, split across 2-3 waterings/week",
        pareto_front=[
            ParetoPoint(
                water_liters_per_week=s.water_liters_per_week, fertilizer_kg_per_acre=s.fertilizer_kg_per_acre,
                water_gap=s.water_gap, fertilizer_gap=s.fertilizer_gap, resource_cost=s.resource_cost,
            )
            for s in nsga2_result.pareto_front
        ],
        optimizer_method="nsga2-multiobjective",
    )

    explanation = build_explanation(top_crop_name, crop_ranking[0] if crop_ranking else CropScore(crop=top_crop_name, topsis_closeness=0.0, electre_net_outranking=0, rank=1), resource_plan, weights_dict)

    response = RecommendationResponse(
        location=req, generated_at=datetime.now(timezone.utc).isoformat(),
        provenance=DataProvenance(
            satellite_source=sat.source, weather_source=weather.source, soil_source=soil.source,
            market_source="csv" if _market_prices_cache else "fallback-index",
        ),
        data_completeness=completeness,
        recommendation_status=recommendation_status,
        partial_data_reason=partial_data_reason,
        ndvi=sat.ndvi, satellite_scene_date=sat.scene_date,
        satellite_tile_url=get_satellite_map_url(req.lat, req.lon),
        rainfall_mm_last_30d=weather.rainfall_mm_last_30d, avg_temp_c=weather.avg_temp_c,
        humidity_pct=weather.humidity_pct,
        solar_radiation_mj_m2=weather.solar_radiation_mj_m2, wind_speed_m_s=weather.wind_speed_m_s,
        soil_ph=soil.ph, soil_moisture_pct=soil.soil_moisture_pct,
        soil_nitrogen_mg_kg=soil.nitrogen_total_mg_kg, soil_organic_carbon_g_kg=soil.organic_carbon_g_kg,
        soil_sand_pct=soil.sand_pct, soil_clay_pct=soil.clay_pct,
        ahp_weights=weights_dict, ahp_consistency_ratio=round(crisp_diagnostic.consistency_ratio, 4),
        ahp_is_consistent=crisp_diagnostic.is_consistent, ahp_method="fuzzy-ahp-chang-extent-analysis",
        top_crop_reference_ranges=top_crop_reference_ranges,
        crop_ranking=crop_ranking, resource_plan=resource_plan, ai_explanation=explanation,
    )

    # Persist every run — this is your audit trail for Chapter 7 validation.
    # First, create or find the farm record for this location
    farm = db.query(Farm).filter(
        (Farm.latitude == req.lat) & (Farm.longitude == req.lon)
    ).first()
    
    if not farm:
        # Create a new farm record for this location
        farm = Farm(
            name=f"Farm at {req.lat:.4f}, {req.lon:.4f}",
            latitude=req.lat,
            longitude=req.lon,
        )
        db.add(farm)
        db.commit()
        db.refresh(farm)
    
    # Now create the recommendation linked to the farm
    record = Recommendation(
        farm_id=farm.id,
        latitude=req.lat, longitude=req.lon,
        ndvi=sat.ndvi, 
        soil_ph=soil.ph, soil_moisture_pct=soil.soil_moisture_pct,
        soil_nitrogen_mg_kg=soil.nitrogen_total_mg_kg, 
        soil_organic_carbon_g_kg=soil.organic_carbon_g_kg,
        soil_sand_pct=soil.sand_pct, soil_clay_pct=soil.clay_pct,
        rainfall_mm_last_30d=weather.rainfall_mm_last_30d, avg_temp_c=weather.avg_temp_c,
        humidity_pct=weather.humidity_pct,
        solar_radiation_mj_m2=weather.solar_radiation_mj_m2,
        wind_speed_m_s=weather.wind_speed_m_s,
        satellite_source=sat.source, weather_source=weather.source,
        soil_source=soil.source, market_source=response.provenance.market_source,
        top_crop=top_crop_name, ahp_consistency_ratio=response.ahp_consistency_ratio,
        full_result=response.model_dump(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    response.id = record.id

    return response
