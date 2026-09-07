from __future__ import annotations

from pydantic import BaseModel, Field


class CriterionContribution(BaseModel):
    criterion: str
    ahp_weight: float
    raw_score: float
    weighted_contribution: float


class RecommendationInsight(BaseModel):
    top_crop: str
    topsis_closeness: float
    rank: int
    top_contributing_criteria: list[CriterionContribution] = Field(default_factory=list)
    weakest_criterion: CriterionContribution
    tie_break_context: str | None = None


class ComparisonCriteriaEntry(BaseModel):
    criterion: str
    crop_a_score: float
    crop_b_score: float
    weighted_diff: float


class ComparisonInsight(BaseModel):
    crop_a: str
    crop_b: str
    criteria_comparison: list[ComparisonCriteriaEntry] = Field(default_factory=list)
    winning_factors: list[str] = Field(default_factory=list)
    losing_factors: list[str] = Field(default_factory=list)
    topsis_a: float
    topsis_b: float
    electre_a: int
    electre_b: int


class EnvironmentalFactorStatus(BaseModel):
    field: str
    live_value: float
    status: str
    preferred_min: float | None = None
    preferred_max: float | None = None


class EnvironmentalInsight(BaseModel):
    target_crop: str
    factors: list[EnvironmentalFactorStatus] = Field(default_factory=list)


class FarmInsightBundle(BaseModel):
    recommendation: RecommendationInsight
    environmental: EnvironmentalInsight
    comparisons: list[ComparisonInsight] = Field(default_factory=list)
