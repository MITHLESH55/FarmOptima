"""Deterministic environmental interpretation helpers for recommendation context.

This module is intentionally pure (no I/O, no LLM call) so it can be reused
across NDVI and later environmental status rules without coupling AI or API
logic to remote services.

NDVI interpretation uses standard remote-sensing vegetation-health bands from
published literature: negative values indicate water/non-vegetated surfaces,
0.0-0.1 is bare soil or very sparse vegetation, 0.1-0.2 sparse vegetation,
0.2-0.4 moderate vegetation, 0.4-0.6 dense vegetation, and >= 0.6 very dense
vegetation. This is the standard vegetation-index interpretation used in
remote-sensing monitoring workflows and is not invented for this app.
"""

from __future__ import annotations


import math


def interpret_ndvi(value: float | None) -> str:
    """Return a deterministic NDVI vegetation-health label for a numeric value."""
    if value is None or not math.isfinite(value):
        return "unavailable"
    if value < 0:
        return "water / non-vegetated surface"
    if value < 0.1:
        return "bare soil / very sparse vegetation"
    if value < 0.2:
        return "sparse vegetation"
    if value < 0.4:
        return "moderate vegetation"
    if value < 0.6:
        return "dense vegetation"
    return "very dense vegetation"


def interpret_factor_range(
    value: float | None,
    opt_min: float | None = None,
    opt_max: float | None = None,
) -> str:
    """Deterministic, single source of truth for environmental factor status relative to crop reference."""
    if value is None or not math.isfinite(value):
        return "unavailable"
    if opt_min is None and opt_max is None:
        return "no_reference_configured"
    if opt_min is not None and opt_max is not None:
        if opt_min <= value <= opt_max:
            return "within_preferred_range"
        if value < opt_min:
            return "below_preferred_range"
        return "above_preferred_range"
    if opt_min is not None:
        return "within_preferred_range" if value >= opt_min else "below_preferred_range"
    if opt_max is not None:
        return "within_preferred_range" if value <= opt_max else "above_preferred_range"
    return "within_preferred_range"

