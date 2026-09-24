# Frontend Runtime Trace

```
App.jsx
  ↓ (Auth Context: Bearer JWT Token)
Dashboard.jsx
  ↓ (Location Request: lat=18.6116, lon=73.9553)
useRecommendation Hook / Axios HTTP Client
  ↓ (POST http://127.0.0.1:8000/api/recommend)
RecommendationResponse Payload Received
  ↓
State Update: `data`
  ↓
LiveFieldDataPanel ({ data, locale })
  ├── MetricCard (Weather): liveBadge="nasa-power" → SourceBadge: "LIVE"
  ├── MetricCard (Soil): liveBadge="soilgrids-cached" → SourceBadge: "CACHED"
  ├── MetricCard (NDVI): value=0.437, status="dense vegetation", badge="gee-sentinel2"
  └── Satellite Tile Card: Leaflet MapContainer + Marker (Centroid: 18.6116° N, 73.9553° E)
```
