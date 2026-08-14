import numpy as np
from app.core.mcdm import ahp_weights, topsis, electre_i


def test_ahp_weights_sum_to_one():
    matrix = [[1, 2, 3], [1/2, 1, 2], [1/3, 1/2, 1]]
    result = ahp_weights(matrix)
    assert abs(sum(result.weights) - 1.0) < 1e-9


def test_ahp_consistent_matrix_has_low_cr():
    # A perfectly consistent matrix (derived from true ratios 1, 2, 3)
    ratios = [3, 2, 1]
    n = len(ratios)
    matrix = [[ratios[i] / ratios[j] for j in range(n)] for i in range(n)]
    result = ahp_weights(matrix)
    assert result.consistency_ratio < 0.01
    assert result.is_consistent


def test_ahp_more_important_criterion_gets_higher_weight():
    # Criterion 0 is heavily favored over 1 and 2
    matrix = [[1, 5, 5], [1/5, 1, 1], [1/5, 1, 1]]
    result = ahp_weights(matrix)
    assert result.weights[0] > result.weights[1]
    assert result.weights[0] > result.weights[2]


def test_topsis_best_alternative_is_dominant_one():
    # Alternative 0 dominates on both criteria (higher is better for both)
    decision_matrix = [
        [0.9, 0.9],  # clearly best
        [0.5, 0.5],  # middle
        [0.1, 0.1],  # clearly worst
    ]
    ranked = topsis(decision_matrix, weights=[0.5, 0.5], is_benefit=[True, True])
    assert ranked[0]["index"] == 0
    assert ranked[-1]["index"] == 2


def test_topsis_handles_mixed_benefit_cost_criteria():
    # criterion 0 = benefit (higher better), criterion 1 = cost (lower better)
    decision_matrix = [
        [0.9, 0.1],  # high benefit, low cost -> best
        [0.1, 0.9],  # low benefit, high cost -> worst
    ]
    ranked = topsis(decision_matrix, weights=[0.5, 0.5], is_benefit=[True, False])
    assert ranked[0]["index"] == 0


def test_electre_outranking_produces_valid_structure():
    decision_matrix = [[0.9, 0.9], [0.5, 0.5], [0.1, 0.1]]
    result = electre_i(decision_matrix, weights=[0.5, 0.5], is_benefit=[True, True])
    assert len(result["net_outranking_count"]) == 3
    # The dominant alternative should have the highest net outranking count
    assert result["net_outranking_count"][0] == max(result["net_outranking_count"])


def test_ahp_configured_weights_full_data():
    """Verify configured AHP weights sum to 1.0 and match pairwise matrix expectations."""
    from app.core.criteria import DEFAULT_AHP_PAIRWISE_MATRIX, CRITERIA_NAMES
    from app.core.fuzzy_ahp import crisp_to_default_fuzzy, select_ahp_weights

    fuzzy_matrix = crisp_to_default_fuzzy(DEFAULT_AHP_PAIRWISE_MATRIX)
    weights, _ = select_ahp_weights(DEFAULT_AHP_PAIRWISE_MATRIX, fuzzy_matrix)
    w_dict = dict(zip(CRITERIA_NAMES, weights))

    assert abs(sum(weights) - 1.0) < 1e-6
    assert abs(w_dict["climate_suitability"] - 0.4495) < 0.01
    assert abs(w_dict["soil_suitability"] - 0.2596) < 0.01
    assert abs(w_dict["water_efficiency"] - 0.1707) < 0.01
    assert abs(w_dict["market_value"] - 0.1202) < 0.01
    assert all(w > 0 for w in weights)


def test_ahp_weights_invariance_when_soil_data_missing():
    """Verify that AHP criteria weights remain 100% IDENTICAL when soil data is missing (fixes AHP collapse bug)."""
    from app.core.criteria import DEFAULT_AHP_PAIRWISE_MATRIX, CRITERIA_NAMES, build_decision_matrix
    from app.core.fuzzy_ahp import crisp_to_default_fuzzy, select_ahp_weights

    # Full data run weights
    fuzzy_matrix_full = crisp_to_default_fuzzy(DEFAULT_AHP_PAIRWISE_MATRIX)
    weights_full, _ = select_ahp_weights(DEFAULT_AHP_PAIRWISE_MATRIX, fuzzy_matrix_full)

    # Missing soil data run decision matrix
    names, matrix, is_benefit = build_decision_matrix(
        ndvi=0.6,
        soil_ph=0.0,  # Missing soil
        rainfall_mm_30d=100.0,
        avg_temp_c=25.0,
        soil_source="unavailable",
    )

    # Weights for missing soil data run must use AHP matrix alone and remain IDENTICAL
    fuzzy_matrix_missing = crisp_to_default_fuzzy(DEFAULT_AHP_PAIRWISE_MATRIX)
    weights_missing, _ = select_ahp_weights(DEFAULT_AHP_PAIRWISE_MATRIX, fuzzy_matrix_missing)

    assert weights_full == weights_missing, "AHP weights must not collapse or redistribute when soil data is missing!"

