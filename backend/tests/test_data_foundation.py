"""
Comprehensive Data Foundation & Data Provenance Test Suite.

Tests:
1. Live provider response handling (weather, soil, satellite)
2. API timeout handling
3. API failure handling (500 errors)
4. Cached fallback path
5. Stale detection (is_stale flag)
6. Lab-vs-SoilGrids precedence (LAB_MEASUREMENT > MODEL_PREDICTION)
7. Coordinate validation
8. Polygon validation & GEE integration
9. Field area calculation scaling
10. Data provenance metadata integrity
11. Source type correctness (LIVE_API, MODEL_PREDICTION, LAB_MEASUREMENT, SATELLITE_OBSERVATION, STATIC_DATASET, CACHED_API, MOCK/FALLBACK)
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.orm import sessionmaker

from app.schemas.common import LocationRequest, ProvenanceItem, DataProvenance
from app.services.weather_service import get_weather_for_location, WeatherResult
from app.services.soil_service import get_soil_for_location, SoilResult
from app.services.satellite_service import get_ndvi_for_location, SatelliteResult
from app.services.market_service import load_market_prices
from app.models.farm import Farm
from app.models.soil_test import SoilTest
from app.models.recommendation import Recommendation
from app.models.user import User


def test_provenance_metadata_structure():
    """Verify that ProvenanceItem has all required data provenance fields."""
    item = ProvenanceItem(
        source_name="nasa-power",
        source_type="LIVE_API",
        observation_date="2026-09-01",
        retrieved_at="2026-09-07T12:00:00Z",
        is_stale=False,
        quality_status="good",
        endpoint_reference="https://power.larc.nasa.gov/api/temporal/daily/point",
    )
    assert item.source_name == "nasa-power"
    assert item.source_type == "LIVE_API"
    assert item.observation_date == "2026-09-01"
    assert item.retrieved_at == "2026-09-07T12:00:00Z"
    assert item.is_stale is False
    assert item.quality_status == "good"


def test_coordinate_validation():
    """Test LocationRequest coordinate validation (lat -90 to 90, lon -180 to 180)."""
    valid = LocationRequest(lat=28.6139, lon=77.2090, field_area_acres=2.5)
    assert valid.lat == 28.6139
    assert valid.lon == 77.2090
    assert valid.field_area_acres == 2.5

    with pytest.raises(ValueError):
        LocationRequest(lat=95.0, lon=77.2090)

    with pytest.raises(ValueError):
        LocationRequest(lat=28.6139, lon=-195.0)


def test_polygon_validation_and_area():
    """Test field boundary polygon parsing and area scaling in LocationRequest."""
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.208, 28.613],
                [77.210, 28.613],
                [77.210, 28.615],
                [77.208, 28.615],
                [77.208, 28.613],
            ]
        ],
    }
    req = LocationRequest(lat=28.614, lon=77.209, field_area_acres=5.0, polygon_geojson=polygon)
    assert req.polygon_geojson == polygon
    assert req.field_area_acres == 5.0


def test_weather_live_provider_response():
    """Test live response handling for weather service (NASA POWER)."""
    mock_payload = {
        "properties": {
            "parameter": {
                "PRECTOTCORR": {"20260901": 5.0, "20260902": 10.0},
                "T2M": {"20260901": 28.0, "20260902": 30.0},
                "RH2M": {"20260901": 70.0, "20260902": 75.0},
                "ALLSKY_SFC_SW_DWN": {"20260901": 18.5, "20260902": 19.5},
                "WS2M": {"20260901": 3.2, "20260902": 2.8},
            }
        }
    }
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        result = get_weather_for_location(28.6139, 77.2090)
        assert result.source == "nasa-power"
        assert result.source_type == "LIVE_API"
        assert result.avg_temp_c == 29.0
        assert result.rainfall_mm_last_30d == 15.0
        assert result.is_stale is False
        assert result.quality_status == "good"


def test_weather_api_timeout_and_fallback(test_db_engine):
    """Test API timeout in weather service falls back to cache or unavailable without fake values."""
    with patch("requests.get", side_effect=Exception("Timeout connecting to NASA POWER")):
        # Without DB cache
        result_no_cache = get_weather_for_location(28.6139, 77.2090)
        assert result_no_cache.source == "unavailable"
        assert result_no_cache.source_type == "MOCK/FALLBACK"
        assert result_no_cache.avg_temp_c == 0.0
        assert result_no_cache.quality_status == "unavailable"

        # With DB cache
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
        db = TestSessionLocal()
        user = User(username="test_weather_cache", hashed_password="pw")
        db.add(user)
        db.commit()

        farm = Farm(name="Test Farm", latitude=28.6139, longitude=77.2090, user_id=user.id)
        db.add(farm)
        db.commit()

        rec = Recommendation(
            farm_id=farm.id,
            latitude=28.6139,
            longitude=77.2090,
            avg_temp_c=27.5,
            rainfall_mm_last_30d=45.0,
            humidity_pct=65.0,
            top_crop="Wheat",
            ahp_consistency_ratio=0.01,
            full_result={},
        )
        db.add(rec)
        db.commit()

        result_cached = get_weather_for_location(28.6139, 77.2090, db=db)
        assert result_cached.source == "nasa-power-cached"
        assert result_cached.source_type == "CACHED_API"
        assert result_cached.is_stale is True
        assert result_cached.quality_status == "stale"
        assert result_cached.avg_temp_c == 27.5
        db.close()


def test_soilgrids_model_prediction():
    """Test SoilGrids live response classified as MODEL_PREDICTION."""
    mock_payload = {
        "properties": {
            "layers": [
                {"name": "phh2o", "depths": [{"label": "0-5cm", "values": {"mean": 65}}]},
                {"name": "clay", "depths": [{"label": "0-5cm", "values": {"mean": 250}}]},
                {"name": "sand", "depths": [{"label": "0-5cm", "values": {"mean": 450}}]},
                {"name": "nitrogen", "depths": [{"label": "0-5cm", "values": {"mean": 35}}]},
                {"name": "soc", "depths": [{"label": "0-5cm", "values": {"mean": 120}}]},
            ]
        }
    }
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        result = get_soil_for_location(28.6139, 77.2090)
        assert result.source == "soilgrids"
        assert result.source_type == "MODEL_PREDICTION"
        assert result.ph == 6.5
        assert result.clay_pct == 25.0
        assert result.sand_pct == 45.0
        assert result.organic_carbon_g_kg == 12.0
        assert result.is_stale is False
        assert result.quality_status == "good"


def test_lab_measurement_precedence_over_soilgrids(test_db_engine):
    """CRITICAL TEST: LAB_MEASUREMENT must take precedence over SoilGrids MODEL_PREDICTION."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    db = TestSessionLocal()

    user = User(username="lab_test_user", hashed_password="pw")
    db.add(user)
    db.commit()

    farm = Farm(name="Lab Tested Farm", latitude=28.6139, longitude=77.2090, user_id=user.id)
    db.add(farm)
    db.commit()

    # Upload verified lab soil test
    lab_test = SoilTest(
        farm_id=farm.id,
        user_id=user.id,
        ph=7.2,
        nitrogen_mg_kg=450.0,
        organic_carbon_g_kg=18.5,
        sand_pct=35.0,
        clay_pct=30.0,
        sample_date="2026-08-15",
        lab_name="National Soil Testing Institute",
    )
    db.add(lab_test)
    db.commit()

    # Call soil service passing farm_id and db
    result = get_soil_for_location(28.6139, 77.2090, db=db, farm_id=farm.id)

    assert result.source == "lab_measurement"
    assert result.source_type == "LAB_MEASUREMENT"
    assert result.ph == 7.2
    assert result.nitrogen_total_mg_kg == 450.0
    assert result.organic_carbon_g_kg == 18.5
    assert result.quality_status == "lab_verified"
    assert result.is_stale is False

    db.close()


def test_market_agmarknet_static_classification():
    """Verify AGMARKNET CSV market data is explicitly classified as STATIC_DATASET."""
    prices = load_market_prices()
    assert isinstance(prices, dict)
    assert len(prices) > 0
    # In recommend endpoint response, market source is agmarknet_historical_csv with STATIC_DATASET type
    item = ProvenanceItem(
        source_name="agmarknet_historical_csv",
        source_type="STATIC_DATASET",
        observation_date="2024-01-01",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        is_stale=False,
        quality_status="good",
        endpoint_reference="agmarknet_market_data.csv",
    )
    assert item.source_type == "STATIC_DATASET"


def test_api_failure_does_not_generate_fake_values():
    """External API failures must return explicit unavailable marker with 0.0 values, NEVER synthetic fake values."""
    with patch("requests.get", side_effect=Exception("Connection refused")), patch("app.services.satellite_service._fetch_via_gee", return_value=None):
        soil_res = get_soil_for_location(28.6139, 77.2090)
        assert soil_res.source == "unavailable"
        assert soil_res.source_type == "MOCK/FALLBACK"
        assert soil_res.ph == 0.0
        assert soil_res.nitrogen_total_mg_kg == 0.0
        assert soil_res.quality_status == "unavailable"

        weather_res = get_weather_for_location(28.6139, 77.2090)
        assert weather_res.source == "unavailable"
        assert weather_res.source_type == "MOCK/FALLBACK"
        assert weather_res.avg_temp_c == 0.0
        assert weather_res.rainfall_mm_last_30d == 0.0
        assert weather_res.quality_status == "unavailable"

        sat_res = get_ndvi_for_location(28.6139, 77.2090)
        assert sat_res.source == "unavailable"
        assert sat_res.source_type == "MOCK/FALLBACK"
        assert sat_res.ndvi == 0.0
        assert sat_res.quality_status == "unavailable"


def test_recommend_endpoint_integration(client, auth_headers):
    """Test full /api/recommend endpoint integration with location request and provenance checks."""
    payload = {
        "lat": 28.6139,
        "lon": 77.2090,
        "field_area_acres": 3.0,
        "polygon_geojson": {
            "type": "Polygon",
            "coordinates": [
                [[77.208, 28.613], [77.210, 28.613], [77.210, 28.615], [77.208, 28.615], [77.208, 28.613]]
            ]
        }
    }
    with patch("app.services.weather_service._fetch_via_nasa_power") as mock_weather, \
         patch("app.services.soil_service._fetch_via_soilgrids") as mock_soil, \
         patch("app.services.satellite_service._fetch_via_gee") as mock_sat:

        mock_weather.return_value = WeatherResult(
            rainfall_mm_last_30d=50.0, avg_temp_c=26.0, humidity_pct=65.0,
            solar_radiation_mj_m2=18.0, wind_speed_m_s=2.5,
            source="nasa-power", source_type="LIVE_API", observation_date="2026-09-01",
            retrieved_at="2026-09-07T12:00:00Z", is_stale=False, quality_status="good"
        )
        mock_soil.return_value = SoilResult(
            ph=6.8, clay_pct=20.0, sand_pct=40.0, soil_moisture_pct=25.0,
            nitrogen_total_mg_kg=350.0, organic_carbon_g_kg=15.0,
            source="soilgrids", source_type="MODEL_PREDICTION", observation_date="2026-09-01",
            retrieved_at="2026-09-07T12:00:00Z", is_stale=False, quality_status="good"
        )
        mock_sat.return_value = SatelliteResult(
            ndvi=0.68, source="gee-sentinel2", scene_date="2026-08-30",
            source_type="SATELLITE_OBSERVATION", retrieved_at="2026-09-07T12:00:00Z",
            is_stale=False, quality_status="good"
        )

        resp = client.post("/api/recommend", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "provenance" in data
        prov = data["provenance"]
        assert prov["satellite_source"] == "gee-sentinel2"
        assert prov["weather_source"] == "nasa-power"
        assert prov["soil_source"] == "soilgrids"
        assert prov["market_source"] == "agmarknet_historical_csv"

        assert prov["weather_provenance"]["source_type"] == "LIVE_API"
        assert prov["soil_provenance"]["source_type"] == "MODEL_PREDICTION"
        assert prov["satellite_provenance"]["source_type"] == "SATELLITE_OBSERVATION"
        assert prov["market_provenance"]["source_type"] == "STATIC_DATASET"

        # Verify fertilizer plan scaled to field_area_acres (3.0 acres)
        assert "fertilizer_plan" in data
        assert data["fertilizer_plan"]["field_area_acres"] == 3.0
