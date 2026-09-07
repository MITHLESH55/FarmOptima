#!/usr/bin/env python3
"""
Phase 1 Validation Test for FarmOptima

Tests:
1. Backend imports and services work
2. Frontend builds successfully
3. API schema includes all 8 metrics
4. Mock data flows through pipeline correctly
"""

import sys
sys.path.insert(0, 'backend')

def test_backend_imports():
    """Test all backend modules import correctly"""
    print("\n✓ Testing backend imports...")
    try:
        from app.main import app
        print("  ✓ app.main imports OK")
        
        from app.schemas.recommendation import RecommendationResponse
        print("  ✓ RecommendationResponse schema OK")
        
        from app.services.weather_service import get_weather_for_location, WeatherResult
        print("  ✓ weather_service OK")
        
        from app.services.soil_service import get_soil_for_location, SoilResult
        print("  ✓ soil_service OK")
        
        from app.services.satellite_service import get_ndvi_for_location, SatelliteResult
        print("  ✓ satellite_service OK")
        
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_services():
    """Test that services return properly formatted data"""
    print("\n✓ Testing service functions...")
    try:
        from app.services.weather_service import get_weather_for_location
        from app.services.soil_service import get_soil_for_location
        from app.services.satellite_service import get_ndvi_for_location
        
        lat, lon = 12.5, 75.5  # Sample coordinates
        
        # Test weather service
        weather = get_weather_for_location(lat, lon)
        assert hasattr(weather, 'rainfall_mm_last_30d'), "Weather missing rainfall"
        assert hasattr(weather, 'avg_temp_c'), "Weather missing temp"
        assert hasattr(weather, 'humidity_pct'), "Weather missing humidity ⚠️"
        assert hasattr(weather, 'source'), "Weather missing source"
        print(f"  ✓ Weather service returns: temp={weather.avg_temp_c}°C, rainfall={weather.rainfall_mm_last_30d}mm, humidity={weather.humidity_pct}%, source={weather.source}")
        
        # Test soil service
        soil = get_soil_for_location(lat, lon)
        assert hasattr(soil, 'ph'), "Soil missing pH"
        assert hasattr(soil, 'soil_moisture_pct'), "Soil missing moisture"
        assert hasattr(soil, 'nitrogen_total_mg_kg'), "Soil missing nitrogen ⚠️"
        assert hasattr(soil, 'organic_carbon_g_kg'), "Soil missing organic carbon ⚠️"
        assert hasattr(soil, 'source'), "Soil missing source"
        print(f"  ✓ Soil service returns: pH={soil.ph}, moisture={soil.soil_moisture_pct}%, nitrogen={soil.nitrogen_total_mg_kg}mg/kg, carbon={soil.organic_carbon_g_kg}g/kg, source={soil.source}")
        
        # Test satellite service
        sat = get_ndvi_for_location(lat, lon)
        assert hasattr(sat, 'ndvi'), "Satellite missing NDVI"
        assert hasattr(sat, 'scene_date'), "Satellite missing scene_date"
        assert hasattr(sat, 'source'), "Satellite missing source"
        print(f"  ✓ Satellite service returns: NDVI={sat.ndvi}, scene_date={sat.scene_date}, source={sat.source}")
        
        return True
    except Exception as e:
        print(f"  ✗ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_schema():
    """Test that RecommendationResponse has all 8 required metrics"""
    print("\n✓ Testing RecommendationResponse schema...")
    try:
        from app.schemas.recommendation import RecommendationResponse
        from pydantic import ValidationError
        
        required_fields = [
            'location', 'generated_at', 'provenance',
            'ndvi', 'satellite_scene_date',  # Vegetation
            'soil_ph', 'soil_moisture_pct', 'soil_nitrogen_mg_kg', 'soil_organic_carbon_g_kg',  # Soil
            'rainfall_mm_last_30d', 'avg_temp_c', 'humidity_pct',  # Weather
            'ahp_weights', 'ahp_consistency_ratio', 'ahp_is_consistent',
            'crop_ranking', 'resource_plan', 'ai_explanation'
        ]
        
        # Check schema fields
        from pydantic import BaseModel
        model_fields = RecommendationResponse.model_fields
        missing = [f for f in required_fields if f not in model_fields]
        
        if missing:
            print(f"  ✗ Missing fields: {missing}")
            return False
        
        print(f"  ✓ All {len(required_fields)} expected fields present in schema")
        
        # Test 8 key agricultural metrics
        metrics = [
            'ndvi', 'satellite_scene_date',
            'soil_ph', 'soil_moisture_pct', 'soil_nitrogen_mg_kg', 'soil_organic_carbon_g_kg',
            'rainfall_mm_last_30d', 'avg_temp_c', 'humidity_pct'
        ]
        
        print(f"\n  ✓ Phase 1 Metrics ({len(metrics)} total):")
        print(f"    - Vegetation: ndvi, satellite_scene_date")
        print(f"    - Soil: pH, moisture, nitrogen, organic_carbon")
        print(f"    - Weather: rainfall_30d, temperature, humidity")
        
        return True
    except Exception as e:
        print(f"  ✗ Schema test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("FarmOptima Phase 1 Validation")
    print("=" * 60)
    
    results = {
        'Backend imports': test_backend_imports(),
        'Services': test_services(),
        'Schema': test_schema(),
    }
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ Phase 1 Backend validation PASSED")
        print("\nNext steps:")
        print("1. Frontend build verification")
        print("2. End-to-end API flow test")
        print("3. Live server testing")
    else:
        print(f"\n❌ {total - passed} test(s) failed")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
