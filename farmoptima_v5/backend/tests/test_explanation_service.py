from app.schemas import CropScore, ResourcePlan
from app.services.explanation_service import build_explanation


def test_build_explanation_uses_reference_based_reasoning():
    rank_row = CropScore(crop="Wheat", topsis_closeness=0.82, electre_net_outranking=5, rank=1)
    plan = ResourcePlan(
        water_liters_per_week=20000,
        fertilizer_kg_per_acre=45,
        optimizer_best_fitness=0.12,
        optimizer_generations_run=120,
        irrigation_schedule="2-3 waterings per week",
        pareto_front=[],
    )
    explanation = build_explanation(
        "Wheat",
        rank_row,
        plan,
        {"climate_suitability": 0.5, "soil_suitability": 0.3, "water_efficiency": 0.1, "market_value": 0.1},
    )

    assert "TOPSIS" in explanation
    assert "highest" in explanation.lower()
    assert "configured preferred range" in explanation.lower() or "reference range" in explanation.lower()
    assert "Why" in explanation or "because" in explanation.lower()
