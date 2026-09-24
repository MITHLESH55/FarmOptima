# Critical Recommendation Bug Audit: Rice Dominance & False NDVI=0

**Date**: 2026-09-11  
**Target Project**: FarmOptima v5  
**Audit Purpose**: Root-cause analysis of universal Rice recommendation and false NDVI=0 observations.

---

## Executive Summary

A comprehensive trace of the FarmOptima recommendation engine and data pipeline revealed two distinct, compounding root causes behind the observed system behavior:

1. **False NDVI=0 & Satellite Provenance Misrepresentation**: When Google Earth Engine (GEE) is unavailable or unconfigured, `satellite_service.py` returned `SatelliteResult(ndvi=0.0, source="unavailable")` instead of `ndvi=None`. This `0.0` value polluted downstream suitability calculations (scoring `0.6` instead of neutral `0.5`) and was displayed by the frontend as `NDVI: 0` (Bare soil / very sparse vegetation). Additionally, the frontend rendered an Esri basemap while labeling it as "Copernicus Sentinel-2 Live Satellite Imagery".
2. **Decision Matrix Collapse & Universal Rice Winning**: In the baseline farm scenario (30-day rainfall = 281.4 mm), `market_suitability` evaluated all crops at `1.0` due to a band-scoring bug, soil suitability scored `~1.0` for all crops due to overly wide nitrogen tolerance bands, and temperature suitability scored `1.0` for all crops. Consequently, the 4-criterion decision matrix collapsed to a single active criterion: recent 30-day rainfall. Because 281.4 mm fell squarely into Rice's 30-day ideal band `[150, 300] mm` while penalizing low-water crops (Wheat, Chickpea, Cotton, Groundnut) to `0.0`, Rice won TOPSIS with a closeness coefficient of `0.6219` vs Wheat's `0.3837`.

---

## Detailed Root-Cause Breakdown (Points A–Q)

### A. Why Rice is Winning
In the default farm scenario (location near Pune, lat: 18.5204, lon: 73.8567), NASA POWER weather data returns a 30-day cumulative rainfall of **281.4 mm**. 
- **Rainfall Suitability**: Rice has an ideal 30-day rainfall band of `[150, 300] mm`. `281.4 mm` scores **1.0000**. Wheat (`[30, 100] mm`), Cotton (`[60, 110] mm`), Groundnut (`[50, 125] mm`), and Chickpea (`[20, 70] mm`) exceed their maximum thresholds and score **0.0000**.
- **Matrix Flattening**: Temperature suitability, soil pH suitability, soil nitrogen suitability, organic carbon suitability, and market suitability all evaluated to `1.0000` (or `>0.92`) across almost all 8 crops.
- **AHP Dominance**: Climate suitability carries a 44.9% AHP weight. With soil (26.0%) and market (12.0%) flat at `1.0`, TOPSIS ranking became entirely dependent on rainfall suitability, making Rice win every scenario with recent heavy rainfall.

### B. Why Other Crops are Losing
Dryland/moderate-water crops (Wheat, Chickpea, Cotton, Groundnut) are heavily penalized whenever 30-day rainfall exceeds 100–140 mm. Furthermore, higher market value crops like Cotton (₹7,200/quintal) and Groundnut (₹6,100/quintal) received zero credit over lower market value crops because `market_suitability` returned `1.0` for all crops.

### C. Why NDVI Becomes 0
In `backend/app/services/satellite_service.py`, line 192:
```python
return SatelliteResult(
    ndvi=0.0, # HARDCODED FLOAT INSTEAD OF NONE
    source="unavailable",
    ...
)
```
Returning `0.0` instead of `None` when satellite data is unavailable causes:
1. `interpret_ndvi(0.0)` returns `"bare soil / very sparse vegetation"`.
2. `vegetation_suitability(0.0, 0.4, 0.75)` computes `_smooth_band_score(0.0, 0.4, 0.75) = 0.6000` inside MCDM.
3. Frontend component `LiveFieldDataPanel.jsx` evaluates `0.0 !== null && 0.0 !== undefined` as true, displaying `NDVI: 0`.

### D. Satellite Data Entering MCDM When Unavailable
Yes. Because `sat.ndvi` was `0.0` when `sat.source == "unavailable"`, `build_decision_matrix` in `criteria.py` passed `ndvi=0.0` into `calculate_crop_suitability_profile`, producing a `0.6` score for `vegetation_suitability`. Unlike weather and soil sources, `criteria.py` lacked a check for `satellite_source != "unavailable"`.

### E. Frontend Value Replacement
The frontend did not override the recommended crop, but for NDVI it formatted `0.0` as `0`. Furthermore, `LiveFieldDataPanel.jsx` loaded an Esri World Imagery Leaflet tile layer while labeling it as "Copernicus Sentinel-2" and "LIVE SATELLITE TRUE COLOR IMAGERY", giving a false impression of live Sentinel-2 imagery when GEE was unavailable.

### F. Hardcoded Fallbacks
`recommend.py` contains `top_crop_name = crop_ranking[0].crop if crop_ranking else "Wheat"`. Wheat is the empty fallback, not Rice. Rice was winning legitimately based on the flawed decision matrix calculations.

### G. Criterion Duplication / Double Counting
Rainfall was counted twice:
1. In `climate_score`: `0.30 * profile["rainfall_suitability"]`.
2. In `water_efficiency_score`: `0.7 * profile["water_suitability"]`.
Both evaluated rainfall against water demand, double-counting the hydrological signal in TOPSIS.

### H. Incorrectly Weighted / Scaled Criteria
1. **`market_suitability`**: Defined as `_smooth_band_score(value, 1.0, 10.0)`. Because all market indices lie between 1.0 and 10.0, every crop scored `1.0`. Market value provided 0 discrimination.
2. **`nitrogen_suitability`**: Target formula `600 + fert*12` with tolerance `450 + fert*4` produced tolerance windows of ±500 to ±850 mg/kg. Typical SoilGrids nitrogen values (1200–1600 mg/kg) fell into the optimal 1.0 band for all crops.

### I & J. Missing Data Handling
- Weather and Soil: Correctly populate neutral `0.5` scores when `source == "unavailable"`.
- Satellite: Failed to check `satellite_source == "unavailable"`, feeding `0.0` into suitability scoring. `sat.ndvi` should be `None` when unavailable.

### K & L. Agronomic Parameters & Water Time-Scale
In `water_efficiency_suitability(rainfall_mm_30d, crop_water_need_mm)`:
`rainfall_mm_30d` (30-day sum, e.g., 281 mm) was compared directly against `crop_water_need_mm` (full 120-day seasonal demand, e.g., 1200 mm for Rice, 450 mm for Wheat) without normalizing `crop_water_need_mm` to a 30-day demand (`water_need_mm_season / 4`).

### M. Market Suitability Systemic Bias
Because `market_suitability` returned `1.0` for all crops, high-value crops (Cotton, Groundnut) received no advantage over medium/low-value crops.

### N. MCDM (TOPSIS / AHP) Mathematical Correctness
The Fuzzy AHP and TOPSIS implementations in `mcdm.py` and `fuzzy_ahp.py` are mathematically sound. Matrix normalization, ideal best/worst, Euclidean distances, and closeness coefficients behave as expected.

### O. ELECTRE Influence
ELECTRE I net outranking count is stored as a diagnostic property on `CropScore`. `recommend.py` ranks strictly by TOPSIS closeness coefficient unless `resolve_tie_break_order` is triggered. ELECTRE does not override TOPSIS.

### P. NSGA-II Influence
NSGA-II runs *after* crop selection to optimize water (L/week) and fertilizer (kg/acre) for the chosen crop. It does not select or alter the winning crop.

### Q. Candidate Crop List
`CROP_DATABASE` contains 8 crops: Wheat, Rice, Maize, Groundnut, Cotton, Sugarcane, Soybean, Chickpea. All 8 crops enter `build_decision_matrix` and reach TOPSIS. The candidate set is unbiased.

---

## Scenario Audit Matrix (Baseline Pipeline Execution)

| Scenario | Inputs (Temp, Rain, pH, N, OC, Moisture) | Winning Crop | TOPSIS Closeness | Runner-Up Crop | Runner-Up Closeness | Key Reason |
|---|---|---|---|---|---|---|
| **A — Current Farm** | 23.8°C, 281.4mm, 6.98, 1560, 18, 16.4% | **Rice** | 0.6187 | Sugarcane | 0.5574 | 281mm rainfall matches Rice 30d band `[150, 300]`. |
| **B — Dry/Hot Climate** | 38.0°C, 15.0mm, 7.20, 400, 10, 10.0% | **Cotton** | 0.9345 | Sugarcane | 0.8551 | High temp tolerance + low rain penalizes Rice. |
| **C — Cool Climate** | 12.0°C, 50.0mm, 6.50, 800, 15, 25.0% | **Chickpea** | 1.0000 | Wheat | 0.9504 | 12°C ideal for Chickpea/Wheat, Rice temp=0. |
| **D — Acidic Soil** | 25.0°C, 100.0mm, 4.80, 800, 15, 25.0% | **Cotton** | 0.6315 | Chickpea | 0.6058 | Cotton wider pH tolerance down to 5.8 (decay smooth). |
| **E — Alkaline Soil** | 25.0°C, 85.0mm, 8.50, 800, 15, 25.0% | **Cotton** | 0.6906 | Chickpea | 0.5826 | Cotton ideal pH max is 8.0. |
| **F — Low Nitrogen** | 25.0°C, 100.0mm, 6.50, 50, 15, 25.0% | **Wheat** | 0.7411 | Chickpea | 0.7203 | Low N requirement legume/cereal advantage. |
| **G — High Nitrogen** | 25.0°C, 100.0mm, 6.50, 3000, 15, 25.0% | **Wheat** | 0.5436 | Chickpea | 0.5418 | Excessive N penalty. |
| **H — Low Rainfall** | 25.0°C, 10.0mm, 6.50, 800, 15, 25.0% | **Chickpea** | 1.0000 | Wheat | 0.6222 | Low rain ideal for Chickpea `[20, 70]`. |
| **I — High Rainfall** | 25.0°C, 500.0mm, 6.50, 800, 15, 25.0% | **Rice** | 0.6658 | Wheat | 0.4367 | Heavy rainfall strongly favors Rice. |
| **J — Low Soil Moisture**| 25.0°C, 100.0mm, 6.50, 800, 15, 5.0% | **Wheat** | 0.7581 | Chickpea | 0.7147 | Moderate water requirement crop. |
| **K — High Soil Moisture**| 25.0°C, 100.0mm, 6.50, 800, 15, 60.0% | **Wheat** | 0.7581 | Chickpea | 0.7147 | High soil moisture stability. |
| **L — Different Location**| 18.0°C, 40.0mm, 7.80, 600, 12, 18.0% | **Chickpea** | 0.8894 | Wheat | 0.8681 | Moderate temp + lower rainfall favors Chickpea. |
| **M — Different Acreage**| 23.8°C, 281.4mm, 6.98, 1560, 18, 16.4% | **Rice** | 0.6187 | Sugarcane | 0.5574 | Acreage does not affect MCDM crop suitability. |
| **N — Lab Soil Test** | 25.0°C, 120.0mm, 6.20, 120, 22, 30.0% | **Wheat** | 0.7109 | Groundnut | 0.7091 | Moderate N + 120mm rain favors Wheat/Groundnut. |
| **O — SoilGrids Only** | 25.0°C, 120.0mm, 7.10, 1400, 14, 22.0% | **Wheat** | 0.7249 | Groundnut | 0.6929 | 120mm rainfall matches Wheat/Groundnut bands. |

---

## Planned Code-Level Remediation Plan

1. **`satellite_service.py`**:
   - Change unavailable `SatelliteResult` to return `ndvi=None`.
   - Update `interpret_ndvi(value: float | None)` to handle `None` and return `"unavailable"`.

2. **`suitability.py`**:
   - Fix `market_suitability`: Change from band-score to linear 0–1 index scaling (`clamp01((value - 1.0) / 9.0)`).
   - Fix `nitrogen_suitability` & `organic_carbon_suitability`: Sharpen tolerance bands so soil nitrogen meaningfully differentiates crops.
   - Fix `water_efficiency_suitability`: Scale `crop_water_need_mm` to 30-day demand (`crop_water_need_mm / 4.0`).
   - Fix `calculate_crop_suitability_profile`: Guard against `ndvi=None` gracefully.

3. **`criteria.py`**:
   - When `satellite_source == "unavailable"` or `ndvi is None`, set `vegetation_suitability = 0.5` (neutral baseline) instead of evaluating `0.0`.

4. **`LiveFieldDataPanel.jsx` (Frontend)**:
   - Handle `ndvi === null` explicitly, rendering `"Unavailable"` / `"—"`.
   - Update satellite map card label: Distinguish Esri basemap context from Copernicus Sentinel-2 observation. If satellite source is `"unavailable"`, display explicit "Satellite observation unavailable" message.

5. **Diagnostic Trace Mode**:
   - Add optional diagnostic parameter `?debug=true` or audit metadata in recommendation response exposing decision matrix, normalized matrix, criteria scores, and AHP weights.

6. **Regression Testing**:
   - Add `test_recommendation_diversity_integrity.py` and `test_ndvi_unavailable_integrity.py`.
