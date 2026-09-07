"""
Targeted Regression Test Suite for NSGA-II / Optimizer Convergence History Integrity.

Verifies:
  1. Convergence history records true continuous multi-objective compromise fitness metrics (not population counts or front size integers like 40/60).
  2. Final convergence history entry matches the returned compromise solution fitness.
  3. Different crops, climates, and locations produce independent, distinct convergence trajectories.
  4. Cross-run isolation: subsequent optimizer executions do not mutate previous results.
"""

import pytest
from app.core.nsga2 import optimize_resources_multiobjective


class TestOptimizerConvergenceIntegrity:
    """Regression test suite for optimizer convergence trajectory integrity."""

    def test_convergence_history_is_true_fitness_not_population_count(self):
        """
        Catches bug where hypervolume_history was appending len(fronts[0]) (e.g. integer 40),
        causing a flatline at the population size in the UI chart.
        """
        pop_size = 40
        generations = 30
        res = optimize_resources_multiobjective(
            crop_water_need_mm=450,
            crop_fert_need_kg_acre=48,
            rainfall_mm_30d=50,
            soil_moisture_pct=20,
            population_size=pop_size,
            generations=generations,
            seed=42,
        )

        assert len(res.hypervolume_history) == generations
        # Values must NOT all be the integer population size (e.g. 40 or 40.0)
        assert not all(val == pop_size for val in res.hypervolume_history)
        
        # Fitness values must be in a realistic fractional error scale (0.0 to 2.0), not >= 10
        assert all(0.0 <= val < 5.0 for val in res.hypervolume_history)
        
        # Final value must match compromise solution fitness
        expected_final = (res.compromise_solution.water_gap ** 2 + res.compromise_solution.fertilizer_gap ** 2) ** 0.5
        assert abs(res.hypervolume_history[-1] - expected_final) < 1e-4

    def test_multi_crop_convergence_independence(self):
        """Different crops with different resource demands must produce distinct convergence curves."""
        # 1. Wheat run
        r_wheat = optimize_resources_multiobjective(
            crop_water_need_mm=450,
            crop_fert_need_kg_acre=48,
            rainfall_mm_30d=40,
            soil_moisture_pct=18,
            generations=40,
            seed=11,
        )
        h_wheat = list(r_wheat.hypervolume_history)

        # 2. Rice run
        r_rice = optimize_resources_multiobjective(
            crop_water_need_mm=1200,
            crop_fert_need_kg_acre=55,
            rainfall_mm_30d=220,
            soil_moisture_pct=35,
            generations=40,
            seed=22,
        )
        h_rice = list(r_rice.hypervolume_history)

        # 3. Maize run
        r_maize = optimize_resources_multiobjective(
            crop_water_need_mm=550,
            crop_fert_need_kg_acre=45,
            rainfall_mm_30d=80,
            soil_moisture_pct=24,
            generations=40,
            seed=33,
        )
        h_maize = list(r_maize.hypervolume_history)

        # Confirm trajectories are distinct
        assert h_wheat != h_rice
        assert h_rice != h_maize
        assert h_wheat != h_maize

        # Ensure no cross-run mutation
        assert r_wheat.hypervolume_history == h_wheat
        assert r_rice.hypervolume_history == h_rice
        assert r_maize.hypervolume_history == h_maize

    def test_multi_location_convergence_independence(self):
        """Different agro-climatic locations produce independent convergence curves."""
        # Location A: Karnal (Semi-arid, low rainfall)
        r_karnal = optimize_resources_multiobjective(
            crop_water_need_mm=500,
            crop_fert_need_kg_acre=20,
            rainfall_mm_30d=25.0,
            soil_moisture_pct=15.0,
            generations=30,
            seed=101,
        )

        # Location B: Belagavi (Sub-humid, moderate rainfall)
        r_belagavi = optimize_resources_multiobjective(
            crop_water_need_mm=500,
            crop_fert_need_kg_acre=20,
            rainfall_mm_30d=140.0,
            soil_moisture_pct=32.0,
            generations=30,
            seed=202,
        )

        # Location C: Mandya (Irrigated zone, high soil moisture)
        r_mandya = optimize_resources_multiobjective(
            crop_water_need_mm=500,
            crop_fert_need_kg_acre=20,
            rainfall_mm_30d=75.0,
            soil_moisture_pct=28.0,
            generations=30,
            seed=303,
        )

        assert r_karnal.hypervolume_history != r_belagavi.hypervolume_history
        assert r_belagavi.hypervolume_history != r_mandya.hypervolume_history
        assert len(r_karnal.hypervolume_history) == 30
        assert len(r_belagavi.hypervolume_history) == 30
        assert len(r_mandya.hypervolume_history) == 30
