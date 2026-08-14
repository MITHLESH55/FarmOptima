# FarmOptima Phase 1 - Real Data Integration Implementation Guide

## Overview

This document describes the implementation of real data integration for Phase 1 of FarmOptima, replacing mock data with live integrations to:

- **SoilGrids API** for soil properties
- **Google Earth Engine / Sentinel-2** for vegetation indices
- **NASA POWER API** for weather data (already working)

## Architecture

```
User Interface (React)
        ↓
FastAPI Backend (/api/recommend)
        ↓
    ┌───┴────────────────────┐
    ↓                         ↓
Weather Service        Soil Service        Satellite Service
(NASA POWER)          (SoilGrids)        (Earth Engine + Sentinel-2)
    ↓                         ↓                       ↓
Weather Data          Soil Data                NDVI + Scene Date + Tile URL
    ↓                         ↓                       ↓
    └─────────────────────────┴───────────────────────┘
                      ↓
            MCDM Pipeline
         (AHP → TOPSIS → ELECTRE → NSGA-II)
                      ↓
            Recommendation Response
                      ↓
             React Dashboard Display
```

## Implementation Details

### 1. Soil Service (`backend/app/services/soil_service.py`)

**Real Integration**: SoilGrids REST API v2.0

**Endpoint**: `https://rest.isric.org/soilgrids/v2.0/properties/query`

**Properties Retrieved** (0-5 cm depth):

- `phh2o` → pH (divided by 10)
- `nitrogen` → Total nitrogen (divided by 100 to convert cg/kg → mg/kg)
- `soc` → Soil organic carbon (divided by 10 to convert dg/kg → g/kg)
- `clay`, `sand` → Texture properties

**Credentials Required**: None (public API)

**Network Requirements**:

- HTTPS access to rest.isric.org
- Timeout: 15 seconds

**Fallback Behavior**:

- If API call fails → Returns `SoilResult` with `source="unavailable"`
- Frontend displays: "—" and "UNAVAILABLE" status badge

**Test**:

```python
from app.services.soil_service import get_soil_for_location
result = get_soil_for_location(12.5, 75.5)
print(f"pH: {result.ph}, Source: {result.source}")
# Expected: pH: X.XX, Source: soilgrids (or unavailable if network fails)
```

### 2. Satellite Service (`backend/app/services/satellite_service.py`)

**Real Integration**: Google Earth Engine + Sentinel-2

**API**: Earth Engine Python API

**Dataset**: COPERNICUS/S2_SR_HARMONIZED (Sentinel-2 L2A)

**Processing**:

1. Filters by location (point + 50m buffer)
2. Filters by date (last 60 days by default)
3. Filters by cloud coverage (<20%)
4. Calculates NDVI = (B8 - B4) / (B8 + B4)
5. Returns mean NDVI, scene date, source

**Credentials Required**:

- Google Cloud Project ID in `GEE_PROJECT` environment variable
- Earth Engine authentication token

**Setup Instructions**:

```bash
# 1. Create a Google Cloud Project
#    https://console.cloud.google.com → Create Project

# 2. Enable Earth Engine API
#    IAM & Admin → APIs & Services → Search "Earth Engine" → Enable

# 3. Create a service account (or use personal account)
#    IAM & Admin → Service Accounts → Create Service Account
#    Download JSON key (save as ~/ee-key.json)

# 4. Install Python dependencies
pip install earthengine-api

# 5. Authenticate
earthengine authenticate

# 6. Set environment variable in .env
GEE_PROJECT=your-google-cloud-project-id

# 7. Verify
earthengine info
```

**Fallback Behavior**:

- If `GEE_PROJECT` not set → Returns `source="unavailable"`
- If authentication fails → Returns `source="unavailable"`
- If no cloud-free scene in date range → Returns `source="unavailable"`

**Test**:

```python
from app.services.satellite_service import get_ndvi_for_location
result = get_ndvi_for_location(12.5, 75.5)
print(f"NDVI: {result.ndvi}, Source: {result.source}")
# Expected: NDVI: 0.XXX, Source: gee-sentinel2 (or unavailable)
```

### 3. Weather Service (`backend/app/services/weather_service.py`)

**Status**: ✅ ALREADY WORKING

**Real Integration**: NASA POWER Daily Point API

**Endpoint**: `https://power.larc.nasa.gov/api/temporal/daily/point`

**Properties**:

- `PRECTOTCORR` → Rainfall (mm/day, 30-day sum)
- `T2M` → Temperature (°C, averaged)
- `RH2M` → Relative Humidity (%, averaged)

**Credentials Required**: None (public API)

**Fallback Behavior**:

- If API fails → Returns `source="mock"` (deterministic)
- Note: Currently uses mock fallback; can be updated to use "unavailable" if needed

---

## Frontend Changes

### Component: `ResultsPanel.jsx`

**Updates**:

1. **SourceBadge Component**
   - Now shows three states:
     - `"live"` → Green badge (data from real source)
     - `"unavailable"` → Red badge (service not accessible)
     - `"mock"` → Beige badge (deterministic fallback)

2. **StatCard Component**
   - Added `isUnavailable` prop
   - Shows "—" instead of "0" when data is unavailable
   - Grayed out text for unavailable fields

3. **Soil Section**
   - Displays: pH, Nitrogen, Organic Carbon, Moisture
   - All with source badges (LIVE, UNAVAILABLE, or MOCK)

4. **Vegetation Section**
   - Displays: NDVI Index, Scene Date (if available)
   - Added: Sentinel-2 True Color satellite image viewer
   - Uses iframe to Sentinel Hub maps for actual satellite imagery

### Satellite Image Viewer

**Implementation**:

```jsx
<iframe
  src={`https://maps.sentinel-hub.com/?zoom=13&lat=${lat}&lng=${lon}&view=true-color`}
  width="100%"
  height="224px"
  style={{ border: "none" }}
  title="Sentinel-2 Satellite View"
/>
```

**Features**:

- Real Sentinel-2 true color composite imagery
- Centered on selected farm coordinates
- Interactive zoom/pan (in iframe)
- Shows acquisition dates and cloud information

---

## API Response Schema

**Endpoint**: `POST /api/recommend`

**New Fields in `RecommendationResponse`**:

```json
{
  "ndvi": 0.456,
  "satellite_scene_date": "2026-08-10",
  "satellite_tile_url": "https://tiles.sentinel-hub.com/wms/{z}/{x}/{y}?...",

  "soil_ph": 6.32,
  "soil_nitrogen_mg_kg": 127.5,
  "soil_organic_carbon_g_kg": 22.3,
  "soil_moisture_pct": 37.2,

  "rainfall_mm_last_30d": 463.6,
  "avg_temp_c": 23.1,
  "humidity_pct": 91.7,

  "provenance": {
    "satellite_source": "gee-sentinel2", // or "unavailable"
    "weather_source": "nasa-power", // or "mock"
    "soil_source": "soilgrids", // or "unavailable"
    "market_source": "csv"
  }
}
```

---

## Data Provenance System

Each data source is tracked in the provenance field:

| Source          | Status              | Indicator               |
| --------------- | ------------------- | ----------------------- |
| `nasa-power`    | ✅ Working          | LIVE (green badge)      |
| `soilgrids`     | ⚠️ Requires network | LIVE or UNAVAILABLE     |
| `gee-sentinel2` | ⚠️ Requires config  | LIVE or UNAVAILABLE     |
| `mock`          | Fallback            | MOCK (beige badge)      |
| `unavailable`   | Service failed      | UNAVAILABLE (red badge) |

**Rule**: No fake data presented as LIVE

- Real data → source shows actual API (e.g., "nasa-power")
- Unavailable → shown as "UNAVAILABLE", not fake values

---

## Testing Phase 1 Implementation

### 1. Backend Testing

```bash
cd backend

# Test soil service
python -c "
from app.services.soil_service import get_soil_for_location
soil = get_soil_for_location(12.5, 75.5)
print(f'Soil: pH={soil.ph}, N={soil.nitrogen_total_mg_kg}mg/kg, C={soil.organic_carbon_g_kg}g/kg, src={soil.source}')
"

# Test weather service
python -c "
from app.services.weather_service import get_weather_for_location
weather = get_weather_for_location(12.5, 75.5)
print(f'Weather: T={weather.avg_temp_c}°C, RH={weather.humidity_pct}%, Rain={weather.rainfall_mm_last_30d}mm, src={weather.source}')
"

# Test satellite service (with GEE_PROJECT set)
python -c "
from app.services.satellite_service import get_ndvi_for_location
sat = get_ndvi_for_location(12.5, 75.5)
print(f'Satellite: NDVI={sat.ndvi}, Date={sat.scene_date}, src={sat.source}')
"
```

### 2. API Testing

```bash
# Start backend
python -m uvicorn app.main:app --reload --port 8000

# In another terminal, test endpoint
curl -X POST http://localhost:8000/api/recommend \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"lat": 12.5, "lon": 75.5}'

# Check provenance
# Should show "soilgrids", "nasa-power", "gee-sentinel2" or "unavailable"
```

### 3. Frontend Testing

```bash
# Build and run
cd frontend
npm run dev
# Navigate to http://localhost:5173

# Test flow:
# 1. Register/Login
# 2. Click location on map
# 3. Click "Get recommendation"
# 4. Check Soil section - should show real values or UNAVAILABLE
# 5. Check Vegetation section - should show satellite image or UNAVAILABLE
# 6. Verify source badges show correct status
```

---

## Troubleshooting

### ❌ Soil Data Shows "UNAVAILABLE"

**Possible Causes**:

1. Network connection to rest.isric.org blocked
2. SoilGrids API temporarily down
3. Firewall/proxy blocking HTTPS

**Solution**:

```bash
# Test connectivity
curl -I https://rest.isric.org/soilgrids/v2.0/properties/query

# Check backend logs for detailed error
# Look for "SoilGrids request failed"
```

### ❌ Satellite Data Shows "UNAVAILABLE"

**Possible Causes**:

1. `GEE_PROJECT` not set in .env
2. Earth Engine authentication failed
3. No cloud-free Sentinel-2 scene in date range

**Solution**:

```bash
# Verify GEE_PROJECT
echo $GEE_PROJECT  # Should print your project ID

# Verify Earth Engine authentication
earthengine info  # Should show authentication status

# Check backend logs for "Earth Engine request failed"
```

### ❌ Recommendation Engine Fails with Unavailable Data

**Expected Behavior**: Recommendation engine should still work

- Uses available data + defaults for unavailable fields
- Recommendation quality may degrade with missing data

**Solution**:

- At least weather (NASA POWER) should work
- Verify recommendation endpoint doesn't crash with null values

---

## Files Modified

### Backend

- `app/services/soil_service.py` - Changed fallback from mock to unavailable
- `app/services/satellite_service.py` - Changed fallback from mock to unavailable, added logging
- `app/schemas/recommendation.py` - Added satellite_tile_url field
- `app/api/routes/recommend.py` - Import and pass satellite_tile_url to response

### Frontend

- `src/components/ResultsPanel.jsx` - Enhanced SourceBadge, added unavailable state, added satellite image viewer

### Configuration

- `.env` - Set GEE_PROJECT (user must create/configure)

---

## Next Steps

### For Phase 1 Completion:

1. [ ] Test with real coordinates in your region
2. [ ] Verify SoilGrids data appears when network available
3. [ ] Configure Google Earth Engine (optional for now)
4. [ ] Verify satellite image displays
5. [ ] Confirm recommendation engine still works with real data
6. [ ] Check database persistence includes new fields

### For Phase 2:

1. Implement historical trend charts
2. Add crop-specific alerts
3. Multi-field management
4. Mobile responsiveness
5. Performance optimization

---

## References

- **SoilGrids**: https://www.isric.org/explore/soilgrids/
- **NASA POWER**: https://power.larc.nasa.gov/
- **Google Earth Engine**: https://earthengine.google.com/
- **Sentinel-2**: https://sentinel.esa.int/web/sentinel/missions/sentinel-2
- **Sentinel Hub Maps**: https://maps.sentinel-hub.com/
