# Phase 1 Implementation - Quick Reference Checklist

## ✅ VERIFICATION CHECKLIST

Use this checklist to verify the Phase 1 real data implementation is working correctly.

---

## 🏃 QUICK START (5 minutes)

- [ ] Backend imports verify
- [ ] Frontend builds successfully
- [ ] Start backend: `python -m uvicorn app.main:app --reload --port 8000`
- [ ] Start frontend: `npm run dev`
- [ ] Login to app at http://localhost:5173
- [ ] Click map location
- [ ] Click "Get recommendation"
- [ ] Verify results (see checklist below)

---

## 🧪 VERIFICATION TESTS

### Backend Compilation

```bash
cd backend
# Should complete with no errors
python -c "from app.services.soil_service import get_soil_for_location; print('✓ OK')"
python -c "from app.services.satellite_service import get_ndvi_for_location; print('✓ OK')"
python -c "from app.main import app; print('✓ OK')"
```

- [ ] All imports succeed
- [ ] No syntax errors
- [ ] No module not found errors

### Frontend Build

```bash
cd frontend
npm run build
# Should complete in <2 seconds
```

- [ ] Build succeeds
- [ ] dist/ folder created
- [ ] No warnings
- [ ] No errors

### Backend Service Test

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
# Should start without errors
```

- [ ] Server starts on port 8000
- [ ] No import errors
- [ ] No connection errors
- [ ] Logs show "Uvicorn running on..."

### Frontend Dev Server

```bash
cd frontend
npm run dev
# Should start without errors
```

- [ ] Dev server starts
- [ ] Shows "Local: http://localhost:5173"
- [ ] No build errors
- [ ] Page loads

---

## 🎯 APPLICATION VERIFICATION

### Authentication Flow

1. Navigate to http://localhost:5173
2. Click "Register" or "Sign In"
   - [ ] Registration page loads
   - [ ] Login page loads
   - [ ] Can register new account
   - [ ] Can login with credentials
   - [ ] JWT token stored in localStorage

### Map & Location Selection

1. After login, should see map with location selector
   - [ ] Leaflet map displays
   - [ ] Can click to select location
   - [ ] Selected location shows marker
   - [ ] Coordinates display in input fields

### Recommendation Request

1. Click "Get Recommendation" button
   - [ ] Button disabled during load (shows spinner)
   - [ ] No 401 Unauthorized errors
   - [ ] No 500 Internal Server errors
   - [ ] Response received within 10 seconds
   - [ ] Dashboard appears with data

---

## 📊 DATA VERIFICATION

### Weather Section (Should WORK - NASA POWER)

```
WEATHER & CLIMATE CONDITIONS
- Temperature: [numeric value] °C
- Rainfall (30-day): [numeric value] mm
- Humidity: [numeric value] %
- Source badges: All should show "LIVE" (green)
```

**Verification**:

- [ ] Temperature value > -10 and < 50 (reasonable range)
- [ ] Rainfall value > 0 (mm)
- [ ] Humidity value 0-100%
- [ ] All three show "LIVE" badge (green)
- [ ] Tooltip says "Live: nasa-power"

### Soil Section (May show LIVE or UNAVAILABLE)

```
SOIL PROPERTIES
- Soil pH: [value or —] [badge]
- Nitrogen: [value or —] mg/kg [badge]
- Organic Carbon: [value or —] g/kg [badge]
- Soil Moisture: [value or —] % [badge]
```

**If LIVE (SoilGrids working)**:

- [ ] pH: 4.0-9.0 (typical soil range)
- [ ] Nitrogen: 0-500 mg/kg
- [ ] Organic Carbon: 0-100 g/kg
- [ ] Moisture: 0-60%
- [ ] All show "LIVE" badge (green)

**If UNAVAILABLE (expected without network)**:

- [ ] pH: shows "—" (dash)
- [ ] Nitrogen: shows "—"
- [ ] Organic Carbon: shows "—"
- [ ] Moisture: shows "—"
- [ ] All show "UNAVAILABLE" badge (red)
- [ ] Tooltip says "Service unavailable"

**NEVER should show**:

- ❌ "MOCK" badge with real-looking numbers
- ❌ "LIVE" with zero values
- ❌ Exact same value every location

### Vegetation Section (May show LIVE or UNAVAILABLE)

```
VEGETATION & SATELLITE DATA
- NDVI Index: [value or —] [badge]
- Scene Date: [date or not shown]
- [Satellite image viewer or unavailable message]
```

**If LIVE (Earth Engine configured + Sentinel-2 available)**:

- [ ] NDVI: -1.0 to +1.0 (real NDVI range)
- [ ] NDVI: > 0.0 for vegetated area
- [ ] Scene date shown (recent date)
- [ ] Shows "LIVE" badge (green)
- [ ] Satellite image viewer displays
- [ ] Can see true-color Sentinel-2 imagery
- [ ] Image shows coordinates in overlay

**If UNAVAILABLE (expected without GEE_PROJECT)**:

- [ ] NDVI: shows "—"
- [ ] Shows "(Service unavailable)"
- [ ] Shows "UNAVAILABLE" badge (red)
- [ ] No satellite image viewer
- [ ] Tooltip says "Service unavailable"

**NEVER should show**:

- ❌ "MOCK" badge with real NDVI
- ❌ "LIVE" with deterministic value
- ❌ Same NDVI value every location

### Data Provenance (Bottom of page)

```
Data Sources: satellite: [source] | weather: [source] | soil: [source]
```

**Verification**:

- [ ] Weather shows: "nasa-power" OR "mock"
- [ ] Soil shows: "soilgrids" OR "unavailable"
- [ ] Satellite shows: "gee-sentinel2" OR "unavailable"
- [ ] Never shows all as "mock"
- [ ] At least weather should be real data

---

## 📈 MCDM Pipeline Verification

### AHP Weights Section

```
AHP ANALYTICAL HIERARCHY PROCESS
Weights:
- Soil: X%
- Weather: X%
- NDVI: X%
- [consistency ratio information]
```

**Verification**:

- [ ] All weights sum to ~100%
- [ ] Weights reasonable (not all zero)
- [ ] Consistency ratio < 0.1 (if shown)
- [ ] No NaN or Infinity values

### Crop Recommendations

```
CROP RANKING (TOPSIS-ELECTRE)
1. [Crop Name] - Score: X.XX
2. [Crop Name] - Score: X.XX
3. [Crop Name] - Score: X.XX
```

**Verification**:

- [ ] List contains 3-5 crops
- [ ] Each has numeric score
- [ ] Scores in reasonable range (0-1.0)
- [ ] Top crop has highest score
- [ ] No repeated crops
- [ ] Works with REAL data (not deterministic mock)

### Resource Plan

```
RESOURCE PLAN & OPTIMIZATION
Water requirement: X units
Fertilizer: X units
Schedule: [timing information]
```

**Verification**:

- [ ] Water, Fertilizer show numeric values
- [ ] Values change based on crop/location
- [ ] Schedule is reasonable
- [ ] Changes with real data (not fixed)

---

## 🔍 BROWSER CONSOLE CHECK

Press F12 in browser to open Developer Tools, check Console tab:

**Should NOT see**:

- ❌ 401 Unauthorized errors
- ❌ 403 Forbidden errors
- ❌ 500 Internal Server errors
- ❌ CORS errors
- ❌ Network errors
- ❌ Undefined is not a function
- ❌ Cannot read property of undefined
- ❌ Failed to parse response JSON

**Should see**:

- ✅ No errors
- ✅ API call to /api/recommend (200 OK)
- ✅ Components rendering without errors

---

## ✅ SUCCESS CRITERIA

### Minimum Passing (Phase 1 works):

- ✅ Backend starts without errors
- ✅ Frontend starts without errors
- ✅ Can login/register
- ✅ Can select location
- ✅ Get recommendation returns data
- ✅ Weather section shows LIVE data
- ✅ Recommendation engine produces results

### Full Passing (All features working):

- ✅ + Soil shows LIVE or UNAVAILABLE (not MOCK as LIVE)
- ✅ + Satellite shows image viewer
- ✅ + All provenance fields accurate
- ✅ + No console errors
- ✅ + MCDM pipeline produces different results for different locations

### Configuration Complete (Advanced):

- ✅ ++ Earth Engine configured (GEE_PROJECT set)
- ✅ ++ NDVI shows LIVE with real Sentinel-2 data
- ✅ ++ Scene dates match current season

---

## 🐛 TROUBLESHOOTING

### "Soil shows UNAVAILABLE"

**Expected**: Yes, if network is blocked or SoilGrids is unreachable
**Solution**:

- [ ] Check: `curl https://rest.isric.org/soilgrids/v2.0/properties/query`
- [ ] Check backend logs for "SoilGrids request failed"
- [ ] This is NOT a bug, just network unavailable

### "Satellite shows UNAVAILABLE"

**Expected**: Yes, if `GEE_PROJECT` not set
**Solution**:

- [ ] Is GEE_PROJECT set in .env? (Check: `echo $GEE_PROJECT`)
- [ ] If not set, this is expected behavior
- [ ] To enable: Follow Earth Engine setup in PHASE_1_REAL_DATA_IMPLEMENTATION.md
- [ ] This is NOT a bug, just feature disabled

### "Weather shows MOCK"

**Expected**: Only if NASA POWER API is down
**Solution**:

- [ ] Check: `curl https://power.larc.nasa.gov/api/temporal/daily/point?...`
- [ ] NASA POWER should work (public API)
- [ ] If failing, NASA servers may be down

### "Recommendation shows all zeros"

**Likely cause**: All services failed simultaneously
**Solution**:

- [ ] Check backend logs for errors
- [ ] Verify network connectivity
- [ ] Try different location
- [ ] Restart backend

### "Get Recommendation button doesn't work"

**Check**: Browser console (F12)

- [ ] 401 error? = Authentication failed, re-login
- [ ] 500 error? = Backend crashed, check logs
- [ ] Network error? = Backend not running
- [ ] CORS error? = Backend/Frontend port mismatch

---

## 📝 FINAL SIGN-OFF

Use this section to document verification results:

**Date**: ******\_******
**Tester**: ******\_******

**Backend Status**: ☐ Pass ☐ Fail
**Frontend Status**: ☐ Pass ☐ Fail
**Integration Status**: ☐ Pass ☐ Fail
**Data Accuracy**: ☐ Pass ☐ Fail

**Notes**:

---

---

**Recommendation**: ☐ Ready for deployment ☐ Needs fixes

---

## 📞 NEXT STEPS IF ALL TESTS PASS

1. **Database Verification**
   - Check SQLite database contains real values
   - Verify recommendation records persist
   - Check provenance field accuracy

2. **Load Testing**
   - Test multiple users simultaneously
   - Test multiple locations
   - Check performance with real data

3. **Earth Engine Setup (Optional)**
   - Configure Google Cloud Project
   - Enable Earth Engine API
   - Set GEE_PROJECT environment variable
   - Verify Sentinel-2 data integration

4. **Production Deployment**
   - Deploy to staging environment
   - Run full test suite on production URLs
   - Monitor for real user issues
   - Document any API rate limiting

---

_Use this checklist after every code change to ensure Phase 1 remains stable._
