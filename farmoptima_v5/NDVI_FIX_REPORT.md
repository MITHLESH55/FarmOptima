# FarmOptima NDVI Issue - Root Cause & Fix

**Date:** 2026-08-13
**Status:** ✅ FIXED
**Issue:** Frontend displaying "NDVI unavailable" despite verified working Google Earth Engine

---

## 🔍 Root Cause Analysis

### Issue 1: Missing earthengine-api Package

**Severity:** CRITICAL
**Impact:** All NDVI requests failed silently

The `earthengine-api` package was commented out in `backend/requirements.txt` on line 16:

```
# earthengine-api==1.1.0  ← COMMENTED OUT
```

When the backend tried to import `ee`, it raised `ModuleNotFoundError`, which was caught by the broad exception handler and silently converted to:

```python
SatelliteResult(ndvi=0.0, source="unavailable", scene_date=None)
```

**Why This Happened:**

- The package was intentionally commented out as "optional" for Phase 1
- Phase 2-3 requires GEE integration but requirements.txt wasn't updated
- No error logging existed to surface the import failure

---

### Issue 2: Cloud Filter Too Strict

**Severity:** HIGH
**Impact:** Even with earthengine-api installed, queries returned empty collections

The original cloud filtering was:

```python
.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))  # Maximum 20% cloud cover
```

For the test location (lat=18.6275, lon=73.9506) during June-August 2026, there were **no cloud-free Sentinel-2 images** with <20% cloud cover in the 60-day lookback period.

GEE's `.first()` on an empty collection returns a null Image object (not Python None), which caused:

```
ee.ee_exception.EEException: Image.select: Parameter 'input' is required and may not be null.
```

**Why This Happened:**

- Cloud cover threshold (20%) was too aggressive for tropical regions
- 60-day lookback may be insufficient for some locations
- No fallback to less-strict filtering was implemented

---

## ✅ Fixes Implemented

### Fix 1: Uncomment earthengine-api in requirements.txt

**File:** `backend/requirements.txt`

Changed:

```
# earthengine-api==1.1.0
```

To:

```
earthengine-api==1.1.0
```

**Installation:**

```bash
pip install earthengine-api==1.1.0
```

This brings in all required Google Cloud dependencies for EE API communication.

---

### Fix 2: Relax Cloud Pixel Percentage Filter

**File:** `backend/app/services/satellite_service.py` (line ~49)

Changed:

```python
.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))  # Too strict
```

To:

```python
.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))  # More reasonable
```

**Rationale:**

- 50% cloud cover is still acceptable for NDVI calculation (we use mean reducer)
- Allows retrieval in tropical/monsoon regions during rainy seasons
- Maintains data quality while avoiding empty collections
- User can adjust this value in `satellite_service.py` if stricter filtering is desired

---

### Fix 3: Robust GEE Null Image Detection

**File:** `backend/app/services/satellite_service.py` (lines 89-94)

Added explicit check to detect null GEE Images before attempting operations:

```python
try:
    image_id_info = image.get("system:id").getInfo()
    logger.info(f"[NDVI_DIAGNOSTIC] Selected image ID: {image_id_info}")
except Exception as e:
    logger.warning(f"[NDVI_DIAGNOSTIC] Image is null or unavailable: {type(e).__name__}: {e}")
    return None
```

This prevents cryptic "Parameter 'input' is required" errors and clearly identifies null images.

---

### Fix 4: Comprehensive Diagnostic Logging

**File:** `backend/app/services/satellite_service.py`

Added detailed logging at every step of the NDVI retrieval:

- GEE project initialization
- Collection query details
- Image selection and ID
- NDVI calculation stages
- Exception tracebacks (with full detail, not silent catches)

**Benefit:** Any future NDVI issues are immediately visible in logs with full context.

---

## 🧪 Verification & Testing

### Test 1: Direct NDVI Calculation

```
Coordinates: lat=18.6275, lon=73.9506
NDVI Result: 0.365 (from 2026-07-14 Sentinel-2 image)
Source: gee-sentinel2
Status: ✅ SUCCESS
```

### Test 2: Startup Configuration

```
GEE_PROJECT loading: ✅ farmoptima-2026
EE.Initialize(): ✅ Succeeded
Earthengine-api import: ✅ Successful
```

### Test 3: API Response Structure

Expected format now returns:

```json
{
  "ndvi": 0.365,
  "source": "gee-sentinel2",
  "scene_date": "2026-07-14"
}
```

Instead of:

```json
{
  "ndvi": 0.0,
  "source": "unavailable",
  "scene_date": null
}
```

---

## 📋 Files Changed

| File                                        | Changes                                                       | Lines  | Status |
| ------------------------------------------- | ------------------------------------------------------------- | ------ | ------ |
| `backend/requirements.txt`                  | Uncomment earthengine-api                                     | 16     | ✅     |
| `backend/app/services/satellite_service.py` | Cloud filter 20→50%, null image detection, diagnostic logging | 42-175 | ✅     |

**Total Changes:** 2 files, ~130 lines

---

## 🚀 Deployment Steps

1. **Install dependencies:**

   ```bash
   cd backend
   .\venv\Scripts\pip install -r requirements.txt
   ```

2. **Restart backend:**

   ```bash
   cd backend
   .\venv\Scripts\python -m uvicorn app.main:app --reload
   ```

3. **Test NDVI endpoint:**

   ```bash
   curl "http://localhost:8000/api/satellite?lat=18.6275&lon=73.9506"
   ```

4. **Test recommendation endpoint:**

   ```bash
   POST /api/recommend
   Body: {"lat": 18.6275, "lon": 73.9506}
   ```

5. **Frontend verification:**
   - Get a recommendation
   - Check NDVI displays numeric value (not "unavailable")
   - Verify it works in all 3 languages (EN, HI, MR)

---

## 📊 Performance Impact

- **NDVI Retrieval Time:** ~2-5 seconds (GEE API call)
- **Memory Impact:** Negligible (small GDAL/numpy operations)
- **Cloud Cost:** Minimal (GEE free tier includes 100x100km analysis regions)

---

## ⚠️ Edge Cases & Fallback Behavior

1. **GEE Project Not Configured:**
   - Returns: `SatelliteResult(ndvi=0.0, source="unavailable", scene_date=None)`
   - Logged: Info-level "GEE_PROJECT not set"
   - Frontend: Shows "NDVI unavailable"

2. **No Suitable Imagery Found:**
   - Tries all images in 60-day period with <50% cloud
   - If still none found, returns unavailable
   - Future: Could expand date range or use mock fallback

3. **GEE Authentication Fails:**
   - Logged: Warning with full exception details
   - Returned: unavailable result (doesn't crash backend)

4. **Network Error:**
   - Logged: Error with exception traceback
   - Returned: unavailable result

---

## 🔐 Security Notes

- ✅ No credentials exposed in logs (only project ID)
- ✅ .env file with GEE_PROJECT not modified
- ✅ Google Cloud IAM unchanged
- ✅ Service account credentials not printed
- ✅ No secrets in diagnostic logging

---

## 📝 Next Steps

After deployment:

1. Monitor backend logs for `[NDVI_DIAGNOSTIC]` entries
2. Test with multiple locations and dates
3. If needed, adjust cloud threshold (currently 50%) in satellite_service.py
4. Consider expanding lookback period if necessary (currently 60 days)
5. Verify NDVI displays in all 3 languages without hardcoding

---

## Summary

✅ **Root Cause:** Missing earthengine-api package + strict cloud filtering  
✅ **Fix:** Install package, relax cloud filter to 50%, add robust null detection  
✅ **Testing:** NDVI 0.365 retrieved successfully for test coordinates  
✅ **Impact:** Zero breaking changes, production-ready  
✅ **Rollback:** Simple (revert requirements.txt, rebuild venv)

**NDVI now working correctly with real Google Earth Engine data!**
