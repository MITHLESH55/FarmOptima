🌾 FarmOptima

AI-Powered Precision Agriculture Decision-Support Platform

From farm data → decision intelligence → optimized resources → explainable action.








</div>

🌱 What is FarmOptima?

FarmOptima is a full-stack agricultural decision-support system that combines:

Soil + Weather + Satellite/NDVI + Water + Market context

with

AHP + Fuzzy AHP + TOPSIS + ELECTRE + NSGA-II

to produce a farm-specific recommendation that includes:

🌾 Crop · 💧 Irrigation · 🧪 Fertilizer · 🧠 Explanation · 🔎 Data Provenance

It is designed as an evidence-driven decision system, not merely a chatbot or a single crop-classification model.

⚡ At a Glance

🧩

Capability

🧩

Capability

🌦️

Weather intelligence

🌱

Soil intelligence

🛰️

Satellite + NDVI

📈

Market signal

🧮

MCDM crop ranking

🧬

NSGA-II optimization

💧

Irrigation planning

🧪

N-P-K fertilizer planning

💬

Grounded AI assistant

🔍

Provenance / freshness

🔐

JWT authentication

🚦

Rate limiting & validation

🏗️ System Architecture

flowchart LR
    U["👨‍🌾 Farmer / Researcher"] --> UI["🖥️ React Dashboard"]

    UI --> API["⚡ FastAPI"]

    API --> DS["📚 Data Services"]
    DS --> W["🌦️ NASA POWER"]
    DS --> S["🌱 SoilGrids"]
    DS --> G["🛰️ GEE / Sentinel-2"]
    DS --> M["📈 AGMARKNET-derived Dataset"]

    DS --> DF["🔎 Data Foundation<br/>Validation • Normalization • Provenance"]

    DF --> DI["🧮 Decision Intelligence"]
    DI --> AHP["AHP / Fuzzy AHP"]
    DI --> TOP["TOPSIS"]
    DI --> ELE["ELECTRE"]

    AHP --> OPT["🧬 NSGA-II"]
    TOP --> OPT
    ELE --> OPT

    OPT --> R["🌾 Farm Recommendation"]
    R --> X["💬 Grounded AI Explanation"]
    X --> UI

    API --> DB[("🗄️ Database")]

Core design principle

External Data
     ↓
Data Foundation
     ↓
Decision Intelligence
     ↓
Multi-Objective Optimization
     ↓
Farm Recommendation
     ↓
Explainable AI

🔄 End-to-End Decision Pipeline

flowchart TB
    A["📍 Select Farm Location / Boundary"]
    B["🌦️ Fetch Weather"]
    C["🌱 Fetch Soil"]
    D["🛰️ Fetch Satellite / NDVI"]
    E["📈 Load Market Signal"]
    F["🔎 Validate + Normalize + Track Provenance"]
    G["🧮 Build Crop Decision Matrix"]
    H["AHP / Fuzzy AHP → Criteria Weights"]
    I["TOPSIS → Suitability Ranking"]
    J["ELECTRE → Outranking Cross-Check"]
    K["🧬 NSGA-II → Resource Trade-offs"]
    L["🌾 Crop + Water + Fertilizer Plan"]
    M["💬 Grounded AI → Why This Crop?"]

    A --> B --> F
    A --> C --> F
    A --> D --> F
    A --> E --> F
    F --> G --> H --> I --> J --> K --> L --> M

🧠 Decision Intelligence

Multi-Criteria Decision-Making

Method

Role

AHP

Criteria weighting + consistency analysis

Fuzzy AHP

Uncertainty-aware weighting workflow

TOPSIS

Distance-based crop suitability ranking

ELECTRE

Concordance / discordance based outranking

Current decision criteria

🌦️ Climate
🌱 Soil
💧 Water Efficiency
📈 Market

Current AHP weights

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

These are the project's configured decision weights, not universal agronomic priorities.

🧬 NSGA-II Optimization

FarmOptima treats resource planning as a multi-objective optimization problem.

Objectives

Minimize
├── Water Gap
├── Fertilizer Gap
└── Monetary / Resource Cost

Optimization flow

flowchart LR
    P["Initial Population"]
    E["Objective Evaluation"]
    N["Non-Dominated Sorting"]
    C["Crowding Distance"]
    S["Selection"]
    X["Crossover"]
    M["Mutation"]
    PF["Pareto Front"]
    R["Compromise Solution"]

    P --> E --> N --> C --> S --> X --> M --> E
    N --> PF --> R

Output: a set of trade-off solutions rather than forcing every objective into a single score.

🛰️ Geospatial Intelligence

FarmOptima uses the farm as a spatial context, not only as a point.

Spatial stack

Farm Location / Polygon
        ↓
Google Earth Engine
        ↓
Sentinel-2 Imagery
        ↓
Band Processing
        ↓
NDVI
        ↓
Vegetation Insight
        ↓
Recommendation Context

Current spatial capabilities

Leaflet · OpenStreetMap · GeoJSON · Sentinel-2 · Google Earth Engine · NDVI

🔎 Data Provenance & Freshness

FarmOptima explicitly distinguishes where a value came from and whether it is live, cached, model-derived, or fallback data.

Soil evidence precedence

LAB_MEASUREMENT
       ↓
MODEL_PREDICTION
       ↓
CACHED_API
       ↓
MOCK / FALLBACK

Domain

Current Source

Current Status

Weather

NASA POWER

Live service + fallback

Soil

SoilGrids v2.0

Model prediction

Soil lab

Verified lab record

Supported, higher precedence

Satellite

GEE / Sentinel-2

Integrated + fallback handling

Market

AGMARKNET-derived CSV

Static historical/local dataset

Maps

OpenStreetMap

Integrated

🤖 Explainable AI

The AI assistant operates as the explanation layer above the recommendation engine.

Recommendation Engine
        ↓
Structured Farm Context
        ↓
Grounding / Context Builder
        ↓
AI Assistant
        ↓
Human-readable Explanation

The assistant can explain:

Why this crop?

Which factors contributed to the decision

How soil/weather/NDVI affected the recommendation

What water and fertilizer actions are suggested

Which data sources were used

🧪 Engineering & Reliability

🔐 Security

JWT/Bearer Authentication · Password Hashing · Protected Farm Operations · Rate Limiting · Environment Secrets

🧱 Architecture

Thin API Routes → Service Layer → Pure Core Algorithms → Database Models → Validated Schemas

🛡️ Reliability

Timeout Handling · Fallbacks · Structured Exceptions · Pydantic Validation · Provenance Tracking

🛠️ Technology Stack

<table>
<tr>
<td width="50%">

Frontend

React

Vite

Tailwind CSS

Leaflet / React-Leaflet

Axios

Recharts / data visualization

</td>
<td width="50%">

Backend

Python 3.12+

FastAPI

Pydantic

SQLAlchemy

Uvicorn

Pytest

</td>
</tr>
<tr>
<td>

Intelligence

Machine Learning

AHP

Fuzzy AHP

TOPSIS

ELECTRE

NSGA-II

</td>
<td>

Geospatial & Data

Google Earth Engine

Sentinel-2

SoilGrids

NASA POWER

AGMARKNET-derived dataset

OpenStreetMap

</td>
</tr>
</table>

📁 Project Structure

FarmOptima/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   └── ai/
│   │   ├── utils/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
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
└── README.md

🔌 API Surface

Endpoint

Method

Purpose

/api/auth/register

POST

User registration

/api/auth/login

POST

Login + token

/api/weather

GET

Weather context

/api/soil

GET

Soil context

/api/satellite

GET

Satellite / NDVI context

/api/farms

GET/POST

Saved farms

/api/farms/{farm_id}/soil-tests

POST

Verified soil test

/api/recommend

POST

Main recommendation pipeline

/api/ai/chat

POST

Grounded AI assistant

API documentation

Swagger UI → http://localhost:8000/docs
OpenAPI    → http://localhost:8000/openapi.json

🚀 Run Locally

1. Clone

git clone https://github.com/MITHLESH55/FarmOptima.git
cd FarmOptima

2. Backend

cd backend
python -m venv .venv

Windows

.venv\Scripts\activate
pip install -r requirements.txt
Windows:
copy .env.example .env

macOS / Linux:
cp .env.example .env
uvicorn app.main:app --reload --port 8000

3. Frontend

cd frontend
npm install
npm run dev

Frontend:

http://localhost:5173

Backend:

http://localhost:8000

✅ Validation

Check

Result

Backend automated tests

340 / 340 passed

Frontend production build

Passed

Research pipelines

3 / 3 passed

Submission / documentation dossier

Complete

Run locally:

cd backend
pytest

cd frontend
npm run build

Research evaluation:

python scripts/run_research_evaluation.py
python scripts/run_optimization_comparison.py
python scripts/run_sensitivity_analysis.py

📊 Research Snapshot

MCDM Evaluation — 6 Indian Agro-Climatic Zones

Metric

Observed

Crisp AHP ↔ Fuzzy AHP mean Spearman ρ

0.9768

Equal-weight TOPSIS ↔ Fuzzy AHP correlation

0.8241

Fuzzy AHP ↔ ELECTRE cross-check correlation

0.9105

Top-1 agreement: Crisp vs Fuzzy AHP

100%

Mean algorithm execution

< 1.5 ms

Optimization Benchmark

Metric

Observed

Non-dominated solutions

~40

Average water gap

18.2%

Average fertilizer gap

10.5%

Benchmark execution

~625 ms

These are results from the project's documented benchmark configuration. Optimizer settings can differ between the application defaults and research benchmark scripts.

📅 Project Timeline

01 July 2026 → 27 September 2026

gantt
    title FarmOptima — Development Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b

    section Foundation
    Problem + Literature Review        :done, a1, 2026-07-01, 10d
    Requirements + Architecture        :done, a2, 2026-07-08, 11d
    Data Sources + Datasets             :done, a3, 2026-07-15, 22d

    section Engineering
    Backend + Database                  :done, b1, 2026-08-01, 15d
    AI/ML Recommendation                :done, b2, 2026-08-05, 21d
    Weather + Soil + Satellite          :done, b3, 2026-08-08, 21d
    Frontend Dashboard                  :done, b4, 2026-08-05, 45d

    section Decision
    AHP/Fuzzy AHP/TOPSIS/ELECTRE        :done, c1, 2026-08-18, 19d
    Fertilizer + Irrigation             :done, c2, 2026-08-28, 16d
    NSGA-II Optimization                :done, c3, 2026-09-02, 14d

    section Finalization
    Explainable AI                      :done, d1, 2026-09-08, 13d
    Integration + Testing               :done, d2, 2026-09-15, 9d
    Research + Sensitivity              :done, d3, 2026-09-18, 8d
    Documentation + Final Submission    :done, d4, 2026-09-22, 6d

🌍 Sustainable Development Alignment

SDG

Relevance

SDG 2

Food production and agricultural decision support

SDG 6

Water-aware irrigation planning

SDG 9

AI, GIS, remote sensing and engineering innovation

SDG 12

Resource-efficient fertilizer / water planning

SDG 13

Climate-aware agricultural decisions

🛣️ Roadmap

Next

PostgreSQL-first deployment · Historical recommendation tracking · Expanded spatial analytics · Production observability

Future Research

IoT sensors · Drone imagery · Disease detection · Field-validated yield prediction · Multilingual voice assistant · Smart irrigation · Mobile application

<details>
<summary><strong>⚠️ Current Limitations</strong></summary>

<br>

Market: Current application uses a curated historical/local AGMARKNET-derived CSV rather than a live intraday mandi stream.

Soil: SoilGrids provides regional model predictions; verified laboratory measurements can take higher precedence.

Satellite: Cloud cover and source availability can affect observations, so fallback handling is used where appropriate.

Yield: Optimization aligns resource allocation with reference targets; it is not a validated field-trial yield guarantee.

Responsible use: FarmOptima is a decision-support system. Recommendations should be considered alongside local conditions, current advisories, soil testing and professional agronomic guidance.

</details>

📚 Methodology References

Saaty — Analytic Hierarchy Process (AHP)

Chang — Fuzzy AHP extent-analysis methodology

Hwang & Yoon — TOPSIS

Roy — ELECTRE / Outranking

Deb et al. (2002) — NSGA-II

FAO-56 / CROPWAT-oriented water-management references

ICAR / agricultural-university nutrient recommendation references

👨‍💻 Project

<div align="center">

FarmOptima

AI + ML + GIS + Remote Sensing + MCDM + Optimization + Explainable AI

⭐ View Repository

</div>

<div align="center">

🌾 From Raw Farm Data to Explainable Decisions

Built as a final-year engineering project focused on practical AI, intelligent decision-making and sustainable resource planning.

</div>
