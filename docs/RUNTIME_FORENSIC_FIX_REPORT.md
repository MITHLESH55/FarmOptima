# Runtime Forensic Fix & Process Mismatch Report

**Date**: 2026-09-11  
**Project Path**: `C:\Users\mithlesh_2\Pictures\FarmOptima_Reliability_Security\farmoptima_v5`  
**Git Branch**: `main`  
**Git Commit**: `3b2d242c08bceb5bc8e416f025d0ba63ca4d1925`  

---

## 1. Project Directory Verification

- **Repository Root**: `C:\Users\mithlesh_2\Pictures\FarmOptima_Reliability_Security\farmoptima_v5`
- **Backend Directory**: `C:\Users\mithlesh_2\Pictures\FarmOptima_Reliability_Security\farmoptima_v5\backend`
- **Frontend Directory**: `C:\Users\mithlesh_2\Pictures\FarmOptima_Reliability_Security\farmoptima_v5\frontend`

---

## 2. Process & Port Audit

- **Stale Backend Process**: `PID 36316` (Started at 7:37 PM using System Python `C:\Program Files\Python312\python.exe`). Bound to port `8000`. Stale background uvicorn instance was serving pre-edited code and un-reloaded bytecode.
- **Stale Frontend Process**: `PID 3408` (Started at 7:38 PM). Bound to port `5173`. Served cached frontend bundles.
- **Remediation Action**: Terminated `PID 36316`, `PID 3408`, and `PID 24700`.
- **Active Backend Process**: `PID 27732` (Started with `.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`).
- **Active Frontend Process**: `PID 255` (Started with `npm run dev -- --host 127.0.0.1 --port 5173`).

---

## 3. Direct HTTP API Response

Queried `POST http://127.0.0.1:8000/api/recommend` with JWT Authorization header for location `(18.6116, 73.9553)`:
```json
{
  "location": { "lat": 18.6116, "lon": 73.9553 },
  "recommendation_status": "complete",
  "ndvi": 0.437,
  "ndvi_status": "dense vegetation",
  "rainfall_mm_last_30d": 281.4,
  "avg_temp_c": 23.8,
  "soil_ph": 7.1,
  "provenance": {
    "satellite_source": "gee-sentinel2",
    "weather_source": "nasa-power",
    "soil_source": "soilgrids-cached"
  },
  "crop_ranking": [
    { "crop": "Rice", "topsis_closeness": 0.7196, "rank": 1 },
    { "crop": "Cotton", "topsis_closeness": 0.5663, "rank": 2 },
    { "crop": "Sugarcane", "topsis_closeness": 0.5544, "rank": 3 },
    { "crop": "Groundnut", "topsis_closeness": 0.4583, "rank": 4 },
    { "crop": "Maize", "topsis_closeness": 0.4230, "rank": 5 },
    { "crop": "Soybean", "topsis_closeness": 0.4121, "rank": 6 },
    { "crop": "Chickpea", "topsis_closeness": 0.3463, "rank": 7 },
    { "crop": "Wheat", "topsis_closeness": 0.2812, "rank": 8 }
  ]
}
```

---

## 4. Real Browser UI Verification

Executed autonomous `browser_subagent` navigation on `http://127.0.0.1:5173/` for coordinates `(18.6116° N, 73.9553° E)`:

- **Rendered Recommended Crop**: Rice (Rank #1 of 8 Analyzed)
- **Rendered TOPSIS Closeness**: `0.7196`
- **Rendered ELECTRE Rank**: `+6`
- **Rendered NDVI Value**: `0.437`
- **Rendered NDVI Status**: `dense vegetation`
- **Rendered Satellite Source**: `gee-sentinel2` (Copernicus Sentinel-2 / Esri)
- **Rendered Soil Source**: `CACHED` (`soilgrids-cached`)
- **Rendered Weather Source**: `LIVE` (`nasa-power`)

When satellite GEE is unconfigured/unavailable:
- **Rendered NDVI Value**: `—`
- **Rendered NDVI Status**: `Unavailable`
- **Rendered Satellite Source**: `FIELD MAP CONTEXT (BASEMAP)` / `Esri World Imagery Basemap`

---

## 5. Files & Functions Changed

1. `backend/app/services/satellite_service.py`: `get_ndvi_for_location` sets `ndvi=None` on fallback.
2. `backend/app/core/environmental_interpretation.py`: `interpret_ndvi` handles `None` and returns `"unavailable"`.
3. `backend/app/core/suitability.py`: `market_suitability` uses linear 0–1 index scaling `clamp01((value - 1.0) / 9.0)`; `water_efficiency_suitability` converts 120-day demand to 30-day demand (`crop_water_need_mm / 4.0`).
4. `backend/app/core/criteria.py`: `build_decision_matrix` checks `satellite_source != "unavailable"`.
5. `backend/app/schemas/recommendation.py`: `RecommendationResponse` sets `ndvi: float | None = None`.
6. `frontend/src/components/dashboard/LiveFieldDataPanel.jsx`: Renders `—` / `Unavailable` when `ndvi` is `null`.
7. `frontend/src/components/dashboard/MetricCard.jsx`: Added explicit `MODEL`, `LAB`, and `CACHED` badge mappings.

---

## 6. Verification & Test Suite Results

- **Backend Pytest**: 322 / 322 tests passing
- **Frontend Oxlint**: 0 errors, 3 warnings
- **Frontend Build**: Passed (`vite build`, 823ms)
- **Browser Subagent UI Verification**: 100% verified against live DOM
