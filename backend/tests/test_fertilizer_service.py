import pytest
from app.services.fertilizer_service import calculate_fertilizer_plan
from app.crop_database import CROP_DATABASE


def test_fertilizer_plan_basic_nutrient_calculation():
    plan = calculate_fertilizer_plan(crop_name="Rice", target_n_kg_per_acre=55.0, field_area_acres=1.0)
    assert plan.crop == "Rice"
    assert plan.field_area_acres == 1.0
    assert plan.nutrient_requirements.nitrogen_kg_per_acre == 55.0
    assert plan.nutrient_requirements.phosphorus_kg_per_acre == 24.0
    assert plan.nutrient_requirements.potassium_kg_per_acre == 20.0
    assert plan.nutrient_requirements.total_field_nitrogen_kg == 55.0


def test_fertilizer_commercial_conversion_mathematical_consistency():
    plan = calculate_fertilizer_plan(crop_name="Wheat", target_n_kg_per_acre=48.0, field_area_acres=1.0)
    
    # Products
    dap = next(f for f in plan.commercial_fertilizers if "DAP" in f.name)
    urea = next(f for f in plan.commercial_fertilizers if "Urea" in f.name)
    mop = next(f for f in plan.commercial_fertilizers if "MOP" in f.name)

    # DAP supplies 46% P2O5 -> DAP = 24 / 0.46 = 52.17 kg/acre
    assert dap.quantity_kg_per_acre == pytest.approx(52.17, abs=0.1)
    
    # N from DAP = 52.17 * 0.18 = 9.39 kg
    # Remaining N = 48.0 - 9.39 = 38.61 kg
    # Urea = 38.61 / 0.46 = 83.93 kg/acre
    assert urea.quantity_kg_per_acre == pytest.approx(83.93, abs=0.5)

    # MOP supplies 60% K2O -> MOP = 16 / 0.60 = 26.67 kg/acre
    assert mop.quantity_kg_per_acre == pytest.approx(26.67, abs=0.1)


def test_field_level_calculation_scaling():
    area = 2.5
    plan = calculate_fertilizer_plan(crop_name="Rice", target_n_kg_per_acre=50.0, field_area_acres=area)
    assert plan.field_area_acres == area
    assert plan.nutrient_requirements.total_field_nitrogen_kg == pytest.approx(50.0 * area, abs=0.1)
    assert plan.nutrient_requirements.total_field_phosphorus_kg == pytest.approx(24.0 * area, abs=0.1)
    assert plan.nutrient_requirements.total_field_potassium_kg == pytest.approx(20.0 * area, abs=0.1)

    for fert in plan.commercial_fertilizers:
        assert fert.quantity_kg_total == pytest.approx(fert.quantity_kg_per_acre * area, abs=0.1)


def test_multiple_field_sizes():
    for area in [0.5, 1.0, 3.0, 10.0]:
        plan = calculate_fertilizer_plan(crop_name="Cotton", target_n_kg_per_acre=60.0, field_area_acres=area)
        assert plan.field_area_acres == area
        assert plan.nutrient_requirements.total_field_nitrogen_kg == pytest.approx(60.0 * area, abs=0.1)


def test_application_schedule_split_math():
    plan = calculate_fertilizer_plan(crop_name="Maize", target_n_kg_per_acre=45.0, field_area_acres=2.0)
    basal = plan.application_schedule[0]
    td1 = plan.application_schedule[1]
    td2 = plan.application_schedule[2]

    # Sum of stage totals equals sum of all commercial products
    total_products_kg = sum(f.quantity_kg_total for f in plan.commercial_fertilizers)
    total_schedule_kg = basal.total_kg + td1.total_kg + td2.total_kg
    assert total_schedule_kg == pytest.approx(total_products_kg, abs=0.1)


def test_soil_nitrogen_adjustment():
    # Low soil N -> N increased by 10%
    plan_low = calculate_fertilizer_plan(crop_name="Wheat", target_n_kg_per_acre=50.0, soil_nitrogen_mg_kg=20.0)
    assert plan_low.nutrient_requirements.nitrogen_kg_per_acre == pytest.approx(55.0, abs=0.1)

    # High soil N -> N decreased by 10%
    plan_high = calculate_fertilizer_plan(crop_name="Wheat", target_n_kg_per_acre=50.0, soil_nitrogen_mg_kg=70.0)
    assert plan_high.nutrient_requirements.nitrogen_kg_per_acre == pytest.approx(45.0, abs=0.1)
