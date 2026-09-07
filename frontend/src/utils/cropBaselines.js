/**
 * DOCUMENTED CROP BASELINE REFERENCE DATA
 *
 * Source: backend/app/crop_database.py and backend/app/core/suitability.py
 * 
 * This file documents all reference ranges used for interpreting live agricultural
 * data. Every comparison in FarmOptima must reference these baselines or explicitly
 * note that a comparison cannot be performed.
 *
 * CRITICAL RULE: Do NOT invent thresholds. Use only documented values from:
 * - CROP_DATABASE (crop-specific preferences)
 * - Suitability functions (normalization ranges)
 * - MCDM criteria (weighting and scoring logic)
 */

/**
 * COMPOSITE REFERENCE RANGES
 * (Used when crop-specific interpretation is not available)
 */
export const COMPOSITE_REFERENCES = {
  // Temperature: common overlap range across most crops
  // Source: CROP_DATABASE ranges vary (Wheat 10–25°C, Rice 20–35°C, etc.)
  // Composite conservative range: values within this band satisfy most crops
  TEMPERATURE: {
    min: 18,
    max: 30,
    unit: "°C",
    source: "CROP_DATABASE composite (Wheat, Rice, Maize, Groundnut, Cotton, Sugarcane, Soybean, Chickpea)",
    explanation: "Temperatures within this range support most crops; narrower ranges apply to specific crops."
  },

  // Rainfall: "favorable" recent precipitation band
  // Source: CROP_DATABASE ideal_rainfall_min/max_mm_30d ranges (Wheat 30–100, Rice 150–300, etc.)
  // Composite range: typical "good" condition for general farming
  RAINFALL: {
    min: 50,
    max: 200,
    unit: "mm/30d",
    source: "CROP_DATABASE composite (approximate favorable band)",
    explanation: "Recent 30-day rainfall in this range indicates favorable conditions for most crops."
  },

  // Humidity: physiological range based on disease and transpiration
  // Source: suitability.py humidity_suitability default (35–80%)
  HUMIDITY: {
    min: 35,
    max: 80,
    unit: "%",
    source: "suitability.py humidity_suitability()",
    explanation: "Humidity in this range balances disease risk and evaporative stress."
  },

  // Soil pH: common preference across most crops
  // Source: CROP_DATABASE ideal_ph ranges (typically 5.5–8.0, most 6.0–7.5)
  SOIL_PH: {
    min: 6.0,
    max: 7.5,
    unit: "pH",
    source: "CROP_DATABASE composite (Wheat 6.0–7.5, Rice 5.5–7.0, etc.)",
    explanation: "pH in this range is favorable for most crops; specific crops may have narrower preferences."
  },

  // Nitrogen: target-based adequacy score
  // Source: suitability.py nitrogen_suitability(target=40, tolerance=25)
  // Optimal range [15, 65] mg/kg
  NITROGEN: {
    min: 15,
    max: 65,
    unit: "mg/kg",
    target: 40,
    tolerance: 25,
    source: "suitability.py nitrogen_suitability()",
    explanation: "Nitrogen within this range is adequate for most crops; score peaks at 40 mg/kg."
  },

  // Organic Carbon: target-based soil health indicator
  // Source: suitability.py organic_carbon_suitability(target=18, tolerance=12)
  // Optimal range [6, 30] g/kg
  ORGANIC_CARBON: {
    min: 6,
    max: 30,
    unit: "g/kg",
    target: 18,
    tolerance: 12,
    source: "suitability.py organic_carbon_suitability()",
    explanation: "Organic carbon in this range indicates good soil health; score peaks at 18 g/kg."
  },

  // Soil Moisture: available water capacity
  // Source: suitability.py soil_moisture_suitability(opt_min=20, opt_max=50)
  SOIL_MOISTURE: {
    min: 20,
    max: 50,
    unit: "%",
    source: "suitability.py soil_moisture_suitability()",
    explanation: "Soil moisture in this range provides good available water capacity for most crops."
  },

  // NDVI: Normalized Difference Vegetation Index
  // Source: suitability.py vegetation_suitability(opt_min=0.45, opt_max=0.75)
  NDVI: {
    min: 0.45,
    max: 0.75,
    unit: "",
    source: "suitability.py vegetation_suitability()",
    explanation: "NDVI in this range indicates good vegetation density/health; valid NDVI range is -1.0 to +1.0."
  },
};

/**
 * CROP-SPECIFIC PREFERENCES
 * Source: CROP_DATABASE
 *
 * Use these when interpreting data for a SPECIFIC recommended crop.
 */
export const CROP_PREFERENCES = {
  Wheat: {
    temp_min: 10,
    temp_max: 25,
    ph_min: 6.0,
    ph_max: 7.5,
    rainfall_min: 30,
    rainfall_max: 100,
    water_need_mm_season: 450,
    fertilizer_n_kg_acre: 48,
  },
  Rice: {
    temp_min: 20,
    temp_max: 35,
    ph_min: 5.5,
    ph_max: 7.0,
    rainfall_min: 150,
    rainfall_max: 300,
    water_need_mm_season: 1200,
    fertilizer_n_kg_acre: 55,
  },
  Maize: {
    temp_min: 18,
    temp_max: 32,
    ph_min: 5.8,
    ph_max: 7.2,
    rainfall_min: 60,
    rainfall_max: 150,
    water_need_mm_season: 550,
    fertilizer_n_kg_acre: 45,
  },
  Groundnut: {
    temp_min: 22,
    temp_max: 33,
    ph_min: 6.0,
    ph_max: 7.0,
    rainfall_min: 50,
    rainfall_max: 125,
    water_need_mm_season: 500,
    fertilizer_n_kg_acre: 20,
  },
  Cotton: {
    temp_min: 21,
    temp_max: 35,
    ph_min: 5.8,
    ph_max: 8.0,
    rainfall_min: 60,
    rainfall_max: 110,
    water_need_mm_season: 700,
    fertilizer_n_kg_acre: 60,
  },
  Sugarcane: {
    temp_min: 21,
    temp_max: 35,
    ph_min: 6.0,
    ph_max: 7.5,
    rainfall_min: 100,
    rainfall_max: 250,
    water_need_mm_season: 1800,
    fertilizer_n_kg_acre: 100,
  },
  Soybean: {
    temp_min: 20,
    temp_max: 30,
    ph_min: 6.0,
    ph_max: 7.0,
    rainfall_min: 60,
    rainfall_max: 140,
    water_need_mm_season: 500,
    fertilizer_n_kg_acre: 20,
  },
  Chickpea: {
    temp_min: 10,
    temp_max: 25,
    ph_min: 6.0,
    ph_max: 7.5,
    rainfall_min: 20,
    rainfall_max: 70,
    water_need_mm_season: 350,
    fertilizer_n_kg_acre: 15,
  },
};

/**
 * AHP CRITERIA WEIGHTS INTERPRETATION
 *
 * Source: backend/app/core/criteria.py DEFAULT_AHP_PAIRWISE_MATRIX
 *
 * The AHP weights represent IMPORTANCE, NOT QUALITY.
 * Example: "climate_suitability: 84.5%" means climate is 84.5% of the
 * recommendation's decision-making weight, NOT that climate quality is 84.5%.
 *
 * Interpretation guide:
 * - Weight > 50%: "X is the dominant factor"
 * - Weight 30–50%: "X is an important factor"
 * - Weight 10–30%: "X is a contributing factor"
 * - Weight < 10%: "X has minimal influence"
 */
export const AHP_INTERPRETATION = {
  climate_suitability: {
    name: "Climate Suitability",
    includes: ["Temperature", "Rainfall", "Humidity"],
    description: "How well current weather matches the crop's needs."
  },
  soil_suitability: {
    name: "Soil Suitability",
    includes: ["Soil pH", "Nitrogen", "Organic Carbon"],
    description: "How well current soil conditions match the crop's needs."
  },
  water_efficiency: {
    name: "Water Efficiency",
    includes: ["Rainfall relative to crop demand", "Vegetation status"],
    description: "How well current water availability matches irrigation needs."
  },
  market_value: {
    name: "Market Value",
    includes: ["Crop price index"],
    description: "Relative market demand and crop price."
  }
};

/**
 * TOPSIS INTERPRETATION
 *
 * Source: backend/app/core/mcdm.py
 *
 * TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)
 * ranks crops by their "closeness to the ideal solution" under the current
 * environmental and market conditions.
 *
 * IMPORTANT:
 * - TOPSIS scores are RELATIVE, not absolute.
 * - A crop with TOPSIS = 0.82 is NOT "82% good"; it means this crop is
 *   closer to the ideal than other crops in THIS recommendation run.
 * - TOPSIS scores only make sense when comparing crops within the SAME
 *   recommendation (same location, date, conditions).
 * - Scores near 0.5 suggest a crop is neither strongly ideal nor strongly
 *   poor.
 * - Scores near 0.0 or 1.0 are rare and indicate an extreme match or mismatch.
 */
export const TOPSIS_INTERPRETATION = {
  explanation:
    "TOPSIS score represents relative closeness to the ideal solution. Higher scores mean better match to current conditions under the AHP-weighted criteria.",
  scale: "Relative ranking (not an absolute percentage)",
  example:
    "Wheat (0.82) > Rice (0.71) > Maize (0.54) means Wheat is closest to ideal, followed by Rice, then Maize, under current conditions.",
};

/**
 * ELECTRE INTERPRETATION
 *
 * Source: backend/app/core/mcdm.py
 *
 * ELECTRE (Elimination And Choice Expressing Reality) measures outranking:
 * how many other crops a candidate crop "outranks" (is superior to) under
 * the current ELECTRE criteria.
 *
 * IMPORTANT:
 * - ELECTRE score represents COUNT of crops outranked, not a percentage.
 * - Wheat +5 means Wheat outranks 5 other crops (and is outranked by some).
 * - Wheat -3 means Wheat is outranked by 3 others (and outranks some).
 * - ELECTRE and TOPSIS may rank crops differently—both provide value as
 *   a cross-check.
 */
export const ELECTRE_INTERPRETATION = {
  explanation:
    "ELECTRE score shows how many crops are outranked (positive) or outrank (negative) this crop.",
  scale: "Count of outranking relationships, not a percentage",
  example:
    "Wheat +5 means Wheat outranks 5 other crops in terms of pairwise criteria comparisons.",
};

/**
 * GPO (Genetic Program Optimization) INTERPRETATION
 *
 * Source: backend/app/core/nsga2.py
 *
 * GPO optimizes water and fertilizer to meet crop needs while minimizing
 * resource gaps. The returned solution is one point on the Pareto front.
 *
 * IMPORTANT:
 * - Water and Fertilizer values are RECOMMENDATIONS, not prescriptions.
 * - Fitness value (e.g., 0.0591) represents the optimization error (lower is better).
 * - Fitness is NOT a crop quality score; it's a technical metric.
 * - Generations show convergence: more generations = better (unless early termination).
 */
export const GPO_INTERPRETATION = {
  water: "Recommended weekly irrigation volume to balance available rainfall and crop demand",
  fertilizer: "Recommended nitrogen fertilizer application rate",
  fitness: "Optimization error (gap between current and ideal conditions); lower is better",
  generations: "Number of NSGA-II evolution rounds; higher may mean better convergence",
  pareto_front: "Alternative resource plans that balance water and fertilizer differently",
};

/**
 * DATA SOURCE LABELS
 *
 * Every live value in FarmOptima should be tagged with its source.
 */
export const DATA_SOURCES = {
  "nasa-power": "🌦️ NASA POWER (Global weather)",
  "soilgrids": "🌱 SoilGrids (ISRIC soil database)",
  "gee-sentinel2": "🛰️ Google Earth Engine / Sentinel-2 (Satellite NDVI)",
  "unavailable": "⚠️ Service unavailable",
  "mock": "🟠 Mock data (for development)",
  "csv": "📊 Local market prices (CSV)",
};
