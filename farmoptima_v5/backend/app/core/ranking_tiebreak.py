from __future__ import annotations

from copy import copy

from app.schemas.ai import CropRankEntry

TOPSIS_TIE_EPSILON = 1e-8

_CRITERIA_ORDER = [
    "climate_suitability",
    "soil_suitability",
    "water_efficiency",
    "market_value",
]


def _criterion_index(criterion_name: str) -> int:
    try:
        return _CRITERIA_ORDER.index(criterion_name)
    except ValueError as exc:
        raise ValueError(f"Unknown criterion '{criterion_name}'") from exc


def _sorted_group_positions(group_positions: list[int], group_entries: list[CropRankEntry], ahp_weights: dict[str, float], decision_matrix: list[list[float]]) -> list[int]:
    """Return the order of rows within a TOPSIS-tied group after applying the tie-break method."""
    electre_values = [group_entries[i].electre_net_outranking for i in range(len(group_entries))]
    if len(set(electre_values)) > 1:
        return [
            group_positions[i]
            for i, _ in sorted(enumerate(group_entries), key=lambda pair: pair[1].electre_net_outranking, reverse=True)
        ]

    dominant_criterion = max(ahp_weights, key=ahp_weights.get) if ahp_weights else _CRITERIA_ORDER[0]
    criterion_idx = _criterion_index(dominant_criterion)
    values = [decision_matrix[pos][criterion_idx] for pos in group_positions]
    if len(set(round(v, 12) for v in values)) > 1:
        order = sorted(
            range(len(group_positions)),
            key=lambda i: decision_matrix[group_positions[i]][criterion_idx],
            reverse=True,
        )
        return [group_positions[i] for i in order]

    return sorted(
        group_positions,
        key=lambda pos: decision_matrix[pos][0] if len(decision_matrix[pos]) > 0 else 0.0,
    )


def resolve_tie_break_order(entries: list[CropRankEntry], ahp_weights: dict[str, float], decision_matrix: list[list[float]]) -> list[CropRankEntry]:
    """
    Resolve TOPSIS ties deterministically and update the recommendation metadata
    with machine-readable reasons that can be passed through the API and AI context.

    Tie-break precedence:
      1. TOPSIS values tied within epsilon
      2. ELECTRE net outranking result
      3. Dominant AHP criterion on raw decision-matrix values
      4. Alphabetical fallback
    """
    if not entries:
        return []

    working = [copy(entry) for entry in entries]
    for item in working:
        item.tie_break_applied = False
        item.tie_break_reason = None

    # Use the ranking order as the starting point. If it is not already sorted by
    # TOPSIS descending, sort it here before resolving tied groups.
    ordered = sorted(working, key=lambda item: item.topsis_closeness, reverse=True)
    row_by_crop = {entry.crop: idx for idx, entry in enumerate(entries)}

    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and abs(ordered[j].topsis_closeness - ordered[i].topsis_closeness) <= TOPSIS_TIE_EPSILON:
            j += 1

        group = ordered[i:j]
        if len(group) > 1:
            group_positions = [row_by_crop[item.crop] for item in group]
            electre_values = [item.electre_net_outranking for item in group]
            if len(set(electre_values)) > 1:
                group_reason = "electre_net_outranking"
                ordered[i:j] = [group[k] for k in sorted(range(len(group)), key=lambda idx: group[idx].electre_net_outranking, reverse=True)]
            else:
                dominant_criterion = max(ahp_weights, key=ahp_weights.get) if ahp_weights else _CRITERIA_ORDER[0]
                criterion_idx = _criterion_index(dominant_criterion)
                matrix_values = [decision_matrix[row_by_crop[item.crop]][criterion_idx] for item in group]
                if len(set(round(v, 12) for v in matrix_values)) > 1:
                    group_reason = f"dominant_criterion:{dominant_criterion}"
                    ordered[i:j] = [
                        group[k]
                        for k in sorted(
                            range(len(group)),
                            key=lambda idx: decision_matrix[row_by_crop[group[idx].crop]][criterion_idx],
                            reverse=True,
                        )
                    ]
                else:
                    group_reason = "alphabetical_fallback"
                    ordered[i:j] = sorted(group, key=lambda item: item.crop.lower())

            for item in ordered[i:j]:
                item.tie_break_applied = True
                item.tie_break_reason = group_reason
        else:
            group_reason = None
            group[0].tie_break_applied = False
            group[0].tie_break_reason = None
        i = j

    return ordered
