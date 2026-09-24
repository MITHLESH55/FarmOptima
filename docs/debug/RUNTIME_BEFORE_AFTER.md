# Runtime Before / After Evidence Matrix

**Date**: 2026-09-11  
**Target Location**: (18.6116° N, 73.9553° E)

---

## 1. Process & Deployment Execution Comparison

| Parameter | Stale Runtime (Before Cleanup) | Corrected Runtime (After Process Reset) |
|---|---|---|
| **Backend PID** | `36316` (Started 7:37 PM with System Python) | `27732` (Started with `.\venv\Scripts\python.exe`) |
| **Backend Port** | `127.0.0.1:8000` | `127.0.0.1:8000` |
| **Frontend PID** | `3408` (Stale Vite dev server) | `255` (Fresh Vite dev server) |
| **Frontend Port** | `127.0.0.1:5173` | `127.0.0.1:5173` |

---

## 2. API & UI Value Comparison

| Value / Metric | Stale Backend (PID 36316) | Direct HTTP API (PID 27732) | Browser Network Response | Browser Rendered UI |
|---|---|---|---|---|
| **Recommended Crop** | Rice (#1) | Rice (#1) | Rice (#1) | **Rice** (Rank #1 of 8) |
| **TOPSIS Closeness** | 0.6219 | 0.7196 | 0.7196 | **0.7196** |
| **ELECTRE Rank** | +2 | +6 | +6 | **+6** |
| **NDVI (GEE Active)** | 0.0 | 0.437 | 0.437 | **0.437** |
| **NDVI (GEE Unavailable)**| 0.0 | null | null | **— / Unavailable** |
| **NDVI Status** | bare soil / sparse veg | dense vegetation | dense vegetation | **dense vegetation** |
| **Satellite Source** | unavailable | gee-sentinel2 | gee-sentinel2 | **gee-sentinel2** |
| **Soil Source Badge** | LIVE | soilgrids-cached | soilgrids-cached | **CACHED** |
| **Weather Source** | nasa-power | nasa-power | nasa-power | **LIVE** (`nasa-power`) |

---

## 3. Key Forensic Discovery

The discrepancy between passing automated tests and the user's observed UI symptoms was caused by **stale background processes**:
1. An old `uvicorn` process (`PID 36316`) was started using System Python (`C:\Program Files\Python312\python.exe`) prior to code edits and remained bound to port `8000`.
2. An old Vite dev server process (`PID 3408`) remained active in memory on port `5173`.
3. After stopping `PID 36316` and `PID 3408` and launching fresh daemons (`PID 27732` for backend and `PID 255` for frontend), the actual browser connected to the updated HTTP endpoints and displayed the corrected UI state.
