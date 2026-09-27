🌾 FarmOptima

AI-Powered Precision Agriculture Decision-Support Platform





FarmOptima converts real-world farm context into explainable, resource-aware agricultural recommendations by combining environmental data, geospatial intelligence, Multi-Criteria Decision-Making (MCDM), optimization, and grounded AI assistance.

🔗 Repository: https://github.com/MITHLESH55/FarmOptima

 Table of Contents

Overview

Why FarmOptima

Core Capabilities

System Architecture

Decision Pipeline

Technology Stack

Data Sources & Provenance

Decision Intelligence

Optimization Engine

Explainability & AI Assistant

Security & Reliability

Project Structure

API Surface

Installation & Local Development

Environment Configuration

Testing & Validation

Research Evaluation

Project Timeline

Dashboard

Limitations & Responsible Use

Roadmap

Academic Relevance

Contributing

License

🌱 Overview

FarmOptima is a web-based agricultural decision-support system designed to help users make farm-level crop planning decisions from a combination of:

🌦️ Weather and rainfall conditions

🌱 Soil properties

🛰️ Satellite-derived vegetation information

💧 Water availability and irrigation requirements

📈 Market intelligence

🤖 Machine-learning / agricultural intelligence

🧮 Multi-Criteria Decision-Making (AHP, Fuzzy AHP, TOPSIS, ELECTRE)

🧬 Multi-objective optimization with NSGA-II

💬 Grounded AI explanations

🔎 Data provenance and freshness indicators

The platform is designed around a simple principle:

Collect evidence → normalize it → rank alternatives → optimize resources → explain the result.

FarmOptima is therefore more than a chatbot or a static crop classifier. The AI assistant sits on top of a structured decision pipeline and uses recommendation context as grounding information.

🎯 Why FarmOptima

Traditional crop planning may rely on individual experience or isolated information sources. FarmOptima combines major decision factors into a single auditable workflow.

Problem

Fragmented Data
     │
     ├── Weather
     ├── Soil
     ├── Satellite
     ├── Water
     └── Market
            │
            ▼
      Difficult to combine
      and interpret manually

FarmOptima Approach

Farm Location
      │
      ▼
Real-World Data Collection
      │
      ├── Weather
      ├── Soil
      ├── Satellite / NDVI
      └── Market
      │
      ▼
Data Foundation
      │
      ├── Validation
      ├── Normalization
      ├── Freshness
      └── Provenance
      │
      ▼
Decision Intelligence
      │
      ├── AHP / Fuzzy AHP
      ├── TOPSIS
      └── ELECTRE
      │
      ▼
Resource Optimization
      │
      └── NSGA-II
      │
      ▼
Farm Recommendation
      │
      ├── Crop
      ├── Water / Irrigation
      ├── Fertilizer
      └── Trade-offs
      │
      ▼
Explainable AI Assistant

✨ Core Capabilities

Capability

Description

🌍 Farm Digital Context

Location, polygon boundary and farm-level context used as recommendation input

🌦️ Weather Intelligence

Weather/environmental observations retrieved through the weather service layer

🌱 Soil Intelligence

SoilGrids model predictions with support for higher-priority verified lab measurements

🛰️ Satellite Intelligence

Sentinel-2 / Google Earth Engine workflow with vegetation-index processing

🌿 NDVI Analysis

Location-specific vegetation condition visualization

📊 Crop Ranking

Multi-criteria ranking using AHP, Fuzzy AHP, TOPSIS and ELECTRE

💧 Water Planning

Irrigation/resource allocation recommendations

🧪 Fertilizer Planning

N-P-K oriented nutrient planning and commercial-fertilizer scheduling

🧬 Optimization

NSGA-II multi-objective optimization across resource objectives

🤖 Explainable AI

“Why this crop?” rationale linked to recommendation context

🔍 Data Provenance

Source, freshness and fallback state exposed for traceability

🔐 Authentication

JWT/Bearer-token based protected operations

🚦 API Protection

Rate-limiting and structured exception handling

🗺️ Interactive GIS

Farm boundary and spatial visualization through Leaflet/OpenStreetMap

📑 Research Evaluation

Reproducible algorithm comparison, sensitivity analysis and validation artifacts

🏗️ System Architecture

flowchart TB
    U[👨‍🌾 Farmer / Researcher / Admin]

    UI[🖥️ React + Vite + Tailwind Dashboard]
    MAP[🗺️ Leaflet + OpenStreetMap]

    API[⚡ FastAPI REST API]

    AUTH[🔐 Authentication + Authorization]
    ROUTES[API Routes]
    SERVICES[Service Layer]
    CORE[Decision & Optimization Core]
    DB[(🗄️ SQLAlchemy Database)]

    WEATHER[🌦️ NASA POWER]
    SOIL[🌱 SoilGrids]
    SAT[🛰️ Google Earth Engine + Sentinel-2]
    MARKET[📈 AGMARKNET-derived Market Dataset]

    DATA[📚 Data Foundation<br/>Validation • Normalization • Provenance • Freshness]

    MCDM[🧮 MCDM Engine<br/>AHP • Fuzzy AHP • TOPSIS • ELECTRE]
    OPT[🧬 Optimization Engine<br/>NSGA-II]
    PLAN[🌾 Farm Recommendation<br/>Crop • Water • Fertilizer]
    XAI[💬 Grounded AI Assistant]

    U --> UI
    U --> MAP
    UI --> API
    MAP --> API

    API --> AUTH
    API --> ROUTES
    ROUTES --> SERVICES
    ROUTES --> CORE
    ROUTES --> DB

    SERVICES --> WEATHER
    SERVICES --> SOIL
    SERVICES --> SAT
    SERVICES --> MARKET

    SERVICES --> DATA
    DATA --> MCDM
    CORE --> MCDM
    MCDM --> OPT
    OPT --> PLAN
    PLAN --> XAI
    XAI --> UI

    DB --> PLAN

🔄 Decision Pipeline

The main recommendation flow is layered so that data access, mathematical decision logic and presentation remain separated.

sequenceDiagram
    participant F as Farmer
    participant UI as React Dashboard
    participant API as FastAPI
    participant S as Data Services
    participant D as Decision Engine
    participant O as NSGA-II
    participant A as AI Grounding
    participant DB as Database

    F->>UI: Select farm / location
    UI->>API: Request recommendation
    API->>S: Fetch weather, soil, satellite, market data
    S-->>API: Observations + provenance
    API->>D: Build decision matrix
    D->>D: AHP / Fuzzy AHP
    D->>D: TOPSIS ranking
    D->>D: ELECTRE outranking
    D->>O: Optimize resource objectives
    O-->>D: Pareto solutions
    D-->>API: Crop + resource plan
    API->>DB: Persist recommendation/context
    API->>A: Build grounded explanation context
    A-->>API: Explainable response
    API-->>UI: Recommendation + evidence + provenance
    UI-->>F: Dashboard + maps + rationale

🧠 Decision Intelligence

1. AHP / Fuzzy AHP

FarmOptima uses hierarchical weighting to represent the relative importance of decision criteria.

Current core criteria include:

Climate

Soil

Water Efficiency

Market

The implementation supports:

Crisp AHP

Consistency checking

Chang-style Fuzzy AHP extent-analysis workflow

Fuzzy-derived criteria weights used by downstream ranking

Current project weighting configuration

Criterion

Weight

Climate

0.4495

Soil

0.2596

Water Efficiency

0.1707

Market

0.1202

These values are project configuration values used by the implementation and are not presented as universally optimal agronomic weights.

2. TOPSIS

TOPSIS evaluates candidate crops according to their distance from an ideal and anti-ideal solution.

Decision Matrix
      ↓
Vector Normalization
      ↓
Weighted Normalized Matrix
      ↓
Ideal Best / Ideal Worst
      ↓
Distance Calculation
      ↓
Closeness Coefficient
      ↓
Crop Ranking

The result is exposed as a ranked crop list together with the underlying decision context.

3. ELECTRE

ELECTRE is used as an outranking cross-check rather than being treated as a duplicate of TOPSIS.

The current implementation uses concordance and discordance thresholds to compute an ELECTRE net-outranking signal.

This allows the system to compare multiple decision methods while keeping the semantics of each method explicit.

🧬 Optimization Engine

FarmOptima uses NSGA-II for multi-objective resource planning.

Current optimization objectives

Minimize:
    1. Water Gap
    2. Fertilizer Gap
    3. Monetary / Resource Cost

NSGA-II flow

flowchart LR
    I[Initial Population]
    E[Evaluate Objectives]
    N[Non-Dominated Sorting]
    C[Crowding Distance]
    S[Selection]
    X[Crossover]
    M[Mutation]
    P[Next Population]
    F[Pareto Front]
    R[Compromise Solution]

    I --> E --> N --> C --> S --> X --> M --> P
    P --> E
    N --> F --> R

Optimization output

Pareto-optimal candidate solutions

Water allocation

Fertilizer allocation

Resource/cost trade-offs

A selected compromise point for dashboard presentation

This is useful when no single solution simultaneously minimizes every objective.

💬 Explainability & AI Assistant

The AI assistant is designed as a grounded explanation layer.

Instead of independently inventing a crop recommendation, the assistant receives recommendation context such as:

Selected crop

Ranked alternatives

Soil observations

Weather observations

Satellite / NDVI context

Fertilizer plan

Irrigation plan

Optimization outputs

Reference ranges

Data provenance

Explanation workflow

Recommendation Engine
        │
        ▼
Structured Farm Context
        │
        ▼
Grounding / Context Builder
        │
        ▼
AI Assistant
        │
        ▼
Human-readable Explanation

Typical user-facing questions include:

Why was this crop selected?

How do soil and weather affect the recommendation?

What fertilizer and irrigation actions are suggested?

Which data sources were used?

🛰️ Geospatial & Satellite Intelligence

FarmOptima treats a farm as a spatial object rather than only a latitude/longitude point.

Spatial capabilities

Farm location selection

Polygon-based farm boundary support

GeoJSON boundary representation

Leaflet/OpenStreetMap visualization

Satellite imagery integration

Sentinel-2 based vegetation analysis

NDVI calculation and visualization

Satellite flow

Farm Boundary / Location
          ↓
Google Earth Engine
          ↓
Sentinel-2 Imagery
          ↓
Cloud / Availability Handling
          ↓
Band Processing
          ↓
NDVI
          ↓
Vegetation Insight

📚 Data Sources & Provenance

Data Domain

Source / Mechanism

Role in System

Current Status

🌦️ Weather

NASA POWER

Weather / climate variables

Live service with fallback handling

🌱 Soil

SoilGrids v2.0

Model-based soil properties

Model prediction

🧪 Soil Lab

Verified lab measurement record

Higher-priority soil evidence

Supported

🛰️ Satellite

Google Earth Engine / Sentinel-2

NDVI / satellite observation

Integrated with fallback handling

📈 Market

AGMARKNET-derived local CSV

Crop price signal

Static historical/local dataset

🗺️ Maps

OpenStreetMap

Base map visualization

Integrated

Provenance hierarchy

FarmOptima distinguishes the type and freshness of evidence rather than presenting every number as equally authoritative.

LAB_MEASUREMENT
       >
MODEL_PREDICTION
       >
CACHED_API
       >
MOCK / FALLBACK

This hierarchy is particularly important for soil information, where verified laboratory measurements can override regional model predictions.

🛡️ Security & Reliability

FarmOptima includes a dedicated reliability/security layer around the recommendation pipeline.

Security

JWT/Bearer-token authentication

Protected farm operations

Current-user dependency validation

Password hashing

Structured authentication errors

Environment-based secret configuration

Rate limiting on sensitive recommendation operations

Hashed passwords excluded from user responses

Reliability

External-service timeout handling

Cached/fallback data handling

Structured API errors

Pydantic request/response validation

Provenance and freshness metadata

Layer-separated, testable business logic

🧰 Technology Stack

Frontend

Technology

Purpose

React

UI architecture

Vite

Frontend build tooling

Tailwind CSS

Styling and responsive UI

React-Leaflet / Leaflet

Interactive mapping

Axios

API communication

Recharts / Plotly-style visualizations

Data presentation

Backend

Technology

Purpose

Python

Core programming language

FastAPI

REST API framework

Pydantic

Validation and schemas

SQLAlchemy

Database access / ORM layer

Uvicorn

ASGI application server

Pytest

Automated testing

Intelligence Layer

Technology / Method

Purpose

Scikit-learn / Python ML stack

Model / feature processing

AHP

Criteria weighting

Fuzzy AHP

Uncertainty-aware weighting workflow

TOPSIS

Suitability ranking

ELECTRE

Outranking analysis

NSGA-II

Multi-objective optimization

Geospatial / Data

Technology

Purpose

Google Earth Engine

Satellite data processing

Sentinel-2

Earth observation imagery

SoilGrids

Soil model data

NASA POWER

Weather/environmental data

AGMARKNET-derived CSV

Market signal

OpenStreetMap

Base map

Engineering

Git

GitHub

Docker-compatible project architecture

Environment-based configuration

Automated testing and research scripts

📁 Project Structure

The repository follows a layered backend architecture in which routes stay thin, services own external I/O, and the algorithm layer remains independently testable.

FarmOptima/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   ├── router.py
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── farms.py
│   │   │       ├── recommend.py
│   │   │       ├── satellite.py
│   │   │       ├── soil.py
│   │   │       └── weather.py
│   │   │
│   │   ├── core/
│   │   │   ├── ai_grounding.py
│   │   │   ├── criteria.py
│   │   │   ├── environmental_interpretation.py
│   │   │   ├── fuzzy_ahp.py
│   │   │   ├── gpo.py
│   │   │   ├── insight_engine.py
│   │   │   ├── mcdm.py
│   │   │   ├── nsga2.py
│   │   │   ├── ranking_tiebreak.py
│   │   │   └── suitability.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   └── ai/
│   │   ├── utils/
│   │   ├── config.py
│   │   ├── crop_database.py
│   │   ├── database.py
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.*
│
├── scripts/
│   ├── run_research_evaluation.py
│   ├── run_optimization_comparison.py
│   └── run_sensitivity_analysis.py
│
├── reports/
│   ├── research_evaluation_results.json
│   ├── optimization_comparison_results.json
│   ├── sensitivity_analysis_results.json
│   └── *.md
│
├── docs/
│   └── FINAL_SUBMISSION_READINESS.md
│
└── README.md

Project documentation and generated research artifacts may evolve as the repository is maintained. Treat the source tree as authoritative for any file-level change.

🔌 API Surface

The backend exposes a FastAPI REST interface.

Endpoint

Method

Purpose

/api/auth/register

POST

Create a user

/api/auth/login

POST

Authenticate and receive access token

/api/weather

GET

Weather context for coordinates

/api/soil

GET

Soil context for coordinates

/api/satellite

GET

NDVI / satellite context

/api/farms

GET

List authenticated user's saved farms

/api/farms

POST

Create/save a farm

/api/farms/{farm_id}/soil-tests

POST

Add a verified soil-test record

/api/recommend

POST

Main recommendation orchestration

/api/ai/chat

POST

Grounded AI assistant interaction

API Documentation

When the backend is running:

Swagger UI:
http://localhost:8000/docs

OpenAPI:
http://localhost:8000/openapi.json

🚀 Installation & Local Development

Prerequisites

Python 3.12+

Node.js 20+ recommended

npm

Git

A supported database configuration

API credentials where required

1. Clone the repository

git clone https://github.com/MITHLESH55/FarmOptima.git
cd FarmOptima

2. Backend setup

cd backend

python -m venv .venv

Windows

.venv\Scripts\activate

macOS / Linux

source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Create environment configuration:

copy .env.example .env

Run the API:

uvicorn app.main:app --reload --port 8000

3. Frontend setup

Open a second terminal:

cd frontend
npm install
npm run dev

The Vite application is typically available at:

http://localhost:5173

🔐 Environment Configuration

Never commit secrets to Git.

Typical environment variables include:

SECRET_KEY=change-me
DATABASE_URL=your-database-url

NASA_POWER_ENABLED=true
SOILGRIDS_ENABLED=true

GEE_PROJECT=your-earth-engine-project

OPENAI_API_KEY=your-key
GEMINI_API_KEY=your-key

Use the repository's .env.example as the authoritative template for the exact variables expected by the current codebase.

🧪 Testing & Validation

FarmOptima includes automated regression tests, integration tests and reproducible research evaluation scripts.

Current verification snapshot

Verification Area

Result

Backend automated tests

340 / 340 passed

Frontend production build

Passed

Research evaluation pipelines

3 / 3 passed

Academic submission dossier

Complete

System documentation

Complete

Run backend tests

cd backend
pytest

Run frontend production build

cd frontend
npm run build

Run research evaluation

python scripts/run_research_evaluation.py
python scripts/run_optimization_comparison.py
python scripts/run_sensitivity_analysis.py

📊 Research Evaluation

FarmOptima includes a reproducible research/evaluation layer rather than relying only on a visual demo.

MCDM Benchmark

Evaluation was performed across 6 Indian agro-climatic zones.

Evaluation

Observed Result

Crisp AHP vs. Fuzzy AHP — mean Spearman ρ

0.9768

Equal-weight TOPSIS vs. Fuzzy AHP — correlation

0.8241

Fuzzy AHP vs. ELECTRE — concordance cross-check correlation

0.9105

Top-1 agreement: Crisp AHP vs. Fuzzy AHP

100.0%

Average algorithm execution time

< 1.5 ms

Optimization Benchmark

A baseline optimization approach was compared with the NSGA-II formulation.

Observed benchmark characteristics include:

Multiple Pareto-optimal resource solutions

Multi-objective treatment of water, fertilizer and cost

Approximately 40 non-dominated solutions in the benchmark configuration

Average water gap around 18.2%

Average fertilizer gap around 10.5%

Benchmark execution around 625 ms for the documented population/generation configuration

Benchmark configuration should be read together with the research scripts/reports because optimizer population and generation settings may differ from the main application defaults.

Sensitivity Analysis

The evaluation also tested recommendation stability under parameter perturbations.

Sensitivity Dimension

Observed Top-1 Retention

AHP weight perturbation (±10–30%)

100%

Fuzzy spread variation

100%

ELECTRE threshold variation

100%

The research artifacts in reports/ contain machine-readable results and detailed interpretation.

📅 Project Timeline

Project duration: 01 July 2026 – 27 September 2026

gantt
    title FarmOptima Development Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b

    section Planning
    Problem Identification & Literature Review :done, p1, 2026-07-01, 10d
    Requirement Analysis & Architecture        :done, p2, 2026-07-08, 11d
    Dataset & Data Source Collection            :done, p3, 2026-07-15, 22d

    section Core Engineering
    Backend & Database Development              :done, b1, 2026-08-01, 15d
    AI/ML Crop Recommendation                   :done, b2, 2026-08-05, 21d
    Soil / Weather / Satellite Integration      :done, b3, 2026-08-08, 21d
    Frontend Dashboard & Visualization          :done, b4, 2026-08-05, 45d

    section Decision Intelligence
    AHP / Fuzzy AHP / TOPSIS / ELECTRE         :done, d1, 2026-08-18, 19d
    Fertilizer & Irrigation Recommendation      :done, d2, 2026-08-28, 16d
    NSGA-II Resource Optimization               :done, d3, 2026-09-02, 14d

    section Explainability & Quality
    Explainable AI / AI Assistant               :done, q1, 2026-09-08, 13d
    System Integration & Testing                :done, q2, 2026-09-15, 9d
    Research Evaluation & Sensitivity Analysis  :done, q3, 2026-09-18, 8d
    Documentation, PPT & Final Submission      :done, q4, 2026-09-22, 6d

🖥️ Dashboard

The dashboard is designed around an evidence-to-action workflow:

┌─────────────────────────────────────────────────────────────┐
│                     FARMOPTIMA DASHBOARD                    │
├─────────────────────────────────────────────────────────────┤
│ Farm Location / Boundary                                   │
├───────────────────┬─────────────────────┬───────────────────┤
│ Weather           │ Soil Properties     │ Water / Moisture  │
│ Temperature       │ pH                  │ Availability      │
│ Rainfall          │ N / P / K           │                   │
└───────────────────┴─────────────────────┴───────────────────┘
├─────────────────────────────────────────────────────────────┤
│ Satellite / Sentinel-2 / NDVI                               │
├─────────────────────────────────────────────────────────────┤
│ Crop Ranking → AHP / TOPSIS / ELECTRE                      │
├─────────────────────────────────────────────────────────────┤
│ Recommended Crop                                             │
├─────────────────────────────────────────────────────────────┤
│ Fertilizer Plan        │ Irrigation Plan │ NSGA-II Tradeoffs │
├─────────────────────────────────────────────────────────────┤
│ "Why This Crop?" / Explainable AI Assistant                 │
├─────────────────────────────────────────────────────────────┤
│ Data Provenance • Freshness • Source Status                  │
└─────────────────────────────────────────────────────────────┘

Recommended screenshot directory

For a polished GitHub presentation, place project screenshots under:

docs/images/
├── dashboard.png
├── recommendation.png
├── ndvi-map.png
├── fertilizer-plan.png
├── optimization.png
└── architecture.png

Then embed them in this README:

![FarmOptima Dashboard](docs/images/dashboard.png)

⚠️ Limitations & Responsible Use

FarmOptima is a decision-support and academic engineering system. Recommendations should be treated as analytical guidance, not as guaranteed agronomic outcomes.

Current limitations

Market intelligence

The current application uses a curated historical/local AGMARKNET-derived CSV dataset.

It is not an intraday live mandi ticker.

Soil resolution

SoilGrids values are model predictions at regional spatial resolution.

Verified laboratory measurements can be represented with higher precedence.

Satellite availability

Cloud cover and source availability can affect satellite observations.

The system includes fallback handling where appropriate.

Yield validation

Optimization evaluates alignment with resource/nutrient targets.

It does not constitute a validated longitudinal field-trial yield guarantee.

Agronomic references

Fertilizer and irrigation logic should be interpreted alongside local agricultural advisories, crop stage, soil-test results and professional agronomic guidance.

🛣️ Roadmap

Near-Term

PostgreSQL-first production deployment

Stronger historical recommendation tracking

Richer farm-level spatial analytics

Monitoring and audit dashboards

Expanded test coverage for external service failure modes

Future Research / Product Directions

📡 IoT soil and weather sensor integration

🚁 Drone imagery and crop-health analysis

🦠 Crop disease detection

🌾 Yield prediction with field-level validation

🌍 Expanded multilingual / voice interaction

💧 Smart irrigation scheduling

🧪 Advanced soil-test ingestion

🌐 Mobile application

🏛️ Government scheme and advisory integration

♻️ Sustainability / carbon-footprint analytics

🎓 Academic Relevance

FarmOptima demonstrates the integration of multiple computer-science and engineering areas into one application:

Area

Demonstrated Component

Software Engineering

Layered architecture, REST APIs, frontend/backend separation

Artificial Intelligence

AI assistant, agricultural intelligence, contextual explanation

Machine Learning

Agricultural recommendation pipeline

Data Engineering

Multi-source ingestion, normalization and provenance

GIS / Remote Sensing

Sentinel-2, GEE, NDVI, farm polygons

Decision Science

AHP, Fuzzy AHP, TOPSIS, ELECTRE

Optimization

NSGA-II multi-objective planning

Cybersecurity

JWT authentication, protected APIs, secret management

Testing

Automated regression and research validation

Research

Benchmarking, sensitivity analysis and reproducibility

Sustainable Engineering

Water/fertilizer resource planning

📚 Key Research References

The project methodology is grounded in established decision-analysis and optimization literature, including:

Saaty, T. L. — Analytic Hierarchy Process (AHP)

Chang, D.-Y. — Fuzzy AHP extent-analysis methodology

Hwang, C.-L. & Yoon, K. — TOPSIS

Roy, B. — ELECTRE / outranking family

Deb, K., Pratap, A., Agarwal, S. & Meyarivan, T. (2002) — NSGA-II

FAO-56 / CROPWAT-oriented agronomic water-management references

ICAR / agricultural university nutrient recommendation references

Detailed project-specific methodology and benchmark artifacts should be read together with the research reports shipped in the repository.

🤝 Contributing

This repository is primarily maintained as an academic engineering project.

For changes:

git checkout -b feature/your-feature
git add .
git commit -m "feat: describe your change"
git push origin feature/your-feature

Please keep:

Secrets out of Git

Generated local databases out of commits

External-service assumptions documented

Tests updated when core algorithms change

Data provenance explicit for new integrations

👨‍💻 Project

FarmOptima
AI-Powered Precision Agriculture Decision-Support Platform

Repository:
https://github.com/MITHLESH55/FarmOptima

Primary engineering focus:
AI + ML + GIS + Remote Sensing + MCDM + Optimization + Full-Stack Development + Explainable AI

📜 License

This repository is maintained as an academic / final-year engineering project.

Add a formal open-source license such as MIT, Apache-2.0, or another license only when the project owner intentionally chooses to publish the source under that license.

⭐ Project Vision

From raw farm data to explainable decisions — FarmOptima connects environmental intelligence, decision science and optimization into one practical agricultural platform.


<!-- Documentation maintained by contributors. -->
