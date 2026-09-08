# Real-World Data & Data-Provenance Audit — FarmOptima

This document provides a comprehensive, transparent audit of every data parameter consumed, computed, and displayed within the FarmOptima Precision Agriculture Decision-Support Platform. Every data value is classified into exactly one canonical source category, detailing its file origin, API/dataset provenance, timestamp availability, location dependency, fallback behavior, and confidence limitations.

---

## 1. Classification Summary

Every parameter displayed by FarmOptima is classified as one of:
- `LIVE_API`: Dynamic data fetched directly from an external REST/web API in real-time.
- `CACHED_API`: API response stored locally with a time-to-live (TTL) to reduce latency and rate limits.
- `STATIC_DATASET`: Local reference dataset, CSV, or agronomic baseline table.
- `MODEL_PREDICTION`: Machine learning model output or spatial gridded estimation (e.g. SoilGrids 250m model).
- `RULE_CALCULATION`: Deterministic mathematical/agronomic formula computed in memory.
- `OPTIMIZATION_RESULT`: Evolutionary optimization output (e.g. NSGA-II Pareto front compromise).
- `USER_INPUT`: Value entered directly by the farmer/user via the UI or API request.
- `LAB_MEASUREMENT`: User/farmer uploaded verified laboratory soil or plant tissue analysis.
- `SATELLITE_OBSERVATION`: Remote sensing spectral measurement derived from Earth observation satellites.
- `MOCK/FALLBACK`: Synthetic fallback marker used only when an external service is unreachable or unconfigured.

---

## 2. Complete Data Parameter Inventory

### A. Location & Farm Metadata

#### 1. Target Farm Coordinates (Latitude & Longitude)
- **Value**: Decimal latitude (e.g., `18.3926° N`) and longitude (e.g., `73.8706° E`).
- **Classification**: `USER_INPUT`
- **Exact File / Module**: [`LocationBar.jsx`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/frontend/src/components/dashboard/LocationBar.jsx), [`LocationMapModal.jsx`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/frontend/src/components/dashboard/LocationMapModal.jsx), [`locationValidation.js`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/frontend/src/utils/locationValidation.js)
- **API / File / DB Origin**: Browser DOM -> `LocationRequest` API payload -> `farms` database table.
- **Timestamp Availability**: Recorded at interactive session time (`created_at` timestamp in DB).
- **Location Dependency**: Exact coordinate point `(lat, lon)`.
- **Fallback Behavior**: Defaults to Pune, Maharashtra centroid (`18.5204, 73.8567`) on initial load.
- **Confidence & Quality Limitations**: High precision (up to 6 decimal places preserved).

#### 2. Field Boundary / Polygon & Field Area
- **Value**: Field boundary geometry (GeoJSON Polygon) and field area in acres (e.g., `2.5 acres`).
- **Classification**: `USER_INPUT` / `RULE_CALCULATION`
- **Exact File / Module**: [`farm.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/models/farm.py), [`common.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/schemas/common.py)
- **API / File / DB Origin**: `LocationRequest.field_area_acres` and `farms.polygon` geometry column.
- **Timestamp Availability**: Saved at farm creation/update.
- **Location Dependency**: Multi-vertex spatial polygon bounding box.
- **Fallback Behavior**: If polygon is omitted, a 1000m circular buffer footprint around point `(lat, lon)` is used for satellite imagery reduction, and `field_area_acres` defaults to `1.0`.
- **Confidence & Quality Limitations**: Dependent on user GPS accuracy or digital drawing precision.

---

### B. Weather & Climate Parameters

#### 3. 30-Day Cumulative Precipitation (`PRECTOTCORR`)
- **Value**: Total rainfall over the last 30 days in millimeters (e.g., `85.0 mm`).
- **Classification**: `LIVE_API`
- **Exact File / Module**: [`weather_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/weather_service.py) (`_fetch_via_nasa_power`)
- **API / File / DB Origin**: NASA POWER Daily Point API (`https://power.larc.nasa.gov/api/temporal/daily/point`)
- **Timestamp Availability**: Daily observation series over trailing 30-day window (`start` to `end` date).
- **Location Dependency**: 0.5° × 0.625° NASA POWER spatial grid cell.
- **Fallback Behavior**: If NASA POWER API is unreachable, `weather_source` is explicitly marked as `"unavailable"` and values set to `0.0`. No synthetic fake data is generated.
- **Confidence & Quality Limitations**: High quality climate reanalysis data; spatial resolution is coarse (~50km grid cell).

#### 4. Average Temperature (`T2M`)
- **Value**: 30-day mean 2-meter air temperature in degrees Celsius (e.g., `27.5 °C`).
- **Classification**: `LIVE_API`
- **Exact File / Module**: [`weather_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/weather_service.py)
- **API / File / DB Origin**: NASA POWER Daily Point API
- **Timestamp Availability**: 30-day daily mean.
- **Location Dependency**: NASA POWER grid cell.
- **Fallback Behavior**: Source marked `"unavailable"`.
- **Confidence & Quality Limitations**: High.

#### 5. Relative Atmospheric Humidity (`RH2M`)
- **Value**: 30-day mean relative humidity percentage (e.g., `60.0%`).
- **Classification**: `LIVE_API`
- **Exact File / Module**: [`weather_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/weather_service.py)
- **API / File / DB Origin**: NASA POWER Daily Point API
- **Timestamp Availability**: 30-day daily mean.
- **Location Dependency**: NASA POWER grid cell.
- **Fallback Behavior**: Source marked `"unavailable"`.
- **Confidence & Quality Limitations**: High.

#### 6. Solar Radiation (`ALLSKY_SFC_SW_DWN`)
- **Value**: All-sky surface shortwave downward irradiance in MJ/m²/day (e.g., `18.0 MJ/m²`).
- **Classification**: `LIVE_API`
- **Exact File / Module**: [`weather_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/weather_service.py)
- **API / File / DB Origin**: NASA POWER Daily Point API
- **Timestamp Availability**: 30-day daily mean.
- **Location Dependency**: NASA POWER grid cell.
- **Fallback Behavior**: Source marked `"unavailable"`.
- **Confidence & Quality Limitations**: High.

#### 7. Wind Speed (`WS2M`)
- **Value**: 2-meter wind speed in meters per second (e.g., `2.5 m/s`).
- **Classification**: `LIVE_API`
- **Exact File / Module**: [`weather_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/weather_service.py)
- **API / File / DB Origin**: NASA POWER Daily Point API
- **Timestamp Availability**: 30-day daily mean.
- **Location Dependency**: NASA POWER grid cell.
- **Fallback Behavior**: Source marked `"unavailable"`.
- **Confidence & Quality Limitations**: High.

---

### C. Soil Properties & Hydrology

#### 8. Topsoil pH (`phh2o`)
- **Value**: Topsoil pH value (e.g., `6.60`).
- **Classification**: `MODEL_PREDICTION` (or `LAB_MEASUREMENT` when soil lab test is provided)
- **Exact File / Module**: [`soil_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/soil_service.py) (`_fetch_via_soilgrids`)
- **API / File / DB Origin**: ISRIC SoilGrids v2.0 REST API (`https://rest.isric.org/soilgrids/v2.0/properties/query`, 0-5cm depth layer `phh2o/10`).
- **Timestamp Availability**: Static global spatial machine learning model predictions based on soil profile covariates.
- **Location Dependency**: 250m spatial resolution raster cell.
- **Fallback Behavior**: If ISRIC API is unresponsive, falls back to regional gridded soil reference model (`source: "soilgrids-reference"`).
- **Confidence & Quality Limitations**: Moderate for unmeasured locations (250m spatial model, not field-sampled wet chemistry). Laboratory measurement takes explicit precedence when available.

#### 9. Soil Clay & Sand Content (`clay`, `sand`)
- **Value**: Clay percentage (e.g., `22.0%`) and Sand percentage (e.g., `35.0%`).
- **Classification**: `MODEL_PREDICTION`
- **Exact File / Module**: [`soil_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/soil_service.py)
- **API / File / DB Origin**: ISRIC SoilGrids v2.0 REST API (0-5cm depth `clay/10` and `sand/10`).
- **Timestamp Availability**: Static spatial model prediction.
- **Location Dependency**: 250m grid cell.
- **Fallback Behavior**: Regional calibrated reference model.
- **Confidence & Quality Limitations**: Moderate.

#### 10. Soil Total Nitrogen (`nitrogen`)
- **Value**: Extractable/total soil nitrogen in mg/kg (e.g., `42.0 mg/kg`).
- **Classification**: `MODEL_PREDICTION` (or `LAB_MEASUREMENT`)
- **Exact File / Module**: [`soil_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/soil_service.py)
- **API / File / DB Origin**: ISRIC SoilGrids v2.0 REST API (`nitrogen * 10` for mg/kg conversion).
- **Timestamp Availability**: Static spatial model dataset.
- **Location Dependency**: 250m grid cell.
- **Fallback Behavior**: Regional calibrated reference model.
- **Confidence & Quality Limitations**: Moderate.

#### 11. Volumetric Soil Moisture (%)
- **Value**: Volumetric soil moisture percentage (e.g., `24.0%`).
- **Classification**: `LIVE_API`
- **Exact File / Module**: [`soil_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/soil_service.py) (`_fetch_live_soil_moisture`)
- **API / File / DB Origin**: Open-Meteo Land Surface API (`https://api.open-meteo.com/v1/forecast`, parameter `soil_moisture_0_to_7cm`).
- **Timestamp Availability**: Current hourly observation/forecast.
- **Location Dependency**: 11km ERA5-Land grid.
- **Fallback Behavior**: Approximated via soil texture relationship `15 + clay*0.5 - sand*0.1`.
- **Confidence & Quality Limitations**: High for topsoil wetness dynamics.

---

### D. Satellite Remote Sensing & Vegetation Health

#### 12. Sentinel-2 NDVI (Normalized Difference Vegetation Index)
- **Value**: NDVI vegetation index value between -1.0 and +1.0 (e.g., `0.550`).
- **Classification**: `SATELLITE_OBSERVATION`
- **Exact File / Module**: [`satellite_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/satellite_service.py) (`_fetch_via_gee`, `compute_ndvi`)
- **API / File / DB Origin**: Google Earth Engine API (`COPERNICUS/S2_SR_HARMONIZED`, spectral bands `B8` NIR and `B4` Red).
- **Timestamp Availability**: Exact satellite scene acquisition date (e.g. `2026-07-15`), with cloudy pixel filtering (<20%).
- **Location Dependency**: 10m spatial resolution pixels reduced over field boundary polygon or 1000m buffer footprint.
- **Fallback Behavior**: If GEE project is unconfigured or no cloud-free scene is available, `satellite_source` is explicitly marked as `"unavailable"` and values set to `0.0`. No synthetic fake values are passed as live.
- **Confidence & Quality Limitations**: High optical precision (10m resolution from Copernicus Sentinel-2 constellation).

---

### E. Agricultural Market & Commodity Prices

#### 13. Market Modal Price per Quintal
- **Value**: Market price in INR per quintal (e.g., `₹3,400 / quintal`).
- **Classification**: `STATIC_DATASET` (Ingested AGMARKNET official market dataset)
- **Exact File / Module**: [`market_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/market_service.py) (`load_market_prices`)
- **API / File / DB Origin**: Local ingested CSV file at `data/market_prices.csv`.
- **Timestamp Availability**: Market record date per commodity (e.g., `2026-07-20`).
- **Location Dependency**: Target state/district APMC mandi (e.g., Karnal, Indore).
- **Fallback Behavior**: Static crop database base market index (`source: "fallback-index"`).
- **Confidence & Quality Limitations**: High when periodically updated from AGMARKNET / data.gov.in exports.

---

### F. Decision Modeling, Optimization & Agronomic Output

#### 14. Crop Agronomic Parameter Baselines
- **Value**: Ideal temperature, pH, rainfall bands, water requirement, NPK benchmarks per crop.
- **Classification**: `STATIC_DATASET`
- **Exact File / Module**: [`crop_database.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/crop_database.py) (`CROP_DATABASE`)
- **API / File / DB Origin**: Embedded python reference dictionary derived from ICAR / FAO handbooks.
- **Timestamp Availability**: Static literature baselines.
- **Location Dependency**: Regional crop suitability baselines.
- **Fallback Behavior**: N/A (embedded baseline).
- **Confidence & Quality Limitations**: High baseline validity.

#### 15. AHP & Fuzzy AHP Criteria Weights
- **Value**: Criteria weights for Climate, Soil, Water Efficiency, and Market Value (summing to 1.0).
- **Classification**: `RULE_CALCULATION`
- **Exact File / Module**: [`fuzzy_ahp.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/fuzzy_ahp.py), [`mcdm.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/mcdm.py)
- **API / File / DB Origin**: Pairwise judgment matrix evaluated via Chang's extent analysis with crisp CR diagnostic.
- **Timestamp Availability**: Calculated in real-time per run.
- **Location Dependency**: Global criteria model.
- **Fallback Behavior**: Crisp Saaty AHP fallback if fuzzy matrix yields degenerate weights.
- **Confidence & Quality Limitations**: High.

#### 16. TOPSIS Closeness & ELECTRE Net Outranking Ranks
- **Value**: Ranked crop vector with TOPSIS closeness scores (0.0 to 1.0) and ELECTRE net outranking counts.
- **Classification**: `RULE_CALCULATION`
- **Exact File / Module**: [`mcdm.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/mcdm.py)
- **API / File / DB Origin**: Vector normalized decision matrix multiplied by Fuzzy AHP weights.
- **Timestamp Availability**: Calculated per run.
- **Location Dependency**: Field specific.
- **Fallback Behavior**: Tie-break resolution protocol (`ranking_tiebreak.py`).
- **Confidence & Quality Limitations**: High mathematical precision.

#### 17. NSGA-II Multi-Objective Resource Plan
- **Value**: Weekly irrigation target (`L/week`), fertilizer dosage (`kg/acre`), and Pareto front.
- **Classification**: `OPTIMIZATION_RESULT`
- **Exact File / Module**: [`nsga2.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/core/nsga2.py) (`optimize_resources_multiobjective`)
- **API / File / DB Origin**: 80-generation non-dominated sorting genetic algorithm execution.
- **Timestamp Availability**: Evaluated per run.
- **Location Dependency**: Field rainfall credit, soil moisture credit, and crop water need.
- **Fallback Behavior**: Compromise solution pick (min normalized distance to ideal point).
- **Confidence & Quality Limitations**: High optimization validity.

#### 18. Structured Agronomic Fertilizer Plan (DAP, Urea, MOP & Split Schedule)
- **Value**: NPK nutrient requirements (kg/acre and field total), DAP/Urea/MOP product quantities, and split application schedule.
- **Classification**: `RULE_CALCULATION`
- **Exact File / Module**: [`fertilizer_service.py`](file:///c:/Users/mithlesh_2/Pictures/FarmOptima_Reliability_Security/farmoptima_v5/backend/app/services/fertilizer_service.py)
- **API / File / DB Origin**: ICAR NPK conversion formulas scaled to field area (`per_acre × area`).
- **Timestamp Availability**: Calculated per run.
- **Location Dependency**: Scaled to user-specified `field_area_acres`.
- **Fallback Behavior**: Default 1.0 acre if area unspecified.
- **Confidence & Quality Limitations**: High agronomic accuracy.
