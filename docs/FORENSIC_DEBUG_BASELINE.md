# Forensic Debug Baseline

**Date**: 2026-09-11  
**Git Branch**: `main`  
**Git Commit**: `3b2d242` ("Add manual farm coordinate selection and fix recommendation request")  
**Backend Tests Collected**: 310 tests  
**Frontend Lint Status**: 0 errors, 3 warnings  
**Current API Endpoint**: `POST /recommend`  
**Reported Symptoms**:
- Target Farm: (18.6116 N, 73.9553 E)
- Top Recommended Crop: Rice
- TOPSIS Closeness: 0.6219
- ELECTRE Rank: +2
- Weather: Temp = 23.8 °C, Rainfall (30d) = 281.4 mm, Humidity = 91.9%, Solar = 12.32 MJ/m²
- Soil: pH = 6.9, Nitrogen = 1335 mg/kg, Organic Carbon = 14 g/kg, Soil Moisture = 15%
- Satellite Source: `unavailable`
- NDVI: `0`
- Satellite Image Card: Displays "Live Satellite True Color Imagery"
