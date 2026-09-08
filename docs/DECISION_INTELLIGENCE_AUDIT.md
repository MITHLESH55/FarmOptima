# FarmOptima Decision Intelligence Audit Document

## Executive Summary
This audit traces the complete multi-stage decision intelligence pipeline of FarmOptima, from farm inputs to multi-criteria crop ranking, farm-specific fertilizer recommendation, water requirement estimation, NSGA-II multi-objective resource trade-off optimization, and explainable AI generation.

---

## 1. Decision Flow Architecture

```
[ Farm Input: (Lat, Lon, Polygon, Acreage, Lab Soil Test) ]
                     │
                     ▼
[ Real Environmental Data Collection & Provenance ]
   ├── Weather (NASA POWER / Open-Meteo: Temp, Rain, Humidity, Solar, Wind)
   ├── Soil (Lab Soil Test > ISRIC SoilGrids v2.0: pH, N, Org C, Sand, Clay)
   ├── Satellite (GEE Copernicus Sentinel-2: Polygon NDVI Reduction)
   └── Market (AGMARKNET Historical CSV: Crop Prices)
                     │
                     ▼
[ Dynamic Crop Suitability Profile Generator (suitability.py) ]
   ├── Continuous Smooth Band Scoring: [0, 1] per parameter
   └── Sub-Scores: Climate, Soil, Water Efficiency, Market
                     │
                     ▼
[ Decision Matrix Construction & Normalization (criteria.py) ]
   └── Matrix Rows: 8 Crops (Wheat, Rice, Maize, Groundnut, Cotton, Sugarcane, Soybean, Chickpea)
   └── Matrix Columns: [climate_suitability, soil_suitability, water_efficiency, market_value]
                     │
                     ▼
[ Multi-Criteria Decision-Making Engine (mcdm.py & fuzzy_ahp.py) ]
   ├── 1. AHP (Analytic Hierarchy Process): Priority Vector, λmax, CI, CR (CR < 0.10 check)
   ├── 2. Fuzzy AHP (Chang's Extent Analysis): TFNs handle expert ambiguity
   ├── 3. TOPSIS: Vector Normalization, Ideal Best/Worst, Closeness Coefficient (Ci*)
   ├── 4. ELECTRE I: Concordance/Discordance Outranking Matrix (Cross-Check)
   └── 5. Ranking & Lexicographical Tie-Break
                     │
                     ▼
[ Top-Ranked Crop Selection & Farm-Specific Fertilizer Engine (fertilizer_service.py) ]
   ├── Crop Base Requirements (N, P₂O₅, K₂O per acre)
   ├── Soil Nutrient Status Adjustment (Lab Test or SoilGrids)
   ├── Net Deficit / Field Total Scaling (Area in Acres)
   ├── Commercial Fertilizer Conversion (DAP, Urea, MOP)
   └── Agronomic Split Application Schedule (Basal, Top Dressing 1, Top Dressing 2)
                     │
                     ▼
[ Multi-Objective Resource Optimizer (nsga2.py) ]
   ├── Objectives: (1) Water Gap, (2) Fertilizer Gap, (3) Resource Cost
   ├── NSGA-II: Elitist Non-Dominated Sorting, Crowding Distance Diversity, SBX Crossover, Polynomial Mutation
   └── Compromise Solution Selection (Min Normalized Distance to Ideal Point)
                     │
                     ▼
[ Explainability & Audit Trail (explanation_service.py & recommend.py) ]
   ├── Structured Machine-Readable & Natural-Language Explanations
   └── DB Audit Trail Persistence (Recommendation Record linked to Farm ID)
```

---

## 2. Stage-by-Stage Detailed Audit

### Stage 1: Environmental & Farm Data Collection
- **Input**: `LocationRequest` (`lat`, `lon`, `field_area_acres`, `polygon_geojson`).
- **Sources**: NASA POWER REST API (`LIVE_API`), ISRIC SoilGrids v2.0 (`MODEL_PREDICTION`), Open-Meteo (`LIVE_API`), GEE Sentinel-2 (`SATELLITE_OBSERVATION`), SoilTest DB (`LAB_MEASUREMENT`), AGMARKNET (`STATIC_DATASET`).
- **Missing Data Behavior**: Explicit `unavailable` markers (`MOCK/FALLBACK`) with zero fake values. When a data source is unreachable and no DB cache exists, parameters are returned as 0.0 with `quality_status = "unavailable"`, preventing silent false data generation.

### Stage 2: Suitability Scoring (`suitability.py`)
- **Formula**: Continuous smooth band function:
  $$\text{Score}(x) = \begin{cases} 1.0 & \text{if } x_{\text{opt\_min}} \le x \le x_{\text{opt\_max}} \\ \max\left(0, 1 - \frac{|x - x_{\text{opt}}|}{\text{span}}\right) & \text{otherwise} \end{cases}$$
- **Parameters Evaluated**: Temperature, Rainfall, Humidity (VPD proxy), Soil pH, Nitrogen adequacy ($N_{\text{target}} = 600 + N_{\text{demand}} \times 12$), Organic Carbon, Soil Moisture, NDVI vegetation, Water Efficiency, Market Index.
- **Output**: Sub-scores in $[0.0, 1.0]$.

### Stage 3: Decision Matrix Construction (`criteria.py`)
- **Input**: 8 candidate crops $\times$ 4 criteria (`climate_suitability`, `soil_suitability`, `water_efficiency`, `market_value`).
- **Missing-Data Handling**: If weather or soil is unavailable, neutral baseline score (0.5) is populated for affected columns so TOPSIS vector normalization remains mathematically valid without crashing or skewing.

### Stage 4: Multi-Criteria Decision-Making (MCDM)
- **AHP / Fuzzy AHP (`mcdm.py` & `fuzzy_ahp.py`)**:
  - **Inputs**: Pairwise comparison matrix $A_{4 \times 4}$.
  - **AHP Formulas**: Normalized column averaging for priority weights $w$; $\lambda_{\max} = \frac{1}{n}\sum \frac{(Aw)_i}{w_i}$; $\text{CI} = \frac{\lambda_{\max} - n}{n - 1}$; $\text{CR} = \frac{\text{CI}}{\text{RI}_4} = \frac{\text{CI}}{0.90}$.
  - **CR Usage**: Reported as diagnostic validation indicator (`ahp_consistency_ratio`, `ahp_is_consistent`). **Never confused with crop suitability or confidence score.**
- **TOPSIS (`mcdm.py`)**:
  - **Vector Normalization**: $r_{ij} = \frac{x_{ij}}{\sqrt{\sum_{k} x_{kj}^2}}$, $v_{ij} = w_j \cdot r_{ij}$.
  - **Ideal Best / Worst**: $v_j^+ = \max_i v_{ij}$, $v_j^- = \min_i v_{ij}$ (for benefit criteria).
  - **Distances & Closeness**: $S_i^+ = \sqrt{\sum (v_{ij} - v_j^+)^2}$, $S_i^- = \sqrt{\sum (v_{ij} - v_j^-)^2}$, $C_i^* = \frac{S_i^-}{S_i^+ + S_i^-}$.
  - **Output**: Ranked alternatives sorted by descending $C_i^*$.
- **ELECTRE I (`mcdm.py`)**:
  - Outranking relation $a P b \iff C(a, b) \ge c^* \land D(a, b) \le d^*$.
  - Thresholds: Concordance threshold $c^* = 0.6$, Discordance threshold $d^* = 0.4$.
  - **Output**: Net outranking count for cross-checking TOPSIS stability.

### Stage 5: Farm-Specific Fertilizer Engine (`fertilizer_service.py`)
- **Input**: Selected crop, target N requirement (from NSGA-II or crop database baseline), soil nitrogen status, field acreage $A$.
- **Nutrient Deficit & Soil Adjustment**:
  - Soil N $< 30 \text{ mg/kg} \implies N_{\text{adj}} = 1.10 \times N_{\text{base}}$ (low soil N).
  - Soil N $> 60 \text{ mg/kg} \implies N_{\text{adj}} = 0.90 \times N_{\text{base}}$ (high soil N).
- **Commercial Fertilizer Allocation**:
  1. DAP (18% N, 46% P₂O₅): $\text{DAP}_{\text{acre}} = \frac{P_{\text{acre}}}{0.46}$, $N_{\text{DAP}} = \text{DAP}_{\text{acre}} \times 0.18$.
  2. Urea (46% N): $N_{\text{rem}} = \max(0, N_{\text{acre}} - N_{\text{DAP}})$, $\text{Urea}_{\text{acre}} = \frac{N_{\text{rem}}}{0.46}$. (Prevents double counting N supplied by DAP).
  3. MOP (60% K₂O): $\text{MOP}_{\text{acre}} = \frac{K_{\text{acre}}}{0.60}$.
  4. Field Totals: Multiplied by field acreage $A$. No negative quantities.
- **Application Schedule**:
  - Basal: 100% DAP + 100% MOP + 50% Urea.
  - Top Dressing 1 (21–30 days): 25% Urea.
  - Top Dressing 2 (40–50 days): 25% Urea.

### Stage 6: Water Requirement Estimation (`suitability.py` & `recommend.py`)
- **Physical Constants**:
  - $\text{ACRE\_TO\_LITERS\_PER\_MM} = 4046.86 \text{ L/(acre}\cdot\text{mm)}$ (Exact metric conversion: 1 acre = 4046.86 m²).
  - $\text{SEASON\_WEEKS} = 16$ weeks (Standard 112-day cropping period).
- **Water Balance**:
  $$\text{Effective Supply} = \text{Irrigation}_{\text{total}} + \text{Rainfall}_{\text{credit}} + \text{SoilMoisture}_{\text{credit}}$$
  $$\text{Rainfall}_{\text{credit}} = R_{30\text{d}} \times 4046.86 \times \frac{\text{Weeks}}{4} \times 0.50$$

### Stage 7: NSGA-II Multi-Objective Optimization (`nsga2.py`)
- **Decision Variables**: $x_1 = \text{Water (L/week)}$, $x_2 = \text{Fertilizer N (kg/acre)}$.
- **Conflicting Objectives (Minimization)**:
  1. $f_1(x) = \text{Water Gap} = \frac{|\text{Supply} - \text{Demand}|}{\text{Demand}}$
  2. $f_2(x) = \text{Fertilizer Gap} = \frac{|x_2 - \text{Fert}_{\text{need}}|}{\text{Fert}_{\text{need}}}$
  3. $f_3(x) = \text{Resource Cost} = (\text{Water L} \times c_w) + (\text{Fert kg} \times c_f)$
- **Algorithmic Features**:
  - Population size: 60, Generations: 80, SBX Crossover ($\eta=15$), Polynomial Mutation.
  - Elitist $(N + N)$ selection combining parent and offspring populations.
  - Fast Non-Dominated Sorting & Crowding Distance diversity maintenance.
- **Compromise Solution Selection**: Minimum normalized Euclidean distance to ideal point $(0, 0, 0)$ on Pareto front.

---

## 3. Discovered Limitations & Hardcoded Assumptions Log

1. **AHP Pairwise Matrix**: Default matrix in `DEFAULT_AHP_PAIRWISE_MATRIX` represents an expert agronomic baseline matrix for Indian conditions.
2. **ELECTRE Thresholds**: Concordance threshold (0.6) and discordance threshold (0.4) are conservative defaults used for outranking cross-check.
3. **ET0 Calculation**: `estimate_et0_mm_day` provides a Hargreaves-style solar radiation proxy for water balance when full FAO Penman-Monteith hourly meteorological data is unavailable.
