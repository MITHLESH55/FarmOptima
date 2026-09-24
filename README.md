# FarmOptima — Scientific Decision Support & Precision Agronomic Intelligence

> **FarmOptima** is an auditable, peer-defensible decision-intelligence platform for precision crop selection and multi-objective resource optimization. It integrates remote-sensing satellite observations, global digital soil mapping, meteorological reanalysis, multi-criteria decision modeling (Fuzzy-AHP, TOPSIS, ELECTRE-I), evolutionary Pareto optimization (NSGA-II), and deterministic AI grounding.

---

## 1. System Architecture & Core Modules

```
                        ┌─────────────────────────────────────────────────────────┐
                        │              React 18 / Tailwind Dashboard              │
                        │   • Live Field Data Matrix  • Auditable MCDM Ranking    │
                        │   • NSGA-II Pareto Frontier • Multilingual AI Assistant │
                        └────────────────────────────┬────────────────────────────┘
                                                     │ HTTP / REST API (FastAPI)
                        ┌────────────────────────────▼────────────────────────────┐
                        │                   FastAPI Application                   │
                        │   • Rate Limiter • JWT Auth • Pydantic Schema Validation│
                        └──────┬─────────────────────┬─────────────────────┬──────┘
                               │                     │                     │
                ┌──────────────▼──────┐   ┌──────────▼──────────┐   ┌──────▼──────────────┐
                │   Services Layer    │   │   Core Algorithms   │   │  AI Grounding Engine│
                │ • NASA POWER API    │   │ • Chang Fuzzy-AHP   │   │ • Semantic Verifier │
                │ • ISRIC SoilGrids   │   │ • Vector TOPSIS     │   │ • Context Builder   │
                │ • Copernicus S2 GEE │   │ • ELECTRE-I Outrank │   │ • Multi-Dialect LLM │
                │ • Agmarknet APMC    │   │ • NSGA-II Pareto GPO│   │ • Viva Question QA  │
                └─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

---

## 2. Algorithmic Formulations

### 2.1 Criteria Weighting: Fuzzy-AHP (Chang's Extent Analysis)
- Pairwise expert comparisons represented as Triangular Fuzzy Numbers (TFNs) $\tilde{M}_{ij} = (l_{ij}, m_{ij}, u_{ij})$.
- Fuzzy synthetic extent computed via $S_i = \sum_{j=1}^m \tilde{M}_{ij} \otimes \left[\sum_{i=1}^n \sum_{j=1}^m \tilde{M}_{ij}\right]^{-1}$.
- Degrees of possibility $V(S_i \ge S_k)$ normalized to produce crisp, uncertainty-hedged weights with Saaty consistency ratio verification ($CR < 0.10$).

### 2.2 Crop Ranking: TOPSIS
- Normalized decision matrix $R_{ij} = \frac{x_{ij}}{\sqrt{\sum_{k=1}^m x_{kj}^2}}$, weighted matrix $V_{ij} = w_j R_{ij}$.
- Euclidean distance to ideal-best ($A^+$) and ideal-worst ($A^-$):
  $$D_i^+ = \sqrt{\sum_{j=1}^n (V_{ij} - V_j^+)^2}, \quad D_i^- = \sqrt{\sum_{j=1}^n (V_{ij} - V_j^-)^2}$$
- Relative closeness coefficient $C_i = \frac{D_i^-}{D_i^+ + D_i^-} \in [0, 1]$.

### 2.3 Cross-Check: ELECTRE-I Outranking
- Concordance $c(a, b) = \sum_{j: v_{aj} \ge v_{bj}} w_j$ and Discordance $d(a, b) = \max_j \frac{|v_{aj} - v_{bj}|}{R_j}$.
- Alternative $a$ outranks $b$ ($a \succ b$) if $c(a, b) \ge 0.60$ and $d(a, b) \le 0.40$.
- Net Outranking Score $O_i - \bar{O}_i = (\#\text{ outranked by } i) - (\#\text{ that outrank } i)$.

### 2.4 Multi-Objective Resource Allocation: NSGA-II
- Optimizes 3 conflicting objectives simultaneously:
  1. $\text{Water Gap} = \frac{|\text{Effective Supply} - \text{Crop Need}|}{\text{Crop Need}}$
  2. $\text{Fertilizer Gap} = \frac{|\text{Fertilizer Applied} - \text{Crop Agronomic Target}|}{\text{Crop Agronomic Target}}$
  3. $\text{Monetary Resource Cost} = \text{Irrigation Cost} + \text{Commercial Fertilizer Cost}$
- Fast non-dominated sorting and crowding distance diversity preservation return a non-dominated Pareto frontier ($20-40$ alternative trade-off points).

---

## 3. Data Provenance & Quality Taxonomy

| Domain | Provider | Classification | Reference / Epoch | Fallback / Quality Control |
|:---|:---|:---|:---|:---|
| **Weather** | NASA POWER / Open-Meteo API | `LIVE_API` | 30-day moving daily aggregation | Database cache with explicit staleness badge |
| **Soil** | ISRIC SoilGrids v2.0 (250m) | `MODEL_PREDICTION` | Global Depth 0–5cm Layer | Subordinate to farmer `LAB_MEASUREMENT` |
| **Vegetation** | Copernicus Sentinel-2 L2A (GEE) | `SATELLITE_OBSERVATION`| 10m Multi-spectral Scene | Clear honest basemap fallback if GEE offline |
| **Market** | AGMARKNET APMC Archive | `STATIC_DATASET` | Seasonal Agmarknet Benchmark | Marked as static historical price baseline |
| **MCDM** | Fuzzy-AHP + TOPSIS Engine | `CALCULATION` | Real-time on demand | $CR < 0.10$ mathematical verification |
| **Resource Plan**| Multi-Objective NSGA-II | `OPTIMIZATION RESULT` | 60 Gens / 40 Population | Pareto Euclidean compromise point |

---

## 4. Reproducible Research Pipelines

To run automated research evaluations, optimization comparisons, and sensitivity analyses:

```bash
# 1. MCDM Comparison (Equal-Weight vs Crisp AHP vs Fuzzy-AHP vs ELECTRE-I)
python scripts/run_research_evaluation.py

# 2. Optimization Comparison (Baseline GPO vs Multi-Objective NSGA-II)
python scripts/run_optimization_comparison.py

# 3. Sensitivity & Robustness Analysis (Weight perturbations, fuzzy spread, ELECTRE thresholds)
python scripts/run_sensitivity_analysis.py
```

Generated reports are located in `reports/`:
- `reports/RESEARCH_EVALUATION_REPORT.md` (`research_evaluation_results.json`)
- `reports/OPTIMIZATION_COMPARISON_REPORT.md` (`optimization_comparison_results.json`)
- `reports/SENSITIVITY_ANALYSIS_REPORT.md` (`sensitivity_analysis_results.json`)

---

## 5. Quick Start & Execution

### Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
- API Documentation: `http://localhost:8000/docs`
- Run Test Suite: `pytest tests/ -v` (340 tests passed, 100%)

### Frontend Setup (React / Vite)
```bash
cd frontend
npm install
npm run dev
```
- Web Application: `http://localhost:5173`
- Production Build: `npm run build`

---

## 6. Known Academic & Field Limitations

1. **Market Prices:** Market suitability indices are computed from historical AGMARKNET APMC seasonal datasets (`STATIC_DATASET`). Live real-time intraday mandi tickers are not used.
2. **Soil Spatial Resolution:** Soil parameters utilize ISRIC SoilGrids v2.0 250-meter spatial machine learning predictions (`MODEL_PREDICTION`), which represent regional estimates unless replaced by farmer-uploaded laboratory soil test certificates (`LAB_MEASUREMENT`).
3. **Yield Projections:** Resource optimization calculates agronomic allocation alignment against FAO-56 irrigation and ICAR nutrient recommendations; it is not a validated longitudinal field trial yield guarantee.
