"""
Unit and integration tests for Manual Location Entry validation & pipeline flow.
"""

from app.services.weather_service import WeatherResult
from app.services.soil_service import SoilResult
from app.services.satellite_service import SatelliteResult
import app.api.routes.recommend as recommend_route
from app.schemas.common import LocationRequest

FAKE_WEATHER = WeatherResult(rainfall_mm_last_30d=85.0, avg_temp_c=27.5, humidity_pct=60.0, solar_radiation_mj_m2=18.0, wind_speed_m_s=2.5, source="nasa-power")
FAKE_SOIL = SoilResult(ph=6.6, clay_pct=22.0, sand_pct=35.0, soil_moisture_pct=24.0, nitrogen_total_mg_kg=42.0, organic_carbon_g_kg=18.0, source="soilgrids")
FAKE_SATELLITE = SatelliteResult(ndvi=0.55, source="gee-sentinel2", scene_date="2026-07-15")


def _patch_all(monkeypatch):
    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: FAKE_WEATHER)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: FAKE_SOIL)
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: FAKE_SATELLITE)


def test_valid_decimal_coordinates(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.3926, "lon": 73.8706}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["location"]["lat"] == 18.3926
    assert body["location"]["lon"] == 73.8706


def test_negative_coordinates(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": -18.3926, "lon": -73.8706}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["location"]["lat"] == -18.3926
    assert body["location"]["lon"] == -73.8706


def test_boundary_latitude_90(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 90.0, "lon": 73.8706}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["location"]["lat"] == 90.0


def test_boundary_latitude_minus_90(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": -90.0, "lon": 73.8706}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["location"]["lat"] == -90.0


def test_boundary_longitude_180(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.3926, "lon": 180.0}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["location"]["lon"] == 180.0


def test_boundary_longitude_minus_180(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.3926, "lon": -180.0}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["location"]["lon"] == -180.0


def test_latitude_above_90_rejected(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 90.1, "lon": 73.8706}, headers=auth_headers)
    assert resp.status_code == 422


def test_latitude_below_minus_90_rejected(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": -90.1, "lon": 73.8706}, headers=auth_headers)
    assert resp.status_code == 422


def test_longitude_above_180_rejected(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.3926, "lon": 180.1}, headers=auth_headers)
    assert resp.status_code == 422


def test_longitude_below_minus_180_rejected(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": 18.3926, "lon": -180.1}, headers=auth_headers)
    assert resp.status_code == 422


def test_non_numeric_coordinates_rejected(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": "abc", "lon": "xyz"}, headers=auth_headers)
    assert resp.status_code == 422


def test_missing_coordinates_rejected(client, monkeypatch, auth_headers):
    _patch_all(monkeypatch)
    resp = client.post("/api/recommend", json={}, headers=auth_headers)
    assert resp.status_code == 422
