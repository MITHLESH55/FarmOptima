#!/usr/bin/env python
"""
Test script to verify that live data sources (NASA POWER, SoilGrids, GEE)
are actually being called and returning real data, not mock/unavailable values.

Run this from the backend directory:
  python ../scripts/test_live_data.py

Tests multiple locations across India to verify:
1. Weather data changes by location
2. Soil data changes by location
3. NDVI data is live or explicitly unavailable (not mock)
4. Crop recommendations change based on actual conditions
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "farmoptima_v5" / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.weather_service import get_weather_for_location
from app.services.soil_service import get_soil_for_location
from app.services.satellite_service import get_ndvi_for_location
from app.services.market_service import load_market_prices

# Test locations (lat, lon, name)
TEST_LOCATIONS = [
    (18.5204, 73.8567, "Pune"),
    (17.3850, 78.4867, "Hyderabad"),
    (26.9124, 75.7873, "Jaipur"),
    (12.9716, 77.5946, "Bengaluru"),
    (25.5941, 85.1376, "Patna"),
]

def test_live_data():
    """Test that live APIs are being called and returning varied data."""
    print("\n" + "="*80)
    print("TESTING LIVE DATA SOURCES FOR MULTIPLE LOCATIONS")
    print("="*80)
    
    results_by_location = {}
    
    for lat, lon, name in TEST_LOCATIONS:
        print(f"\n{'─'*80}")
        print(f"Location: {name} ({lat}, {lon})")
        print(f"{'─'*80}")
        
        # Get live data
        weather = get_weather_for_location(lat, lon)
        soil = get_soil_for_location(lat, lon)
        satellite = get_ndvi_for_location(lat, lon)
        
        # Store results
        results_by_location[name] = {
            "weather": weather,
            "soil": soil,
            "satellite": satellite,
        }
        
        # Display results
        print(f"\nWEATHER (Source: {weather.source})")
        print(f"  Temperature:      {weather.avg_temp_c}°C")
        print(f"  Rainfall (30d):   {weather.rainfall_mm_last_30d} mm")
        print(f"  Humidity:         {weather.humidity_pct}%")
        print(f"  Solar Radiation:  {weather.solar_radiation_mj_m2} MJ/m²")
        print(f"  Wind Speed:       {weather.wind_speed_m_s} m/s")
        
        print(f"\nSOIL (Source: {soil.source})")
        print(f"  pH:               {soil.ph}")
        print(f"  Clay:             {soil.clay_pct}%")
        print(f"  Sand:             {soil.sand_pct}%")
        print(f"  Soil Moisture:    {soil.soil_moisture_pct}%")
        print(f"  Nitrogen:         {soil.nitrogen_total_mg_kg} mg/kg")
        print(f"  Organic Carbon:   {soil.organic_carbon_g_kg} g/kg")
        
        print(f"\nSATELLITE (Source: {satellite.source})")
        print(f"  NDVI:             {satellite.ndvi}")
        print(f"  Scene Date:       {satellite.scene_date}")
    
    # Verify data varies by location
    print(f"\n{'='*80}")
    print("DATA VARIATION ANALYSIS")
    print(f"{'='*80}")
    
    temps = [results_by_location[name]["weather"].avg_temp_c for name, _, _ in TEST_LOCATIONS[1:]]
    rainfall_vals = [results_by_location[name]["weather"].rainfall_mm_last_30d for name, _, _ in TEST_LOCATIONS[1:]]
    soil_phs = [results_by_location[name]["soil"].ph for name, _, _ in TEST_LOCATIONS[1:]]
    ndvi_vals = [results_by_location[name]["satellite"].ndvi for name, _, _ in TEST_LOCATIONS[1:]]
    
    print(f"\nTemperature variation: {min(temps):.1f}°C - {max(temps):.1f}°C")
    print(f"  → Expected: Different values per location")
    print(f"  → Result: {'✓ PASS' if len(set(temps)) > 1 else '✗ FAIL - All temperatures are identical'}")
    
    print(f"\nRainfall variation: {min(rainfall_vals):.1f}mm - {max(rainfall_vals):.1f}mm")
    print(f"  → Expected: Different values per location")
    print(f"  → Result: {'✓ PASS' if len(set(rainfall_vals)) > 1 else '✗ FAIL - All rainfall values are identical'}")
    
    print(f"\nSoil pH variation: {min(soil_phs):.2f} - {max(soil_phs):.2f}")
    print(f"  → Expected: Different values per location")
    print(f"  → Result: {'✓ PASS' if len(set(soil_phs)) > 1 else '✗ FAIL - All pH values are identical'}")
    
    print(f"\nNDVI variation: {min(ndvi_vals):.3f} - {max(ndvi_vals):.3f}")
    print(f"  → Expected: Different values per location or explicit unavailable")
    print(f"  → Result: {'✓ PASS' if len(set(ndvi_vals)) > 1 else '✗ FAIL - All NDVI values are identical'}")
    
    # Check sources
    print(f"\n{'─'*80}")
    print("DATA SOURCE VERIFICATION")
    print(f"{'─'*80}")
    
    for name in [n for _, _, n in TEST_LOCATIONS]:
        weather_source = results_by_location[name]["weather"].source
        soil_source = results_by_location[name]["soil"].source
        satellite_source = results_by_location[name]["satellite"].source
        
        print(f"\n{name}:")
        print(f"  Weather:   {weather_source:20} {'✓' if weather_source == 'nasa-power' else '✗ Expected: nasa-power'}")
        print(f"  Soil:      {soil_source:20} {'✓' if soil_source == 'soilgrids' else '✗ Expected: soilgrids'}")
        print(f"  Satellite: {satellite_source:20} {'✓' if satellite_source in ('gee-sentinel2', 'unavailable') else '✗ Expected: gee-sentinel2 or unavailable'}")
    
    # Verify NO MOCK values
    print(f"\n{'─'*80}")
    print("MOCK DATA CHECK (Should be EMPTY)")
    print(f"{'─'*80}")
    
    mock_found = []
    for name in [n for _, _, n in TEST_LOCATIONS]:
        sources = [
            results_by_location[name]["weather"].source,
            results_by_location[name]["soil"].source,
            results_by_location[name]["satellite"].source,
        ]
        for source in sources:
            if source == "mock":
                mock_found.append(f"{name}: {source}")
    
    if mock_found:
        print("✗ FAIL - Mock data found (should all be live or unavailable):")
        for item in mock_found:
            print(f"  - {item}")
    else:
        print("✓ PASS - No mock data detected")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    test_live_data()
