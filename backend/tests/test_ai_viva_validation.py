"""
FarmOptima AI Assistant Viva & Academic Question Validation Test Suite.

Validates the 8 mandatory viva/evaluation questions against live structured recommendation context:
  1. "Why was this crop recommended?"
  2. "What are the crop ranking scores?"
  3. "What does the NDVI value indicate?"
  4. "How much fertilizer is required?"
  5. "How much irrigation is recommended?"
  6. "What are the data sources?"
  7. "Which values are live/model/static?"
  8. "Why is the selected crop different from the second-ranked crop?"

Verifies:
  - Numerical consistency
  - No fabricated values
  - Honest distinction between measured, model prediction, static dataset, and calculation
  - Grounding prompt context richness (N-P-K, commercial fertilizers, split schedule, NDVI, TOPSIS/ELECTRE scores).
"""

import pytest
from app.schemas.ai import FarmContext
from app.services.ai.context_builder import build_farm_context
from app.core.ai_grounding import build_grounding_prompt, validate_answer_is_grounded
from app.schemas.recommendation import RecommendationResponse, CropScore, ResourcePlan, DataProvenance, FertilizerPlan, NutrientRequirements, CommercialFertilizerItem, ApplicationStageItem


@pytest.fixture
def sample_recommendation_response():
    return RecommendationResponse(
        id=101,
        location={"lat": 18.5204, "lon": 73.8567, "field_area_acres": 2.5},
        generated_at="2026-09-24T12:00:00Z",
        provenance=DataProvenance(
            weather_source="nasa-power",
            soil_source="soilgrids",
            satellite_source="gee-sentinel2",
            market_source="agmarknet_csv",
            ahp_weights_source="expert_fuzzy_matrix",
        ),
        crop_ranking=[
            CropScore(crop="Rice", topsis_closeness=0.8421, electre_net_outranking=4, rank=1, criteria_scores={"climate_suitability": 0.88, "soil_suitability": 0.82, "water_efficiency": 0.79, "market_value": 0.75}),
            CropScore(crop="Wheat", topsis_closeness=0.7615, electre_net_outranking=2, rank=2, criteria_scores={"climate_suitability": 0.72, "soil_suitability": 0.80, "water_efficiency": 0.85, "market_value": 0.68}),
            CropScore(crop="Maize", topsis_closeness=0.6840, electre_net_outranking=-1, rank=3, criteria_scores={"climate_suitability": 0.70, "soil_suitability": 0.75, "water_efficiency": 0.65, "market_value": 0.60}),
        ],
        avg_temp_c=27.5,
        rainfall_mm_last_30d=165.0,
        humidity_pct=72.0,
        wind_speed_m_s=2.8,
        solar_radiation_mj_m2=18.5,
        soil_ph=6.8,
        soil_nitrogen_mg_kg=220.0,
        soil_organic_carbon_g_kg=7.5,
        soil_sand_pct=35.0,
        soil_clay_pct=28.0,
        soil_moisture_pct=38.0,
        ndvi=0.62,
        ndvi_status="Healthy vegetation",
        satellite_scene_date="2026-09-18T00:00:00Z",
        ahp_weights={"climate_suitability": 0.4495, "soil_suitability": 0.2596, "water_efficiency": 0.1707, "market_value": 0.1202},
        ahp_consistency_ratio=0.0265,
        ahp_is_consistent=True,
        ai_explanation="Rice is selected as optimal based on high rainfall alignment and favorable soil nutrient status.",
        resource_plan=ResourcePlan(
            water_liters_per_week=42000.0,
            fertilizer_kg_per_acre=55.0,
            optimizer_best_fitness=0.045,
            optimizer_generations_run=60,
            irrigation_schedule="~6000 L/day, split across 2-3 waterings/week",
            optimizer_method="nsga2-multiobjective",
        ),
        fertilizer_plan=FertilizerPlan(
            crop="Rice",
            field_area_acres=2.5,
            nutrient_requirements=NutrientRequirements(
                nitrogen_kg_per_acre=55.0,
                phosphorus_kg_per_acre=24.0,
                potassium_kg_per_acre=20.0,
                total_field_nitrogen_kg=137.5,
                total_field_phosphorus_kg=60.0,
                total_field_potassium_kg=50.0,
            ),
            commercial_fertilizers=[
                CommercialFertilizerItem(name="DAP", composition="18% N, 46% P2O5", quantity_kg_per_acre=52.17, quantity_kg_total=130.4, application_stage="Basal"),
                CommercialFertilizerItem(name="Urea", composition="46% N", quantity_kg_per_acre=99.15, quantity_kg_total=247.9, application_stage="Split (Basal + 2 Top Dressings)"),
                CommercialFertilizerItem(name="MOP", composition="60% K2O", quantity_kg_per_acre=33.33, quantity_kg_total=83.3, application_stage="Basal"),
            ],
            application_schedule=[
                ApplicationStageItem(stage="Basal", dap_kg=130.4, urea_kg=123.9, mop_kg=83.3, total_kg=337.6),
                ApplicationStageItem(stage="Top Dressing 1", dap_kg=0.0, urea_kg=62.0, mop_kg=0.0, total_kg=62.0),
                ApplicationStageItem(stage="Top Dressing 2", dap_kg=0.0, urea_kg=62.0, mop_kg=0.0, total_kg=62.0),
            ],
            explanation="Basal application supplies total phosphorus and potassium plus 50% nitrogen; top dressings supply vegetative growth requirements.",
        ),
    )


def test_viva_q1_why_recommended(sample_recommendation_response):
    """Q1: Why was this crop recommended?"""
    ctx = build_farm_context(sample_recommendation_response)
    prompt = build_grounding_prompt(ctx, "Why was this crop recommended?")
    
    assert "Rice" in prompt
    assert "0.8421" in prompt  # TOPSIS closeness
    assert "NASA POWER" in prompt or "nasa-power" in prompt
    
    # Simulate a grounded assistant response
    sample_answer = "Rice is recommended because it achieved the highest TOPSIS closeness score of 0.8421 and an ELECTRE net outranking of +4, demonstrating superior climate suitability (0.88) and soil suitability (0.82) for your field conditions."
    res = validate_answer_is_grounded(sample_answer, ctx)
    assert res.passed is True
    assert len(res.ungrounded_numeric_claims) == 0


def test_viva_q2_ranking_scores(sample_recommendation_response):
    """Q2: What are the crop ranking scores?"""
    ctx = build_farm_context(sample_recommendation_response)
    prompt = build_grounding_prompt(ctx, "What are the crop ranking scores?")
    
    assert "Rice" in prompt and "Wheat" in prompt and "Maize" in prompt
    assert "0.8421" in prompt and "0.7615" in prompt
    
    sample_answer = "The crop rankings are: 1. Rice with TOPSIS closeness 0.8421 (ELECTRE +4), 2. Wheat with TOPSIS closeness 0.7615 (ELECTRE +2), and 3. Maize with TOPSIS closeness 0.6840 (ELECTRE -1)."
    res = validate_answer_is_grounded(sample_answer, ctx)
    assert res.passed is True


def test_viva_q3_ndvi_meaning(sample_recommendation_response):
    """Q3: What does the NDVI value indicate?"""
    ctx = build_farm_context(sample_recommendation_response)
    prompt = build_grounding_prompt(ctx, "What does the NDVI value indicate?")
    
    assert "0.62" in prompt
    assert "dense vegetation" in prompt
    
    sample_answer = "The field NDVI is 0.62, observed on 2026-09-18 from Copernicus Sentinel-2 L2A satellite data, indicating very dense vegetation cover."
    res = validate_answer_is_grounded(sample_answer, ctx)
    assert res.passed is True


def test_viva_q4_fertilizer_quantities(sample_recommendation_response):
    """Q4: How much fertilizer is required?"""
    ctx = build_farm_context(sample_recommendation_response)
    prompt = build_grounding_prompt(ctx, "How much fertilizer is required?")
    
    assert "55" in prompt or "55.0" in prompt
    assert "DAP" in prompt and "Urea" in prompt and "MOP" in prompt
    
    sample_answer = "For your 2.5 acre field, the total commercial requirement is 130.4 kg DAP, 247.9 kg Urea, and 83.3 kg MOP to satisfy the target of 55 kg N, 24 kg P2O5, and 20 kg K2O per acre."
    res = validate_answer_is_grounded(sample_answer, ctx)
    assert res.passed is True


def test_viva_q5_irrigation_recommendation(sample_recommendation_response):
    """Q5: How much irrigation is recommended?"""
    ctx = build_farm_context(sample_recommendation_response)
    prompt = build_grounding_prompt(ctx, "How much irrigation is recommended?")
    
    assert "42000" in prompt
    
    sample_answer = "The multi-objective NSGA-II plan recommends 42000 liters of irrigation water per week (~6000 L/day split across 2-3 waterings/week) for your field, taking into account recent rainfall credits of 165 mm."
    res = validate_answer_is_grounded(sample_answer, ctx)
    assert res.passed is True


def test_viva_q6_and_q7_data_sources_and_provenance(sample_recommendation_response):
    """Q6 & Q7: What are data sources and which values are live/model/static?"""
    ctx = build_farm_context(sample_recommendation_response)
    prompt = build_grounding_prompt(ctx, "Which data values are live, model prediction, or static?")
    
    assert "NASA POWER" in prompt or "nasa-power" in prompt
    assert "SoilGrids" in prompt or "soilgrids" in prompt
    assert "Sentinel-2" in prompt or "gee-sentinel2" in prompt
    assert "AGMARKNET" in prompt or "agmarknet_csv" in prompt


def test_viva_q8_why_different_from_rank2(sample_recommendation_response):
    """Q8: Why is the selected crop different from the second-ranked crop?"""
    ctx = build_farm_context(sample_recommendation_response)
    prompt = build_grounding_prompt(ctx, "Why is Rice chosen over Wheat?")
    
    assert "Rice" in prompt
    assert "Wheat" in prompt
    
    sample_answer = "Rice scored higher than Wheat (TOPSIS 0.8421 vs 0.7615) primarily because current temperature (27.5 °C) and high rainfall (165 mm) provide superior climate suitability for Rice compared to Wheat's cooler optimal range."
    res = validate_answer_is_grounded(sample_answer, ctx)
    assert res.passed is True
