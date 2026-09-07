"""
AI assistant orchestrator.

answer_farm_question() is the single public entry point for the AI service
layer.  It:
  1. Builds the grounding prompt.
  2. Calls the LLM.
  3. Validates the answer is grounded.
  4. If grounding fails and ai_grounding_strict=True:
       - Makes one correction attempt with an explicit "correct yourself"
         instruction.
       - If the corrected answer still fails grounding, returns a safe
         explicit fallback (never the ungrounded claim).
  5. Persists one AIInteraction row.
  6. Returns AIAnswerResponse.

All grounding failures are logged at WARNING with the offending claims,
providing a permanent audit trail for debugging and report documentation.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.core.ai_grounding import build_grounding_prompt, validate_answer_is_grounded
from app.models.ai_interaction import AIInteraction
from app.schemas.ai import AIAnswerResponse, FarmContext
from app.services.ai import llm_client as _llm_client

logger = logging.getLogger(__name__)

from app.services.ai.intent_resolver import resolve_question_intent

# Safe, informative fallbacks by language returned when grounding check fails after retry.
_GROUNDING_FALLBACKS = {
    "en": (
        "I'm sorry — I could not verify that answer against your current farm recommendation data. "
        "I can answer questions about your crop ranking, TOPSIS score, water and fertilizer requirements, "
        "soil, weather, NDVI satellite status, and irrigation plan. Please rephrase or ask about one of these topics."
    ),
    "hi": (
        "मुझे खेद है — मैं आपके वर्तमान फ़ार्म अनुशंसा डेटा के विरुद्ध उस उत्तर की पुष्टि नहीं कर सका। "
        "मैं आपकी फसल रैंकिंग, TOPSIS स्कोर, पानी और उर्वरक की आवश्यकता, मिट्टी, मौसम, "
        "NDVI उपग्रह स्थिति और सिंचाई योजना के बारे में उत्तर दे सकता हूँ।"
    ),
    "mr": (
        "मला माफ करा — मी तुमच्या सध्याच्या शेती शिफारस डेटाविरुद्ध त्या उत्तराची पडताळणी करू शकलो नाही. "
        "मी तुमच्या पिकांची क्रमवारी, TOPSIS स्कोअर, पाणी आणि खतांची आवश्यकता, माती, हवामान, "
        "NDVI उपग्रह स्थिती आणि सिंचन योजनेबद्दलच्या प्रश्नांची उत्तरे देऊ शकतो."
    ),
}


def answer_farm_question(
    context: FarmContext,
    question: str,
    db: Session,
    language: str = "en",
) -> AIAnswerResponse:
    """
    Answer a farmer's question, grounded against the provided FarmContext.
    Resolves question intent, constructs a focused grounding prompt, and applies
    strict claim-level validation.
    """
    resolved_q = resolve_question_intent(question, context, requested_language=language)
    effective_lang = resolved_q.effective_response_language

    system_prompt = build_grounding_prompt(context, question, language=effective_lang)

    logger.info(
        "AI Q&A | rec_id=%s | intent=%s | lang=%s | detected=%s | crop=%s",
        context.recommendation_id,
        resolved_q.canonical_intent.value,
        effective_lang,
        resolved_q.detected_language,
        resolved_q.target_crop,
    )

    # --- First LLM call ---
    raw_answer = _llm_client.call_llm(system_prompt=system_prompt, user_message=question)
    check = validate_answer_is_grounded(raw_answer, context)

    final_answer: str
    grounding_passed: bool

    if check.passed:
        final_answer = raw_answer
        grounding_passed = True
        logger.debug(
            "Grounding check PASSED for recommendation_id=%s", context.recommendation_id
        )
    else:
        logger.warning(
            "Grounding check FAILED for recommendation_id=%s | "
            "Ungrounded crops: %s | Ungrounded numbers: %s",
            context.recommendation_id,
            check.ungrounded_crop_claims,
            check.ungrounded_numeric_claims,
        )

        if settings.ai_grounding_strict:
            # --- Correction attempt ---
            correction_instruction = _build_correction_instruction(check)
            corrected_answer = _llm_client.call_llm(
                system_prompt=system_prompt,
                user_message=correction_instruction,
            )
            corrected_check = validate_answer_is_grounded(corrected_answer, context)

            if corrected_check.passed:
                final_answer = corrected_answer
                grounding_passed = True
                logger.info(
                    "Grounding check PASSED on correction attempt for recommendation_id=%s",
                    context.recommendation_id,
                )
            else:
                logger.warning(
                    "Grounding check FAILED on correction attempt for recommendation_id=%s. "
                    "Returning safe fallback. Ungrounded crops: %s | numbers: %s",
                    context.recommendation_id,
                    corrected_check.ungrounded_crop_claims,
                    corrected_check.ungrounded_numeric_claims,
                )
                final_answer = _GROUNDING_FALLBACKS.get(effective_lang, _GROUNDING_FALLBACKS["en"])
                grounding_passed = False
                check.grounded_fields_used = list(
                    set(check.grounded_fields_used) | set(corrected_check.grounded_fields_used)
                )
        else:
            logger.warning(
                "ai_grounding_strict=False — returning potentially ungrounded answer "
                "for recommendation_id=%s.",
                context.recommendation_id,
            )
            final_answer = raw_answer
            grounding_passed = False

    # --- Persist audit row ---
    interaction = AIInteraction(
        recommendation_id=context.recommendation_id,
        question=question,
        answer=final_answer,
        grounded_fields_used=check.grounded_fields_used,
        grounding_passed=grounding_passed,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return AIAnswerResponse(
        answer=final_answer,
        grounded_fields_used=check.grounded_fields_used,
        context_snapshot_id=context.recommendation_id,
    )


def _build_correction_instruction(check) -> str:
    """
    Build the correction user-message for the second LLM call.
    Tells the model exactly what it got wrong so it can self-correct.
    """
    lines = [
        "Your previous answer contained claims that could not be verified against "
        "the farm context provided. Please correct your answer:",
    ]
    if check.ungrounded_crop_claims:
        lines.append(
            f"- The following crop names do NOT appear in the recommendation's "
            f"crop ranking and must NOT be mentioned: {', '.join(check.ungrounded_crop_claims)}."
        )
    if check.ungrounded_numeric_claims:
        lines.append(
            f"- The following numbers do NOT appear in the farm context and must "
            f"NOT be used: {', '.join(check.ungrounded_numeric_claims)}."
        )
    lines.append(
        "Provide a corrected answer using ONLY the data values from the context. "
        "If the correct answer is not in the context, say 'not available'."
    )
    return "\n".join(lines)


def answer_question_for_recommendation(
    recommendation_id: int,
    question: str,
    db: Session,
    language: str = "en",
) -> AIAnswerResponse:
    """
    Load a persisted recommendation from the DB by id and answer a question
    grounded against its EXACT stored context.

    This is a thin orchestration wrapper introduced in Step 2.2.  All
    grounding safety logic lives in the Step 2.1 answer_farm_question()
    function, which is called unchanged.

    Parameters
    ----------
    recommendation_id:
        The primary-key id returned by a previous /api/recommend call.
    question:
        The farmer's natural-language question.
    db:
        An active SQLAlchemy session (used by context_loader for the DB
        query and by answer_farm_question for persisting the AIInteraction).

    Returns
    -------
    AIAnswerResponse
        The grounded answer.  The AIInteraction row persisted by
        answer_farm_question() carries the REAL recommendation_id (loaded
        from the DB record), linking every AI interaction to its exact
        data context for full audit traceability.

    Raises
    ------
    RecommendationNotFoundError
        If recommendation_id does not exist in the database.
    AIServiceUnavailableError
        If the LLM API call fails.
    """
    # Import here (not at module level) to avoid a circular-import risk
    # between assistant_service ↔ context_loader.  Both are in the same
    # sub-package but context_loader imports build_farm_context which in
    # turn imports from schemas.  Lazy import keeps the dependency graph clean.
    from app.services.ai.context_loader import get_context_for_recommendation

    context = get_context_for_recommendation(recommendation_id, db)

    # context.recommendation_id is set by context_loader from record.id,
    # so the AIInteraction row persisted inside answer_farm_question() will
    # carry the real non-null recommendation_id automatically.
    try:
        return answer_farm_question(context=context, question=question, db=db, language=language)
    except TypeError:
        # Backward-compatible fallback for tests or older callers that still monkeypatch
        # the legacy answer_farm_question(context, question, db) signature.
        return answer_farm_question(context=context, question=question, db=db)

