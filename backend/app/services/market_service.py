"""
Market price service — AGMARKNET CSV Data Ingestion with Data Provenance tracking.

EXPLICIT DATA CLASSIFICATION:
Agmarknet CSV data is explicitly classified as STATIC_DATASET (historical dataset ingestion),
NEVER as "live market data".
"""

from __future__ import annotations
import csv
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "market_prices.csv"


@dataclass
class MarketResult:
    prices: dict[str, float]
    source: str  # "agmarknet-csv" or "fallback-index"
    source_type: str = "STATIC_DATASET"  # "STATIC_DATASET" or "MOCK/FALLBACK"
    observation_date: str | None = None
    retrieved_at: str = ""
    is_stale: bool = False
    quality_status: str = "good"

    def __post_init__(self):
        if not self.retrieved_at:
            self.retrieved_at = datetime.now(timezone.utc).isoformat()


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


def get_market_provenance(csv_path: Path = DEFAULT_CSV_PATH) -> MarketResult:
    """Load market prices and return structured provenance metadata."""
    prices = load_market_prices(csv_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    if prices:
        return MarketResult(
            prices=prices,
            source="agmarknet-csv",
            source_type="STATIC_DATASET",
            observation_date="2026-07-20",
            retrieved_at=now_iso,
            is_stale=False,
            quality_status="good",
        )
    return MarketResult(
        prices={},
        source="fallback-index",
        source_type="MOCK/FALLBACK",
        observation_date=None,
        retrieved_at=now_iso,
        is_stale=True,
        quality_status="unavailable",
    )


def get_market_value_index(crop: str, prices: dict[str, float], fallback_index: float) -> float:
    """
    Returns a 1-10 style market value index. If price data is loaded,
    normalizes the crop's price against the range of prices in the dataset;
    otherwise uses the crop database's static fallback index.
    """
    if crop in prices and prices:
        all_prices = list(prices.values())
        lo, hi = min(all_prices), max(all_prices)
        if hi == lo:
            return 5.0
        return 1 + 9 * (prices[crop] - lo) / (hi - lo)
    return fallback_index
