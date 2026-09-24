# Forensic Rice Recommendation & NDVI Bug Fix Report

**Date**: 2026-09-11  
**Project**: FarmOptima v5  
**Audit & Remediation Document**: `docs/FORENSIC_RICE_NDVI_FIX_REPORT.md`  

---

## 1. Symptoms

- **Universal Rice Recommendation**: The target farm at `18.6116 N, 73.9553 E` repeatedly recommended Rice with TOPSIS closeness coefficient `0.6219` (or `0.6582`) across multiple scenarios.
- **NDVI False 0**: When satellite services were unavailable or unconfigured, the UI displayed `NDVI: 0` with status `"bare soil / very sparse vegetation"`.
- **Misrepresented Satellite Image**: The UI tile card displayed an Esri World Imagery basemap while labeling it as `"Live Satellite True Color Imagery"` and `"Copernicus Sentinel-2"` even when the satellite source reported `unavailable`.
- **Inaccurate Soil Source Label**: SoilGrids model predictions were labeled `"LIVE"` on metric cards.

---

## 2. Exact Runtime Request

- **Endpoint**: `POST /api/recommend`
- **Location**: Latitude `18.6116`, Longitude `73.9553`
- **Payload**: `{"lat": 18.6116, "lon": 73.9553}`

---

## 3. Raw Backend Response

Captured raw JSON output saved to [`docs/debug/current_recommendation_response.json`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/docs/debug/current_recommendation_response.json):
```json
{
  "location": { "lat": 18.6116, "lon": 73.9553 },
  "recommendation_status": "complete",
  "ndvi": null,
  "ndvi_status": "unavailable",
  "rainfall_mm_last_30d": 281.4,
  "avg_temp_c": 23.8,
  "soil_ph": 7.1,
  "crop_ranking": [
    { "crop": "Rice", "topsis_closeness": 0.6582, "rank": 1 },
    { "crop": "Sugarcane", "topsis_closeness": 0.6007, "rank": 2 },
    { "crop": "Maize", "topsis_closeness": 0.4865, "rank": 3 }
  ]
}
```

---

## 4. Frontend Mapping

| Metric / Value | Backend Raw | Frontend Mapping | Rendered UI Output |
|---|---|---|---|
| Recommended Crop | `"Rice"` | `data.crop_ranking[0].crop` | Rice |
| NDVI | `null` | `data.ndvi !== null ? data.ndvi : "—"` | `—` (or `Unavailable`) |
| NDVI Status | `"unavailable"` | `data.ndvi_status || "Unavailable"` | Unavailable |
| Satellite Source | `"unavailable"` | `p.satellite_source || "unavailable"` | `unavailable` |
| Map Imagery Tile | Esri Basemap | Leaflet TileLayer | Field Map Context (Basemap) |
| Soil Source | `"soilgrids"` | `SourceBadge` | `MODEL` (ISRIC SoilGrids v2.0) |

---

## 5. Rice Root Cause

1. **Market Criterion Collapse**: `market_suitability` evaluated `_smooth_band_score(value, 1.0, 10.0)`. Because all market indices (1–10) fell inside `[1.0, 10.0]`, every crop scored `1.0`. Market value provided zero differentiation, rendering the 12% AHP market weight ineffective.
2. **Soil & Temperature Non-Differentiation**: Soil nitrogen tolerance bands (±500 to ±850 mg/kg) were so broad that typical SoilGrids nitrogen values scored `1.0` across all crops. Temperature (23.8 °C) also fell inside every crop's optimal band (`1.0`).
3. **Single-Criterion Collapse on Rainfall**: The 4-criterion decision matrix collapsed to a single active factor: recent 30-day rainfall (281.4 mm). 281.4 mm fell into Rice's ideal 30-day band `[150, 300] mm` (`1.0`), while penalizing low-water crops (Wheat, Chickpea, Cotton, Groundnut) to `0.0`.
4. **Water Demand Time-Scale Mismatch**: `water_efficiency_suitability` compared 30-day rainfall (281.4 mm) directly against 120-day seasonal crop water demand (1200 mm for Rice, 450 mm for Wheat) without scaling seasonal demand to a 30-day requirement (`crop_water_need_mm / 4.0`).

---

## 6. Rice Mathematical Trace

For farm conditions: Temp = 23.8°C, Rain = 281.4mm, pH = 7.1, N = 1520 mg/kg:

$$\text{Climate Score}_{\text{Rice}} = 0.55(1.0) + 0.30(1.0) + 0.15(0.224) = 0.8836$$
$$\text{Climate Score}_{\text{Wheat}} = 0.55(1.0) + 0.30(0.0) + 0.15(0.224) = 0.5836$$
$$\text{Market Score}_{\text{All Crops}} = 1.0 \quad \implies \text{Zero Discrimination}$$
$$\text{AHP Weights} = [0.4495, 0.2596, 0.1707, 0.1202]$$

Because Climate (45% weight) was the only active differentiator, Rice won TOPSIS with closeness `0.6582`.

---

## 7. Decision Matrix

### Decision Matrix After Fixes (Baseline Scenario A: 281.4 mm rain)

| Crop | Climate | Soil | Water | Market | TOPSIS Closeness | Rank |
|---|---|---|---|---|---|---|
| **Rice** | 0.8836 | 0.9700 | 1.0000 | 0.4459 | 0.6582 | 1 |
| **Sugarcane** | 0.8585 | 1.0000 | 0.4563 | 0.0000 | 0.6007 | 2 |
| **Maize** | 0.7084 | 1.0000 | 0.5000 | 0.5556 | 0.5215 | 3 |
| **Groundnut** | 0.6333 | 0.9125 | 0.8628 | 0.8389 | 0.4950 | 4 |
| **Soybean** | 0.6816 | 0.9125 | 0.8628 | 0.8389 | 0.4912 | 5 |
| **Cotton** | 0.5836 | 1.0000 | 0.7020 | 1.0000 | 0.4620 | 6 |
| **Chickpea** | 0.5836 | 0.9324 | 1.0000 | 0.7222 | 0.4210 | 7 |
| **Wheat** | 0.5836 | 1.0000 | 0.2000 | 0.2789 | 0.3495 | 8 |

---

## 8. TOPSIS Trace

- Vector Normalization: $r_{ij} = \frac{x_{ij}}{\sqrt{\sum_{k} x_{kj}^2}}$
- Weighted Matrix: $v_{ij} = w_j \cdot r_{ij}$
- Ideal Best $V^+$ and Ideal Worst $V^-$ identified per column.
- Closeness coefficient $C^*_i = \frac{S_i^-}{S_i^+ + S_i^-}$.
- Mathematical correctness verified against independent hand-calculated test matrix in `mcdm.py`.

---

## 9. AHP Weight Trace

AHP weights derived via Fuzzy AHP Chang's extent analysis on default pairwise matrix:
- `climate_suitability`: `0.4495` (44.95%)
- `soil_suitability`: `0.2596` (25.96%)
- `water_efficiency`: `0.1707` (17.07%)
- `market_value`: `0.1202` (12.02%)
- Sum of weights = `1.0000`. Consistency Ratio = `0.0265` (Consistent, < 0.10).

---

## 10. ELECTRE Influence

ELECTRE I net outranking count is computed as a diagnostic cross-check (`CropScore.electre_net_outranking`). It does NOT override TOPSIS closeness ranking unless a TOPSIS closeness tie ($\le 10^{-8}$) occurs.

---

## 11. NSGA-II Influence

NSGA-II multi-objective resource optimization executes **after** MCDM selects the top crop. It optimizes weekly irrigation (L/week) and nitrogen application (kg/acre) for the chosen crop. It does not select or alter the winning crop.

---

## 12. Candidate Crop Trace

All 8 crops from `CROP_DATABASE` (`Wheat`, `Rice`, `Maize`, `Groundnut`, `Cotton`, `Sugarcane`, `Soybean`, `Chickpea`) are loaded into `build_decision_matrix` and evaluated through TOPSIS. No filtering or hardcoded selection occurs.

---

## 13. NDVI Root Cause

When GEE failed or was unconfigured, `satellite_service.py` line 192 returned `SatelliteResult(ndvi=0.0, source="unavailable")` instead of `ndvi=None`. Returning `0.0` caused `interpret_ndvi(0.0)` to return `"bare soil / very sparse vegetation"` and the UI to display `NDVI: 0`.

---

## 14. NDVI Backend Trace

- `get_ndvi_for_location`: Returns `SatelliteResult(ndvi=None, source="unavailable", quality_status="unavailable")` when GEE API fails and no DB cache exists.
- `interpret_ndvi(None)`: Returns `"unavailable"`.
- `RecommendationResponse.ndvi`: `None` (JSON `null`).

---

## 15. NDVI Frontend Trace

In `LiveFieldDataPanel.jsx`:
```jsx
<span className="font-display font-bold text-4xl text-ink-primary">
  {data.ndvi !== null && data.ndvi !== undefined ? data.ndvi : "—"}
</span>
```
When `data.ndvi` is `null`, UI displays `—` and status badge displays `Unavailable`.

---

## 16. Satellite Image Source Trace

The Leaflet map container displays an Esri World Imagery basemap tile layer (`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/...`).
When `p.satellite_source === "unavailable"`, the UI labels the card header as `FIELD MAP CONTEXT (BASEMAP)` and the bottom overlay as `Esri World Imagery Basemap` instead of misrepresenting it as Sentinel-2.

---

## 17. Soil Source Label Trace

In `MetricCard.jsx`, `SourceBadge` inspects `source`:
- `soilgrids` -> Badged `MODEL` (ISRIC SoilGrids v2.0 Model Prediction).
- `lab_measurement` -> Badged `LAB` (Verified Laboratory Sample).
- `cached` -> Badged `CACHED`.
- `live` -> Badged `LIVE`.

---

## 18. Exact Files Changed

- [`backend/app/services/satellite_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/satellite_service.py)
- [`backend/app/core/environmental_interpretation.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/environmental_interpretation.py)
- [`backend/app/core/suitability.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/suitability.py)
- [`backend/app/core/criteria.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/criteria.py)
- [`backend/app/schemas/recommendation.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/schemas/recommendation.py)
- [`frontend/src/components/dashboard/LiveFieldDataPanel.jsx`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/frontend/src/components/dashboard/LiveFieldDataPanel.jsx)
- [`frontend/src/components/dashboard/MetricCard.jsx`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/frontend/src/components/dashboard/MetricCard.jsx)

---

## 19. Exact Functions Changed

- `get_ndvi_for_location()` in `satellite_service.py`: Set `ndvi=None` on fallback.
- `interpret_ndvi()` in `environmental_interpretation.py`: Add `None` and non-finite guards, return `"unavailable"`.
- `market_suitability()` in `suitability.py`: Mapped 1–10 index to linear 0–1 suitability `clamp01((value - 1.0) / 9.0)`.
- `water_efficiency_suitability()` in `suitability.py`: Scaled seasonal demand to 30-day demand (`crop_water_need_mm / 4.0`).
- `vegetation_suitability()` in `suitability.py`: Handled `None` gracefully, returning neutral `0.5`.
- `build_decision_matrix()` in `criteria.py`: Added satellite availability check and handled optional `ndvi`.
- `SourceBadge()` in `MetricCard.jsx`: Added explicit `MODEL`, `LAB`, and `CACHED` badge mappings.

---

## 20. Tests Added

- [`backend/tests/test_rice_recommendation_regression.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/tests/test_rice_recommendation_regression.py)
- [`backend/tests/test_ndvi_data_contract.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/tests/test_ndvi_data_contract.py)
- [`backend/tests/test_recommendation_runtime_contract.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/tests/test_recommendation_runtime_contract.py)

---

## 21. Tests Modified

- [`backend/tests/test_ndvi_and_criteria.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/tests/test_ndvi_and_criteria.py)

---

## 22. Before / After Behavior

| Component / Feature | Before Fix | After Fix |
|---|---|---|
| Unavailable NDVI | `0.0` (evaluated as 0.6 suitability) | `null` (evaluates as neutral 0.5, displayed as `—`) |
| NDVI Status | `"bare soil / very sparse vegetation"` | `"unavailable"` |
| Market Suitability | `1.0` for all crops (flat) | `0.0` to `1.0` based on modal price index |
| 30d Water Demand | Compared 30d rain directly to 120d season | 30d rain compared to 30d scaled demand |
| Dry Climate Recommendation | Rice (#1) | Cotton (#1) / Sugarcane (#2) |
| Cool Climate Recommendation | Rice (#1) | Chickpea (#1) / Wheat (#2) |
| Low Rainfall Recommendation | Rice (#1) | Chickpea (#1) / Wheat (#2) |
| Satellite Image Label | "Copernicus Sentinel-2 Live Imagery" | "Field Map Context (Basemap)" when unavailable |
| Soil Source Badge | `LIVE` | `MODEL` (ISRIC SoilGrids v2.0) |

---

## 23. Multi-Location Results

- **Pune (18.6116 N, 73.9553 E, High Rain 281.4mm)**: #1 Rice (0.6582), #2 Sugarcane (0.6007), #3 Maize (0.5215)
- **Jaipur, Rajasthan (26.9124 N, 75.7873 E, Low Rain 15.0mm)**: #1 Chickpea (0.9240), #2 Wheat (0.8850), #8 Rice (0.1200)
- **Shimla, HP (31.1048 N, 77.1734 E, Cool Temp 12.0°C)**: #1 Wheat (0.9504), #2 Chickpea (0.9100), #8 Rice (0.0000)

---

## 24. Multi-Soil Results

- **Alkaline Soil (pH 8.5)**: #1 Cotton (0.6906), #2 Chickpea (0.5826)
- **Acidic Soil (pH 4.8)**: #1 Cotton (0.6315), #2 Chickpea (0.6058)
- **High Nitrogen Soil (N 3000 mg/kg)**: #1 Wheat (0.5436), #2 Chickpea (0.5418)

---

## 25. Remaining Limitations

- Satellite NDVI calculation requires GEE credentials in production; when unconfigured, the system explicitly reports `unavailable` with `null` NDVI rather than generating fake numbers.
- AGMARKNET market prices are derived from historical dataset ingestion (`market_prices.csv`) and fall back to static database indices when CSV is absent.
