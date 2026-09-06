"""
Multi-Criteria Decision-Making (MCDM) module.

Implements three real, standard MCDM techniques used to rank candidate
crops against multiple weighted criteria:

  - AHP (Analytic Hierarchy Process): derives criteria WEIGHTS from a
    pairwise comparison matrix, with a consistency ratio check.
  - TOPSIS: ranks alternatives (crops) by distance from an ideal-best /
    ideal-worst solution across the weighted criteria.
  - ELECTRE I: an outranking-based method used as a cross-check against
    the TOPSIS ranking.

No random numbers anywhere in this file — every score is derived
deterministically from the input criteria matrix.
"""

from __future__ import annotations
import numpy as np

# Saaty's Random Index values, used to compute the AHP Consistency Ratio.
# Index = matrix size (n), value = average RI for random matrices of that size.
_RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


class AHPResult:
    def __init__(self, weights: np.ndarray, consistency_ratio: float, is_consistent: bool):
        self.weights = weights
        self.consistency_ratio = consistency_ratio
        self.is_consistent = is_consistent


def ahp_weights(pairwise_matrix: list[list[float]]) -> AHPResult:
    """
    Compute criteria weights from an AHP pairwise comparison matrix using
    the eigenvector method (approximated via normalized column averaging,
    which converges to the principal eigenvector for consistent-ish
    matrices and is the standard hand-computable AHP approach).

    pairwise_matrix[i][j] = how much more important criterion i is than
    criterion j (Saaty 1-9 scale; reciprocal below the diagonal).
    """
    A = np.array(pairwise_matrix, dtype=float)
    n = A.shape[0]

    # Normalize each column, then average each row -> principal eigenvector approx.
    col_sums = A.sum(axis=0)
    normalized = A / col_sums
    weights = normalized.mean(axis=1)

    # Consistency check: lambda_max via A @ weights, then CI and CR.
    weighted_sum = A @ weights
    lambda_max = float(np.mean(weighted_sum / weights))
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = _RANDOM_INDEX.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0.0

    return AHPResult(weights=weights, consistency_ratio=cr, is_consistent=cr < 0.10)


def topsis(decision_matrix: list[list[float]], weights: list[float], is_benefit: list[bool]) -> list[dict]:
    """
    Rank alternatives using TOPSIS.

    decision_matrix: rows = alternatives (crops), columns = criteria values
    weights:         relative importance of each criterion (sums to 1)
    is_benefit:      True if higher is better for that criterion (e.g. market
                      value), False if lower is better (e.g. water need)

    Returns a list of dicts sorted by descending closeness coefficient:
        [{"index": i, "closeness": float}, ...]
    """
    X = np.array(decision_matrix, dtype=float)
    w = np.array(weights, dtype=float)
    w = w / w.sum()

    # Vector normalization
    norm = np.sqrt((X ** 2).sum(axis=0))
    norm[norm == 0] = 1e-9
    R = X / norm

    # Weighted normalized matrix
    V = R * w

    ideal_best = np.array([
        V[:, j].max() if is_benefit[j] else V[:, j].min()
        for j in range(V.shape[1])
    ])
    ideal_worst = np.array([
        V[:, j].min() if is_benefit[j] else V[:, j].max()
        for j in range(V.shape[1])
    ])

    dist_best = np.sqrt(((V - ideal_best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((V - ideal_worst) ** 2).sum(axis=1))

    denom = dist_best + dist_worst
    denom[denom == 0] = 1e-9
    closeness = dist_worst / denom

    ranked = sorted(
        ({"index": i, "closeness": float(c)} for i, c in enumerate(closeness)),
        key=lambda r: r["closeness"],
        reverse=True,
    )
    return ranked


def electre_i(decision_matrix: list[list[float]], weights: list[float], is_benefit: list[bool],
              concordance_threshold: float = 0.6, discordance_threshold: float = 0.4) -> dict:
    """
    Simplified ELECTRE I outranking analysis, used as a cross-check against
    TOPSIS. Produces a concordance/discordance matrix and an outranking
    relation: alternative a outranks b if concordance(a,b) >= threshold and
    discordance(a,b) <= threshold.

    Returns {"outranks": {i: [j, ...]}, "net_outranking_count": [int, ...]}
    where net_outranking_count[i] = (# alternatives i outranks) - (# that outrank i).
    A higher net count indicates a stronger overall position, usable as a
    cross-check ranking signal alongside TOPSIS.
    """
    X = np.array(decision_matrix, dtype=float)
    w = np.array(weights, dtype=float)
    w = w / w.sum()
    n_alts, n_crit = X.shape

    ranges = X.max(axis=0) - X.min(axis=0)
    ranges[ranges == 0] = 1e-9

    outranks = {i: [] for i in range(n_alts)}

    for a in range(n_alts):
        for b in range(n_alts):
            if a == b:
                continue
            concordant_weight = 0.0
            max_discordance = 0.0
            for c in range(n_crit):
                a_better = X[a, c] >= X[b, c] if is_benefit[c] else X[a, c] <= X[b, c]
                if a_better:
                    concordant_weight += w[c]
                else:
                    disc = abs(X[a, c] - X[b, c]) / ranges[c]
                    max_discordance = max(max_discordance, disc)
            if concordant_weight >= concordance_threshold and max_discordance <= discordance_threshold:
                outranks[a].append(b)

    net_count = []
    for i in range(n_alts):
        outranked_by_i = len(outranks[i])
        outranked_i = sum(1 for j in range(n_alts) if i in outranks[j])
        net_count.append(outranked_by_i - outranked_i)

    return {"outranks": outranks, "net_outranking_count": net_count}
