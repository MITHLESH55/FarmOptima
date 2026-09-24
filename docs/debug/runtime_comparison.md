# Runtime Comparison Audit

| Field | Direct API (`http://127.0.0.1:8000/api/recommend`) | Browser Network Payload | Rendered UI Element |
|---|---|---|---|
| `top_crop` | `"Rice"` | `"Rice"` | `"Rice"` (Rank #1 of 8 Analyzed) |
| `topsis_closeness` | `0.7196` | `0.7196` | `0.7196` |
| `electre_net_outranking` | `6` | `6` | `+6` |
| `ndvi` (GEE Live) | `0.437` | `0.437` | `0.437` |
| `ndvi` (GEE Unavailable) | `null` | `null` | `—` / `Unavailable` |
| `ndvi_status` | `"dense vegetation"` | `"dense vegetation"` | `"dense vegetation"` |
| `satellite_source` | `"gee-sentinel2"` | `"gee-sentinel2"` | `"gee-sentinel2"` |
| `soil_source` | `"soilgrids-cached"` | `"soilgrids-cached"` | `"CACHED"` |
| `weather_source` | `"nasa-power"` | `"nasa-power"` | `"LIVE"` |
