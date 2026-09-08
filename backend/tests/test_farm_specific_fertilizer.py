"""
Dedicated test suite for Farm-Specific Fertilizer Recommendation Engine.

Tests:
- Acreage scaling (1 acre vs 5 acres vs 25 acres)
- Soil test N adjustment (Low soil N increases N requirement; High soil N decreases N requirement)
- DAP, Urea, MOP commercial conversion without double counting DAP N
- No negative fertilizer quantities
- Split application schedule integrity
"""

import pytest
from app.services.fertilizer_service import calculate_fertilizer_plan


def test_fertilizer_acreage_scaling():
    """Verify commercial fertilizer quantities scale linearly with field area in acres."""
    plan_1 = calculate_fertilizer_plan("Wheat", target_n_kg_per_acre=48.0, field_area_acres=1.0)
    plan_5 = calculate_fertilizer_plan("Wheat", target_n_kg_per_acre=48.0, field_area_acres=5.0)

    for item_1, item_5 in zip(plan_1.commercial_fertilizers, plan_5.commercial_fertilizers):
        assert pytest.approx(item_1.quantity_kg_per_acre, 0.01) == item_5.quantity_kg_per_acre
        assert pytest.approx(item_5.quantity_kg_total, 0.05) == item_1.quantity_kg_total * 5.0


def test_soil_nitrogen_adjustment():
    """Verify that low soil N increases nitrogen dosage and high soil N decreases nitrogen dosage."""
    plan_low_n = calculate_fertilizer_plan("Wheat", target_n_kg_per_acre=48.0, soil_nitrogen_mg_kg=20.0, field_area_acres=1.0)
    plan_high_n = calculate_fertilizer_plan("Wheat", target_n_kg_per_acre=48.0, soil_nitrogen_mg_kg=80.0, field_area_acres=1.0)

    assert plan_low_n.nutrient_requirements.nitrogen_kg_per_acre > plan_high_n.nutrient_requirements.nitrogen_kg_per_acre


def test_no_double_counting_dap_nitrogen():
    """Verify that Urea calculation subtracts the N supplied by DAP and never returns negative quantities."""
    plan = calculate_fertilizer_plan("Wheat", target_n_kg_per_acre=48.0, field_area_acres=1.0)

    dap_item = next(item for item in plan.commercial_fertilizers if "DAP" in item.name)
    urea_item = next(item for item in plan.commercial_fertilizers if "Urea" in item.name)

    # DAP is 18% N and 46% P₂O₅.
    p_req = plan.nutrient_requirements.phosphorus_kg_per_acre
    expected_dap = p_req / 0.46
    n_from_dap = expected_dap * 0.18
    remaining_n = max(0.0, plan.nutrient_requirements.nitrogen_kg_per_acre - n_from_dap)
    expected_urea = remaining_n / 0.46

    assert pytest.approx(dap_item.quantity_kg_per_acre, 0.1) == expected_dap
    assert pytest.approx(urea_item.quantity_kg_per_acre, 0.1) == expected_urea
    assert urea_item.quantity_kg_per_acre >= 0.0
    assert dap_item.quantity_kg_per_acre >= 0.0


def test_application_schedule_totals():
    """Verify that the sum of split schedule applications equals the total commercial fertilizer requirements."""
    plan = calculate_fertilizer_plan("Cotton", target_n_kg_per_acre=60.0, field_area_acres=3.5)
    
    total_dap_sch = sum(stage.dap_kg for stage in plan.application_schedule)
    total_urea_sch = sum(stage.urea_kg for stage in plan.application_schedule)
    total_mop_sch = sum(stage.mop_kg for stage in plan.application_schedule)

    dap_item = next(item for item in plan.commercial_fertilizers if "DAP" in item.name)
    urea_item = next(item for item in plan.commercial_fertilizers if "Urea" in item.name)
    mop_item = next(item for item in plan.commercial_fertilizers if "MOP" in item.name)

    assert pytest.approx(total_dap_sch, 0.1) == dap_item.quantity_kg_total
    assert pytest.approx(total_urea_sch, 0.1) == urea_item.quantity_kg_total
    assert pytest.approx(total_mop_sch, 0.1) == mop_item.quantity_kg_total
