<a id="top"></a>

<div align="center"> <img src="https://capsule-render.vercel.app/api?type=waving&color=0:052e16,25:14532D,50:15803D,75:16A34A,100:052e16&height=210&section=header&text=FarmOptima&fontSize=66&fontColor=FFFFFF&fontAlignY=34&animation=fadeIn&desc=AI-Powered%20Precision%20Agriculture%20Decision-Support&descAlignY=56&descSize=17&descColor=BBF7D0" width="100%"/>
<a href="https://readme-typing-svg.demolab.com"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=21&duration=2800&pause=800&color=16A34A&center=true&vCenter=true&width=820&lines=From+farm+data+%E2%86%92+decision+intelligence+%E2%86%92+action;Soil+%C2%B7+Weather+%C2%B7+Satellite+%C2%B7+Water+%C2%B7+Market;AHP+%C2%B7+Fuzzy+AHP+%C2%B7+TOPSIS+%C2%B7+ELECTRE+%C2%B7+NSGA-II;Explainable%2C+evidence-driven+recommendations" alt="Typing SVG"/></a>

<p> <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white"/> <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/> <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black"/> <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white"/> <img src="https://img.shields.io/badge/Tailwind-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white"/> </p> <p> <img src="https://img.shields.io/badge/tests-340%2F340%20passing-22C55E?style=for-the-badge&logo=pytest&logoColor=white"/> <img src="https://img.shields.io/badge/build-passing-16A34A?style=for-the-badge&logo=vercel&logoColor=white"/> <img src="https://img.shields.io/badge/research%20pipelines-3%2F3-15803D?style=for-the-badge&logo=databricks&logoColor=white"/> <img src="https://img.shields.io/badge/status-active-0EA5E9?style=for-the-badge"/> </p>
<b>A full-stack agricultural decision-support system</b> — it turns soil, weather, satellite, water & market signals<br/> into a farm-specific, explainable plan for <b>crop · irrigation · fertilizer</b>, backed by MCDM + multi-objective optimization.

<sub>🌾 An evidence-driven decision system — not merely a chatbot or a single crop-classification model.</sub>

<br/>
<a href="https://github.com/MITHLESH55/FarmOptima"><img src="https://img.shields.io/badge/⭐_View_Repository-052e16?style=for-the-badge&logo=github&logoColor=white"/></a>

</div>
<p align="center"> <a href="#overview"><b>Overview</b></a> &nbsp;•&nbsp; <a href="#glance"><b>Features</b></a> &nbsp;•&nbsp; <a href="#architecture"><b>Architecture</b></a> &nbsp;•&nbsp; <a href="#pipeline"><b>Pipeline</b></a> &nbsp;•&nbsp; <a href="#intelligence"><b>Decision Intelligence</b></a> &nbsp;•&nbsp; <a href="#optimization"><b>NSGA-II</b></a> &nbsp;•&nbsp; <a href="#geospatial"><b>Geospatial</b></a> <br/> <a href="#provenance"><b>Provenance</b></a> &nbsp;•&nbsp; <a href="#xai"><b>Explainable AI</b></a> &nbsp;•&nbsp; <a href="#stack"><b>Tech Stack</b></a> &nbsp;•&nbsp; <a href="#api"><b>API</b></a> &nbsp;•&nbsp; <a href="#run"><b>Run Locally</b></a> &nbsp;•&nbsp; <a href="#validation"><b>Validation</b></a> &nbsp;•&nbsp; <a href="#roadmap"><b>Roadmap</b></a> </p>
<a id="overview"></a>

🌱 What is FarmOptima?
FarmOptima is a full-stack agricultural decision-support system that fuses Soil + Weather + Satellite/NDVI + Water + Market context with a layered decision engine — AHP · Fuzzy AHP · TOPSIS · ELECTRE · NSGA-II — to produce a farm-specific recommendation:

<div align="center">
🌾 Crop  ·  💧 Irrigation  ·  🧪 Fertilizer  ·  🧠 Explanation  ·  🔎 Data Provenance

</div>
[!NOTE] Design philosophy: external data flows through a validation-and-provenance Data Foundation, into Decision Intelligence (MCDM), then Multi-Objective Optimization, and finally an Explainable AI layer — so every recommendation is traceable back to the evidence that produced it.

<a id="glance"></a>

⚡ At a Glance
<div align="center">
🌦️ Weather intelligence	🌱 Soil intelligence	🛰️ Satellite + NDVI
📈 Market signal	🧮 MCDM crop ranking	🧬 NSGA-II optimization
💧 Irrigation planning	🧪 N-P-K fertilizer planning	💬 Grounded AI assistant
🔎 Provenance / freshness	🔐 JWT authentication	🚦 Rate limiting & validation
</div>
<a id="architecture"></a>

🏗️ System Architecture
flowchart LR
    U["👨‍🌾 Farmer / Researcher"] --> UI["🖥️ React Dashboard"]
    UI --> API["⚡ FastAPI"]
    API --> DS["📚 Data Services"]
    DS --> W["🌦️ NASA POWER"]
    DS --> S["🌱 SoilGrids"]
    DS --> G["🛰️ GEE / Sentinel-2"]
    DS --> M["📈 AGMARKNET Dataset"]
    DS --> DF["🔎 Data Foundation<br/>Validation · Normalization · Provenance"]
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

    classDef ui fill:#16A34A,stroke:#052e16,color:#fff
    classDef data fill:#0EA5E9,stroke:#052e16,color:#fff
    classDef intel fill:#6366F1,stroke:#052e16,color:#fff
    classDef out fill:#F59E0B,stroke:#7c2d12,color:#1c1917
    class U,UI,API ui
    class DS,W,S,G,M,DF data
    class DI,AHP,TOP,ELE,OPT intel
    class R,X,DB out
<details> <summary><b>🧭 Core design principle — the layered decision flow</b></summary>
flowchart TD
    A["📡 External Data"] --> B["🔎 Data Foundation"] --> C["🧮 Decision Intelligence"] --> D["🧬 Multi-Objective Optimization"] --> E["🌾 Farm Recommendation"] --> F["💬 Explainable AI"]
    classDef step fill:#14532D,stroke:#052e16,color:#fff
    class A,B,C,D,E,F step
</details>
<a id="pipeline"></a>

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

    classDef inp fill:#0EA5E9,stroke:#052e16,color:#fff
    classDef mid fill:#6366F1,stroke:#052e16,color:#fff
    classDef out fill:#16A34A,stroke:#052e16,color:#fff
    class A,B,C,D,E inp
    class F,G,H,I,J,K mid
    class L,M out
<a id="intelligence"></a>

🧠 Decision Intelligence
FarmOptima layers four complementary Multi-Criteria Decision-Making (MCDM) methods, so the crop ranking is cross-validated rather than resting on a single algorithm.

<div align="center">
Method	Role
🟢 AHP	Criteria weighting + consistency analysis
🟡 Fuzzy AHP	Uncertainty-aware weighting workflow
🔵 TOPSIS	Distance-based crop suitability ranking
🟣 ELECTRE	Concordance / discordance outranking
</div>
Current decision criteria   🌦️ Climate  ·  🌱 Soil  ·  💧 Water Efficiency  ·  📈 Market

Current AHP weights
pie showData
    title AHP Criteria Weights
    "🌦️ Climate" : 0.4495
    "🌱 Soil" : 0.2596
    "💧 Water Efficiency" : 0.1707
    "📈 Market" : 0.1202
[!IMPORTANT] These are the project's configured decision weights, not universal agronomic priorities. They are tunable inputs to the pipeline, and sensitivity analysis is provided (see Validation).

<a id="optimization"></a>

🧬 NSGA-II Multi-Objective Optimization
FarmOptima treats resource planning as a multi-objective optimization problem — producing a set of trade-off solutions instead of forcing every objective into one score.

<div align="center">
🎯 Objective	Direction
💧 Water Gap	minimize
🧪 Fertilizer Gap	minimize
💰 Monetary / Resource Cost	minimize
</div>
flowchart LR
    P["Initial Population"] --> E["Objective Evaluation"] --> N["Non-Dominated Sorting"]
    N --> C["Crowding Distance"] --> S["Selection"] --> X["Crossover"] --> M["Mutation"] --> E
    N --> PF["🏅 Pareto Front"] --> R["⚖️ Compromise Solution"]

    classDef loop fill:#6366F1,stroke:#052e16,color:#fff
    classDef res fill:#16A34A,stroke:#052e16,color:#fff
    class P,E,N,C,S,X,M loop
    class PF,R res
<div align="center"><sub><b>Output:</b> a Pareto set of trade-off solutions, then a chosen compromise plan.</sub></div>
<a id="geospatial"></a>

🛰️ Geospatial Intelligence
FarmOptima uses the farm as a spatial context, not merely a point — deriving vegetation insight from satellite imagery.

flowchart LR
    A["🗺️ Farm Location / Polygon"] --> B["🌍 Google Earth Engine"] --> C["🛰️ Sentinel-2 Imagery"]
    C --> D["🎚️ Band Processing"] --> E["🌿 NDVI"] --> F["📊 Vegetation Insight"] --> G["🌾 Recommendation Context"]
    classDef geo fill:#15803D,stroke:#052e16,color:#fff
    class A,B,C,D,E,F,G geo
<div align="center">
Current spatial stack

<img src="https://img.shields.io/badge/Leaflet-199900?style=flat-square&logo=leaflet&logoColor=white"/> <img src="https://img.shields.io/badge/OpenStreetMap-7EBC6F?style=flat-square&logo=openstreetmap&logoColor=white"/> <img src="https://img.shields.io/badge/GeoJSON-2563EB?style=flat-square"/> <img src="https://img.shields.io/badge/Sentinel--2-1E40AF?style=flat-square"/> <img src="https://img.shields.io/badge/Google_Earth_Engine-4285F4?style=flat-square&logo=googleearth&logoColor=white"/> <img src="https://img.shields.io/badge/NDVI-16A34A?style=flat-square"/> </div>
<a id="provenance"></a>

🔎 Data Provenance & Freshness
Every value carries where it came from and how fresh it is — live, cached, model-derived, or fallback.

Soil evidence precedence — highest-trust source wins:

flowchart LR
    A["🧪 LAB_MEASUREMENT"] --> B["🤖 MODEL_PREDICTION"] --> C["💾 CACHED_API"] --> D["🧩 MOCK / FALLBACK"]
    classDef hi fill:#16A34A,stroke:#052e16,color:#fff
    classDef md fill:#65A30D,stroke:#052e16,color:#fff
    classDef lo fill:#CA8A04,stroke:#052e16,color:#fff
    classDef fb fill:#B91C1C,stroke:#052e16,color:#fff
    class A hi
    class B md
    class C lo
    class D fb
<div align="center">
Domain	Current Source	Status
🌦️ Weather	NASA POWER	Live + fallback
🌱 Soil	SoilGrids v2.0	Model prediction
🧪 Soil lab	Verified lab record	Higher precedence
🛰️ Satellite	GEE / Sentinel-2	Integrated + fallback
📈 Market	AGMARKNET-derived CSV	Static historical dataset
🗺️ Maps	OpenStreetMap	Integrated
</div>
<a id="xai"></a>

🤖 Explainable AI
The AI assistant is the explanation layer above the recommendation engine — grounded in the structured farm context, not free-floating chat.

flowchart LR
    A["🌾 Recommendation Engine"] --> B["🧱 Structured Farm Context"] --> C["🔗 Grounding / Context Builder"] --> D["🤖 AI Assistant"] --> E["🗣️ Human-readable Explanation"]
    classDef xai fill:#6D28D9,stroke:#052e16,color:#fff
    class A,B,C,D,E xai
The assistant can explain: why this crop, which factors drove the decision, how soil / weather / NDVI contributed, what water & fertilizer actions are suggested, and which data sources were used.

🧪 Engineering & Reliability
<table> <tr> <td valign="top" width="33%">
🔐 Security

JWT / Bearer auth · password hashing · protected farm operations · rate limiting · environment secrets

</td> <td valign="top" width="33%">
🧱 Architecture

Thin API routes → service layer → pure core algorithms → database models → validated schemas

</td> <td valign="top" width="34%">
🛡️ Reliability

Timeout handling · fallbacks · structured exceptions · Pydantic validation · provenance tracking

</td> </tr> </table>
[!TIP] Clean separation of concerns keeps the MCDM / NSGA-II core pure and testable — decoupled from I/O, framework, and data-source details.

<a id="stack"></a>

🛠️ Technology Stack
<div align="center">
🖥️ Frontend <br/> <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB"/> <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white"/> <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white"/> <img src="https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white"/> <img src="https://img.shields.io/badge/Axios-5A29E4?style=for-the-badge&logo=axios&logoColor=white"/> <img src="https://img.shields.io/badge/Recharts-22B5BF?style=for-the-badge"/>

⚙️ Backend <br/> <img src="https://img.shields.io/badge/Python_3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white"/> <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/> <img src="https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white"/> <img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white"/> <img src="https://img.shields.io/badge/Uvicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white"/> <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white"/>

🧠 Intelligence  ·  🌍 Geospatial & Data <br/> <img src="https://img.shields.io/badge/Machine_Learning-FF6F00?style=for-the-badge&logo=scikitlearn&logoColor=white"/> <img src="https://img.shields.io/badge/AHP_/_Fuzzy_AHP-6366F1?style=for-the-badge"/> <img src="https://img.shields.io/badge/TOPSIS-2563EB?style=for-the-badge"/> <img src="https://img.shields.io/badge/ELECTRE-7C3AED?style=for-the-badge"/> <img src="https://img.shields.io/badge/NSGA--II-15803D?style=for-the-badge"/> <br/> <img src="https://img.shields.io/badge/Google_Earth_Engine-4285F4?style=for-the-badge&logo=googleearth&logoColor=white"/> <img src="https://img.shields.io/badge/Sentinel--2-1E40AF?style=for-the-badge"/> <img src="https://img.shields.io/badge/SoilGrids-8B5E3C?style=for-the-badge"/> <img src="https://img.shields.io/badge/NASA_POWER-0B3D91?style=for-the-badge&logo=nasa&logoColor=white"/> <img src="https://img.shields.io/badge/OpenStreetMap-7EBC6F?style=for-the-badge&logo=openstreetmap&logoColor=white"/>

</div>
📁 Project Structure
<details> <summary><b>Click to expand the repository layout</b></summary>
FarmOptima/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # thin HTTP routes
│   │   ├── core/             # pure algorithms (AHP, TOPSIS, ELECTRE, NSGA-II)
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/ai/      # data services + grounded AI
│   │   ├── utils/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # React + Vite + Tailwind dashboard
│   ├── src/  public/  package.json  vite.config.*
├── scripts/                  # research + benchmark runners
│   ├── run_research_evaluation.py
│   ├── run_optimization_comparison.py
│   └── run_sensitivity_analysis.py
├── reports/                  # generated results (JSON + MD)
├── docs/
└── README.md
</details>
<a id="api"></a>

🔌 API Surface
<div align="center">
Endpoint	Method	Purpose
/api/auth/register	POST	User registration
/api/auth/login	POST	Login + token
/api/weather	GET	Weather context
/api/soil	GET	Soil context
/api/satellite	GET	Satellite / NDVI context
/api/farms	GET POST	Saved farms
/api/farms/{farm_id}/soil-tests	POST	Verified soil test
/api/recommend	POST	Main recommendation pipeline
/api/ai/chat	POST	Grounded AI assistant
</div>
📖 Swagger UI → http://localhost:8000/docs  ·  OpenAPI → http://localhost:8000/openapi.json

<a id="run"></a>

🚀 Run Locally
1️⃣ Clone

git clone https://github.com/MITHLESH55/FarmOptima.git
cd FarmOptima
2️⃣ Backend — FastAPI on :8000

cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
3️⃣ Frontend — React + Vite on :5173

cd frontend
npm install
npm run dev
<div align="center">
🖥️ Frontend → http://localhost:5173  ·  ⚙️ Backend → http://localhost:8000

</div>
<a id="validation"></a>

✅ Validation
<div align="center">
Check	Result
Backend automated tests	✅ 340 / 340 passed
Frontend production build	✅ Passed
Research pipelines	✅ 3 / 3 passed
Submission / documentation dossier	✅ Complete
</div>
# Backend tests
cd backend && pytest

# Frontend build
cd frontend && npm run build

# Research evaluation
python scripts/run_research_evaluation.py
python scripts/run_optimization_comparison.py
python scripts/run_sensitivity_analysis.py
📊 Research Snapshot
<div align="center">
MCDM Evaluation — 6 Indian agro-climatic zones

Metric	Observed
Crisp ↔ Fuzzy AHP mean Spearman ρ	0.9768
Equal-weight TOPSIS ↔ Fuzzy AHP correlation	0.8241
Fuzzy AHP ↔ ELECTRE cross-check correlation	0.9105
Top-1 agreement: Crisp vs Fuzzy AHP	100%
Mean algorithm execution	< 1.5 ms
Optimization Benchmark

Metric	Observed
Non-dominated solutions	~40
Average water gap	18.2%
Average fertilizer gap	10.5%
Benchmark execution	~625 ms
</div>
[!NOTE] Results come from the project's documented benchmark configuration. Optimizer settings can differ between application defaults and research benchmark scripts.

📅 Project Timeline
<div align="center"><sub>01 July 2026 → 27 September 2026</sub></div>
gantt
    title FarmOptima — Development Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b

    section Foundation
    Problem + Literature Review        :done, a1, 2026-07-01, 10d
    Requirements + Architecture        :done, a2, 2026-07-08, 11d
    Data Sources + Datasets            :done, a3, 2026-07-15, 22d

    section Engineering
    Backend + Database                 :done, b1, 2026-08-01, 15d
    AI/ML Recommendation               :done, b2, 2026-08-05, 21d
    Weather + Soil + Satellite         :done, b3, 2026-08-08, 21d
    Frontend Dashboard                 :done, b4, 2026-08-05, 45d

    section Decision
    AHP/Fuzzy/TOPSIS/ELECTRE           :done, c1, 2026-08-18, 19d
    Fertilizer + Irrigation            :done, c2, 2026-08-28, 16d
    NSGA-II Optimization               :done, c3, 2026-09-02, 14d

    section Finalization
    Explainable AI                     :done, d1, 2026-09-08, 13d
    Integration + Testing              :done, d2, 2026-09-15, 9d
    Research + Sensitivity             :done, d3, 2026-09-18, 8d
    Documentation + Submission         :done, d4, 2026-09-22, 6d
🌍 Sustainable Development Alignment
<div align="center">
Relevance
<img src="https://img.shields.io/badge/SDG_2-Zero_Hunger-DDA63A?style=flat-square"/>	Food production & agricultural decision support
<img src="https://img.shields.io/badge/SDG_6-Clean_Water-26BDE2?style=flat-square"/>	Water-aware irrigation planning
<img src="https://img.shields.io/badge/SDG_9-Innovation-FD6925?style=flat-square"/>	AI, GIS & remote-sensing engineering innovation
<img src="https://img.shields.io/badge/SDG_12-Responsible_Use-BF8B2E?style=flat-square"/>	Resource-efficient fertilizer / water planning
<img src="https://img.shields.io/badge/SDG_13-Climate_Action-3F7E44?style=flat-square"/>	Climate-aware agricultural decisions
</div>
<a id="roadmap"></a>

🛣️ Roadmap
<table> <tr> <td valign="top" width="50%">
⏭️ Next

PostgreSQL-first deployment
Historical recommendation tracking
Expanded spatial analytics
Production observability
</td> <td valign="top" width="50%">
🔬 Future Research

IoT sensors · drone imagery
Disease detection
Field-validated yield prediction
Multilingual voice assistant
Smart irrigation · mobile app
</td> </tr> </table>
⚠️ Current Limitations & Responsible Use
<details> <summary><b>Click to expand — scope & honest caveats</b></summary> <br/>
Market — uses a curated historical / local AGMARKNET-derived CSV rather than a live intraday mandi stream.
Soil — SoilGrids provides regional model predictions; verified laboratory measurements take higher precedence.
Satellite — cloud cover and source availability can affect observations, so fallback handling is used where appropriate.
Yield — optimization aligns resource allocation with reference targets; it is not a validated field-trial yield guarantee.
[!CAUTION] Responsible use: FarmOptima is a decision-support system. Recommendations should be weighed alongside local conditions, current advisories, soil testing, and professional agronomic guidance.

</details>
📚 Methodology References
Saaty — Analytic Hierarchy Process (AHP)
Chang — Fuzzy AHP extent-analysis methodology
Hwang & Yoon — TOPSIS
Roy — ELECTRE / outranking
Deb et al. (2002) — NSGA-II
FAO-56 / CROPWAT — water-management references
ICAR / agricultural-university — nutrient recommendation references
<div align="center">
🌾 From Raw Farm Data to Explainable Decisions
<sub>AI · ML · GIS · Remote Sensing · MCDM · Optimization · Explainable AI</sub>

<br/>
Built as a final-year engineering project focused on practical AI, intelligent decision-making, and sustainable resource planning.

<br/>
<a href="https://github.com/MITHLESH55/FarmOptima"><img src="https://img.shields.io/badge/⭐_Star_this_repo-052e16?style=for-the-badge&logo=github&logoColor=white"/></a> <a href="#top"><img src="https://img.shields.io/badge/⬆_Back_to_Top-15803D?style=for-the-badge"/></a>

</div> <img src="https://capsule-render.vercel.app/api?type=waving&color=0:052e16,25:14532D,50:15803D,75:16A34A,100:052e16&height=130&section=footer&animation=fadeIn" width="100%"/>
