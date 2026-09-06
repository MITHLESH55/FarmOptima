"""
Explanation service. Still template-based for now, but it is intentionally
reference-driven: it explains ranking relative to the evaluated crop set and
uses the configured agronomic ranges from the crop database as the baseline.
"""

from app.schemas import CropScore, ResourcePlan


def build_explanation(top_crop: str, rank_row: CropScore, plan: ResourcePlan, weights: dict) -> str:
    dominant_criterion = max(weights, key=weights.get)
    dominant_label = dominant_criterion.replace('_', ' ')
    return (
        f"Why {top_crop}? Among the currently evaluated crops, {top_crop} has the highest TOPSIS "
        f"closeness score ({rank_row.topsis_closeness:.3f}), so it is closest to the ideal multi-criteria "
        f"solution under this recommendation run. The strongest influence on the ranking is '{dominant_label}' "
        f"with an AHP weight of {weights[dominant_criterion]:.2f}, which is a relative importance measure, "
        f"not a direct suitability score. This ranking is compared against the configured crop-reference ranges "
        f"in the crop database and the current live field conditions, then checked by ELECTRE as an outranking "
        f"cross-check. The NSGA-II optimizer then selected a resource plan of {plan.water_liters_per_week:.0f} L/week "
        f"of irrigation and {plan.fertilizer_kg_per_acre:.1f} kg/acre of fertilizer, with final fitness cost "
        f"{plan.optimizer_best_fitness:.4f} after {plan.optimizer_generations_run} generations; lower fitness is better "
        f"only within the optimizer's objective function, not as a universal crop-quality label."
    )
