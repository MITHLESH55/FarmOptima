from app.core.gpo import optimize_resources, _fitness


def test_fitness_decreases_when_supply_matches_need_exactly():
    # If irrigation alone exactly meets the crop's water need with no
    # rainfall/soil contribution, the water gap term should be near zero.
    season_weeks = 16
    crop_water_need_mm = 450
    required_liters = crop_water_need_mm * 4046.86
    water_l_week = required_liters / season_weeks

    cost_exact = _fitness(
        water_l_week, fert_kg_acre=48, season_weeks=season_weeks,
        crop_water_need_mm=crop_water_need_mm, crop_fert_need_kg_acre=48,
        rainfall_mm_30d=0, soil_moisture_pct=0,
    )
    cost_way_off = _fitness(
        water_l_week * 3, fert_kg_acre=200, season_weeks=season_weeks,
        crop_water_need_mm=crop_water_need_mm, crop_fert_need_kg_acre=48,
        rainfall_mm_30d=0, soil_moisture_pct=0,
    )
    assert cost_exact < cost_way_off


def test_optimizer_converges_to_lower_fitness_over_generations():
    result = optimize_resources(
        crop_water_need_mm=450, crop_fert_need_kg_acre=48,
        rainfall_mm_30d=50, soil_moisture_pct=20,
        population_size=30, generations=40, seed=42,
    )
    # Fitness history should be non-increasing (elitism guarantees this)
    for i in range(1, len(result.fitness_history)):
        assert result.fitness_history[i] <= result.fitness_history[i - 1] + 1e-9
    # Final fitness should be meaningfully better than the first generation's
    assert result.fitness_history[-1] < result.fitness_history[0]


def test_optimizer_respects_bounds():
    water_bounds = (300, 1000)
    fert_bounds = (10, 60)
    result = optimize_resources(
        crop_water_need_mm=450, crop_fert_need_kg_acre=48,
        rainfall_mm_30d=50, soil_moisture_pct=20,
        population_size=20, generations=20, seed=1,
        water_bounds=water_bounds, fert_bounds=fert_bounds,
    )
    assert water_bounds[0] <= result.best_water_liters_per_week <= water_bounds[1]
    assert fert_bounds[0] <= result.best_fertilizer_kg_per_acre <= fert_bounds[1]


def test_optimizer_is_deterministic_given_same_seed():
    kwargs = dict(
        crop_water_need_mm=550, crop_fert_need_kg_acre=45,
        rainfall_mm_30d=80, soil_moisture_pct=25,
        population_size=20, generations=25, seed=7,
    )
    r1 = optimize_resources(**kwargs)
    r2 = optimize_resources(**kwargs)
    assert r1.best_water_liters_per_week == r2.best_water_liters_per_week
    assert r1.best_fertilizer_kg_per_acre == r2.best_fertilizer_kg_per_acre
