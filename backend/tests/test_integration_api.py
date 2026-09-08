"""
Integration tests for the full HTTP API. Unlike tests/test_mcdm.py,
test_gpo.py, etc. (which test pure algorithm functions directly), these
tests go through the real FastAPI app, real routing, real dependency
injection, and a real (isolated, temporary) database — proving the whole
system wires together correctly, not just that individual functions are
correct in isolation.

External services (weather/soil/satellite APIs) are mocked at the import
point inside each route module, so these tests never make a real network
call and never depend on internet access or live credentials — they will
pass identically on any machine, at any time.
"""

from app.services.weather_service import WeatherResult
from app.services.soil_service import SoilResult
from app.services.satellite_service import SatelliteResult
import app.api.routes.weather as weather_route
import app.api.routes.soil as soil_route
import app.api.routes.satellite as satellite_route
import app.api.routes.recommend as recommend_route


FAKE_WEATHER = WeatherResult(rainfall_mm_last_30d=85.0, avg_temp_c=27.5, humidity_pct=60.0, solar_radiation_mj_m2=18.0, wind_speed_m_s=2.5, source="nasa-power")
FAKE_SOIL = SoilResult(
    ph=6.6,
    clay_pct=22.0,
    sand_pct=35.0,
    soil_moisture_pct=24.0,
    nitrogen_total_mg_kg=42.0,
    organic_carbon_g_kg=18.0,
    source="soilgrids",
)
FAKE_SATELLITE = SatelliteResult(ndvi=0.55, source="gee-sentinel2", scene_date="2026-07-15")


def _patch_all_services(monkeypatch):
    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: FAKE_WEATHER)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: FAKE_SOIL)
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: FAKE_SATELLITE)


def test_root_health_check(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "FarmOptima API"


def test_weather_route_returns_mocked_data(client, monkeypatch):
    monkeypatch.setattr(weather_route, "get_weather_for_location", lambda lat, lon: FAKE_WEATHER)
    resp = client.get("/api/weather", params={"lat": 19.0, "lon": 73.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "nasa-power"
    assert body["rainfall_mm_last_30d"] == 85.0


def test_soil_route_returns_mocked_data(client, monkeypatch):
    monkeypatch.setattr(soil_route, "get_soil_for_location", lambda lat, lon: FAKE_SOIL)
    resp = client.get("/api/soil", params={"lat": 19.0, "lon": 73.0})
    assert resp.status_code == 200
    assert resp.json()["ph"] == 6.6


def test_satellite_route_returns_mocked_data(client, monkeypatch):
    monkeypatch.setattr(satellite_route, "get_ndvi_for_location", lambda lat, lon: FAKE_SATELLITE)
    resp = client.get("/api/satellite", params={"lat": 19.0, "lon": 73.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ndvi"] == 0.55
    assert body["source"] == "gee-sentinel2"


def test_recommend_full_pipeline_end_to_end(client, monkeypatch, auth_headers):
    _patch_all_services(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 19.5, "lon": 73.5}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()

    # Structural correctness
    assert body["id"] is not None
    assert body["provenance"]["weather_source"] == "nasa-power"
    assert body["provenance"]["soil_source"] == "soilgrids"
    assert body["provenance"]["satellite_source"] == "gee-sentinel2"
    assert body["data_completeness"]["weather"] == "live"
    assert body["data_completeness"]["soil"] == "live"
    assert body["data_completeness"]["satellite"] == "live"
    assert body["recommendation_status"] == "complete"
    assert body["partial_data_reason"] is None
    assert body["ahp_method"] == "fuzzy-ahp-chang-extent-analysis"
    assert body["resource_plan"]["optimizer_method"] == "nsga2-multiobjective"

    # AHP weights should sum to ~1
    assert abs(sum(body["ahp_weights"].values()) - 1.0) < 1e-6

    # Crop ranking should be properly ordered by rank 1..N
    ranks = [c["rank"] for c in body["crop_ranking"]]
    assert ranks == sorted(ranks)
    assert ranks[0] == 1

    # Pareto front should be non-empty and each point within reasonable shape
    assert len(body["resource_plan"]["pareto_front"]) > 0
    for point in body["resource_plan"]["pareto_front"]:
        assert point["water_liters_per_week"] > 0
        assert point["fertilizer_kg_per_acre"] > 0


def test_recommend_completeness_partial_data_missing_soil(client, monkeypatch, auth_headers):
    _patch_all_services(monkeypatch)
    UNAVAILABLE_SOIL = SoilResult(ph=0, clay_pct=0, sand_pct=0, soil_moisture_pct=0, nitrogen_total_mg_kg=0, organic_carbon_g_kg=0, source="unavailable")
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: UNAVAILABLE_SOIL)

    resp = client.post("/api/recommend", json={"lat": 19.5, "lon": 73.5}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommendation_status"] == "partial"
    assert body["data_completeness"]["soil"] == "unavailable"
    assert "soil (SoilGrids)" in body["partial_data_reason"]
    assert len(body["crop_ranking"]) > 0


def test_recommend_completeness_all_unavailable(client, monkeypatch, auth_headers):
    UNAVAILABLE_WEATHER = WeatherResult(rainfall_mm_last_30d=0, avg_temp_c=0, humidity_pct=0, solar_radiation_mj_m2=0, wind_speed_m_s=0, source="unavailable")
    UNAVAILABLE_SOIL = SoilResult(ph=0, clay_pct=0, sand_pct=0, soil_moisture_pct=0, nitrogen_total_mg_kg=0, organic_carbon_g_kg=0, source="unavailable")
    UNAVAILABLE_SAT = SatelliteResult(ndvi=0, source="unavailable", scene_date=None)

    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: UNAVAILABLE_WEATHER)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: UNAVAILABLE_SOIL)
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: UNAVAILABLE_SAT)

    resp = client.post("/api/recommend", json={"lat": 19.5, "lon": 73.5}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommendation_status"] == "unavailable"
    assert body["crop_ranking"] == []
    assert "All required environmental data sources are currently unreachable" in body["partial_data_reason"]



def test_recommend_persists_to_database(client, monkeypatch, auth_headers):
    _patch_all_services(monkeypatch)
    resp1 = client.post("/api/recommend", json={"lat": 19.5, "lon": 73.5}, headers=auth_headers)
    resp2 = client.post("/api/recommend", json={"lat": 20.1, "lon": 74.2}, headers=auth_headers)
    id1 = resp1.json()["id"]
    id2 = resp2.json()["id"]
    assert id1 != id2  # two distinct persisted rows


def test_recommend_rejects_null_island(client, monkeypatch, auth_headers):
    _patch_all_services(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 0, "lon": 0}, headers=auth_headers)
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "invalid_location"


def test_recommend_rejects_out_of_range_latitude(client, monkeypatch, auth_headers):
    _patch_all_services(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 999, "lon": 73.5}, headers=auth_headers)
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"


def test_farms_create_and_list(client, auth_headers):
    create_resp = client.post("/api/farms", params={"name": "Test Farm"}, json={"lat": 19.0, "lon": 73.0}, headers=auth_headers)
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["name"] == "Test Farm"

    list_resp = client.get("/api/farms", headers=auth_headers)
    assert list_resp.status_code == 200
    farms = list_resp.json()
    assert len(farms) == 1
    assert farms[0]["id"] == created["id"]


def test_farms_list_empty_when_none_created(client, auth_headers):
    resp = client.get("/api/farms", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_unhandled_exception_returns_standard_error_envelope(client, monkeypatch):
    def broken(lat, lon):
        raise RuntimeError("simulated upstream crash")

    monkeypatch.setattr(weather_route, "get_weather_for_location", broken)
    resp = client.get("/api/weather", params={"lat": 19.0, "lon": 73.0})
    assert resp.status_code == 500
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "internal_error"


def test_recommend_accepts_manual_decimal_coordinates(client, monkeypatch, auth_headers):
    _patch_all_services(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.3926, "lon": 73.8706}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["location"]["lat"] == 18.3926
    assert body["location"]["lon"] == 73.8706
    assert body["recommendation_status"] == "complete"


def test_recommend_accepts_negative_coordinates(client, monkeypatch, auth_headers):
    _patch_all_services(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": -18.3926, "lon": -73.8706}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["location"]["lat"] == -18.3926
    assert body["location"]["lon"] == -73.8706


def test_recommend_accepts_boundary_coordinates(client, monkeypatch, auth_headers):
    _patch_all_services(monkeypatch)
    # Latitude boundary: 90
    resp_north = client.post("/api/recommend", json={"lat": 90.0, "lon": 45.0}, headers=auth_headers)
    assert resp_north.status_code == 200

    # Latitude boundary: -90
    resp_south = client.post("/api/recommend", json={"lat": -90.0, "lon": 45.0}, headers=auth_headers)
    assert resp_south.status_code == 200

    # Longitude boundary: 180
    resp_east = client.post("/api/recommend", json={"lat": 45.0, "lon": 180.0}, headers=auth_headers)
    assert resp_east.status_code == 200

    # Longitude boundary: -180
    resp_west = client.post("/api/recommend", json={"lat": 45.0, "lon": -180.0}, headers=auth_headers)
    assert resp_west.status_code == 200


def test_recommend_rejects_out_of_range_longitude(client, monkeypatch, auth_headers):
    _patch_all_services(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.3926, "lon": 181.0}, headers=auth_headers)
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"

