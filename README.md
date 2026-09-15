# FarmOptima

**Precision Agriculture Decision Support & Multi-Objective Resource Optimization**

FarmOptima is a location-aware agricultural decision-support platform that combines environmental data, soil information, satellite/GIS analysis, agronomic knowledge, **Multi-Criteria Decision Making (MCDM)**, and **multi-objective optimization** to support crop selection and farm-resource planning.

The system is built around two core questions:

> **Which crop is most suitable for this farm?**
> **How can water and fertilizer resources be planned efficiently for that crop?**

FarmOptima brings together real-world data sources, agronomic suitability scoring, AHP/Fuzzy AHP, TOPSIS, ELECTRE I, farm-specific fertilizer calculations, water-resource calculations, NSGA-II optimization, explainability, and data provenance into a single end-to-end platform.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Objectives](#objectives)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Architecture Layers](#architecture-layers)
- [End-to-End Data Flow](#end-to-end-data-flow)
- [Decision Intelligence Pipeline](#decision-intelligence-pipeline)
- [Crop Recommendation](#crop-recommendation)
- [Decision Methods](#decision-methods)
  - [AHP](#ahp--analytic-hierarchy-process)
  - [Fuzzy AHP](#fuzzy-ahp)
  - [TOPSIS](#topsis)
  - [ELECTRE I](#electre-i)
- [Farm-Specific Fertilizer Engine](#farm-specific-fertilizer-engine)
- [Water and Resource Planning](#water-and-resource-planning)
- [NSGA-II Multi-Objective Optimization](#nsga-ii-multi-objective-optimization)
- [AI Assistant](#ai-assistant)
- [Satellite and NDVI](#satellite-and-ndvi)
- [Data Sources](#data-sources)
- [Data Provenance and Quality](#data-provenance-and-quality)
- [Database Design](#database-design)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [API Architecture](#api-architecture)
- [Security and Reliability](#security-and-reliability)
- [Testing](#testing)
- [Installation and Local Setup](#installation-and-local-setup)
- [Engineering Challenges](#engineering-challenges)
- [My Contribution](#my-contribution)
- [Current Limitations](#current-limitations)
- [Future Scope](#future-scope)
- [Project Status](#project-status)
- [Author](#author)
- [Disclaimer](#disclaimer)

---

## Problem Statement

Traditional crop recommendations are often based on generalized agricultural information. In practice, the most suitable crop for a particular farm depends on multiple, often conflicting, factors, including:

- Location
- Temperature and rainfall
- Soil pH, nutrients, and texture
- Soil moisture
- Water availability
- Vegetation condition
- Market evidence

These factors frequently trade off against one another. For example, Crop A may offer high climate suitability but require significantly more water, while Crop B offers moderate suitability with a much lower water requirement. A simple classifier does not naturally represent this kind of trade-off.

FarmOptima therefore treats **crop selection as a multi-criteria decision problem** and **resource planning as a multi-objective optimization problem**, rather than reducing either to a single score.

---

## Objectives

FarmOptima aims to:

- Provide location-aware crop recommendations
- Integrate multiple agricultural and environmental data sources
- Support both spatial soil predictions and laboratory soil measurements
- Evaluate candidate crops using MCDM methods
- Generate farm-specific fertilizer requirements
- Estimate water/resource requirements
- Optimize competing resource objectives using NSGA-II
- Explain the reasoning behind each recommendation
- Preserve data provenance and traceability
- Handle unavailable and stale information explicitly, rather than silently

---

## Key Features

| Category | Capabilities |
|---|---|
| **Farm & Field Management** | Latitude/longitude selection, farm polygon/field boundary, field acreage, location-aware recommendations |
| **Weather Intelligence** | Temperature, rainfall, humidity, solar radiation, wind speed |
| **Soil Intelligence** | Soil pH, nitrogen, organic carbon, sand, clay, soil moisture, laboratory soil-test support |
| **Satellite & GIS** | Google Earth Engine, Sentinel-2, NDVI, farm-polygon processing, map/basemap context |
| **Decision Intelligence** | Agronomic suitability scoring, AHP, Fuzzy AHP, TOPSIS, ELECTRE I |
| **Fertilizer Planning** | Nutrient requirement, N/P₂O₅/K₂O calculations, DAP/Urea/MOP conversion, field-area scaling, split application schedule |
| **Resource Planning** | Crop water demand, rainfall contribution, soil-water contribution, irrigation calculations |
| **Optimization** | NSGA-II, multi-objective optimization, Pareto front, compromise resource solution |
| **Explainability** | Crop ranking rationale, TOPSIS score, AHP weights, contributing/limiting factors, missing-data reporting, fertilizer and optimization rationale |
| **AI Assistant** | Natural-language Q&A, recommendation explanation, context-aware farming discussion |
| **Reliability** | Data provenance, source classification, stale-cache handling, explicit "unavailable" states, regression testing |

---

## System Architecture

```
                         FARMER / USER
                              │
                              ▼
              FRONTEND — REACT + VITE
   Dashboard | Farm Location | Maps | Recommendation | AI Chat
   Weather   | Soil          | NDVI | Fertilizer     | Reports
                              │
                        REST / Axios
                              │
                              ▼
                    FASTAPI BACKEND
        API Routes → Validation → Service Orchestration
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   Weather Service      Soil Service       Satellite Service
          │                   │                   │
          ▼                   ▼                   ▼
     NASA POWER        SoilGrids / Lab      GEE / Sentinel-2
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                    TRUSTED FARM DATA
          (Values + Provenance + Quality + Availability)
                              │
                              ▼
                 AGRONOMIC SUITABILITY
                              │
                              ▼
              AHP / FUZZY AHP — Criterion Priorities
                              │
                              ▼
                  TOPSIS — Crop Ranking
                              │
                              ▼
              ELECTRE I — Outranking Cross-Check
                              │
                              ▼
                       CROP RANKING
               ┌──────────────┴──────────────┐
               ▼                             ▼
     Fertilizer Engine              Water Calculation
               └──────────────┬──────────────┘
                              ▼
                    NSGA-II Optimization
                              ▼
                  Pareto Resource Solutions
                              ▼
                    Compromise Solution
                ┌─────────────┴────────────┐
                ▼                          ▼
        Explanation Engine         Database Persistence
                └─────────────┬────────────┘
                              ▼
             React Dashboard — Final Recommendation
```

---

## Architecture Layers

FarmOptima follows a layered architecture:

1. **Presentation Layer** — React / Vite / Dashboard
2. **API / Application Layer** — FastAPI / REST / Validation
3. **Data Acquisition Layer** — Weather / Soil / Satellite / Market / Farm Data
4. **Decision Intelligence Layer** — Suitability / AHP / TOPSIS / ELECTRE / Fuzzy AHP
5. **Resource Planning Layer** — Fertilizer / Water
6. **Optimization Layer** — NSGA-II / Pareto Analysis
7. **Explanation & Traceability Layer** — Provenance / Explanation / History

---

## End-to-End Data Flow

```
Farmer → Location + Polygon + Area → External Data Collection
      → Data Validation → Provenance / Quality → Farm Data Snapshot
      → Candidate Crops → Agronomic Suitability → AHP / Fuzzy AHP
      → TOPSIS Ranking → ELECTRE Cross-Check → Recommended Crop
      → Fertilizer Requirement + Water Requirement → NSGA-II Optimization
      → Pareto Solutions → Compromise Resource Plan
      → Explanation → Database → Dashboard
```

---

## Decision Intelligence Pipeline

FarmOptima separates crop-selection logic from resource optimization:

```
FARM DATA → Suitability Evaluation → AHP / Fuzzy AHP (Weights/Priorities)
          → TOPSIS (Crop Ranking) → ELECTRE I (Cross-Check) → CROP RANKING
          → [ Fertilizer Plan | Water Plan ] → NSGA-II → Pareto Resource Plans
```

---

## Crop Recommendation

FarmOptima currently evaluates candidate crops including:

Rice · Wheat · Maize · Groundnut · Cotton · Sugarcane · Soybean · Chickpea

At a high level:

```
Farm Conditions (Climate, Soil, Water, Market Evidence)
        → Candidate Crop Scores → MCDM Ranking → Recommended Crop
```

The recommendation is based on the available evidence for the selected farm, rather than defaulting to a fixed crop.

---

## Decision Methods

### AHP — Analytic Hierarchy Process

AHP determines the relative importance of decision criteria, such as:

- Climate Suitability
- Soil Suitability
- Water Efficiency
- Market Evidence

**Flow:** Pairwise Comparison Matrix → Normalize Matrix → Priority/Weight Vector → Consistency Calculation → Criterion Weights

AHP also computes **λmax**, **CI**, and **CR**. The Consistency Ratio (CR) is used strictly as a diagnostic of the pairwise-comparison matrix — it is **not** a crop confidence score.

### Fuzzy AHP

Fuzzy AHP extends the weighting process using **Triangular Fuzzy Numbers (TFNs)**, modeling uncertainty in expert or configured judgments rather than treating every comparison as a single precise value.

**Flow:** Expert/Configured Judgments → Triangular Fuzzy Numbers → Fuzzy Extent Analysis → Priority Weights

### TOPSIS

*Technique for Order Preference by Similarity to Ideal Solution.*

TOPSIS ranks alternatives based on how close they are to the ideal solution and how far they are from the worst solution.

**Flow:** Decision Matrix → Normalization → Weighted Matrix → Ideal Best/Worst → Distance Calculation → Closeness Coefficient → Ranking

$$C_i^{*} = \frac{S_i^{-}}{S_i^{+} + S_i^{-}}$$

where `S_i+` is the distance from the ideal best and `S_i-` is the distance from the ideal worst. A higher closeness coefficient indicates a better relative position. **The TOPSIS score is a ranking measure, not a probability.**

### ELECTRE I

ELECTRE I provides an outranking-based cross-check between alternatives, using **concordance**, **discordance**, and **outranking relations**.

**Flow:** Decision Matrix → Concordance + Discordance Analysis → Outranking Relations → Cross-Check

ELECTRE I is maintained as a method distinct from TOPSIS, rather than a duplicate ranking pass.

---

## Farm-Specific Fertilizer Engine

The fertilizer module produces a structured, farm-level fertilizer plan:

```
Crop Requirement + Soil Information + Farm Area
    → Nutrient Requirement → Available/Interpretable Soil Information
    → Nutrient Planning → Commercial Fertilizer Conversion
    → Field-Level Quantity → Application Schedule
```

Supported commercial fertilizer formulations:

| Fertilizer | Grade |
|---|---|
| DAP | 18% N + 46% P₂O₅ |
| Urea | 46% N |
| MOP | 60% K₂O |

The system accounts for the nitrogen contributed by DAP before calculating the remaining nitrogen requirement through urea, avoiding double-counting.

**Outputs:** nutrient requirement, fertilizer quantity, area-scaled field total, commercial fertilizer quantities, split application schedule, calculation explanation, and provenance information.

---

## Water and Resource Planning

FarmOptima distinguishes between:

```
Crop Water Demand → Rainfall Contribution → Soil Water Contribution
                  → Irrigation Requirement → Resource Optimization
```

**Unit conversion used:**

- 1 acre = 4046.86 m²
- 1 mm of water over 1 acre = 4,046.86 liters

The water calculation layer is intentionally kept separate from NSGA-II so that resource calculations can be inspected and validated independently of the optimizer.

---

## NSGA-II Multi-Objective Optimization

**NSGA-II** (Non-dominated Sorting Genetic Algorithm II) is a multi-objective evolutionary optimization algorithm. In FarmOptima, it is used to find resource plans that balance competing objectives, for example:

- Reduce water use
- Reduce fertilizer use
- Reduce cost
- Meet crop requirements

Rather than a single answer, NSGA-II searches for a set of **non-dominated (Pareto) solutions**.

**Workflow:**

```
Initial Population → Objective Evaluation → Constraint Evaluation
    → Non-Dominated Sorting → Crowding Distance → Selection
    → Crossover → Mutation → Offspring
    → Parent + Offspring → Elitist Selection → Next Generation
    → Pareto Front → Compromise Solution
```

**Current optimization objectives:**

1. Water Gap
2. Fertilizer Gap
3. Resource Cost

Each objective is evaluated independently, and the result is a **Pareto set** rather than an assumption that any one objective always dominates the others.

---

## AI Assistant

FarmOptima includes an AI-assisted conversational interface intended primarily for:

- Explaining recommendations
- Answering questions about a recommendation
- Explaining resource plans and decision criteria
- General natural-language interaction

**Conceptual architecture:**

```
Farmer Question → FastAPI AI Endpoint → Structured FarmOptima Context
                → Configured AI Model → Natural-Language Response
```

**Example**

> **User:** Why was this crop recommended?
>
> **FarmOptima Context:** crop ranking, TOPSIS score, AHP weights, weather, soil, water, provenance
>
> **AI Assistant:** A human-readable explanation grounded in that context.

The conversational layer explains the pipeline's output — it does not replace the underlying MCDM and optimization calculations.

---

## Satellite and NDVI

FarmOptima supports **Google Earth Engine (GEE)** and **Sentinel-2** for satellite processing, when the required GEE authentication/configuration is available.

**NDVI:**

```
NDVI = (NIR - Red) / (NIR + Red)
```

NDVI is calculated from Sentinel-2 data over the selected farm polygon. The system explicitly distinguishes `NDVI = 0` (a valid observation) from `NDVI = unavailable` (no valid observation exists) — a basemap is never represented as a Sentinel-2 observation.

**Satellite processing flow:**

```
Farm Polygon → GeoJSON → Earth Engine Geometry → Sentinel-2 Collection
             → Image Filtering → Red + NIR Bands → NDVI Calculation
             → Polygon Reduction → NDVI + Provenance → Dashboard
```

If GEE is unavailable:

```
Satellite Observation → unavailable → NDVI = null → UI shows "Unavailable"
```

---

## Data Sources

| Source | Purpose | Classification |
|---|---|---|
| NASA POWER | Weather / climate | `LIVE_API` |
| ISRIC SoilGrids | Spatial soil properties | `MODEL_PREDICTION` |
| Laboratory Soil Analysis | Verified soil measurement | `LAB_MEASUREMENT` |
| Open-Meteo | Soil-moisture-related data | `LIVE_API` |
| Google Earth Engine | Satellite processing | `SATELLITE_OBSERVATION` |
| Sentinel-2 | Vegetation/satellite analysis | `SATELLITE_OBSERVATION` |
| AGMARKNET historical dataset | Market evidence | `STATIC_DATASET` |

---

## Data Provenance and Quality

FarmOptima explicitly distinguishes different kinds of evidence using the following source types:

`LIVE_API` · `MODEL_PREDICTION` · `LAB_MEASUREMENT` · `SATELLITE_OBSERVATION` · `STATIC_DATASET` · `CACHED_API` · `UNAVAILABLE`

Each provenance record can include:

- `source_name`
- `source_type`
- `observation_date`
- `retrieved_at`
- `is_stale`
- `quality_status`
- `endpoint_reference`

This allows any recommendation to be traced back to its underlying evidence.

**Failure and fallback handling** follows a data-safe fallback principle:

```
Primary External Source → Success?
    YES → Current Data
    NO  → Database Cache Available?
              YES → Cached/Stale Data
              NO  → Unavailable
```

FarmOptima does not silently fabricate observations when an external source is unavailable — for example, if GEE is unavailable, NDVI is reported as `null` with status `unavailable`, rather than defaulting to `NDVI = 0`.

---

## Database Design

**Conceptual relationships:**

```
User → Farm → SoilTest
            → Recommendation → Input Snapshot
                              → Recommendation Output
                              → Provenance
                              → Ranking
                              → Optimization Results
```

**Farm record:** `location`, `latitude`, `longitude`, `polygon_geojson`, `field_area_acres`

**Laboratory soil record (`SoilTest`):** `pH`, `Nitrogen`, `Organic Carbon`, `Sand`, `Clay`, `Sample Date`, `Laboratory`

Recommendation persistence supports full traceability of the decision output.

---

## Project Structure

```
FarmOptima/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── farm.py
│   │   │   │   ├── recommend.py
│   │   │   │   ├── soil_test.py
│   │   │   │   └── ...
│   │   │   └── router.py
│   │   │
│   │   ├── core/
│   │   │   ├── suitability.py
│   │   │   ├── criteria.py
│   │   │   ├── mcdm.py
│   │   │   ├── fuzzy_ahp.py
│   │   │   └── nsga2.py
│   │   │
│   │   ├── models/
│   │   │   ├── farm.py
│   │   │   ├── soil_test.py
│   │   │   ├── recommendation.py
│   │   │   └── ...
│   │   │
│   │   ├── schemas/
│   │   │   ├── common.py
│   │   │   ├── recommendation.py
│   │   │   └── ...
│   │   │
│   │   ├── services/
│   │   │   ├── weather_service.py
│   │   │   ├── soil_service.py
│   │   │   ├── satellite_service.py
│   │   │   ├── market_service.py
│   │   │   ├── fertilizer_service.py
│   │   │   ├── explanation_service.py
│   │   │   └── ...
│   │   │
│   │   └── crop_database.py
│   │
│   ├── tests/
│   │   ├── test_data_foundation.py
│   │   ├── test_decision_intelligence.py
│   │   ├── test_mcdm_integrity.py
│   │   ├── test_farm_specific_fertilizer.py
│   │   ├── test_nsga2_integrity.py
│   │   ├── test_water_requirement.py
│   │   └── ...
│   │
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── ...
│   ├── package.json
│   └── vite.config.*
│
├── docs/
│   ├── DECISION_INTELLIGENCE_AUDIT.md
│   ├── PHASE3_DECISION_INTELLIGENCE_REPORT.md
│   ├── PHASE3_1_SCIENTIFIC_INTEGRITY_REPORT.md
│   ├── CRITICAL_RECOMMENDATION_BUG_AUDIT.md
│   ├── FORENSIC_RICE_NDVI_FIX_REPORT.md
│   └── ...
│
├── scripts/
├── .gitignore
└── README.md
```

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React, Vite, JavaScript/JSX, Tailwind CSS, Axios, Leaflet / React-Leaflet, data visualization components |
| **Backend** | Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Uvicorn, Pytest |
| **Scientific Computing** | NumPy, Pandas, scikit-learn (where applicable) |
| **GIS / Geospatial** | GeoPandas, Shapely, GeoJSON |
| **Remote Sensing** | Google Earth Engine, Sentinel-2 |
| **Data Sources** | NASA POWER, ISRIC SoilGrids, Open-Meteo, AGMARKNET historical dataset |
| **Database** | SQLAlchemy ORM, SQLite (lightweight/local development), PostgreSQL (target production database) |
| **AI** | Configured AI provider integration for the conversational assistant |

---

## API Architecture

FarmOptima exposes backend functionality through REST APIs built with FastAPI.

**Conceptual API groups:**

```
/api/auth
/api/farms
/api/weather
/api/soil
/api/satellite
/api/recommend
/api/soil-tests
```

Exact routes are defined in the backend implementation. Typical REST operations:

| Method | Purpose |
|---|---|
| `GET` | Retrieve data |
| `POST` | Create / submit data |
| `PUT` | Replace/update a resource |
| `PATCH` | Partially update a resource |
| `DELETE` | Remove a resource |

FastAPI also provides interactive OpenAPI/Swagger documentation at:

```
http://localhost:8000/docs
```

---

## Security and Reliability

- JWT-based authentication
- Environment-based secret configuration
- Input validation
- CORS configuration
- Structured error handling
- Rate limiting where configured
- Audit/trace information
- Clear separation of frontend and backend
- No API credentials committed to source control

Secrets are always stored outside the repository.

---

## Testing

FarmOptima includes unit, integration, algorithm-integrity, and regression tests covering:

```
Data Foundation → Weather / Soil → Satellite Contract → Crop Recommendation
    → AHP → TOPSIS → ELECTRE → Fertilizer → Water → NSGA-II
    → Explanation / Runtime Contracts
```

**Test coverage areas include:**

- Data provenance and API failure handling
- Cache behavior and laboratory soil precedence
- Candidate-crop generation and MCDM integrity
- Fertilizer conversion, N/P₂O₅/K₂O handling, area scaling
- Water calculations
- NSGA-II dominance, Pareto solutions, and seed reproducibility
- NDVI data contracts and runtime response contracts
- Recommendation regression

---

## Installation and Local Setup

### Prerequisites

- Python 3.12+
- Node.js and npm
- Git

### Clone the repository

```bash
git clone https://github.com/MITHLESH55/FarmOptima.git
cd FarmOptima
```

### Backend setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

Configure environment variables using the project's environment template, then start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

- Backend: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

### Frontend setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite.

### Environment configuration

Depending on enabled integrations, environment configuration may include:

```
DATABASE_URL
JWT_SECRET
GEE_PROJECT
AI provider credentials
```

Never commit `.env` files, API keys, passwords, service-account credentials, private keys, or tokens to the repository.

---

## Complete Recommendation Example

```
User selects farm → Latitude/Longitude → Farm Polygon + Area
    → Weather (Temperature, Rainfall, Humidity, Solar/Wind)
    → Soil (SoilGrids / Lab — pH, N, OC, Texture)
    → Satellite (Sentinel-2 / NDVI)
    → Data Provenance → Candidate Crop Set → Suitability Scores
    → AHP / Fuzzy AHP → TOPSIS → ELECTRE I → Crop Ranking
    → [ Fertilizer Plan | Water Requirement ] → NSGA-II → Pareto Front
    → Compromise Plan → [ Explanation | Database ] → Final Dashboard
```

**Example explainability output:**

```json
{
  "crop": "Rice",
  "rank": 1,
  "topsis_closeness": 0.65,
  "mcdm_method": "TOPSIS",
  "criterion_weights": {
    "climate": 0.45,
    "soil": 0.26,
    "water": 0.17,
    "market": 0.12
  },
  "limiting_factors": [],
  "missing_data": [],
  "provenance": []
}
```

*(Actual values are generated by the running recommendation pipeline.)*

The explanation layer is designed to answer **why** a crop received a given ranking for a given farm, rather than returning only the crop name.

---

## Engineering Challenges

### 1. Repeated Rice Recommendation

During development, Rice repeatedly surfaced as the top recommendation across very different scenarios. Rather than simply penalizing Rice, the decision pipeline was traced end to end, and the root cause was found in the scoring/data-flow logic: insufficient differentiation between criteria, overly flat scores, and an inappropriate time-scale comparison between recent rainfall and seasonal crop-water requirements. The scoring pipeline was corrected, and regression tests were added to ensure recommendations respond appropriately to changing farm conditions.

### 2. NDVI Unavailable vs. Zero

An important data-integrity issue arose when satellite data was unavailable and the system incorrectly mapped it to `NDVI = 0` — indistinguishable from a genuine zero observation. The fix distinguishes a valid observation (`NDVI = 0`) from no valid observation (`NDVI = null`, `status = unavailable`), and this distinction is now enforced in the backend/frontend contract.

### 3. Data Source Classification

Correctly labeling data by source type (e.g., SoilGrids → `MODEL_PREDICTION`, Laboratory Soil → `LAB_MEASUREMENT`, NASA POWER → `LIVE_API`, Sentinel-2 → `SATELLITE_OBSERVATION`, AGMARKNET → `STATIC_DATASET`) prevents a model-derived or historical value from being presented as a direct live measurement.

---

## My Contribution

I worked on the end-to-end engineering of the FarmOptima decision-support workflow, including:

**Backend Development**
- FastAPI REST APIs and service-layer architecture
- Request/response schemas and recommendation orchestration
- Database integration

**Real-World Data Integration**
- NASA POWER, SoilGrids, Open-Meteo
- Laboratory soil-test workflow
- Google Earth Engine / Sentinel-2
- Market dataset integration

**Decision Intelligence**
- Agronomic suitability engine
- AHP, Fuzzy AHP, TOPSIS, ELECTRE I

**Resource Planning**
- Farm-specific fertilizer calculations (DAP/Urea/MOP conversion)
- Field-area scaling
- Water/resource calculations

**Optimization**
- NSGA-II, objective evaluation, constraint handling
- Pareto-front generation and compromise-solution selection

**Explainability & Reliability**
- Recommendation rationale and provenance
- Missing-data and stale-data handling
- Regression and integration tests
- Frontend/backend contract validation

---

## Why FarmOptima Is Different

FarmOptima is not designed as a conventional `Input → Machine Learning Model → Crop` system. Instead, it follows:

```
Real-World Farm Data → Data Quality & Provenance → Agronomic Evidence
    → Multi-Criteria Decision Making → Crop Ranking → Resource Planning
    → Multi-Objective Optimization → Explainable Recommendation
```

This combines Agriculture, Artificial Intelligence, Decision Support Systems, MCDM, Optimization, GIS, Remote Sensing, Data Engineering, and Explainable AI in a single application.

### Reliability principles

1. **No fabricated observations** — unavailable external information never silently becomes a real measurement.
2. **Provenance-aware decisions** — every important input carries source and quality information.
3. **Separation of concerns** — data acquisition, decision intelligence, resource planning, optimization, explanation, persistence, and presentation are kept distinct.
4. **Explainable decisions** — the system can describe the factors contributing to a recommendation.
5. **Transparent limitations** — model predictions, measurements, datasets, calculations, and unavailable information are kept conceptually distinct.

---

## Current Limitations

- **Google Earth Engine** — live Sentinel-2 processing requires proper GEE configuration and authentication; when unavailable, satellite observations are explicitly represented as unavailable.
- **Market Data** — the current implementation uses an AGMARKNET historical/static dataset rather than a guaranteed live market-price feed.
- **Soil Predictions** — SoilGrids provides spatial model predictions and should not be treated as a direct replacement for laboratory soil analysis.
- **Agronomic Validation** — FarmOptima is a decision-support engineering/research system; broader real-field validation is required before claiming measured agricultural performance improvements or general agronomic accuracy.
- **Production Deployment** — a production deployment would require additional monitoring, security hardening, scalability testing, data-quality monitoring, field validation, and operational support.

---

## Future Scope

**Data**
- Verified live market-data integration
- Larger laboratory soil datasets and wider regional datasets
- Additional satellite indicators

**Agriculture**
- Crop-growth-stage modeling
- Improved soil interpretation and more detailed nutrient models
- Crop-specific irrigation modeling

**Optimization**
- Additional environmental objectives
- Multi-season optimization
- Farmer preference modeling and more detailed cost models

**Validation**
- Real-field trials and predicted-vs-actual yield comparison
- Water-saving and fertilizer-saving measurement
- Multi-season performance evaluation

**Platform**
- Production deployment, monitoring, and observability
- Mobile support
- Farmer feedback systems and regional language support

---

## Project Status

**Implemented**

- [x] Farm location and field definition
- [x] Farm polygon and acreage
- [x] Weather integration
- [x] Soil model integration
- [x] Laboratory soil-test support
- [x] Satellite/GIS integration
- [x] NDVI data contract
- [x] Data provenance
- [x] Agronomic suitability
- [x] AHP
- [x] Fuzzy AHP
- [x] TOPSIS
- [x] ELECTRE I
- [x] Farm-specific fertilizer engine
- [x] Water/resource calculations
- [x] NSGA-II optimization
- [x] Pareto resource planning
- [x] Explanation layer
- [x] Recommendation persistence
- [x] Automated testing
- [x] Frontend/backend integration

Dedicated tests exist for data foundation, MCDM integrity, fertilizer calculations, water calculations, NSGA-II, NDVI contracts, recommendation regression, and runtime contracts. The exact current test count should be taken from the latest development run rather than treated as a fixed statistic.

**Technical areas combined:** Precision Agriculture · Decision Support Systems · Multi-Criteria Decision Making · Multi-Objective Optimization · Machine Learning · GIS · Remote Sensing · Explainable AI · REST API Engineering · Data Engineering

### Interview-oriented summary

> FarmOptima is a precision-agriculture decision-support platform that uses environmental data, MCDM techniques, and NSGA-II optimization to recommend suitable crops and plan farm resources such as water and fertilizer. MCDM helps decide which crop is more suitable; NSGA-II helps find better trade-offs for resource usage after crop selection.

---

## Author

**Mithlesh Yadav**
Computer Science / Software Development
GitHub: [github.com/MITHLESH55/FarmOptima](https://github.com/MITHLESH55/FarmOptima)

---

## Disclaimer

FarmOptima is a software-based agricultural decision-support system. Its recommendations and estimates should not be treated as a replacement for qualified agronomic advice, laboratory soil analysis, local agricultural recommendations, field trials, or professional farm management decisions. Real-world agricultural performance should be established through appropriate field validation.

---

## Project Vision

FarmOptima aims to transform agricultural recommendations from generic crop suggestions into transparent, location-aware, and resource-aware decision support — combining reliable data, agronomic knowledge, decision intelligence, optimization, explainability, and field validation into a practical platform for better farm-level decision making.
