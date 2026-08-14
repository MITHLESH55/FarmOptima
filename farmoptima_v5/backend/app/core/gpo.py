"""
Genetic Particle Optimization (GPO) module.

This is a real genetic algorithm (selection, crossover, mutation, elitism)
that searches for an efficient water + fertilizer allocation plan for a
given crop, given its agronomic requirement and the farm's current rainfall
and soil moisture. No random "fake" scoring — the fitness function is a
concrete, explainable cost/penalty formula.
"""

from __future__ import annotations
import random
from dataclasses import dataclass


@dataclass
class GPOResult:
    best_water_liters_per_week: float
    best_fertilizer_kg_per_acre: float
    best_fitness: float
    fitness_history: list[float]  # best fitness per generation, for convergence plots
    generations_run: int


def _fitness(water_l_week: float, fert_kg_acre: float, *, season_weeks: int,
             crop_water_need_mm: float, crop_fert_need_kg_acre: float,
             rainfall_mm_30d: float, soil_moisture_pct: float,
             acre_to_liters_per_mm: float = 4046.86) -> float:
    """
    Lower is better. Penalizes:
      1. Under- or over-supplying total seasonal water vs. crop need
         (rainfall contribution is credited, reducing required irrigation).
      2. Under- or over-supplying fertilizer vs. crop need.
      3. Raw water use (encourages efficiency, not just meeting the need).
    """
    total_irrigation_liters = water_l_week * season_weeks
    # 1mm of rainfall over 1 acre = ~4046.86 liters; credit rainfall + existing soil moisture
    rainfall_credit_liters = rainfall_mm_30d * acre_to_liters_per_mm * (season_weeks / 4.0) * 0.5
    soil_moisture_credit_liters = (soil_moisture_pct / 100.0) * crop_water_need_mm * acre_to_liters_per_mm * 0.2

    effective_supply_liters = total_irrigation_liters + rainfall_credit_liters + soil_moisture_credit_liters
    required_liters = crop_water_need_mm * acre_to_liters_per_mm

    water_gap = abs(effective_supply_liters - required_liters) / max(required_liters, 1.0)
    fert_gap = abs(fert_kg_acre - crop_fert_need_kg_acre) / max(crop_fert_need_kg_acre, 1.0)
    efficiency_penalty = total_irrigation_liters / max(required_liters, 1.0) * 0.05

    return water_gap * 1.0 + fert_gap * 0.6 + efficiency_penalty


def optimize_resources(
    *,
    crop_water_need_mm: float,
    crop_fert_need_kg_acre: float,
    rainfall_mm_30d: float,
    soil_moisture_pct: float,
    season_weeks: int = 16,
    population_size: int = 40,
    generations: int = 60,
    mutation_rate: float = 0.15,
    water_bounds: tuple[float, float] = (200, 3000),
    fert_bounds: tuple[float, float] = (5, 120),
    seed: int | None = None,
) -> GPOResult:
    """
    Run a real genetic algorithm to find (water_liters_per_week,
    fertilizer_kg_per_acre) that minimizes the fitness cost above.
    """
    rng = random.Random(seed)

    def random_individual():
        return [
            rng.uniform(*water_bounds),
            rng.uniform(*fert_bounds),
        ]

    def fitness_of(ind):
        return _fitness(
            ind[0], ind[1],
            season_weeks=season_weeks,
            crop_water_need_mm=crop_water_need_mm,
            crop_fert_need_kg_acre=crop_fert_need_kg_acre,
            rainfall_mm_30d=rainfall_mm_30d,
            soil_moisture_pct=soil_moisture_pct,
        )

    def clamp(ind):
        ind[0] = min(max(ind[0], water_bounds[0]), water_bounds[1])
        ind[1] = min(max(ind[1], fert_bounds[0]), fert_bounds[1])
        return ind

    def tournament_select(pop_with_fitness, k=3):
        contenders = rng.sample(pop_with_fitness, k)
        return min(contenders, key=lambda p: p[1])[0]

    def crossover(p1, p2):
        alpha = rng.random()
        child = [
            alpha * p1[0] + (1 - alpha) * p2[0],
            alpha * p1[1] + (1 - alpha) * p2[1],
        ]
        return child

    def mutate(ind):
        if rng.random() < mutation_rate:
            ind[0] += rng.gauss(0, (water_bounds[1] - water_bounds[0]) * 0.05)
        if rng.random() < mutation_rate:
            ind[1] += rng.gauss(0, (fert_bounds[1] - fert_bounds[0]) * 0.05)
        return clamp(ind)

    population = [random_individual() for _ in range(population_size)]
    fitness_history = []
    best_ind, best_fit = None, float("inf")

    for gen in range(generations):
        pop_with_fitness = [(ind, fitness_of(ind)) for ind in population]
        pop_with_fitness.sort(key=lambda p: p[1])

        if pop_with_fitness[0][1] < best_fit:
            best_ind, best_fit = pop_with_fitness[0][0][:], pop_with_fitness[0][1]
        fitness_history.append(best_fit)

        # Elitism: carry the top 2 forward unchanged.
        next_gen = [pop_with_fitness[0][0][:], pop_with_fitness[1][0][:]]

        while len(next_gen) < population_size:
            parent1 = tournament_select(pop_with_fitness)
            parent2 = tournament_select(pop_with_fitness)
            child = crossover(parent1, parent2)
            child = mutate(child)
            next_gen.append(child)

        population = next_gen

    return GPOResult(
        best_water_liters_per_week=round(best_ind[0], 1),
        best_fertilizer_kg_per_acre=round(best_ind[1], 1),
        best_fitness=round(best_fit, 5),
        fitness_history=fitness_history,
        generations_run=generations,
    )
