# FarmOptima — Backend (Layered Architecture)

Built backend-first, following a proper layered structure so every new
piece (a data source, an algorithm, a route) has exactly one place to
live. Everything below is real and tested — 16 passing unit tests plus a
verified live smoke test of every endpoint.

## Architecture

```
backend/
├── app/
│   ├── main.py                    Thin entry point: wiring only
│   ├── config.py                  Settings from .env (pydantic-settings)
│   ├── database.py                SQLAlchemy engine/session (SQLite by default)
│   │
│   ├── models/                    Database tables (SQLAlchemy ORM)
│   │   ├── farm.py                Saved farm locations
│   │   └── recommendation.py      Every /recommend run, persisted for audit
│   │
│   ├── schemas/                   Request/response validation (Pydantic)
│   │   ├── common.py
│   │   ├── recommendation.py
│   │   └── data_sources.py
│   │
│   ├── api/
│   │   ├── router.py              Aggregates all route modules
│   │   └── routes/                One file per resource — thin HTTP handlers
│   │       ├── weather.py
│   │       ├── soil.py
│   │       ├── satellite.py
│   │       ├── recommend.py       Orchestrates the full pipeline + persists it
│   │       └── farms.py
│   │
│   ├── services/                  Business logic — calls external APIs
│   │   ├── weather_service.py     NASA POWER (real API)
│   │   ├── soil_service.py        SoilGrids (real API)
│   │   ├── satellite_service.py   NDVI math + Google Earth Engine
│   │   ├── market_service.py      CSV-based market price ingestion
│   │   └── explanation_service.py Templated explanation (LLM slot for Phase 4)
│   │
│   ├── core/                      Pure algorithms — no I/O, fully unit-testable
│   │   ├── mcdm.py                Real AHP, TOPSIS, ELECTRE
│   │   ├── gpo.py                 Real genetic algorithm
│   │   └── criteria.py            Builds the decision matrix from real data
│   │
│   ├── crop_database.py           Agronomic reference data
│   └── utils/
│       ├── logging_config.py      One place to configure logging
│       ├── exceptions.py          Custom exception types
│       └── responses.py           Standard error envelope
│
├── tests/                          16 tests, all independent of live APIs
├── data/market_prices.csv
├── requirements.txt
└── .env.example
```

## Why this layering

- **`core/` has zero I/O.** AHP, TOPSIS, ELECTRE, and the genetic algorithm
  are pure functions — no network calls, no database. This is exactly why
  they're fully unit-testable without internet access, and it's the
  cleanest thing to point to when explaining your algorithm's correctness
  in a viva or patent filing.
- **`services/` owns every external call.** Each data source (weather,
  soil, satellite, market) has its own file, its own real API integration,
  and its own honest mock fallback. Swapping a data source, or adding a
  new one, never touches a route or the algorithm layer.
- **`api/routes/` is deliberately thin.** Routes only orchestrate — they
  call services and core functions, then return. No business logic lives
  in a route file.
- **`models/` vs `schemas/`** — a common professional distinction:
  `models/` are database tables (SQLAlchemy), `schemas/` are API
  input/output validation (Pydantic). They often look similar but serve
  different jobs — the DB shape and the API shape are allowed to evolve
  independently.
- **Every error looks the same to a client**, regardless of where it was
  raised — see `utils/exceptions.py` + the handlers in `main.py`. This is
  what "standard API response format" means in practice: predictable
  errors, typed and fully-documented successes (via FastAPI's
  `response_model`, visible at `/docs`).

## Running it

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs — every route (`/api/weather`,
`/api/soil`, `/api/satellite`, `/api/recommend`, `/api/farms`) is there,
fully documented, testable with the "Try it out" button. No Postman needed.

Run the algorithm test suite (works with zero internet access):
```bash
pytest -v
```

## Database

SQLite by default — a `farmoptima.db` file appears the first time you run
the app, no setup required. Every `/api/recommend` call is saved to the
`recommendations` table (full JSON result included), and `/api/farms`
lets you save/list named locations. To move to PostgreSQL later, just set
`DATABASE_URL` in `.env` to a `postgresql://...` connection string —
nothing else in the codebase changes, since all queries go through
SQLAlchemy's ORM.

**Why this matters for your report:** you can now query the
`recommendations` table directly to produce your Chapter 7 validation
evidence — e.g. "here are the 12 test locations we ran, here's what each
one recommended, here's which data sources were live vs. mock for each" —
instead of relying on screenshots.

## Week-by-week build order (as followed)

| Week | Focus |
|---|---|
| 1 | FastAPI setup, config, database, logging, error handling, Swagger |
| 2 | Weather service + route, Soil service + route |
| 3 | Satellite service + route (Google Earth Engine slot) |
| 4 | Farms persistence, Recommendation persistence |
| 5+ | MCDM (done), GPO (done), frontend integration, LLM explanation |

## Advanced algorithms (this revision)

Two upgrades over the Phase-1 baseline, both real, tested, and wired into
`/api/recommend`:

- **Fuzzy AHP** (`core/fuzzy_ahp.py`, Chang's 1996 extent analysis) —
  replaces crisp Saaty-scale pairwise comparisons with triangular fuzzy
  numbers, so criteria weighting reflects genuine expert uncertainty
  ("climate is moderately-to-strongly more important") instead of forcing
  a single crisp number. The crisp AHP Consistency Ratio is still reported
  as a diagnostic on the underlying judgment matrix.
- **NSGA-II** (`core/nsga2.py`) — replaces the single-objective GPO with a
  real multi-objective genetic algorithm (fast non-dominated sorting +
  crowding distance, per Deb et al. 2002) optimizing three simultaneously
  conflicting objectives: water gap, fertilizer gap, and resource cost.
  The API returns the full Pareto front (`resource_plan.pareto_front`)
  plus one "compromise" pick (minimum distance to the ideal point across
  normalized objectives) for the dashboard.

**Honest caveat:** `water_cost_per_liter` and `fert_cost_per_kg` in
`nsga2.py` are placeholder values (₹0.05/L, ₹25/kg) — replace these with
real local tariffs/prices for your target region before treating the
`resource_cost` objective (or the compromise solution) as meaningful.

The old single-objective GPO (`core/gpo.py`) and crisp AHP
(`core/mcdm.py::ahp_weights`) are kept and still tested — they're valuable
as an ablation-study baseline in your report ("here's what crisp AHP +
single-objective GA gives vs. fuzzy AHP + NSGA-II, on the same input").

## Reliability (this revision)

`tests/test_integration_api.py` and `tests/test_auth.py` add real
integration tests — going through the actual FastAPI app, routing,
dependency injection, and an isolated temporary SQLite database, with
external services (weather/soil/satellite) mocked at the import point via
`monkeypatch`. This is different from the algorithm unit tests: it proves
the whole system wires together correctly (auth, persistence, error
handling, the full recommend pipeline) rather than just that individual
functions are correct. 50 tests total, all passing, none requiring
internet access or live credentials.

## Security (this revision)

- **JWT authentication** (`utils/security.py`, `api/deps.py`,
  `api/routes/auth.py`) — `POST /api/auth/register` and
  `POST /api/auth/login` issue a signed JWT; `/api/recommend` and
  `/api/farms` require a valid `Authorization: Bearer <token>` header via
  the `get_current_user` dependency. Passwords are hashed with bcrypt
  (via passlib) — never stored or compared in plaintext.
- **Rate limiting** (`utils/rate_limit.py`, slowapi) — `/api/recommend`
  (the expensive NSGA-II endpoint) is limited via `RECOMMEND_RATE_LIMIT`
  in `.env` (default 20/minute). Verified live: with the limit set to
  3/minute, requests 1-3 returned 200, requests 4-5 returned 429 with the
  standard error envelope.

**Before any real deployment:** generate a real `SECRET_KEY` (see
`.env.example`) — the default is fine for local development only.

## Infra — still queued (not yet built)

Async service calls (httpx), a simple TTL cache for weather/soil/satellite
lookups, a retry policy (tenacity), Docker + docker-compose, and a GitHub
Actions CI workflow running `pytest` on every push. Say "continue" to have
these built next.

## Other next steps

1. Finish Google Earth Engine registration — `provenance.satellite_source`
   will switch from `"mock"` to `"gee-sentinel2"` automatically once
   `GEE_PROJECT` is set in `.env`.
2. Wire a real LLM call into `services/explanation_service.py` (Phase 4).
3. Consider adding Alembic migrations once the schema stabilizes (not
   needed yet — `create_all()` is fine for a single-developer project at
   this stage).
4. Register a real user (not the `dev-only` defaults) and generate a real
   `SECRET_KEY` before ever deploying this outside your own machine.

