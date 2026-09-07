"""
Intent and evidence resolution layer for FarmOptima AI Assistant.

Separates Question Understanding from Grounding Validation:
  1. Detects question language (English, Hindi, Marathi, mixed-language).
  2. Resolves canonical intent (recommendation explanation, resource plan, ranking,
     what-if scenario, complete reasoning, metric lookup, unsupported fact check).
  3. Extracts target entities (canonical crop name, criterion, resource type).
  4. Identifies required canonical evidence IDs from the authoritative FarmContext.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.schemas.ai import FarmContext
from app.core.ai_grounding import CROP_ALIASES


class CanonicalIntent(str, Enum):
    RECOMMENDATION_EXPLANATION = "recommendation_explanation"
    WATER_REQUIREMENT = "water_requirement"
    FERTILIZER_REQUIREMENT = "fertilizer_requirement"
    RESOURCE_PLAN = "resource_plan"
    RANKING_EXPLANATION = "ranking_explanation"
    COMPLETE_REASONING = "complete_reasoning"
    WHAT_IF_SCENARIO = "what_if_scenario"
    NDVI_SATELLITE = "ndvi_satellite"
    SOIL_CONDITIONS = "soil_conditions"
    WEATHER_CONDITIONS = "weather_conditions"
    DOMINANT_CRITERION = "dominant_criterion"
    UNSUPPORTED_DATA = "unsupported_data"
    GENERAL_GROUNDED_QA = "general_grounded_qa"


@dataclass
class ResolvedQuestion:
    raw_question: str
    detected_language: str  # "en", "hi", "mr"
    effective_response_language: str  # "en", "hi", "mr"
    canonical_intent: CanonicalIntent
    target_crop: str | None = None
    target_crop_rank: int | None = None
    required_evidence_ids: list[str] = field(default_factory=list)
    is_hypothetical: bool = False


# Devanagari detection & language markers
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_MARATHI_SPECIFIC_WORDS = {
    "आहे", "नाही", "काय", "कसे", "कशी", "करा", "सांगा", "पाणी", "पाण्याची", "शेतासाठी",
    "खत", "पिके", "पिकांची", "पिकांचे", "क्रमवारी", "हवामान", "माती", "झाले", "तर",
    "कमी", "जास्त", "तांदूळ", "भात", "भुईमूग", "गहू", "कापूस", "ऊस", "हरभरा", "मका"
}
_HINDI_SPECIFIC_WORDS = {
    "है", "नहीं", "क्या", "कैसे", "कैसी", "करें", "बताएं", "पानी", "उर्वरक", "फसल",
    "फसलों", "रैंकिंग", "मौसम", "मिट्टी", "हुआ", "तो", "कम", "ज्यादा", "चावल", "धान",
    "मूंगफली", "गेहूं", "कपास", "गन्ना", "चना", "मक्का", "दिए", "गए", "तर्क"
}


def detect_question_language(text: str, fallback_language: str = "en") -> str:
    """
    Detect the primary language of the question text.
    Handles English, Hindi, Marathi, and mixed (Hinglish/Marathi-English).
    """
    if not text:
        return fallback_language

    has_devanagari = bool(_DEVANAGARI_RE.search(text))
    if not has_devanagari:
        # Latin script: could be English or transliterated Hindi/Marathi (Hinglish)
        lower = text.lower()
        if any(w in lower for w in ("kyun", "kya", "kaise", "pani", "khat", "fasal")):
            return "hi"
        if any(w in lower for w in ("kasa", "kay", "pani", "sheta", "pik")):
            return "mr"
        return "en"

    # Devanagari script: distinguish Hindi vs Marathi
    tokens = set(re.findall(r"[\u0900-\u097F]+", text.lower()))
    marathi_count = len(tokens & _MARATHI_SPECIFIC_WORDS)
    hindi_count = len(tokens & _HINDI_SPECIFIC_WORDS)

    if marathi_count > hindi_count:
        return "mr"
    if hindi_count > marathi_count:
        return "hi"

    # Fallback to the requested locale if ambiguous
    return fallback_language if fallback_language in {"hi", "mr"} else "hi"


def extract_target_crop(text: str, context: FarmContext | None = None) -> tuple[str | None, int | None]:
    """
    Extract any referenced crop from the question text using canonical aliases.
    If no crop is explicitly mentioned, returns the top recommended crop.
    """
    text_lower = text.lower()
    for alias, canonical in CROP_ALIASES.items():
        pattern = r"(?:\b|_|^)" + re.escape(alias.lower()) + r"(?:\b|_|$)"
        if re.search(pattern, text_lower):
            # Find rank if context is provided
            rank = None
            if context:
                for entry in context.crop_ranking:
                    if entry.crop.lower() == canonical.lower():
                        rank = entry.rank
                        break
            return canonical, rank

    # If no specific crop mentioned and context exists, default to top crop
    if context and context.crop_ranking:
        top = context.crop_ranking[0]
        return top.crop, top.rank

    return None, None


def resolve_question_intent(
    question: str,
    context: FarmContext,
    requested_language: str = "en",
) -> ResolvedQuestion:
    """
    Resolve the farmer's natural-language question into a canonical intent
    and required evidence set from the FarmContext.
    """
    detected_lang = detect_question_language(question, fallback_language=requested_language)
    effective_lang = requested_language if requested_language in {"en", "hi", "mr"} else detected_lang

    q_lower = question.lower()
    target_crop, target_rank = extract_target_crop(question, context)

    # 1. Complete reasoning / overall explanation
    if any(k in q_lower for k in (
        "complete reasoning", "entire reasoning", "full reasoning", "why recommendation",
        "पूरे तर्क", "पूरा तर्क", "संपूर्ण तर्क", "सर्व कारणे", "संपूर्ण स्पष्टीकरण",
        "detailed explanation", "all factors", "everything behind"
    )):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.COMPLETE_REASONING,
            target_crop=target_crop,
            target_crop_rank=target_rank,
            required_evidence_ids=[
                "crop_ranking", "topsis_closeness", "electre_net_outranking", "ahp_weights",
                "weather", "soil", "resource_plan", "ndvi"
            ],
        )

    # 2. What-if / Hypothetical scenarios
    if any(k in q_lower for k in (
        "what if", "what would happen", "if water", "decreased", "if rainfall", "if drought",
        "क्या होगा", "अगर", "यदि", "कम हो जाए", "हो जाए तो", "पाणी कमी", "कमी झाली तर", "झाले तर", "काय होईल", "जर"
    )):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.WHAT_IF_SCENARIO,
            target_crop=target_crop,
            target_crop_rank=target_rank,
            is_hypothetical=True,
            required_evidence_ids=[
                "resource_plan.water_liters_per_week", "crop_ranking", "water_efficiency"
            ],
        )

    # 3. Water requirement & irrigation
    if any(k in q_lower for k in (
        "water", "irrigation", "liters", "litre", "पानी", "जल", "सिंचाई", "पाणी", "ओलिताचे", "पाण्याची"
    )) and not any(k in q_lower for k in ("fertilizer", "उर्वरक", "खत")):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.WATER_REQUIREMENT,
            target_crop=target_crop,
            target_crop_rank=target_rank,
            required_evidence_ids=[
                "resource_plan.water_liters_per_week", "resource_plan.irrigation_schedule"
            ],
        )

    # 4. Fertilizer requirement
    if any(k in q_lower for k in (
        "fertilizer", "fert", "npk", "dosage", "उर्वरक", "खाद", "खत", "खताचे"
    )) and not any(k in q_lower for k in ("water", "पानी", "पाणी")):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.FERTILIZER_REQUIREMENT,
            target_crop=target_crop,
            target_crop_rank=target_rank,
            required_evidence_ids=[
                "resource_plan.fertilizer_kg_per_acre"
            ],
        )

    # 5. Combined Water + Fertilizer Resource Plan
    if any(k in q_lower for k in ("water and fertilizer", "fertilizer and water", "पानी और उर्वरक", "पाणी आणि खत", "resource plan", "संसाधन")):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.RESOURCE_PLAN,
            target_crop=target_crop,
            target_crop_rank=target_rank,
            required_evidence_ids=[
                "resource_plan.water_liters_per_week", "resource_plan.fertilizer_kg_per_acre",
                "resource_plan.irrigation_schedule"
            ],
        )

    # 6. Ranking / Scores comparison
    if any(k in q_lower for k in (
        "ranking", "scores", "all crops", "compare crops", "other crops", "rank 1", "rank 2",
        "रैंकिंग", "स्कोर", "सभी फसलें", "अन्य फसलें", "पिकांची क्रमवारी", "इतर पिके", "स्कोअर"
    )):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.RANKING_EXPLANATION,
            target_crop=target_crop,
            target_crop_rank=target_rank,
            required_evidence_ids=[
                "crop_ranking", "crop_names_in_ranking", "topsis_closeness", "electre_net_outranking"
            ],
        )

    # 7. NDVI / Satellite query
    if any(k in q_lower for k in ("ndvi", "satellite", "vegetation", "उपग्रह", "वनस्पति", "वनस्पती")):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.NDVI_SATELLITE,
            required_evidence_ids=["ndvi"],
        )

    # 8. Dominant Criterion / AHP Factor
    if any(k in q_lower for k in (
        "dominant factor", "most influence", "highest weight", "ahp", "which factor",
        "सबसे अधिक प्रभावित", "मुख्य कारक", "प्रमुख घटक", "सर्वाधिक प्रभाव", "महत्त्वाचा घटक"
    )):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.DOMINANT_CRITERION,
            required_evidence_ids=["ahp_weights"],
        )

    # 9. Specific Recommendation Explanation (e.g. "Why was Rice recommended?", "Why did you choose Rice?")
    if any(k in q_lower for k in (
        "why", "how was", "reason", "choose", "chose", "selected", "first", "best option",
        "क्यों", "कारण", "चुना", "पसंद", "पहला", "का", "निवड", "निवडले", "प्रथम"
    )):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.RECOMMENDATION_EXPLANATION,
            target_crop=target_crop,
            target_crop_rank=target_rank,
            required_evidence_ids=[
                "crop_ranking", "topsis_closeness", "electre_net_outranking", "ahp_weights"
            ],
        )

    # 10. Unsupported / Future Data requests (e.g. "exact yield in tonnes", "future price next year")
    if any(k in q_lower for k in ("exact yield", "tonnes per acre", "tons", "market price next year", "भविष्य", "अचूक उत्पादन", "टन")):
        return ResolvedQuestion(
            raw_question=question,
            detected_language=detected_lang,
            effective_response_language=effective_lang,
            canonical_intent=CanonicalIntent.UNSUPPORTED_DATA,
            required_evidence_ids=[],
        )

    # Default: General Grounded Q&A
    return ResolvedQuestion(
        raw_question=question,
        detected_language=detected_lang,
        effective_response_language=effective_lang,
        canonical_intent=CanonicalIntent.GENERAL_GROUNDED_QA,
        target_crop=target_crop,
        target_crop_rank=target_rank,
        required_evidence_ids=["crop_ranking", "resource_plan", "ahp_weights", "weather", "soil"],
    )
