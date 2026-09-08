# Phase 3: Decision Intelligence, Farm-Specific Fertilizer Engine & Multi-Objective Optimization Report

## Executive Summary
Phase 3 of FarmOptima introduces a mathematically rigorous, scientifically defensible Decision Intelligence architecture. This phase connects real-world environmental data and laboratory soil measurements with dynamic agronomic suitability modeling, Analytic Hierarchy Process (AHP), Fuzzy AHP, TOPSIS ranking, ELECTRE I outranking cross-checking, farm-specific commercial fertilizer decomposition (DAP, Urea, MOP), FAO-based water balance calculations, and elitist NSGA-II multi-objective resource optimization.

---

## 1. Files Changed & Added in Phase 3

### Core Backend Modules
- **[`backend/app/crop_database.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/crop_database.py)**: Curated literature-typical crop agronomic parameters (water demand, pH bands, temperature/rainfall bands, NPK baselines).
- **[`backend/app/core/suitability.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/suitability.py)**: Smooth continuous band scoring in $[0, 1]$ for climate, soil, water efficiency, and market suitability.
- **[`backend/app/core/criteria.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/criteria.py)**: Dynamic decision matrix generator supporting neutral baseline scoring (0.5) for unavailable data sources.
- **[`backend/app/core/mcdm.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/mcdm.py)**: Eigenvector AHP with Consistency Ratio ($\text{CR} < 0.10$ check), vector-normalized TOPSIS, and ELECTRE I outranking matrix.
- **[`backend/app/core/fuzzy_ahp.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/fuzzy_ahp.py)**: Chang's extent analysis on Triangular Fuzzy Numbers (TFNs).
- **[`backend/app/core/nsga2.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/nsga2.py)**: Real NSGA-II multi-objective optimization (water gap, fertilizer gap, resource cost) with elitist non-dominated sorting and crowding distance.
- **[`backend/app/services/fertilizer_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/fertilizer_service.py)**: Farm-specific commercial fertilizer allocation (DAP, Urea, MOP), soil N adjustment, area scaling, and 3-stage split application schedule.
- **[`backend/app/services/explanation_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/explanation_service.py)**: Machine-readable & natural language explanation engine.
- **[`backend/app/api/routes/recommend.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/api/routes/recommend.py)**: Orchestration layer connecting data provenance, MCDM, fertilizer, NSGA-II, and audit persistence.

### Documentation & Audit Artifacts
- **[`docs/DECISION_INTELLIGENCE_AUDIT.md`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/docs/DECISION_INTELLIGENCE_AUDIT.md)** *(NEW)*: Complete audit log of the decision pipeline from farm input to recommendation output.
- **[`docs/PHASE3_DECISION_INTELLIGENCE_REPORT.md`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/docs/PHASE3_DECISION_INTELLIGENCE_REPORT.md)** *(NEW)*: Comprehensive final report.

### Test Suites
- **[`backend/tests/test_decision_intelligence.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/tests/test_decision_intelligence.py)** *(NEW)*: End-to-end decision pipeline tests.
- **[`backend/tests/test_mcdm_integrity.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/tests/test_mcdm_integrity.py)** *(NEW)*: Dedicated AHP, TOPSIS, and ELECTRE I integrity tests.
- **[`backend/tests/test_farm_specific_fertilizer.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/tests/test_farm_specific_fertilizer.py)** *(NEW)*: Dedicated commercial fertilizer conversion & acreage scaling tests.
- **[`backend/tests/test_nsga2_integrity.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/tests/test_nsga2_integrity.py)** *(NEW)*: Dedicated NSGA-II non-dominated sorting & Pareto front tests.
- **[`backend/tests/test_water_requirement.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/tests/test_water_requirement.py)** *(NEW)*: Water balance & physical constant unit conversion tests.

---

## 2. SmartAgri Integration
- FarmOptima reuses the agronomic suitability rules and crop parameter database (`CROP_DATABASE`) established in the SmartAgri knowledge base.
- Clean backend service boundaries isolate raw input parsing, suitability scoring (`suitability.py`), criteria evaluation (`criteria.py`), and commercial fertilizer decomposition (`fertilizer_service.py`), avoiding duplicate logic across endpoints.

---

## 3. Crop Recommendation Flow
1. **Farm Input Ingestion**: Receives `lat`, `lon`, `polygon_geojson`, `field_area_acres`, and authenticated user credentials.
2. **Data Collection**: Retrieves real environmental observations (NASA POWER, SoilGrids v2.0 / Lab Test, Open-Meteo, Sentinel-2 GEE, AGMARKNET).
3. **Agronomic Suitability Scoring**: Evaluates continuous smooth band scores for climate, soil, water efficiency, and market index across candidate crops.
4. **MCDM Ranking**: Applies AHP / Fuzzy AHP criteria weights, computes TOPSIS closeness coefficients ($C_i^*$), cross-checks with ELECTRE I outranking counts, and resolves lexicographical tie-breaks.
5. **Fertilizer Engine**: Calculates exact elemental N-P-K nutrient requirements, applies soil N adjustments, converts elemental demand into commercial fertilizer bags (DAP, Urea, MOP), and generates a 3-stage split application schedule.
6. **NSGA-II Optimization**: Simulates a 60-individual population over 80 generations to optimize water gap, fertilizer gap, and monetary cost simultaneously, returning the non-dominated Pareto front and selecting the minimum-distance compromise solution.
7. **Explainability & Audit Trail**: Generates machine-readable and natural language explanations, persisting the run to SQLite database.

---

## 4. AHP Implementation
- **Pairwise Matrix**: Evaluates relative importance on Saaty's 1–9 scale:
  $$A = \begin{pmatrix} 1 & 2 & 3 & 3 \\ 1/2 & 1 & 2 & 2 \\ 1/3 & 1/2 & 1 & 2 \\ 1/3 & 1/2 & 1/2 & 1 \end{pmatrix}$$
- **Principal Eigenvector Approximation**: Calculated via normalized column averaging ($w = \text{mean}_{\text{row}}(A / \text{col\_sum})$).
- **Consistency Verification**: $\lambda_{\max} = \frac{1}{n} \sum \frac{(Aw)_i}{w_i}$; $\text{CI} = \frac{\lambda_{\max} - n}{n - 1}$; $\text{CR} = \frac{\text{CI}}{\text{RI}_4} = \frac{\text{CI}}{0.90}$.
- **Diagnostic Usage**: CR is reported strictly as an independent matrix consistency metric (`ahp_consistency_ratio`), **never labeled as a crop suitability score or confidence value**.

---

## 5. TOPSIS Implementation
- **Decision Matrix**: $X_{8 \times 4}$ representing 8 candidate crops across 4 benefit criteria.
- **Vector Normalization**: $r_{ij} = \frac{x_{ij}}{\sqrt{\sum_{k=1}^m x_{kj}^2}}$; $v_{ij} = w_j \cdot r_{ij}$.
- **Ideal Solutions**: Ideal Best $v_j^+ = \max_i v_{ij}$; Ideal Worst $v_j^- = \min_i v_{ij}$.
- **Distances & Closeness**: $S_i^+ = \sqrt{\sum (v_{ij} - v_j^+)^2}$; $S_i^- = \sqrt{\sum (v_{ij} - v_j^-)^2}$; $C_i^* = \frac{S_i^-}{S_i^+ + S_i^-}$. Alternatives are ranked by descending $C_i^*$.

---

## 6. ELECTRE I Status
- **Concordance Index**: $C(a, b) = \sum_{c: x_{ac} \ge x_{bc}} w_c$.
- **Discordance Index**: $D(a, b) = \max_{c: x_{ac} < x_{bc}} \frac{|x_{ac} - x_{bc}|}{\text{range}_c}$.
- **Outranking Thresholds**: Concordance threshold $c^* = 0.60$, Discordance threshold $d^* = 0.40$.
- **Role**: Used as a cross-checking signal (`electre_net_outranking`) alongside TOPSIS.

---

## 7. Fertilizer Calculation Methodology
1. **Base Requirement**: Retrieved from crop database ($N_{\text{base}}, P_{\text{base}}, K_{\text{base}}$ in kg/acre).
2. **Soil Test Adjustment**: If soil N is deficient ($<30 \text{ mg/kg}$), N is increased by 10%; if soil N is high ($>60 \text{ mg/kg}$), N is decreased by 10%.
3. **Commercial Fertilizer Conversion**:
   - $\text{DAP}_{\text{acre}} = \frac{P_{\text{base}}}{0.46}$ (Supplies 18% N and 46% P₂O₅).
   - $N_{\text{supplied\_by\_DAP}} = \text{DAP}_{\text{acre}} \times 0.18$.
   - $\text{Urea}_{\text{acre}} = \frac{\max(0, N_{\text{req}} - N_{\text{supplied\_by\_DAP}})}{0.46}$ (Supplies remaining N; **prevents double-counting N supplied by DAP**).
   - $\text{MOP}_{\text{acre}} = \frac{K_{\text{base}}}{0.60}$ (Supplies 60% K₂O).
4. **Field Scaling**: Total field requirement $= \text{DAP}_{\text{acre}} \times \text{field\_area\_acres}$.
5. **Split Schedule**: Basal (100% DAP + 100% MOP + 50% Urea), Top Dressing 1 (25% Urea), Top Dressing 2 (25% Urea).

---

## 8. Water Calculation Methodology
- **Physical Constant**: $\text{ACRE\_TO\_LITERS\_PER\_MM} = 4046.86 \text{ L/(acre}\cdot\text{mm)}$.
- **Crop Seasonal Need**: $W_{\text{req}} = \text{water\_need\_mm\_season} \times 4046.86 \text{ L/acre}$.
- **Rainfall Credit**: $R_{\text{credit}} = R_{30\text{d}} \times 4046.86 \times 4 \times 0.50 \text{ L/acre}$.
- **Soil Moisture Credit**: $\text{SM}_{\text{credit}} = \frac{\text{SM}_{\%}}{100} \times W_{\text{req}} \times 0.20$.
- **Net Irrigation Supply**: Total Irrigation + $R_{\text{credit}} + \text{SM}_{\text{credit}}$.

---

## 9. NSGA-II Methodology
- **Reference**: Deb et al. (2002), IEEE Transactions on Evolutionary Computation.
- **Population**: 60 individuals, 80 generations.
- **Genetic Operators**: Simulated Binary Crossover (SBX, $\eta=15$), Polynomial Mutation, Binary Tournament Selection by $(Rank, Crowding)$.
- **Selection**: Elitist $(N + N)$ non-dominated sorting and crowding distance truncation.
- **Compromise Solution Selection**: Minimum normalized Euclidean distance to ideal point $(0, 0, 0)$ on the non-dominated Pareto front.

---

## 10. Objective Functions
1. **$f_1(x) = \text{Water Gap}$**: $\frac{|\text{Effective Supply} - \text{Crop Water Demand}|}{\text{Crop Water Demand}}$ (Minimization).
2. **$f_2(x) = \text{Fertilizer Gap}$**: $\frac{|\text{Fertilizer N Applied} - \text{Target N Demand}|}{\text{Target N Demand}}$ (Minimization).
3. **$f_3(x) = \text{Resource Cost}$**: $(\text{Water L} \times 0.05) + (\text{Fertilizer N kg} \times 25.0)$ in local currency units (Minimization).

---

## 11. Constraints
- **Decision Variable Bounds**:
  - Irrigation Water $x_1 \in [\text{Naive Water} \times 0.2, \text{Naive Water} \times 2.0] \text{ L/week}$.
  - Fertilizer Nitrogen $x_2 \in [\text{Target N} \times 0.3, \text{Target N} \times 2.0] \text{ kg/acre}$.
- **Non-Negativity**: All decision variables and objective values strictly $\ge 0$.

---

## 12. Assumptions
- **Cropping Season Duration**: 16 weeks (112 days).
- **Commercial Fertilizer Formulations**: DAP (18:46:0), Urea (46:0:0), MOP (0:0:60).
- **Unit Water Cost**: 0.05 INR per Liter (agricultural canal/borewell pumping estimate).
- **Unit Fertilizer Cost**: 25.0 INR per kg (subsidized commercial N baseline).

---

## 13. Data Sources
- **NASA POWER REST API**: Daily precipitation, 2m temperature, relative humidity, solar radiation, wind speed (`LIVE_API`).
- **ISRIC SoilGrids v2.0 REST API**: Soil pH, sand %, clay %, total N, organic carbon at 0-5cm (`MODEL_PREDICTION`).
- **Open-Meteo REST API**: Volumetric soil moisture (`LIVE_API`).
- **GEE Sentinel-2 (`COPERNICUS/S2_SR_HARMONIZED`)**: Field polygon geometry NDVI reduction (`SATELLITE_OBSERVATION`).
- **Laboratory Soil Analysis DB (`SoilTest`)**: Verified farmer soil sample (`LAB_MEASUREMENT`).
- **AGMARKNET CSV**: Wholesale market prices (`STATIC_DATASET`).

---

## 14. Provenance Handling
- Every environmental data item attaches a structured `ProvenanceItem`:
  - `source_name` (e.g. `nasa-power`, `soilgrids`, `lab_measurement`, `gee-sentinel2`, `agmarknet_historical_csv`)
  - `source_type` (`LIVE_API`, `MODEL_PREDICTION`, `LAB_MEASUREMENT`, `SATELLITE_OBSERVATION`, `STATIC_DATASET`, `CACHED_API`, `MOCK/FALLBACK`)
  - `observation_date`, `retrieved_at`, `is_stale`, `quality_status`, `endpoint_reference`

---

## 15. Explanation Architecture
- Machine-readable structure attached to `RecommendationResponse` detailing dominant criteria, AHP weights, TOPSIS closeness coefficient, ELECTRE cross-check outranking counts, limiting environmental factors, missing data markers, and NSGA-II compromise solution rationale.

---

## 16. Database & Versioning Changes
- **`Farm` model**: Added `polygon_geojson` (JSON) and `field_area_acres` (Float).
- **`SoilTest` model**: Ingests verified lab measurements (`ph`, `nitrogen_mg_kg`, `organic_carbon_g_kg`, `sand_pct`, `clay_pct`, `sample_date`, `lab_name`).
- **`Recommendation` model**: Stores full JSON input/output snapshot linked to `Farm.id`.

---

## 17. Frontend Changes
- The frontend dynamically displays the backend recommendation response, crop ranking, TOPSIS closeness scores, AHP weights, fertilizer plan, commercial fertilizer bag quantities (DAP, Urea, MOP), 3-stage split application schedule, and Pareto resource plan.
- Verified build with Vite: **0 errors**.

---

## 18. Testing & Test Counts
- **Total Backend Pytest Suite**: **298 / 298 passed** (100% pass rate in 110 seconds).
- **Phase 3 Dedicated Test Suites**:
  - `test_decision_intelligence.py`: 3 / 3 passed.
  - `test_mcdm_integrity.py`: 4 / 4 passed.
  - `test_farm_specific_fertilizer.py`: 4 / 4 passed.
  - `test_nsga2_integrity.py`: 3 / 3 passed.
  - `test_water_requirement.py`: 2 / 2 passed.
  - `test_data_foundation.py`: 10 / 10 passed.

---

## 19. Known Limitations
1. **GEE Service Account Authentication**: Requires `GEE_PROJECT` configuration in server environment for live Earth Engine API calls. When unauthenticated, falls back to DB cache (`CACHED_API`) or explicit unavailable marker (`MOCK/FALLBACK`).
2. **AGMARKNET Live API Ingestion**: Market prices are sourced from AGMARKNET historical dataset (`STATIC_DATASET`).

---

## 20. Scientifically Supported Assumptions Summary
All agronomic parameters (pH bands, temperature ranges, NPK baseline demands, DAP/Urea/MOP fertilizer grades, physical unit conversion constants) are anchored to established FAO and ICAR literature references and explicitly documented in `docs/DECISION_INTELLIGENCE_AUDIT.md`.
