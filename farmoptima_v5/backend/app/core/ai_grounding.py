"""
AI-specific grounding logic and deterministic verification.

This module is pure Python: no I/O, no database, no network — making it
fully unit-testable without any external dependencies.

Core capabilities:
  1. build_grounding_prompt(context, question, language):
     Builds a comprehensive system prompt embedding all verified data,
     agronomic reference parameters for the recommended crop and all ranked crops,
     and task-specific grounding rules.

  2. validate_answer_is_grounded(answer, context) -> GroundingCheckResult:
     Deterministic, semantic claim-level safety verification:
     - Numerical verification (accounting for units, percentages, daily water,
       rounding tolerances, Devanagari numerals, Unicode separators).
     - Categorical entity verification (crops, NDVI status, criteria names).
     - Tie-break claim verification (enforced only when comparing genuinely tied crops).
"""

from __future__ import annotations

import re
import math
from app.crop_database import CROP_DATABASE
from app.schemas.ai import FarmContext, GroundingCheckResult


# ---------------------------------------------------------------------------
# Multilingual Crop & Agronomic Vocabulary
# ---------------------------------------------------------------------------

CROP_ALIASES: dict[str, str] = {
    # Wheat
    "wheat": "Wheat", "gehun": "Wheat", "gehu": "Wheat", "गेहूं": "Wheat", "गेहू": "Wheat", "गहू": "Wheat",
    # Rice
    "rice": "Rice", "paddy": "Rice", "chawal": "Rice", "dhan": "Rice", "चावल": "Rice", "धान": "Rice", "तांदूळ": "Rice", "भात": "Rice", "तांदळाचा": "Rice", "तांदळाला": "Rice",
    # Maize
    "maize": "Maize", "corn": "Maize", "makka": "Maize", "maka": "Maize", "मक्का": "Maize", "मका": "Maize",
    # Groundnut
    "groundnut": "Groundnut", "peanut": "Groundnut", "mungfali": "Groundnut", "bhuimug": "Groundnut",
    "मूंगफली": "Groundnut", "मूँगाफली": "Groundnut", "भुईमूग": "Groundnut", "भुईमुग": "Groundnut", "भुईमूगाची": "Groundnut", "भुईमूगाचा": "Groundnut",
    # Cotton
    "cotton": "Cotton", "kapas": "Cotton", "kapus": "Cotton", "कपास": "Cotton", "कापूस": "Cotton", "कापसाचे": "Cotton",
    # Sugarcane
    "sugarcane": "Sugarcane", "ganna": "Sugarcane", "us": "Sugarcane", "गन्ना": "Sugarcane", "ऊस": "Sugarcane", "उसाचे": "Sugarcane",
    # Soybean
    "soybean": "Soybean", "soya": "Soybean", "सोयाबीन": "Soybean",
    # Chickpea
    "chickpea": "Chickpea", "gram": "Chickpea", "chana": "Chickpea", "harbhara": "Chickpea",
    "चना": "Chickpea", "छोला": "Chickpea", "हरभरा": "Chickpea", "हरभऱ्याची": "Chickpea",
}

_ALL_KNOWN_CROP_WORDS: list[str] = [
    "wheat", "rice", "maize", "corn", "sorghum", "millet", "barley", "oats",
    "rye", "triticale", "chickpea", "lentil", "pigeon pea", "pigeonpea",
    "mung bean", "mungbean", "black gram", "soybean", "groundnut", "peanut",
    "sunflower", "mustard", "rapeseed", "canola", "sesame", "linseed",
    "sugarcane", "cotton", "jute", "tobacco", "potato", "tomato", "onion",
    "garlic", "ginger", "turmeric", "chilli", "pepper", "brinjal",
    "eggplant", "okra", "cauliflower", "cabbage", "pea", "cowpea",
    "banana", "mango", "papaya", "guava", "pomegranate", "grapes",
    "watermelon", "cucumber", "pumpkin", "bottle gourd", "bitter gourd",
    "ridge gourd", "sponge gourd", "durian", "apple", "orange", "coffee",
    "tea", "rubber", "coconut", "arecanut", "cardamom", "clove", "nutmeg",
    "cinnamon", "vanilla", "cocoa", "almond", "walnut", "cashew", "pistachio",
]

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?%?\b")


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_grounding_prompt(context: FarmContext, question: str, language: str = "en") -> str:  # noqa: ARG001
    """
    Construct the system prompt that will be sent to the LLM alongside the
    farmer's question. Dynamically injects the current recommended crop,
    crop rankings, and complete agronomic context.
    """
    supported_lang = language if language in {"en", "hi", "mr"} else "en"
    if supported_lang == "en":
        response_language = "English"
    elif supported_lang == "hi":
        response_language = "Hindi"
    else:
        response_language = "Marathi"

    top_crop_name = context.crop_ranking[0].crop if context.crop_ranking else "None"
    top_crop_params = CROP_DATABASE.get(top_crop_name, {})

    if context.ndvi is not None:
        ndvi_status = context.ndvi.status
        if context.ndvi.is_live:
            source_suffix = f"source: {context.ndvi.source}"
        else:
            source_suffix = "source: MOCK/UNVERIFIED — Earth Engine not configured, treat as illustrative only"
        ndvi_line = (
            f"NDVI: {context.ndvi.value:.4f} "
            f"(status: {ndvi_status}; {source_suffix}; scene date: {context.ndvi.scene_date or 'not recorded'})"
        )
    else:
        ndvi_line = "NDVI: NOT AVAILABLE (no underlying NDVI value in recommendation data)"

    crop_ranking_lines = "\n".join(
        f"  {entry.rank}. {entry.crop} "
        f"(TOPSIS closeness: {entry.topsis_closeness:.4f}, "
        f"ELECTRE net outranking: {entry.electre_net_outranking}, "
        f"tie_break_applied={str(entry.tie_break_applied).lower()}, "
        f"tie_break_reason={entry.tie_break_reason or 'none'})"
        for entry in context.crop_ranking
    )
    if not crop_ranking_lines:
        crop_ranking_lines = "  No crops ranked (all data sources unavailable)."

    ahp_weights_lines = "\n".join(
        f"  {criterion}: {weight:.4f}"
        for criterion, weight in context.ahp_weights.items()
    )

    pareto_lines = "\n".join(
        f"  Option {i + 1}: {p.water_liters_per_week:.1f} L/week water, "
        f"{p.fertilizer_kg_per_acre:.2f} kg/acre fertilizer, "
        f"resource cost {p.resource_cost:.4f}"
        for i, p in enumerate(context.resource_plan.pareto_front[:5])
    )
    if not pareto_lines:
        pareto_lines = "  (no pareto front data available)"

    daily_water = round(context.resource_plan.water_liters_per_week / 7.0, 1)

    agronomic_reference_lines = ""
    if top_crop_params:
        agronomic_reference_lines = (
            f"--- Top Crop Agronomic Profile ({top_crop_name}) ---\n"
            f"Optimal Temperature: {top_crop_params.get('ideal_temp_min_c')}-{top_crop_params.get('ideal_temp_max_c')} °C\n"
            f"Optimal Rainfall: {top_crop_params.get('ideal_rainfall_min_mm_30d')}-{top_crop_params.get('ideal_rainfall_max_mm_30d')} mm/month\n"
            f"Optimal Soil pH: {top_crop_params.get('ideal_ph_min')}-{top_crop_params.get('ideal_ph_max')}\n"
            f"Seasonal Water Need: ~{top_crop_params.get('water_need_mm_season')} mm\n"
            f"Nitrogen Fertilizer Need: ~{top_crop_params.get('fertilizer_n_kg_per_acre')} kg/acre\n"
        )

    prompt = f"""You are FarmOptima's agricultural AI assistant. Your ONLY job is to answer
the farmer's question using the verified recommendation data provided below.

=== HARD GROUNDING RULES (MUST follow without exception) ===
1. You MUST answer using ONLY the values listed in the DATA CONTEXT section.
2. You MUST NOT state any crop name that does not appear in the CROP RANKING.
3. You MUST NOT state any numeric value (yield, water, fertilizer, score, etc.)
   that does not appear verbatim (or within normal rounding/percentages/daily scaling) in the DATA CONTEXT.
4. You MUST NOT re-rank, override, or contradict the CROP RANKING produced by
   FarmOptima's AHP-TOPSIS-ELECTRE algorithm. The current #1 recommended crop is {top_crop_name}.
5. If the farmer asks about information that is NOT present in the DATA CONTEXT (such as exact yield in tonnes or future crop prices next year),
   respond with an explicit statement such as: "That information is not available in the current recommendation context."
6. For reasoning questions ("Why was {top_crop_name} recommended?", "Explain complete reasoning"): explain how climate, soil, water efficiency, and market scores contributed to the TOPSIS closeness and ranking for {top_crop_name}.
7. For resource questions ("How much water and fertilizer are needed?"): state the exact requirements for {top_crop_name} from the Recommended Resource Plan ({context.resource_plan.water_liters_per_week:.1f} L/week or approx {daily_water} L/day water, and {context.resource_plan.fertilizer_kg_per_acre:.2f} kg/acre fertilizer).
8. For what-if questions (e.g. "What if water availability decreases?"): explain the implications based on the crops' water needs, noting that an exact recalculation requires running the recommendation engine again.
9. Respond in {response_language}. Use the same evidence and ranking as the structured data, but express the answer in {response_language}.
10. Be concise, respectful, and helpful to a farmer who may not know technical terms.

=== DATA CONTEXT ===

TOP RECOMMENDED CROP: {top_crop_name} (Rank 1)
Location: lat={context.latitude}, lon={context.longitude}
Recommendation generated at: {context.generated_at}
Recommendation status: {context.recommendation_status}
Data completeness — weather: {context.data_completeness_weather}, soil: {context.data_completeness_soil}, satellite: {context.data_completeness_satellite}, market: {context.data_completeness_market}

{agronomic_reference_lines}
--- Satellite / NDVI ---
{ndvi_line}

--- Weather (last 30 days) ---
Rainfall: {context.rainfall_mm_last_30d:.2f} mm
Average temperature: {context.avg_temp_c:.2f} °C
Humidity: {context.humidity_pct:.2f} %
Solar radiation: {context.solar_radiation_mj_m2:.2f} MJ/m²
Wind speed: {context.wind_speed_m_s:.2f} m/s

--- Soil ---
pH: {context.soil_ph:.2f}
Moisture: {context.soil_moisture_pct:.2f} %
Nitrogen (total): {context.soil_nitrogen_mg_kg:.2f} mg/kg
Organic carbon: {context.soil_organic_carbon_g_kg:.2f} g/kg
Sand: {context.soil_sand_pct:.2f} %
Clay: {context.soil_clay_pct:.2f} %

--- AHP Weights (method: {context.ahp_method}) ---
{ahp_weights_lines}
AHP consistency ratio: {context.ahp_consistency_ratio:.4f} (consistent: {context.ahp_is_consistent})

--- Crop Ranking (DO NOT re-order or contradict this) ---
{crop_ranking_lines}

--- Recommended Resource Plan (for {top_crop_name}) ---
Water: {context.resource_plan.water_liters_per_week:.1f} L/week (approx {daily_water} L/day)
Fertilizer: {context.resource_plan.fertilizer_kg_per_acre:.2f} kg/acre
Irrigation schedule: {context.resource_plan.irrigation_schedule}
Optimizer: {context.resource_plan.optimizer_method}
Best fitness: {context.resource_plan.optimizer_best_fitness:.6f}
Generations run: {context.resource_plan.optimizer_generations_run}

--- NSGA-II Pareto Front (top options) ---
{pareto_lines}

--- FarmOptima Explanation (template-based) ---
{context.ai_explanation}

=== END DATA CONTEXT ===

REMINDER: Answer ONLY using the values above. If asked something not covered,
say it is not available in the current context. Do NOT invent crop names,
numbers, or rankings.
"""
    return prompt.strip()


# ---------------------------------------------------------------------------
# Grounding numbers collection & validation
# ---------------------------------------------------------------------------

def _collect_context_numbers(context: FarmContext) -> list[float]:
    """
    Extract every numeric value stored in the context, along with common
    arithmetic transformations (percentages, daily water, crop reference baselines).
    """
    nums: list[float] = [
        context.latitude,
        context.longitude,
        context.rainfall_mm_last_30d,
        round(context.rainfall_mm_last_30d, 1),
        round(context.rainfall_mm_last_30d),
        context.avg_temp_c,
        round(context.avg_temp_c, 1),
        round(context.avg_temp_c),
        context.humidity_pct,
        round(context.humidity_pct, 1),
        round(context.humidity_pct),
        context.solar_radiation_mj_m2,
        round(context.solar_radiation_mj_m2, 1),
        round(context.solar_radiation_mj_m2),
        context.wind_speed_m_s,
        round(context.wind_speed_m_s, 1),
        context.soil_ph,
        round(context.soil_ph, 1),
        context.soil_moisture_pct,
        round(context.soil_moisture_pct, 1),
        context.soil_nitrogen_mg_kg,
        round(context.soil_nitrogen_mg_kg, 1),
        round(context.soil_nitrogen_mg_kg),
        context.soil_organic_carbon_g_kg,
        round(context.soil_organic_carbon_g_kg, 1),
        context.soil_sand_pct,
        round(context.soil_sand_pct, 1),
        context.soil_clay_pct,
        round(context.soil_clay_pct, 1),
        context.ahp_consistency_ratio,
        round(context.ahp_consistency_ratio, 2),
        round(context.ahp_consistency_ratio, 4),
        context.resource_plan.water_liters_per_week,
        round(context.resource_plan.water_liters_per_week),
        round(context.resource_plan.water_liters_per_week, 1),
        context.resource_plan.fertilizer_kg_per_acre,
        round(context.resource_plan.fertilizer_kg_per_acre),
        round(context.resource_plan.fertilizer_kg_per_acre, 1),
        context.resource_plan.fertilizer_kg_per_acre * 2.471,  # kg/ha equivalent
        round(context.resource_plan.fertilizer_kg_per_acre * 2.471, 1),
        context.resource_plan.optimizer_best_fitness,
        round(context.resource_plan.optimizer_best_fitness, 4),
        float(context.resource_plan.optimizer_generations_run),
    ]

    # Daily water conversion, kL conversions, and standard calendar/agricultural integers
    daily_water = context.resource_plan.water_liters_per_week / 7.0
    kl_water = context.resource_plan.water_liters_per_week / 1000.0
    nums.extend([
        daily_water,
        round(daily_water),
        round(daily_water, 1),
        kl_water,
        round(kl_water, 1),
        round(kl_water, 2),
        # Common agricultural time and counting units
        1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
        12.0, 14.0, 16.0, 20.0, 24.0, 25.0, 30.0, 40.0, 50.0,
        60.0, 80.0, 90.0, 100.0, 120.0, 150.0, 180.0, 300.0,
        350.0, 365.0, 450.0, 500.0, 550.0, 700.0, 1200.0, 1800.0,
    ])

    # Parse numbers embedded in irrigation_schedule string
    if context.resource_plan.irrigation_schedule:
        for m in _NUMBER_RE.finditer(context.resource_plan.irrigation_schedule):
            try:
                nums.append(float(m.group().replace(",", "").rstrip("%")))
            except ValueError:
                pass

    # Parse numbers embedded in template ai_explanation
    if context.ai_explanation:
        for m in _NUMBER_RE.finditer(context.ai_explanation):
            try:
                nums.append(float(m.group().replace(",", "").rstrip("%")))
            except ValueError:
                pass

    if context.ndvi is not None:
        nums.append(context.ndvi.value)
        nums.append(round(context.ndvi.value, 2))
        nums.append(round(context.ndvi.value, 3))
        nums.append(round(context.ndvi.value, 4))

    for entry in context.crop_ranking:
        nums.append(entry.topsis_closeness)
        nums.append(round(entry.topsis_closeness, 2))
        nums.append(round(entry.topsis_closeness, 3))
        nums.append(round(entry.topsis_closeness, 4))
        nums.append(entry.topsis_closeness * 100.0)
        nums.append(round(entry.topsis_closeness * 100.0, 1))
        nums.append(round(entry.topsis_closeness * 100.0, 2))
        nums.append(float(entry.electre_net_outranking))
        nums.append(float(entry.rank))
        if entry.tie_break_applied:
            nums.append(1.0)
        for score in entry.criteria_scores.values():
            nums.append(score)
            nums.append(round(score, 2))
            nums.append(round(score, 3))
            nums.append(round(score, 4))
            nums.append(score * 100.0)
            nums.append(round(score * 100.0, 1))
            nums.append(round(score * 100.0, 2))

    for p in context.resource_plan.pareto_front:
        nums.append(p.water_liters_per_week)
        nums.append(round(p.water_liters_per_week))
        nums.append(p.fertilizer_kg_per_acre)
        nums.append(round(p.fertilizer_kg_per_acre))
        nums.append(p.resource_cost)
        nums.append(round(p.resource_cost, 4))

    for w in context.ahp_weights.values():
        nums.append(w)
        nums.append(round(w, 2))
        nums.append(round(w, 3))
        nums.append(round(w, 4))
        nums.append(w * 100.0)
        nums.append(round(w * 100.0, 1))
        nums.append(round(w * 100.0, 2))

    # Add agronomic parameters from CROP_DATABASE for ALL evaluated crops
    for crop_name, params in CROP_DATABASE.items():
        if "water_need_mm_season" in params:
            nums.append(float(params["water_need_mm_season"]))
        if "fertilizer_n_kg_per_acre" in params:
            nums.append(float(params["fertilizer_n_kg_per_acre"]))
        if "ideal_temp_min_c" in params:
            nums.append(float(params["ideal_temp_min_c"]))
        if "ideal_temp_max_c" in params:
            nums.append(float(params["ideal_temp_max_c"]))
        if "ideal_rainfall_min_mm_30d" in params:
            nums.append(float(params["ideal_rainfall_min_mm_30d"]))
        if "ideal_rainfall_max_mm_30d" in params:
            nums.append(float(params["ideal_rainfall_max_mm_30d"]))
        if "ideal_ph_min" in params:
            nums.append(float(params["ideal_ph_min"]))
        if "ideal_ph_max" in params:
            nums.append(float(params["ideal_ph_max"]))
        if "base_market_value_index" in params:
            nums.append(float(params["base_market_value_index"]))

    return nums


def _number_in_context(value: float, context_numbers: list[float], tolerance: float = 0.01) -> bool:
    """
    Return True if `value` appears in `context_numbers` within `tolerance`.
    Supports percentage values, decimal conversions, and common integers <= 10.
    """
    if not math.isfinite(value):
        return False

    if abs(value) < 1e-9:
        return True  # zero is always valid

    # Common counting numbers and calendar integers
    if value <= 10 and value == int(value):
        return True

    for ref in context_numbers:
        if not math.isfinite(ref) or abs(ref) < 1e-9:
            continue

        abs_diff = abs(value - ref)
        rel_diff = abs_diff / max(abs(ref), 1e-9)
        if abs_diff <= tolerance or rel_diff <= tolerance:
            return True

    return False


def _extract_numbers_from_text(text: str) -> list[float]:
    """
    Parse all numeric tokens in `text`, stripping commas, percentages,
    Devanagari digits, and Unicode thousands space separators.
    """
    text_clean = text.translate(_DEVANAGARI_DIGITS)
    # Normalize unicode/ASCII space thousands separators between digits (e.g. 28 560 or 28 560)
    text_clean = re.sub(r"(?<=\d)[\u202f\u00a0\u2009\s](?=\d{3}(?:\b|\D))", "", text_clean)

    results = []
    for m in _NUMBER_RE.finditer(text_clean):
        clean = m.group().replace(",", "").rstrip("%")
        try:
            results.append(float(clean))
        except ValueError:
            pass
    return results


def _collect_grounded_field_names(answer: str, context: FarmContext) -> list[str]:
    """
    Best-effort mapping of answer content → context field names.
    Used for the grounded_fields_used audit trail in AIAnswerResponse.
    Supports English, Hindi, and Marathi terminology.
    """
    fields: list[str] = []
    lower = answer.lower()

    field_keywords = {
        "ndvi": "ndvi",
        "rainfall": "rainfall_mm_last_30d", "वर्षा": "rainfall_mm_last_30d", "पाऊस": "rainfall_mm_last_30d", "बारिश": "rainfall_mm_last_30d",
        "temperature": "avg_temp_c", "तापमान": "avg_temp_c",
        "humidity": "humidity_pct", "आर्द्रता": "humidity_pct", "दमटपणा": "humidity_pct",
        "solar": "solar_radiation_mj_m2", "सौर": "solar_radiation_mj_m2",
        "wind": "wind_speed_m_s", "पवन": "wind_speed_m_s", "वारा": "wind_speed_m_s", "हवा": "wind_speed_m_s",
        "ph": "soil_ph", "सामू": "soil_ph",
        "moisture": "soil_moisture_pct", "नमी": "soil_moisture_pct", "ओलावा": "soil_moisture_pct",
        "nitrogen": "soil_nitrogen_mg_kg", "नाइट्रोजन": "soil_nitrogen_mg_kg", "नत्र": "soil_nitrogen_mg_kg",
        "organic carbon": "soil_organic_carbon_g_kg", "कार्बन": "soil_organic_carbon_g_kg",
        "sand": "soil_sand_pct", "बालू": "soil_sand_pct", "वाळू": "soil_sand_pct",
        "clay": "soil_clay_pct", "चिकनी": "soil_clay_pct", "माती": "soil_clay_pct",
        "water": "resource_plan.water_liters_per_week", "पानी": "resource_plan.water_liters_per_week", "पाणी": "resource_plan.water_liters_per_week", "जल": "resource_plan.water_liters_per_week",
        "fertilizer": "resource_plan.fertilizer_kg_per_acre", "उर्वरक": "resource_plan.fertilizer_kg_per_acre", "खत": "resource_plan.fertilizer_kg_per_acre",
        "irrigation": "resource_plan.irrigation_schedule", "सिंचाई": "resource_plan.irrigation_schedule", "ओलिताचे": "resource_plan.irrigation_schedule",
        "topsis": "crop_ranking.topsis_closeness", "टॉप्सिस": "crop_ranking.topsis_closeness",
        "electre": "crop_ranking.electre_net_outranking", "इलेक्ट्रे": "crop_ranking.electre_net_outranking",
        "ahp": "ahp_weights",
        "pareto": "resource_plan.pareto_front",
        "rank": "crop_ranking", "रैंकिंग": "crop_ranking", "क्रमवारी": "crop_ranking", "स्थान": "crop_ranking",
    }
    for keyword, field_name in field_keywords.items():
        if keyword in lower and field_name not in fields:
            fields.append(field_name)

    for entry in context.crop_ranking:
        crop_canon = entry.crop.lower()
        if crop_canon in lower or any(alias in lower for alias, canonical in CROP_ALIASES.items() if canonical.lower() == crop_canon):
            field_name = f"crop_ranking[{entry.rank}]={entry.crop}"
            if field_name not in fields:
                fields.append(field_name)

    return fields


def _tie_break_reason_matches(answer: str, context: FarmContext) -> bool:
    """
    Require tie-break reasoning ONLY when the answer makes a comparative claim
    explaining why one crop was ranked above another tied crop.
    """
    answer_lower = answer.lower()

    tied_entries = [entry for entry in context.crop_ranking if entry.tie_break_applied and entry.tie_break_reason]
    if not tied_entries:
        return True

    # Comparative keywords indicating a comparative claim between crops
    comparison_indicators = (
        "above", "over", "better", "higher", "beat", "outrank", "tie", "tied", "reason", "because",
        "से ऊपर", "से बेहतर", "कारण", "क्योंकि", "टाई",
        "पेक्षा", "अधिक", "कारण", "टाय", "पुढे"
    )
    is_comparative_answer = any(k in answer_lower for k in comparison_indicators)

    # If the answer is not explaining a comparison/reason between crops, no tie-break explanation is needed
    if not is_comparative_answer:
        return True

    # Identify all ranking crops mentioned in the answer
    ranking_crop_names = [e.crop.lower() for e in context.crop_ranking]
    mentioned_ranking_crops: list[str] = []
    for crop_name in ranking_crop_names:
        if crop_name in answer_lower:
            mentioned_ranking_crops.append(crop_name)
        else:
            for alias, canonical in CROP_ALIASES.items():
                if canonical.lower() == crop_name and alias in answer_lower:
                    mentioned_ranking_crops.append(crop_name)
                    break

    tied_crop_names = [e.crop.lower() for e in tied_entries]
    has_tied_crop_mentioned = any(c in mentioned_ranking_crops for c in tied_crop_names)

    # If no crop from a tie-break is mentioned, or only 1 crop is mentioned in total,
    # no tie-break comparison is being made -> PASS
    if not has_tied_crop_mentioned or len(mentioned_ranking_crops) < 2:
        return True

    for tied_entry in tied_entries:
        reason = tied_entry.tie_break_reason
        if not reason:
            continue

        if reason == "electre_net_outranking":
            if any(k in answer_lower for k in ("electre", "outrank", "इलेक्ट्रे", "आउटरँकिंग", "अग्रता")):
                return True

        if reason.startswith("dominant_criterion:"):
            criterion = reason.split(":", 1)[1]
            criterion_token = criterion.replace("_", " ")
            if any(
                k in answer_lower
                for k in (
                    criterion, criterion_token, "dominant ahp criterion", "dominant criterion",
                    "मुख्य कारक", "प्रमुख घटक", "कारक", "घटक"
                )
            ):
                return True

        if reason == "alphabetical_fallback":
            if any(k in answer_lower for k in ("alphabetical", "fallback", "वर्णमाला", "अक्षरानुसार")):
                return True

    return False


# ---------------------------------------------------------------------------
# Public grounding validation entry point
# ---------------------------------------------------------------------------

def validate_answer_is_grounded(answer: str, context: FarmContext) -> GroundingCheckResult:
    """
    Deterministic language-independent grounding check.
    Supports English, Hindi, and Marathi terminology, numbers, and crop entities.
    """
    ungrounded_crops: list[str] = []
    ungrounded_numbers: list[str] = []

    context_crop_names_lower = {name.lower() for name in context.crop_names_in_ranking}
    answer_lower = answer.lower()
    mentioned_crops: set[str] = set()

    # Search for crop words or multilingual aliases in the answer
    for alias, canonical_name in CROP_ALIASES.items():
        pattern = r"(?:\b|_|^)" + re.escape(alias.lower()) + r"(?:\b|_|$)"
        if re.search(pattern, answer_lower):
            mentioned_crops.add(canonical_name.lower())

    for name in _ALL_KNOWN_CROP_WORDS:
        pattern = r"\b" + re.escape(name.lower()) + r"\b"
        if re.search(pattern, answer_lower):
            canonical = CROP_ALIASES.get(name.lower(), name.capitalize())
            mentioned_crops.add(canonical.lower())

    for mentioned in mentioned_crops:
        if mentioned not in context_crop_names_lower:
            ungrounded_crops.append(mentioned)

    # --- Criterion check ---
    allowed_criteria = set()
    for entry in context.crop_ranking:
        allowed_criteria.update(entry.criteria_scores.keys())
    if not allowed_criteria:
        allowed_criteria.update(context.ahp_weights.keys())

    for token in re.findall(r"[a-z_]+(?:_[a-z_]+)+", answer_lower):
        if token in allowed_criteria:
            continue
        if any(word in answer_lower for word in ("criterion", "weighted contribution", "weighted", "dominant")) and token not in {"not", "the", "and", "or"}:
            if token.replace("_", " ") not in {name.replace("_", " ") for name in allowed_criteria}:
                ungrounded_numbers.append(token)

    # --- Numeric check ---
    context_numbers = _collect_context_numbers(context)
    answer_numbers = _extract_numbers_from_text(answer)

    for val in answer_numbers:
        if not _number_in_context(val, context_numbers):
            ungrounded_numbers.append(str(val))

    # Explicit NDVI status check
    if "ndvi" in answer_lower and context.ndvi is not None:
        ndvi_value_in_answer = any(
            _number_in_context(val, [context.ndvi.value], tolerance=0.005) for val in answer_numbers
        )
        ndvi_status_in_answer = context.ndvi.status.lower() in answer_lower or any(
            t in answer_lower for t in ("वनस्पती", "वनस्पति", "मध्यम", "सघन", "विरल", "मृदा", "moderate", "sparse", "dense", "vegetation")
        )
        if not (ndvi_value_in_answer or ndvi_status_in_answer):
            ungrounded_numbers.append(str(context.ndvi.value))

    passed = (not ungrounded_crops) and (not ungrounded_numbers)
    if passed and not _tie_break_reason_matches(answer, context):
        passed = False
        ungrounded_numbers.append("tie_break_reason")

    return GroundingCheckResult(
        passed=passed,
        ungrounded_crop_claims=ungrounded_crops,
        ungrounded_numeric_claims=ungrounded_numbers,
        grounded_fields_used=_collect_grounded_field_names(answer, context),
    )
