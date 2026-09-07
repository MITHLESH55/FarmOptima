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


def interpret_ndvi(value: float) -> str:
    """Return a deterministic NDVI vegetation-health label for a numeric value."""
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
