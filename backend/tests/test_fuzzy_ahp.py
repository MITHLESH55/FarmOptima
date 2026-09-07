import math

from app.core.fuzzy_ahp import (
    fuzzy_ahp_weights,
    crisp_to_default_fuzzy,
    _degree_of_possibility,
    select_ahp_weights,
)


def test_degree_of_possibility_full_when_clearly_greater():
    m1 = (5, 6, 7)
    m2 = (1, 2, 3)
    assert _degree_of_possibility(m1, m2) == 1.0


def test_degree_of_possibility_zero_when_clearly_smaller():
    m1 = (1, 2, 3)
    m2 = (5, 6, 7)
    assert _degree_of_possibility(m1, m2) == 0.0


def test_degree_of_possibility_partial_overlap_between_zero_and_one():
    m1 = (2, 4, 6)
    m2 = (3, 5, 7)
    v = _degree_of_possibility(m1, m2)
    assert 0.0 < v < 1.0


def test_fuzzy_ahp_weights_sum_to_one():
    fuzzy_matrix = crisp_to_default_fuzzy([[1, 2, 3], [1/2, 1, 2], [1/3, 1/2, 1]])
    result = fuzzy_ahp_weights(fuzzy_matrix)
    assert abs(sum(result.weights) - 1.0) < 1e-9


def test_fuzzy_ahp_more_important_criterion_gets_higher_weight():
    fuzzy_matrix = crisp_to_default_fuzzy([[1, 5, 5], [1/5, 1, 1], [1/5, 1, 1]])
    result = fuzzy_ahp_weights(fuzzy_matrix)
    assert result.weights[0] > result.weights[1]
    assert result.weights[0] > result.weights[2]


def test_fuzzy_ahp_equal_importance_gives_near_equal_weights():
    fuzzy_matrix = crisp_to_default_fuzzy([[1, 1, 1], [1, 1, 1], [1, 1, 1]])
    result = fuzzy_ahp_weights(fuzzy_matrix)
    assert all(abs(w - 1/3) < 0.05 for w in result.weights)


def test_crisp_to_default_fuzzy_preserves_most_likely_value():
    crisp = [[1, 2], [0.5, 1]]
    fuzzy = crisp_to_default_fuzzy(crisp, spread=0.2)
    assert fuzzy[0][1][1] == 2       # m component unchanged
    assert fuzzy[0][1][0] == 2 * 0.8  # l = m * (1-spread)
    assert fuzzy[0][1][2] == 2 * 1.2  # u = m * (1+spread)


def test_crisp_to_default_fuzzy_uses_reciprocal_lower_triangle():
    crisp = [[1, 2, 3], [0.5, 1, 2], [1/3, 0.5, 1]]
    fuzzy = crisp_to_default_fuzzy(crisp, spread=0.15)

    expected_10 = (1 / fuzzy[0][1][2], 1 / fuzzy[0][1][1], 1 / fuzzy[0][1][0])
    expected_21 = (1 / fuzzy[1][2][2], 1 / fuzzy[1][2][1], 1 / fuzzy[1][2][0])

    assert all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9) for a, b in zip(fuzzy[1][0], expected_10))
    assert all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9) for a, b in zip(fuzzy[2][1], expected_21))


def test_select_ahp_weights_falls_back_when_fuzzy_matrix_is_degenerate():
    crisp = [[1, 2, 3, 3], [0.5, 1, 2, 2], [1/3, 0.5, 1, 2], [1/3, 0.5, 0.5, 1]]
    fuzzy = crisp_to_default_fuzzy(crisp)
    weights, used_crisp_fallback = select_ahp_weights(crisp, fuzzy)

    assert used_crisp_fallback is False
    assert abs(sum(weights) - 1.0) < 1e-9
    assert len(weights) == 4
