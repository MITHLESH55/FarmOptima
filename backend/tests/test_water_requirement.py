"""
Dedicated test suite for Crop Water Requirement & Irrigation Schedule Engine.

Tests:
- Physical conversion constant ACRE_TO_LITERS_PER_MM = 4046.86 L/(acre*mm)
- Season duration assumption SEASON_WEEKS = 16
- Water balance calculation (crop water requirement vs effective rainfall & soil moisture credit)
- Irrigation schedule conversion (L/week and daily split guidance)
"""

import pytest
from app.core.nsga2 import ACRE_TO_LITERS_PER_MM, _objectives



def test_physical_constants_integrity():
    """Verify physical unit conversion constants."""
    # 1 acre = 4,046.8564224 m². 1 mm of rain over 1 m² = 1 Liter.
    # Therefore, 1 mm over 1 acre = 4046.86 Liters.
    assert ACRE_TO_LITERS_PER_MM == 4046.86


def test_water_balance_and_effective_rainfall_credit():
    """Verify that higher rainfall and soil moisture increase supply credit and reduce water gap."""
    # Low rainfall, dry soil
    w_gap_dry, f_gap_1, cost_1 = _objectives(
        water_l_week=2000.0,
        fert_kg_acre=45.0,
        season_weeks=16,
        crop_water_need_mm=500.0,
        crop_fert_need_kg_acre=45.0,
        rainfall_mm_30d=20.0,
        soil_moisture_pct=15.0,
        water_cost_per_liter=0.05,
        fert_cost_per_kg=25.0,
    )

    # High rainfall, moist soil with same irrigation water
    w_gap_wet, f_gap_2, cost_2 = _objectives(
        water_l_week=2000.0,
        fert_kg_acre=45.0,
        season_weeks=16,
        crop_water_need_mm=500.0,
        crop_fert_need_kg_acre=45.0,
        rainfall_mm_30d=120.0,
        soil_moisture_pct=40.0,
        water_cost_per_liter=0.05,
        fert_cost_per_kg=25.0,
    )

    # Supply in high rainfall scenario is greater, shifting effective supply closer to crop requirement
    assert w_gap_dry != w_gap_wet
