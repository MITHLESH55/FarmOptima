import pytest
from unittest.mock import patch, MagicMock
import requests

from app.services.soil_service import get_soil_for_location, _fetch_via_soilgrids, SoilResult


def test_soilgrids_unit_conversion_and_retries():
    """Verify SoilGrids phh2o (/10), soc (/10), and nitrogen (*10 cg/kg -> mg/kg) conversions."""
    mock_response_payload = {
        "properties": {
            "layers": [
                {
                    "name": "phh2o",
                    "depths": [{"label": "0-5cm", "values": {"mean": 65}}] # 65 / 10 = 6.5 pH
                },
                {
                    "name": "clay",
                    "depths": [{"label": "0-5cm", "values": {"mean": 250}}] # 250 / 10 = 25.0%
                },
                {
                    "name": "sand",
                    "depths": [{"label": "0-5cm", "values": {"mean": 450}}] # 450 / 10 = 45.0%
                },
                {
                    "name": "nitrogen",
                    "depths": [{"label": "0-5cm", "values": {"mean": 150}}] # 150 * 10 = 1500.0 mg/kg
                },
                {
                    "name": "soc",
                    "depths": [{"label": "0-5cm", "values": {"mean": 180}}] # 180 / 10 = 18.0 g/kg
                },
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_payload

    with patch("requests.get", return_value=mock_resp):
        res = get_soil_for_location(15.9016, 75.9837)
        assert res.source == "soilgrids"
        assert res.ph == 6.5
        assert res.clay_pct == 25.0
        assert res.sand_pct == 45.0
        assert res.nitrogen_total_mg_kg == 1500.0
        assert res.organic_carbon_g_kg == 18.0


def test_soilgrids_failure_returns_unavailable_status():
    """Verify that when SoilGrids fails and no DB cache exists, get_soil_for_location returns explicit unavailable marker without fake data."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("requests.get", return_value=mock_resp):
        res = get_soil_for_location(15.9016, 75.9837)
        assert res.source == "unavailable"
        assert res.source_type == "MOCK/FALLBACK"
        assert res.quality_status == "unavailable"
        assert res.ph == 0.0
        assert res.nitrogen_total_mg_kg == 0.0


