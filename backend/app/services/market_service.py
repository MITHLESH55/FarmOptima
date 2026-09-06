"""
Market price service.

AGMARKNET does not expose a clean, stable public REST API (it's built for
manual/portal browsing, and data.gov.in's coverage of it is inconsistent
by state/commodity). The professional approach here — rather than
pretending it's a live API — is a deliberate CSV ingestion pipeline:

  1. Periodically export commodity price data from AGMARKNET (or a
     data.gov.in dataset if available for your target state) as CSV.
  2. Drop the file at data/market_prices.csv (see the sample format below).
  3. This service loads and caches it, matched by crop name.

This keeps the data source honest and documented rather than silently
faking market prices, while being realistic about what solo-dev API access
actually looks like for this dataset.

Sample CSV format expected (data/market_prices.csv):
    crop,modal_price_per_quintal_inr,market,date
    Wheat,2250,Indore,2026-07-20
    Rice,3400,Karnal,2026-07-20
"""

from __future__ import annotations
import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "market_prices.csv"


def load_market_prices(csv_path: Path = DEFAULT_CSV_PATH) -> dict[str, float]:
    """Returns {crop_name: modal_price_per_quintal_inr}. Empty dict if file missing."""
    if not csv_path.exists():
        logger.info("No market_prices.csv found at %s — using base_market_value_index fallback.", csv_path)
        return {}
    prices = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                prices[row["crop"]] = float(row["modal_price_per_quintal_inr"])
            except (KeyError, ValueError):
                continue
    return prices


def get_market_value_index(crop: str, prices: dict[str, float], fallback_index: float) -> float:
    """
    Returns a 1-10 style market value index. If real price data is loaded,
    normalizes the crop's price against the range of prices in the dataset;
    otherwise uses the crop database's static fallback index (clearly a
    lower-fidelity signal — surfaced via the `source` field upstream).
    """
    if crop in prices and prices:
        all_prices = list(prices.values())
        lo, hi = min(all_prices), max(all_prices)
        if hi == lo:
            return 5.0
        return 1 + 9 * (prices[crop] - lo) / (hi - lo)
    return fallback_index
