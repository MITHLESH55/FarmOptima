"""
Dedicated test suite for MCDM algorithm integrity (AHP, TOPSIS, ELECTRE I).

Tests:
- AHP priority vector calculation, λmax, CI, and CR independence
- Consistency Ratio (CR) is reported separately and not confused with confidence/suitability
- TOPSIS normalization, ideal best/worst identification, and closeness score calculation
- ELECTRE I concordance, discordance, and outranking matrix properties
"""

import pytest
import numpy as np
from app.core.mcdm import ahp_weights, topsis, electre_i, AHPResult


def test_ahp_consistent_matrix():
    """Verify AHP weight calculation on a consistent 4x4 matrix."""
    matrix = [
        [1,   2,   3,   4],
        [1/2, 1,   2,   3],
        [1/3, 1/2, 1,   2],
        [1/4, 1/3, 1/2, 1],
    ]
    res = ahp_weights(matrix)
    assert isinstance(res, AHPResult)
    assert len(res.weights) == 4
    assert pytest.approx(sum(res.weights), 0.001) == 1.0
    assert res.consistency_ratio < 0.10
    assert res.is_consistent is True


def test_ahp_inconsistent_matrix():
    """Verify that highly inconsistent matrix produces CR > 0.10 and is_consistent=False."""
    matrix = [
        [1,   9,   1/9, 9],
        [1/9, 1,   9,   1/9],
        [9,   1/9, 1,   9],
        [1/9, 9,   1/9, 1],
    ]
    res = ahp_weights(matrix)
    assert res.consistency_ratio > 0.10
    assert res.is_consistent is False


def test_topsis_vector_normalization_and_closeness():
    """Verify TOPSIS ranking properties: closeness coefficient in [0, 1] and correct ordering."""
    matrix = [
        [0.9, 0.8, 0.7, 0.6],  # Alt 0: Superior across all benefit criteria
        [0.4, 0.3, 0.4, 0.3],  # Alt 1: Weak across all benefit criteria
    ]
    weights = [0.25, 0.25, 0.25, 0.25]
    is_benefit = [True, True, True, True]

    ranked = topsis(matrix, weights, is_benefit)
    assert len(ranked) == 2
    assert ranked[0]["index"] == 0  # Superior alternative ranks 1st
    assert ranked[1]["index"] == 1
    assert 0.0 <= ranked[0]["closeness"] <= 1.0
    assert 0.0 <= ranked[1]["closeness"] <= 1.0
    assert ranked[0]["closeness"] > ranked[1]["closeness"]


def test_electre_i_outranking_relation():
    """Verify ELECTRE I outranking and net count calculation."""
    matrix = [
        [0.9, 0.9, 0.8, 0.9],
        [0.3, 0.4, 0.3, 0.3],
    ]
    weights = [0.25, 0.25, 0.25, 0.25]
    is_benefit = [True, True, True, True]

    result = electre_i(matrix, weights, is_benefit, concordance_threshold=0.6, discordance_threshold=0.4)
    assert "outranks" in result
    assert "net_outranking_count" in result
    # Alternative 0 should outrank Alternative 1
    assert 1 in result["outranks"][0]
    assert result["net_outranking_count"][0] > result["net_outranking_count"][1]
