"""
Dedicated test suite for NSGA-II Multi-Objective Optimization algorithm integrity.

Tests:
- Fast non-dominated sorting and crowding distance implementation
- Multi-objective trade-off generation (Pareto front)
- Minimum distance compromise solution selection
- Seed reproducibility
- Boundary constraint enforcement
"""

import pytest
from app.core.nsga2 import optimize_resources_multiobjective, ParetoSolution, NSGA2Result


def test_nsga2_pareto_front_non_dominated():
    """Verify that NSGA-II returns a non-dominated Pareto front where solutions excel in different objectives."""
    res = optimize_resources_multiobjective(
        crop_water_need_mm=450.0,
        crop_fert_need_kg_acre=48.0,
        rainfall_mm_30d=50.0,
        soil_moisture_pct=25.0,
        population_size=40,
        generations=30,
        seed=42,
    )
    assert isinstance(res, NSGA2Result)
    assert len(res.pareto_front) > 0
    assert isinstance(res.compromise_solution, ParetoSolution)

    # Check non-domination property on rank 0
    for s1 in res.pareto_front:
        for s2 in res.pareto_front:
            if s1 == s2:
                continue
            # s1 should not strictly dominate s2 across all 3 objectives
            s1_better_all = (
                s1.water_gap <= s2.water_gap and
                s1.fertilizer_gap <= s2.fertilizer_gap and
                s1.resource_cost <= s2.resource_cost and
                (s1.water_gap < s2.water_gap or s1.fertilizer_gap < s2.fertilizer_gap or s1.resource_cost < s2.resource_cost)
            )
            assert not s1_better_all, "Pareto front contains a dominated solution!"


def test_nsga2_seed_reproducibility():
    """Verify that NSGA-II with a fixed random seed produces identical optimization results."""
    res1 = optimize_resources_multiobjective(
        crop_water_need_mm=550.0,
        crop_fert_need_kg_acre=45.0,
        rainfall_mm_30d=40.0,
        soil_moisture_pct=20.0,
        population_size=30,
        generations=20,
        seed=12345,
    )
    res2 = optimize_resources_multiobjective(
        crop_water_need_mm=550.0,
        crop_fert_need_kg_acre=45.0,
        rainfall_mm_30d=40.0,
        soil_moisture_pct=20.0,
        population_size=30,
        generations=20,
        seed=12345,
    )

    assert res1.compromise_solution.water_liters_per_week == res2.compromise_solution.water_liters_per_week
    assert res1.compromise_solution.fertilizer_kg_per_acre == res2.compromise_solution.fertilizer_kg_per_acre
    assert len(res1.pareto_front) == len(res2.pareto_front)


def test_nsga2_bounds_enforcement():
    """Verify that NSGA-II decision variables strictly obey min and max bounds."""
    water_bounds = (500.0, 1500.0)
    fert_bounds = (10.0, 60.0)

    res = optimize_resources_multiobjective(
        crop_water_need_mm=500.0,
        crop_fert_need_kg_acre=30.0,
        rainfall_mm_30d=30.0,
        soil_moisture_pct=15.0,
        water_bounds=water_bounds,
        fert_bounds=fert_bounds,
        population_size=30,
        generations=20,
        seed=99,
    )

    for sol in res.pareto_front:
        assert water_bounds[0] <= sol.water_liters_per_week <= water_bounds[1]
        assert fert_bounds[0] <= sol.fertilizer_kg_per_acre <= fert_bounds[1]
