"""
AI-specific grounding logic.

This module is pure Python: no I/O, no database, no network — making it
fully unit-testable without any external dependencies.  It matches the
project's existing pattern for core/ modules (see core/mcdm.py).

Two public functions:

  build_grounding_prompt(context, question) -> str
      Constructs the system + context block that is sent to the LLM.
      The prompt embeds every numeric and categorical value from context
      so the LLM has no reason to hallucinate data.  It also contains
      explicit grounding instructions.

  validate_answer_is_grounded(answer, context) -> GroundingCheckResult
      A deterministic (non-LLM) safety check that parses crop names and
      numeric values out of the model's answer and verifies that each one
      can be traced back to a field in the provided context.  This is the
      concrete "grounded AI" mechanism — testable, auditable, and patent-
      documentable.
"""

from __future__ import annotations

import re

from app.schemas.ai import FarmContext, GroundingCheckResult


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_grounding_prompt(context: FarmContext, question: str) -> str:  # noqa: ARG001 (question used in docstring context, not here)
    """
    Construct the system prompt that will be sent to the LLM alongside the
    farmer's question.

    The returned string is the *system* prompt only; the caller sends
    `question` as the *user* message.  This separation lets the LLM API
    enforce role-based prompting correctly.

    Design rules:
    1. Every numeric value in context is spelled out explicitly so the LLM
       can cite it without inventing alternatives.
    2. The grounding instructions are stated as hard constraints at both the
       top and bottom of the prompt (double-binding).
    3. If a field is marked unavailable, the prompt says so; the LLM is
       told to respond "not available" rather than guessing.
    4. The crop ranking order is stated verbatim so the LLM cannot re-rank.
    """

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
        for i, p in enumerate(context.resource_plan.pareto_front[:5])  # cap at 5 for brevity
    )
    if not pareto_lines:
        pareto_lines = "  (no pareto front data available)"

    prompt = f"""You are FarmOptima's agricultural AI assistant.  Your ONLY job is to answer
the farmer's question using the verified recommendation data provided below.

=== HARD GROUNDING RULES (MUST follow without exception) ===
1. You MUST answer using ONLY the values listed in the DATA CONTEXT section.
2. You MUST NOT state any crop name that does not appear in the CROP RANKING.
3. You MUST NOT state any numeric value (yield, water, fertilizer, score, etc.)
   that does not appear verbatim (or within normal rounding) in the DATA CONTEXT.
4. You MUST NOT re-rank, override, or contradict the CROP RANKING produced by
   FarmOptima's AHP-TOPSIS-ELECTRE algorithm.  You may explain it; you may not
   change it.
5. If the farmer asks about information that is NOT present in the DATA CONTEXT,
   respond with an explicit statement such as: "That information is not available
   in the current recommendation context."
6. Never invent agronomic rules, yield estimates, prices, or comparisons that
   are not stated in the DATA CONTEXT.
7. Be concise, respectful, and helpful to a farmer who may not know technical terms.

=== DATA CONTEXT ===

Location: lat={context.latitude}, lon={context.longitude}
Recommendation generated at: {context.generated_at}
Recommendation status: {context.recommendation_status}
Data completeness — weather: {context.data_completeness_weather}, soil: {context.data_completeness_soil}, satellite: {context.data_completeness_satellite}, market: {context.data_completeness_market}

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

--- Recommended Resource Plan ---
Water: {context.resource_plan.water_liters_per_week:.1f} L/week
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

REMINDER: Answer ONLY using the values above.  If asked something not covered,
say it is not available in the current context.  Do NOT invent crop names,
numbers, or rankings.
"""
    return prompt.strip()


# ---------------------------------------------------------------------------
# Grounding validator
# ---------------------------------------------------------------------------

# Regex: find numbers (int or float, possibly with commas) in the answer text.
_NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")


def _collect_context_numbers(context: FarmContext) -> list[float]:
    """
    Extract every numeric value stored in the context into a flat list.
    Used as the reference set for validate_answer_is_grounded().
    """
    nums: list[float] = [
        context.latitude,
        context.longitude,
        context.rainfall_mm_last_30d,
        context.avg_temp_c,
        context.humidity_pct,
        context.solar_radiation_mj_m2,
        context.wind_speed_m_s,
        context.soil_ph,
        context.soil_moisture_pct,
        context.soil_nitrogen_mg_kg,
        context.soil_organic_carbon_g_kg,
        context.soil_sand_pct,
        context.soil_clay_pct,
        context.ahp_consistency_ratio,
        context.resource_plan.water_liters_per_week,
        context.resource_plan.fertilizer_kg_per_acre,
        context.resource_plan.optimizer_best_fitness,
        float(context.resource_plan.optimizer_generations_run),
    ]
    if context.ndvi is not None:
        nums.append(context.ndvi.value)

    for entry in context.crop_ranking:
        nums.append(entry.topsis_closeness)
        nums.append(float(entry.electre_net_outranking))
        nums.append(float(entry.rank))
        if entry.tie_break_applied:
            nums.append(1.0)

    for p in context.resource_plan.pareto_front:
        nums.append(p.water_liters_per_week)
        nums.append(p.fertilizer_kg_per_acre)
        nums.append(p.resource_cost)

    for w in context.ahp_weights.values():
        nums.append(w)

    return nums


def _number_in_context(value: float, context_numbers: list[float], tolerance: float = 0.01) -> bool:
    """
    Return True if `value` appears in `context_numbers` within `tolerance`
    (relative or absolute, whichever is more permissive).

    tolerance=0.01 → 1% rounding tolerance covers normal decimal formatting
    differences (e.g. 0.4495 displayed as 0.45 in the answer).

    We also allow small integers (≤ 10) to pass freely because they are
    common in everyday language ("top 3 crops", "one farm") and do not
    represent specific agronomic values.
    """
    if abs(value) < 1e-9:
        return True  # zero is always valid (e.g. rank 0, empty list)
    if value <= 10 and value == int(value):
        return True  # common small integers — not agronomic claims

    for ref in context_numbers:
        if abs(ref) < 1e-9:
            continue
        abs_diff = abs(value - ref)
        rel_diff = abs_diff / max(abs(ref), 1e-9)
        if abs_diff <= tolerance or rel_diff <= tolerance:
            return True
    return False


def _extract_numbers_from_text(text: str) -> list[float]:
    """Parse all numeric tokens in `text`, stripping commas."""
    results = []
    for m in _NUMBER_RE.finditer(text):
        try:
            results.append(float(m.group().replace(",", "")))
        except ValueError:
            pass
    return results


def _collect_grounded_field_names(answer: str, context: FarmContext) -> list[str]:
    """
    Best-effort mapping of answer content → context field names.
    Used for the grounded_fields_used audit trail in AIAnswerResponse.
    """
    fields: list[str] = []
    lower = answer.lower()

    field_keywords = {
        "ndvi": "ndvi",
        "rainfall": "rainfall_mm_last_30d",
        "temperature": "avg_temp_c",
        "humidity": "humidity_pct",
        "solar": "solar_radiation_mj_m2",
        "wind": "wind_speed_m_s",
        "ph": "soil_ph",
        "moisture": "soil_moisture_pct",
        "nitrogen": "soil_nitrogen_mg_kg",
        "organic carbon": "soil_organic_carbon_g_kg",
        "sand": "soil_sand_pct",
        "clay": "soil_clay_pct",
        "water": "resource_plan.water_liters_per_week",
        "fertilizer": "resource_plan.fertilizer_kg_per_acre",
        "irrigation": "resource_plan.irrigation_schedule",
        "topsis": "crop_ranking.topsis_closeness",
        "electre": "crop_ranking.electre_net_outranking",
        "ahp": "ahp_weights",
        "pareto": "resource_plan.pareto_front",
        "rank": "crop_ranking",
    }
    for keyword, field_name in field_keywords.items():
        if keyword in lower and field_name not in fields:
            fields.append(field_name)

    # Also add crop-specific field if any ranking crop is mentioned
    for entry in context.crop_ranking:
        if entry.crop.lower() in lower:
            field_name = f"crop_ranking[{entry.rank}]={entry.crop}"
            if field_name not in fields:
                fields.append(field_name)

    return fields


def _tie_break_reason_matches(answer: str, context: FarmContext) -> bool:
    """Require the exact tie-break reason only when the answer compares tied crops."""
    answer_lower = answer.lower()

    tied_entries = [entry for entry in context.crop_ranking if entry.tie_break_applied and entry.tie_break_reason]
    if not tied_entries:
        return True

    # Generic answers about only one crop do not need to recount the tie-break.
    mentioned_crops = [entry.crop.lower() for entry in context.crop_ranking if entry.crop.lower() in answer_lower]
    if len(mentioned_crops) < 2:
        return True

    for tied_entry in tied_entries:
        reason = tied_entry.tie_break_reason
        if reason is None:
            continue

        if reason == "electre_net_outranking":
            if tied_entry.crop.lower() in answer_lower and any(
                other.crop.lower() in answer_lower for other in context.crop_ranking if other.crop.lower() != tied_entry.crop.lower()
            ):
                return "electre" in answer_lower and ("outranking" in answer_lower or "outrank" in answer_lower)

        if reason.startswith("dominant_criterion:"):
            criterion = reason.split(":", 1)[1]
            criterion_token = criterion.replace("_", " ")
            if tied_entry.crop.lower() in answer_lower and any(
                other.crop.lower() in answer_lower for other in context.crop_ranking if other.crop.lower() != tied_entry.crop.lower()
            ):
                return (
                    criterion in answer_lower
                    or criterion_token in answer_lower
                    or "dominant ahp criterion" in answer_lower
                    or "dominant criterion" in answer_lower
                )

        if reason == "alphabetical_fallback":
            if tied_entry.crop.lower() in answer_lower and any(
                other.crop.lower() in answer_lower for other in context.crop_ranking if other.crop.lower() != tied_entry.crop.lower()
            ):
                return "alphabetical" in answer_lower and ("fallback" in answer_lower or "order" in answer_lower)

    return True


def validate_answer_is_grounded(answer: str, context: FarmContext) -> GroundingCheckResult:
    """
    Deterministic grounding check.  Returns a GroundingCheckResult
    indicating whether the answer is safe to return to the farmer.

    Crop check:
      Every crop name mentioned in the answer must appear in
      context.crop_names_in_ranking (case-insensitive, whole-word match).
      Single-character or very common words are skipped.

    Numeric check:
      Every decimal number (or integer > 10) extracted from the answer
      must match at least one numeric value in context within 1% tolerance.

    Criterion check:
      If the answer names an agronomic criterion (e.g. climate_suitability,
      market_value, water_efficiency), it must match the actual criteria
      produced by the recommendation run.  This prevents invented claim names
      such as "market_price" from passing as if they were backed by the model.
    """
    ungrounded_crops: list[str] = []
    ungrounded_numbers: list[str] = []

    # --- Crop name check ---
    context_crop_names_lower = {name.lower() for name in context.crop_names_in_ranking}

    # Build a set of all crop names mentioned in the answer using exact word search
    answer_lower = answer.lower()
    mentioned_crops: set[str] = set()
    for name in _ALL_KNOWN_CROP_WORDS:
        # whole-word match so "wheat" doesn't match "buckwheat"
        pattern = r"\b" + re.escape(name.lower()) + r"\b"
        if re.search(pattern, answer_lower):
            mentioned_crops.add(name.lower())

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

    # Explicit NDVI status check: if NDVI is mentioned in the answer, the
    # status label must also match the structured NDVI block.
    answer_lower = answer.lower()
    if "ndvi" in answer_lower and context.ndvi is not None:
        ndvi_value_in_answer = any(
            _number_in_context(val, [context.ndvi.value], tolerance=0.01) for val in answer_numbers
        )
        ndvi_status_in_answer = context.ndvi.status.lower() in answer_lower
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


# ---------------------------------------------------------------------------
# Known agricultural crop vocabulary for grounding checks
# ---------------------------------------------------------------------------
# This list is used to scan the LLM answer for crop mentions.
# It covers all crops in FarmOptima's crop_database plus common synonyms.
# Only crops in this list AND in context.crop_names_in_ranking are valid.

_ALL_KNOWN_CROP_WORDS = [
    "wheat", "rice", "maize", "corn", "sorghum", "millet", "barley", "oats",
    "rye", "triticale", "chickpea", "lentil", "pigeon pea", "pigeonpea",
    "mung bean", "mungbean", "black gram", "soybean", "groundnut", "peanut",
    "sunflower", "mustard", "rapeseed", "canola", "sesame", "linseed",
    "sugarcane", "cotton", "jute", "tobacco", "potato", "tomato", "onion",
    "garlic", "ginger", "turmeric", "chilli", "pepper", "brinjal",
    "eggplant", "okra", "cauliflower", "cabbage", "pea", "cowpea",
    "banana", "mango", "papaya", "guava", "pomegranate", "grapes",
    "watermelon", "cucumber", "pumpkin", "bottle gourd", "bitter gourd",
    "ridge gourd", "sponge gourd",
]
