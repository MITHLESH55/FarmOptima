from __future__ import annotations

from app.crop_database import CROP_DATABASE
from app.schemas.ai import FarmContext
from app.schemas.insight import (
    ComparisonCriteriaEntry,
    ComparisonInsight,
    CriterionContribution,
    EnvironmentalFactorStatus,
    EnvironmentalInsight,
    RecommendationInsight,
)


class CropNotInRankingError(ValueError):
    """Raised when an insight is requested for a crop absent from the ranking."""


class MissingCriterionScoresError(ValueError):
    """Raised when a recommendation snapshot lacks the evidence required for insight generation."""


def _get_entry_by_crop(context: FarmContext, crop_name: str):
    for entry in context.crop_ranking:
        if entry.crop.lower() == crop_name.lower():
            return entry
    raise CropNotInRankingError(f"Crop '{crop_name}' is not in the current ranking.")


def _criterion_entries_for_entry(entry, ahp_weights: dict[str, float]) -> list[CriterionContribution]:
    scores = dict(entry.criteria_scores or {})
    if not scores:
        raise MissingCriterionScoresError(
            f"No authoritative criterion scores are available for crop '{entry.crop}'. "
            "Insight generation requires the persisted recommendation snapshot."
        )

    ordered = sorted(scores.items(), key=lambda item: (-float(item[1]), item[0]))
    return [
        CriterionContribution(
            criterion=criterion,
            ahp_weight=float(ahp_weights.get(criterion, 0.0)),
            raw_score=float(score),
            weighted_contribution=float(ahp_weights.get(criterion, 0.0) * score),
        )
        for criterion, score in ordered
    ]


def generate_recommendation_insight(context: FarmContext) -> RecommendationInsight:
    if not context.crop_ranking:
        raise ValueError("Cannot generate recommendation insight for an empty crop ranking.")

    top_entry = context.crop_ranking[0]
    criteria = _criterion_entries_for_entry(top_entry, context.ahp_weights)
    top_crop = top_entry.crop
    tie_break_context = top_entry.tie_break_reason if top_entry.tie_break_applied else None

    return RecommendationInsight(
        top_crop=top_crop,
        topsis_closeness=float(top_entry.topsis_closeness),
        rank=int(top_entry.rank),
        top_contributing_criteria=criteria,
        weakest_criterion=min(criteria, key=lambda item: item.raw_score),
        tie_break_context=tie_break_context,
    )


def generate_comparison_insight(context: FarmContext, crop_a: str, crop_b: str) -> ComparisonInsight:
    """Internal comparison helper for deterministic evidence-driven insight generation.

    The current endpoint contract intentionally does not expose these results via
    the public /insight response, so this function remains a pure internal helper
    rather than a public API feature.
    """
    entry_a = _get_entry_by_crop(context, crop_a)
    entry_b = _get_entry_by_crop(context, crop_b)
    if not entry_a.criteria_scores or not entry_b.criteria_scores:
        raise MissingCriterionScoresError(
            "Comparison insight requires authoritative criterion scores from the recommendation snapshot."
        )

    criteria = sorted(
        set(entry_a.criteria_scores.keys()) | set(entry_b.criteria_scores.keys()),
        key=lambda criterion: (
            -abs(float(entry_a.criteria_scores.get(criterion, 0.0)) - float(entry_b.criteria_scores.get(criterion, 0.0))),
            criterion,
        ),
    )

    comparison_entries: list[ComparisonCriteriaEntry] = []
    for criterion in criteria:
        score_a = float(entry_a.criteria_scores.get(criterion, 0.0))
        score_b = float(entry_b.criteria_scores.get(criterion, 0.0))
        diff = score_a - score_b
        comparison_entries.append(
            ComparisonCriteriaEntry(
                criterion=criterion,
                crop_a_score=score_a,
                crop_b_score=score_b,
                weighted_diff=float(context.ahp_weights.get(criterion, 0.0) * diff),
            )
        )

    winning_criteria = [
        item.criterion
        for item in comparison_entries
        if item.weighted_diff > 0.0
    ]
    winning_criteria = sorted(winning_criteria, key=lambda c: (-abs(next(x.weighted_diff for x in comparison_entries if x.criterion == c)), c))[:1]

    losing_criteria = sorted(
        [item.criterion for item in comparison_entries if item.criterion not in winning_criteria],
        key=lambda c: c,
    )

    return ComparisonInsight(
        crop_a=entry_a.crop,
        crop_b=entry_b.crop,
        criteria_comparison=comparison_entries,
        winning_factors=winning_criteria,
        losing_factors=losing_criteria,
        topsis_a=float(entry_a.topsis_closeness),
        topsis_b=float(entry_b.topsis_closeness),
        electre_a=int(entry_a.electre_net_outranking),
        electre_b=int(entry_b.electre_net_outranking),
    )


def generate_environmental_insight(context: FarmContext, crop_name: str) -> EnvironmentalInsight:
    crop_params = CROP_DATABASE.get(crop_name)
    if crop_params is None:
        raise CropNotInRankingError(f"Crop '{crop_name}' is not in the crop reference database.")

    factors: list[EnvironmentalFactorStatus] = []

    def add_factor(field_name: str, value: float | None, preferred_min: float | None = None, preferred_max: float | None = None):
        if value is None:
            status = "not_available"
            preferred_min = None
            preferred_max = None
        elif preferred_min is None and preferred_max is None:
            status = "no_reference_configured"
        elif preferred_min <= value <= preferred_max:
            status = "within_preferred_range"
        elif value < preferred_min:
            status = "below_preferred_range"
        else:
            status = "above_preferred_range"
        factors.append(
            EnvironmentalFactorStatus(
                field=field_name,
                live_value=float(value) if value is not None else 0.0,
                status=status,
                preferred_min=preferred_min,
                preferred_max=preferred_max,
            )
        )

    if context.ndvi is not None:
        if isinstance(context.ndvi, (int, float)):
            ndvi_val = float(context.ndvi)
            ndvi_status = "not_available"
        else:
            ndvi_val = float(context.ndvi.value)
            ndvi_status = context.ndvi.status or "not_available"
        add_factor("ndvi", ndvi_val, None, None)
        factors[-1].status = ndvi_status
        factors[-1].preferred_min = None
        factors[-1].preferred_max = None

    add_factor(
        "rainfall_mm_last_30d",
        context.rainfall_mm_last_30d,
        float(crop_params["ideal_rainfall_min_mm_30d"]),
        float(crop_params["ideal_rainfall_max_mm_30d"]),
    )
    add_factor(
        "avg_temp_c",
        context.avg_temp_c,
        float(crop_params["ideal_temp_min_c"]),
        float(crop_params["ideal_temp_max_c"]),
    )
    add_factor(
        "soil_ph",
        context.soil_ph,
        float(crop_params["ideal_ph_min"]),
        float(crop_params["ideal_ph_max"]),
    )
    add_factor("soil_moisture_pct", context.soil_moisture_pct)

    return EnvironmentalInsight(target_crop=crop_name, factors=factors)
