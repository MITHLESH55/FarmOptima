"""
Crop agronomic reference data.

These are approximate, commonly-cited agronomic parameter ranges used as the
CRITERIA basis for MCDM scoring. They are intentionally conservative,
literature-typical ranges (FAO / ICAR-style figures) meant as a reasonable
starting point for a final-year project — for a submission or publication,
cite your literature-survey sources against these figures and adjust to
match your target region's actual agro-climatic data.

Fields:
    water_need_mm_season   : total crop water requirement over a season (mm)
    ideal_ph_min/max        : optimal soil pH range (SoilGrids phh2o is pH*10)
    ideal_temp_min/max_c    : optimal mean growing temperature range (deg C)
    ideal_rainfall_min/max_mm_30d : reasonable recent-rainfall band that
                              indicates favorable current conditions
    base_market_value_index : relative index (1-10) used only when live
                              market price data is unavailable
"""

CROP_DATABASE = {
    "Wheat": {
        "water_need_mm_season": 450,
        "ideal_ph_min": 6.0, "ideal_ph_max": 7.5,
        "ideal_temp_min_c": 10, "ideal_temp_max_c": 25,
        "ideal_rainfall_min_mm_30d": 30, "ideal_rainfall_max_mm_30d": 100,
        "base_market_value_index": 6,
        "fertilizer_n_kg_per_acre": 48,
    },
    "Rice": {
        "water_need_mm_season": 1200,
        "ideal_ph_min": 5.5, "ideal_ph_max": 7.0,
        "ideal_temp_min_c": 20, "ideal_temp_max_c": 35,
        "ideal_rainfall_min_mm_30d": 150, "ideal_rainfall_max_mm_30d": 300,
        "base_market_value_index": 7,
        "fertilizer_n_kg_per_acre": 55,
    },
    "Maize": {
        "water_need_mm_season": 550,
        "ideal_ph_min": 5.8, "ideal_ph_max": 7.2,
        "ideal_temp_min_c": 18, "ideal_temp_max_c": 32,
        "ideal_rainfall_min_mm_30d": 60, "ideal_rainfall_max_mm_30d": 150,
        "base_market_value_index": 6,
        "fertilizer_n_kg_per_acre": 45,
    },
    "Groundnut": {
        "water_need_mm_season": 500,
        "ideal_ph_min": 6.0, "ideal_ph_max": 7.0,
        "ideal_temp_min_c": 22, "ideal_temp_max_c": 33,
        "ideal_rainfall_min_mm_30d": 50, "ideal_rainfall_max_mm_30d": 125,
        "base_market_value_index": 7,
        "fertilizer_n_kg_per_acre": 20,
    },
    "Cotton": {
        "water_need_mm_season": 700,
        "ideal_ph_min": 5.8, "ideal_ph_max": 8.0,
        "ideal_temp_min_c": 21, "ideal_temp_max_c": 35,
        "ideal_rainfall_min_mm_30d": 60, "ideal_rainfall_max_mm_30d": 110,
        "base_market_value_index": 8,
        "fertilizer_n_kg_per_acre": 60,
    },
    "Sugarcane": {
        "water_need_mm_season": 1800,
        "ideal_ph_min": 6.0, "ideal_ph_max": 7.5,
        "ideal_temp_min_c": 21, "ideal_temp_max_c": 35,
        "ideal_rainfall_min_mm_30d": 100, "ideal_rainfall_max_mm_30d": 250,
        "base_market_value_index": 6,
        "fertilizer_n_kg_per_acre": 100,
    },
    "Soybean": {
        "water_need_mm_season": 500,
        "ideal_ph_min": 6.0, "ideal_ph_max": 7.0,
        "ideal_temp_min_c": 20, "ideal_temp_max_c": 30,
        "ideal_rainfall_min_mm_30d": 60, "ideal_rainfall_max_mm_30d": 140,
        "base_market_value_index": 7,
        "fertilizer_n_kg_per_acre": 20,
    },
    "Chickpea": {
        "water_need_mm_season": 350,
        "ideal_ph_min": 6.0, "ideal_ph_max": 7.5,
        "ideal_temp_min_c": 10, "ideal_temp_max_c": 25,
        "ideal_rainfall_min_mm_30d": 20, "ideal_rainfall_max_mm_30d": 70,
        "base_market_value_index": 7,
        "fertilizer_n_kg_per_acre": 15,
    },
}
