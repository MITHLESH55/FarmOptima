"""
Fuzzy AHP — Chang's (1996) extent analysis method.

Upgrades crisp AHP (core/mcdm.py::ahp_weights) to handle genuine expert
UNCERTAINTY in pairwise comparisons. Instead of forcing an expert to commit
to a single crisp number (e.g. "climate is exactly 3x more important than
market value"), each comparison is a triangular fuzzy number (l, m, u) —
a lower, most-likely, and upper estimate — which is the standard way the
MCDM literature represents linguistic hedging ("climate is moderately to
strongly more important").

This is what actually differentiates "using AHP" (well-established, not
patentable on its own) from "using AHP in a way that handles the genuine
uncertainty an agricultural expert has when weighting criteria" — a real,
citable methodological contribution.

Reference: Chang, D. Y. (1996). "Applications of the extent analysis
method on fuzzy AHP." European Journal of Operational Research, 95(3),
649-655.
"""

from __future__ import annotations
from dataclasses import dataclass

from app.core.mcdm import ahp_weights

TriangularFuzzyNumber = tuple[float, float, float]  # (l, m, u)


@dataclass
class FuzzyAHPResult:
    weights: list[float]           # crisp, normalized weights (sum to 1)
    fuzzy_synthetic_extents: list[TriangularFuzzyNumber]
    is_fully_consistent: bool      # True if every degree-of-possibility comparison was decisive (no zero weights before normalization)


def _tfn_add(a: TriangularFuzzyNumber, b: TriangularFuzzyNumber) -> TriangularFuzzyNumber:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _tfn_sum(tfns: list[TriangularFuzzyNumber]) -> TriangularFuzzyNumber:
    result = (0.0, 0.0, 0.0)
    for t in tfns:
        result = _tfn_add(result, t)
    return result


def _degree_of_possibility(m1: TriangularFuzzyNumber, m2: TriangularFuzzyNumber) -> float:
    """V(M1 >= M2) — the degree to which fuzzy number m1 is at least as large as m2."""
    l1, m1_, u1 = m1
    l2, m2_, u2 = m2
    if m1_ >= m2_:
        return 1.0
    if l2 >= u1:
        return 0.0
    return (l2 - u1) / ((m1_ - u1) - (m2_ - l2))


def fuzzy_ahp_weights(fuzzy_pairwise_matrix: list[list[TriangularFuzzyNumber]]) -> FuzzyAHPResult:
    """
    fuzzy_pairwise_matrix[i][j] = (l, m, u), the fuzzy judgement of how much
    more important criterion i is than criterion j. Diagonal should be
    (1,1,1); [j][i] should be the reciprocal-ish inverse of [i][j]
    (conventionally approximated as (1/u, 1/m, 1/l)).
    """
    n = len(fuzzy_pairwise_matrix)

    # Step 1: fuzzy synthetic extent value S_i for each criterion i
    row_sums = [_tfn_sum(fuzzy_pairwise_matrix[i]) for i in range(n)]
    grand_total = _tfn_sum(row_sums)
    # Reciprocal of grand_total = (1/u_total, 1/m_total, 1/l_total), applied in reverse order
    grand_total_inv = (1 / grand_total[2], 1 / grand_total[1], 1 / grand_total[0])

    synthetic_extents: list[TriangularFuzzyNumber] = [
        (row_sums[i][0] * grand_total_inv[0], row_sums[i][1] * grand_total_inv[1], row_sums[i][2] * grand_total_inv[2])
        for i in range(n)
    ]

    # Step 2: degree of possibility of S_i >= S_j for all j != i, take the minimum
    min_possibility = []
    fully_consistent = True
    for i in range(n):
        possibilities = [
            _degree_of_possibility(synthetic_extents[i], synthetic_extents[j])
            for j in range(n) if j != i
        ]
        min_v = min(possibilities) if possibilities else 1.0
        if min_v == 0.0:
            fully_consistent = False
        min_possibility.append(min_v)

    # Step 3: normalize into crisp weights
    total = sum(min_possibility)
    if total == 0:
        weights = [1.0 / n] * n
    else:
        weights = [v / total for v in min_possibility]

    return FuzzyAHPResult(
        weights=weights, fuzzy_synthetic_extents=synthetic_extents,
        is_fully_consistent=fully_consistent,
    )


def select_ahp_weights(
    crisp_pairwise_matrix: list[list[float]],
    fuzzy_pairwise_matrix: list[list[TriangularFuzzyNumber]],
) -> tuple[list[float], bool]:
    """
    Prefer the fuzzy AHP result when it yields a decisive, non-degenerate weight
    vector. If the fuzzy matrix produces zero weights (which indicates a
    dominated/ambiguous judgement structure), fall back to the crisp AHP vector,
    which remains a standard and well-defined aggregation of the same Saaty matrix.
    """
    fuzzy_result = fuzzy_ahp_weights(fuzzy_pairwise_matrix)
    if fuzzy_result.is_fully_consistent and all(w > 0 for w in fuzzy_result.weights):
        return fuzzy_result.weights, True

    crisp_result = ahp_weights(crisp_pairwise_matrix)
    return crisp_result.weights.tolist(), False


def crisp_to_default_fuzzy(crisp_pairwise_matrix: list[list[float]], spread: float = 0.15) -> list[list[TriangularFuzzyNumber]]:
    """
    Convenience helper: turns a crisp Saaty-scale matrix into a fuzzy one while
    preserving the reciprocal property required by AHP: if criterion i is judged
    r times as important as j, then criterion j is judged 1/r times as important
    as i. For a triangular fuzzy number (l, m, u), the reciprocal is
    (1/u, 1/m, 1/l).

    The input matrix is assumed to be in the standard AHP convention where
    value[i][j] is the comparison of i relative to j, and value[j][i] = 1 / value[i][j].
    We therefore form each off-diagonal fuzzy estimate from the corresponding
    direct AHP value, and for the lower triangle we explicitly take the reciprocal
    fuzzy number to keep the matrix mathematically consistent.
    """
    n = len(crisp_pairwise_matrix)
    fuzzy = []
    for i in range(n):
        row: list[TriangularFuzzyNumber] = []
        for j in range(n):
            if i == j:
                row.append((1.0, 1.0, 1.0))
                continue

            if i < j:
                m = crisp_pairwise_matrix[i][j]
            else:
                m = crisp_pairwise_matrix[j][i]

            if m <= 0:
                raise ValueError("All crisp pairwise comparisons must be positive.")

            l = m * (1 - spread)
            u = m * (1 + spread)
            if i < j:
                row.append((l, m, u))
            else:
                row.append((1 / u, 1 / m, 1 / l))
        fuzzy.append(row)
    return fuzzy
