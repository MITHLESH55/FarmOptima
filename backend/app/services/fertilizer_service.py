"""
Agronomic Fertilizer Breakdown Service for FarmOptima.

Computes explicit N-P-K nutrient requirements, converts elemental nutrient needs
into commercial fertilizer products (DAP, Urea, MOP), performs field-level scaling
(per acre vs. total field requirement), and builds a split application schedule.
"""

from __future__ import annotations
import math
from app.crop_database import CROP_DATABASE
from app.schemas.recommendation import (
    FertilizerPlan,
    NutrientRequirements,
    CommercialFertilizerItem,
    ApplicationStageItem,
)


def calculate_fertilizer_plan(
    crop_name: str,
    target_n_kg_per_acre: float,
    soil_nitrogen_mg_kg: float | None = None,
    field_area_acres: float = 1.0,
) -> FertilizerPlan:
    """
    Calculate structured agronomic fertilizer plan for a selected crop and field area.
    
    - DAP (18% N, 46% P₂O₅) supplies Phosphorus and part of Nitrogen.
    - Urea (46% N) supplies remaining Nitrogen.
    - MOP (60% K₂O) supplies Potassium.
    """
    crop_info = CROP_DATABASE.get(crop_name, CROP_DATABASE.get("Wheat", {}))

    # Base requirements
    base_n = (
        float(target_n_kg_per_acre)
        if target_n_kg_per_acre is not None and target_n_kg_per_acre > 0
        else float(crop_info.get("fertilizer_n_kg_per_acre", 45.0))
    )
    base_p = float(crop_info.get("fertilizer_p_kg_per_acre", 24.0))
    base_k = float(crop_info.get("fertilizer_k_kg_per_acre", 16.0))

    # Soil Nitrogen adjustment if soil test is available
    soil_adj = 1.0
    if soil_nitrogen_mg_kg is not None and soil_nitrogen_mg_kg > 0:
        if soil_nitrogen_mg_kg < 30.0:
            soil_adj = 1.10  # Low soil N -> increase N by 10%
        elif soil_nitrogen_mg_kg > 60.0:
            soil_adj = 0.90  # High soil N -> decrease N by 10%

    n_per_acre = round(base_n * soil_adj, 2)
    p_per_acre = round(base_p, 2)
    k_per_acre = round(base_k, 2)

    area = max(0.01, float(field_area_acres))

    total_n = round(n_per_acre * area, 2)
    total_p = round(p_per_acre * area, 2)
    total_k = round(k_per_acre * area, 2)

    nutrients = NutrientRequirements(
        nitrogen_kg_per_acre=n_per_acre,
        phosphorus_kg_per_acre=p_per_acre,
        potassium_kg_per_acre=k_per_acre,
        total_field_nitrogen_kg=total_n,
        total_field_phosphorus_kg=total_p,
        total_field_potassium_kg=total_k,
    )

    # 1. DAP (18% N, 46% P₂O₅)
    # P₂O₅ needed = p_per_acre. DAP needed = p_per_acre / 0.46
    dap_per_acre = round(p_per_acre / 0.46, 2)
    dap_total = round(dap_per_acre * area, 2)
    n_from_dap_per_acre = dap_per_acre * 0.18

    # 2. Urea (46% N)
    # Remaining N needed = max(0, n_per_acre - n_from_dap)
    remaining_n_per_acre = max(0.0, n_per_acre - n_from_dap_per_acre)
    urea_per_acre = round(remaining_n_per_acre / 0.46, 2)
    urea_total = round(urea_per_acre * area, 2)

    # 3. MOP (60% K₂O)
    # K₂O needed = k_per_acre. MOP needed = k_per_acre / 0.60
    mop_per_acre = round(k_per_acre / 0.60, 2)
    mop_total = round(mop_per_acre * area, 2)

    commercial_fertilizers = [
        CommercialFertilizerItem(
            name="DAP (Diammonium Phosphate)",
            composition="18% N, 46% P₂O₅",
            quantity_kg_per_acre=dap_per_acre,
            quantity_kg_total=dap_total,
            application_stage="Basal (at sowing/transplanting)",
        ),
        CommercialFertilizerItem(
            name="Urea",
            composition="46% N",
            quantity_kg_per_acre=urea_per_acre,
            quantity_kg_total=urea_total,
            application_stage="Split: 50% Basal, 25% Top Dressing 1, 25% Top Dressing 2",
        ),
        CommercialFertilizerItem(
            name="MOP (Muriate of Potash)",
            composition="60% K₂O",
            quantity_kg_per_acre=mop_per_acre,
            quantity_kg_total=mop_total,
            application_stage="Basal (at sowing/transplanting)",
        ),
    ]

    # Application Schedule Breakdown (Total field quantities in kg)
    urea_basal = round(urea_total * 0.50, 2)
    urea_td1 = round(urea_total * 0.25, 2)
    urea_td2 = round(urea_total * 0.25, 2)

    schedule = [
        ApplicationStageItem(
            stage="Basal (Sowing / Transplanting)",
            dap_kg=dap_total,
            urea_kg=urea_basal,
            mop_kg=mop_total,
            total_kg=round(dap_total + urea_basal + mop_total, 2),
        ),
        ApplicationStageItem(
            stage="First Top Dressing (21-30 Days)",
            dap_kg=0.0,
            urea_kg=urea_td1,
            mop_kg=0.0,
            total_kg=urea_td1,
        ),
        ApplicationStageItem(
            stage="Second Top Dressing (40-50 Days)",
            dap_kg=0.0,
            urea_kg=urea_td2,
            mop_kg=0.0,
            total_kg=urea_td2,
        ),
    ]

    explanation = (
        f"For {crop_name} on {area:.1f} acre(s), total nutrient requirement is "
        f"{n_per_acre:.1f} kg/acre N, {p_per_acre:.1f} kg/acre P₂O₅, and {k_per_acre:.1f} kg/acre K₂O. "
        f"Phosphorus is supplied via DAP ({dap_total:.1f} kg total), which also contributes {n_from_dap_per_acre * area:.1f} kg N. "
        f"Remaining Nitrogen is supplied via Urea ({urea_total:.1f} kg total). "
        f"Potassium is supplied via MOP ({mop_total:.1f} kg total). "
        f"All DAP and MOP with 50% Urea are applied basal; remaining Urea is split into two equal top dressings to maximize nutrient absorption efficiency."
    )

    return FertilizerPlan(
        crop=crop_name,
        field_area_acres=area,
        nutrient_requirements=nutrients,
        commercial_fertilizers=commercial_fertilizers,
        application_schedule=schedule,
        explanation=explanation,
    )
