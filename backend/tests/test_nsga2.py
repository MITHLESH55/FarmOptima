from app.core.nsga2 import (
    optimize_resources_multiobjective, _dominates, _fast_non_dominated_sort, _crowding_distance,
)


def test_dominates_basic_cases():
    assert _dominates((1, 1, 1), (2, 2, 2))       # strictly better in all
    assert _dominates((1, 2, 2), (1, 2, 3))       # equal in some, better in one
    assert not _dominates((1, 2, 3), (1, 2, 3))   # identical -> no domination
    assert not _dominates((2, 1, 1), (1, 2, 2))   # mixed -> neither dominates


def test_fast_non_dominated_sort_identifies_correct_front():
    # obj 0 dominates everything, obj 1 and 2 are mutually non-dominated, obj 3 is dominated by all
    objs = [(1, 1, 1), (2, 0, 1), (0, 2, 1), (3, 3, 3)]
    fronts = _fast_non_dominated_sort(objs)
    assert 0 in fronts[0]
    assert 3 not in fronts[0]
    assert 3 == fronts[-1][0]


def test_crowding_distance_gives_infinite_to_boundary_points():
    objs = [(0, 5), (1, 4), (2, 3), (3, 2), (4, 1)]
    front = [0, 1, 2, 3, 4]
    cd = _crowding_distance(objs, front)
    assert cd[0] == float("inf")
    assert cd[4] == float("inf")
    # interior points should have finite, non-negative distance
    assert all(cd[i] >= 0 for i in [1, 2, 3])


def test_nsga2_produces_nonempty_pareto_front_within_bounds():
    result = optimize_resources_multiobjective(
        crop_water_need_mm=450, crop_fert_need_kg_acre=48,
        rainfall_mm_30d=50, soil_moisture_pct=20,
        population_size=30, generations=25, seed=1,
        water_bounds=(300, 1000), fert_bounds=(10, 60),
    )
    assert len(result.pareto_front) >= 1
    for sol in result.pareto_front:
        assert 300 <= sol.water_liters_per_week <= 1000
        assert 10 <= sol.fertilizer_kg_per_acre <= 60


def test_nsga2_pareto_front_is_actually_non_dominated():
    result = optimize_resources_multiobjective(
        crop_water_need_mm=450, crop_fert_need_kg_acre=48,
        rainfall_mm_30d=50, soil_moisture_pct=20,
        population_size=30, generations=30, seed=2,
    )
    objs = [(s.water_gap, s.fertilizer_gap, s.resource_cost) for s in result.pareto_front]
    # No solution in the returned front should dominate another
    for i in range(len(objs)):
        for j in range(len(objs)):
            if i != j:
                assert not _dominates(objs[i], objs[j]), "Front is not truly non-dominated"


def test_nsga2_compromise_solution_is_member_of_front():
    result = optimize_resources_multiobjective(
        crop_water_need_mm=450, crop_fert_need_kg_acre=48,
        rainfall_mm_30d=50, soil_moisture_pct=20,
        population_size=30, generations=25, seed=3,
    )
    assert result.compromise_solution in result.pareto_front


def test_nsga2_deterministic_given_same_seed():
    kwargs = dict(
        crop_water_need_mm=550, crop_fert_need_kg_acre=45,
        rainfall_mm_30d=80, soil_moisture_pct=25,
        population_size=20, generations=20, seed=7,
    )
    r1 = optimize_resources_multiobjective(**kwargs)
    r2 = optimize_resources_multiobjective(**kwargs)
    assert r1.compromise_solution.water_liters_per_week == r2.compromise_solution.water_liters_per_week
    assert r1.compromise_solution.fertilizer_kg_per_acre == r2.compromise_solution.fertilizer_kg_per_acre
