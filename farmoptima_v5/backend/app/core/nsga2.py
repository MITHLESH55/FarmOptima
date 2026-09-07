"""
Multi-objective Genetic Particle Optimization (NSGA-II).

Upgrades the single-objective GPO (core/gpo.py) to a real NSGA-II
implementation: fast non-dominated sorting, crowding-distance diversity
preservation, and binary tournament selection by (rank, crowding). This
optimizes THREE simultaneously conflicting objectives instead of one
scalarized cost:

  1. water_gap      — deviation from the crop's true seasonal water need
                       (accounting for rainfall/soil credit)
  2. fertilizer_gap — deviation from the crop's fertilizer need
  3. resource_cost   — the monetary cost of the water + fertilizer used

Minimizing (1) and (2) exactly often means USING more resources than the
cheapest option, which increases (3) — this is a genuine trade-off, not a
restated single objective, which is what makes this multi-objective (not
just multi-term) and is the actual algorithmic contribution over the
Phase-1 single-objective GPO.

Reference algorithm: Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T.
(2002). "A fast and elitist multiobjective genetic algorithm: NSGA-II."
IEEE Transactions on Evolutionary Computation, 6(2), 182-197.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field

ACRE_TO_LITERS_PER_MM = 4046.86


@dataclass
class ParetoSolution:
    water_liters_per_week: float
    fertilizer_kg_per_acre: float
    water_gap: float
    fertilizer_gap: float
    resource_cost: float
    rank: int = 0
    crowding_distance: float = 0.0


@dataclass
class NSGA2Result:
    pareto_front: list[ParetoSolution]     # rank-0, non-dominated solutions
    compromise_solution: ParetoSolution     # single "recommended" pick from the front
    generations_run: int
    hypervolume_history: list[float]        # best compromise fitness per generation, for convergence plots


def _objectives(
    water_l_week: float, fert_kg_acre: float, *, season_weeks: int,
    crop_water_need_mm: float, crop_fert_need_kg_acre: float,
    rainfall_mm_30d: float, soil_moisture_pct: float,
    water_cost_per_liter: float, fert_cost_per_kg: float,
) -> tuple[float, float, float]:
    total_irrigation_liters = water_l_week * season_weeks
    rainfall_credit_liters = rainfall_mm_30d * ACRE_TO_LITERS_PER_MM * (season_weeks / 4.0) * 0.5
    soil_moisture_credit_liters = (soil_moisture_pct / 100.0) * crop_water_need_mm * ACRE_TO_LITERS_PER_MM * 0.2
    effective_supply = total_irrigation_liters + rainfall_credit_liters + soil_moisture_credit_liters
    required_liters = crop_water_need_mm * ACRE_TO_LITERS_PER_MM

    water_gap = abs(effective_supply - required_liters) / max(required_liters, 1.0)
    fert_gap = abs(fert_kg_acre - crop_fert_need_kg_acre) / max(crop_fert_need_kg_acre, 1.0)
    resource_cost = total_irrigation_liters * water_cost_per_liter + fert_kg_acre * fert_cost_per_kg

    return water_gap, fert_gap, resource_cost


def _dominates(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    """a dominates b if a is no worse in all objectives and strictly better in at least one (minimization)."""
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def _fast_non_dominated_sort(objs: list[tuple[float, float, float]]) -> list[list[int]]:
    n = len(objs)
    dominated_by = [[] for _ in range(n)]   # indices this individual dominates
    domination_count = [0] * n              # how many individuals dominate this one
    fronts: list[list[int]] = [[]]

    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if _dominates(objs[p], objs[q]):
                dominated_by[p].append(q)
            elif _dominates(objs[q], objs[p]):
                domination_count[p] += 1
        if domination_count[p] == 0:
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        next_front = []
        for p in fronts[i]:
            for q in dominated_by[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    next_front.append(q)
        i += 1
        fronts.append(next_front)
    fronts.pop()  # last appended front is always empty
    return fronts


def _crowding_distance(objs: list[tuple[float, float, float]], front: list[int]) -> dict[int, float]:
    distance = {i: 0.0 for i in front}
    if len(front) <= 2:
        for i in front:
            distance[i] = float("inf")
        return distance

    num_objectives = len(objs[0])
    for m in range(num_objectives):
        front_sorted = sorted(front, key=lambda i: objs[i][m])
        distance[front_sorted[0]] = float("inf")
        distance[front_sorted[-1]] = float("inf")
        obj_min = objs[front_sorted[0]][m]
        obj_max = objs[front_sorted[-1]][m]
        obj_range = max(obj_max - obj_min, 1e-9)
        for k in range(1, len(front_sorted) - 1):
            prev_val = objs[front_sorted[k - 1]][m]
            next_val = objs[front_sorted[k + 1]][m]
            distance[front_sorted[k]] += (next_val - prev_val) / obj_range
    return distance


def optimize_resources_multiobjective(
    *,
    crop_water_need_mm: float,
    crop_fert_need_kg_acre: float,
    rainfall_mm_30d: float,
    soil_moisture_pct: float,
    season_weeks: int = 16,
    population_size: int = 60,
    generations: int = 80,
    mutation_rate: float = 0.15,
    water_bounds: tuple[float, float] = (200, 3000),
    fert_bounds: tuple[float, float] = (5, 120),
    water_cost_per_liter: float = 0.05,   # INR per liter, adjust to local tariffs
    fert_cost_per_kg: float = 25.0,       # INR per kg, adjust to local prices
    seed: int | None = None,
) -> NSGA2Result:
    rng = random.Random(seed)

    def random_individual():
        return [rng.uniform(*water_bounds), rng.uniform(*fert_bounds)]

    def clamp(ind):
        ind[0] = min(max(ind[0], water_bounds[0]), water_bounds[1])
        ind[1] = min(max(ind[1], fert_bounds[0]), fert_bounds[1])
        return ind

    def evaluate(ind):
        return _objectives(
            ind[0], ind[1], season_weeks=season_weeks,
            crop_water_need_mm=crop_water_need_mm, crop_fert_need_kg_acre=crop_fert_need_kg_acre,
            rainfall_mm_30d=rainfall_mm_30d, soil_moisture_pct=soil_moisture_pct,
            water_cost_per_liter=water_cost_per_liter, fert_cost_per_kg=fert_cost_per_kg,
        )

    def sbx_crossover(p1, p2, eta=15):
        child = []
        for x1, x2 in zip(p1, p2):
            if rng.random() <= 0.5 and abs(x1 - x2) > 1e-12:
                u = rng.random()
                beta = (2 * u) ** (1 / (eta + 1)) if u <= 0.5 else (1 / (2 * (1 - u))) ** (1 / (eta + 1))
                child.append(0.5 * ((1 + beta) * x1 + (1 - beta) * x2))
            else:
                child.append(x1)
        return child

    def mutate(ind):
        if rng.random() < mutation_rate:
            ind[0] += rng.gauss(0, (water_bounds[1] - water_bounds[0]) * 0.05)
        if rng.random() < mutation_rate:
            ind[1] += rng.gauss(0, (fert_bounds[1] - fert_bounds[0]) * 0.05)
        return clamp(ind)

    def tournament_select(pop, ranks, crowd, k=2):
        contenders = rng.sample(range(len(pop)), k)
        best = contenders[0]
        for c in contenders[1:]:
            if ranks[c] < ranks[best] or (ranks[c] == ranks[best] and crowd[c] > crowd[best]):
                best = c
        return pop[best][:]

    def normalize(vals):
        lo, hi = min(vals), max(vals)
        span = max(hi - lo, 1e-9)
        return [(v - lo) / span for v in vals]

    population = [random_individual() for _ in range(population_size)]
    hypervolume_history = []

    for gen in range(generations):
        objs = [evaluate(ind) for ind in population]
        fronts = _fast_non_dominated_sort(objs)

        ranks = [0] * len(population)
        crowd = [0.0] * len(population)
        for rank_idx, front in enumerate(fronts):
            cd = _crowding_distance(objs, front)
            for i in front:
                ranks[i] = rank_idx
                crowd[i] = cd[i]

        # Generate offspring via tournament selection + SBX crossover + mutation
        offspring = []
        while len(offspring) < population_size:
            parent1 = tournament_select(population, ranks, crowd)
            parent2 = tournament_select(population, ranks, crowd)
            child = mutate(clamp(sbx_crossover(parent1, parent2)))
            offspring.append(child)

        # Combine parent + offspring, then select next generation by rank + crowding (elitism)
        combined = population + offspring
        combined_objs = objs + [evaluate(ind) for ind in offspring]
        combined_fronts = _fast_non_dominated_sort(combined_objs)

        next_population = []
        for front in combined_fronts:
            if len(next_population) + len(front) <= population_size:
                next_population.extend(front)
            else:
                cd = _crowding_distance(combined_objs, front)
                remaining = population_size - len(next_population)
                sorted_front = sorted(front, key=lambda i: cd[i], reverse=True)
                next_population.extend(sorted_front[:remaining])
                break

        population = [combined[i][:] for i in next_population]

        # Evaluate selected population and record its compromise fitness for this generation
        gen_objs = [evaluate(ind) for ind in population]
        gen_fronts = _fast_non_dominated_sort(gen_objs)
        front0_objs = [gen_objs[i] for i in gen_fronts[0]]
        if len(front0_objs) == 1:
            comp_fitness = (front0_objs[0][0] ** 2 + front0_objs[0][1] ** 2) ** 0.5
        else:
            wg = normalize([o[0] for o in front0_objs])
            fg = normalize([o[1] for o in front0_objs])
            cg = normalize([o[2] for o in front0_objs])
            dists = [(wg[k] ** 2 + fg[k] ** 2 + cg[k] ** 2) ** 0.5 for k in range(len(front0_objs))]
            comp_idx = dists.index(min(dists))
            comp_fitness = (front0_objs[comp_idx][0] ** 2 + front0_objs[comp_idx][1] ** 2) ** 0.5
        hypervolume_history.append(round(comp_fitness, 5))

    # Final evaluation for the returned Pareto front
    final_objs = [evaluate(ind) for ind in population]
    final_fronts = _fast_non_dominated_sort(final_objs)
    final_cd = _crowding_distance(final_objs, final_fronts[0])

    pareto_front = [
        ParetoSolution(
            water_liters_per_week=round(population[i][0], 1),
            fertilizer_kg_per_acre=round(population[i][1], 1),
            water_gap=round(final_objs[i][0], 5),
            fertilizer_gap=round(final_objs[i][1], 5),
            resource_cost=round(final_objs[i][2], 2),
            rank=0,
            crowding_distance=final_cd[i] if final_cd[i] != float("inf") else 1e9,
        )
        for i in final_fronts[0]
    ]

    # Compromise pick: minimum distance to the ideal point (min of each objective
    # across the front) after normalization — a standard, explainable way to pick
    # one solution from a Pareto front without arbitrarily favoring one objective.
    def normalize(vals):
        lo, hi = min(vals), max(vals)
        span = max(hi - lo, 1e-9)
        return [(v - lo) / span for v in vals]

    water_gaps = normalize([s.water_gap for s in pareto_front])
    fert_gaps = normalize([s.fertilizer_gap for s in pareto_front])
    costs = normalize([s.resource_cost for s in pareto_front])
    distances = [
        (water_gaps[i] ** 2 + fert_gaps[i] ** 2 + costs[i] ** 2) ** 0.5
        for i in range(len(pareto_front))
    ]
    compromise_idx = distances.index(min(distances))

    return NSGA2Result(
        pareto_front=pareto_front,
        compromise_solution=pareto_front[compromise_idx],
        generations_run=generations,
        hypervolume_history=hypervolume_history,
    )
