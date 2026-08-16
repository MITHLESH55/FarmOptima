"""
AI routes — Phase 2.1 health check + Phase 2.3 Chat API.

GET  /api/ai/health  — unauthenticated diagnostic endpoint.
POST /api/ai/chat    — authenticated, ownership-enforced AI question endpoint.

No LLM secrets are ever returned. All grounding logic lives in the
Phase 2.1 service layer (answer_farm_question). Authorization (Phase 2.3A
get_authorized_recommendation) happens BEFORE context loading and LLM calls.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.api.deps import get_current_user, get_authorized_recommendation
from app.schemas.ai import AIAnswerResponse, VoiceAnswerResponse

router = APIRouter(prefix="/ai", tags=["ai"])


# ---------------------------------------------------------------------------
# Phase 2.3 — Chat request schema
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """
    Authenticated farmer's question about a specific persisted recommendation.

    recommendation_id must identify a recommendation owned by the calling user.
    question is trimmed server-side; empty/whitespace-only questions are
    rejected at validation time (min_length=1 on the stripped value is enforced
    by the strip_question validator).
    """
    recommendation_id: int
    question: str = Field(..., min_length=1, max_length=2000)

    # Pydantic v2: strip surrounding whitespace and reject blank strings
    from pydantic import field_validator

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("question must not be empty or whitespace-only")
        return stripped


# ---------------------------------------------------------------------------
# Phase 2.3 — Chat endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/chat",
    response_model=AIAnswerResponse,
    summary="Ask an AI question about a specific recommendation",
)
def ai_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIAnswerResponse:
    """
    Ask the AI assistant a natural-language question about ONE specific,
    previously persisted recommendation that belongs to the authenticated user.

    Security contract (strictly ordered):
      1. Authentication — enforced by get_current_user dependency.
      2. Ownership authorization — get_authorized_recommendation() verifies
         Recommendation.farm_id → Farm.user_id == current_user.id BEFORE
         any context loading or LLM invocation.
      3. Context loading — answer_question_for_recommendation() calls
         get_context_for_recommendation() which reads Recommendation.full_result.
      4. AI pipeline — existing Phase 2.1 grounding / LLM call / retry /
         AIInteraction persistence.

    Authorization errors (nonexistent OR other user's recommendation):
      → RecommendationNotFoundError (HTTP 404, error_code=recommendation_not_found)

    LLM errors:
      → AIServiceUnavailableError (HTTP 502)
    """
    # Step 1: Authorize ownership — raises RecommendationNotFoundError if
    # the recommendation does not exist OR belongs to another user.
    # This is the ONLY authorization check; do not duplicate it downstream.
    get_authorized_recommendation(payload.recommendation_id, current_user, db)

    # Step 2: Delegate entirely to the Phase 2.2 orchestration wrapper.
    # It calls context_loader → FarmContext → Phase 2.1 AI pipeline → AIInteraction.
    from app.services.ai.assistant_service import answer_question_for_recommendation
    return answer_question_for_recommendation(
        recommendation_id=payload.recommendation_id,
        question=payload.question,
        db=db,
    )


# ---------------------------------------------------------------------------
# Phase 2.4 — Voice endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/voice",
    response_model=VoiceAnswerResponse,
    summary="Ask an AI question about a recommendation using voice",
)
async def ai_voice(
    recommendation_id: int = Form(..., description="ID of the owned recommendation to query"),
    audio: UploadFile = File(..., description="Recorded audio question (MP3, WAV, WEBM, M4A, OGG, FLAC)"),
    enable_tts: bool = Form(True, description="Whether to synthesize audio response via TTS"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VoiceAnswerResponse:
    """
    Process an authenticated voice question from a farmer about a specific recommendation.

    Order of operations:
      1. Authentication — enforced by get_current_user dependency.
      2. Ownership authorization — verified by get_authorized_recommendation()
         BEFORE audio transcription, LLM invocation, or TTS synthesis.
      3. STT transcription — audio bytes converted to text.
      4. Grounded AI Q&A — delegates to the existing Phase 2.2/2.1 pipeline.
      5. Optional TTS — converts the grounded answer into audio.
    """
    from app.services.voice.voice_service import process_voice_question

    audio_bytes = await audio.read()

    return process_voice_question(
        recommendation_id=recommendation_id,
        audio_bytes=audio_bytes,
        filename=audio.filename or "recording.webm",
        content_type=audio.content_type,
        db=db,
        current_user=current_user,
        enable_tts=enable_tts,
    )


# ---------------------------------------------------------------------------
# Phase 2.1 — Health check (unchanged)
# ---------------------------------------------------------------------------

@router.get("/health", summary="AI subsystem health check")
def ai_health():
    """
    Diagnostic endpoint for the Step 2.1 AI foundation.

    - Does NOT require authentication.
    - Does NOT call the LLM API (zero cost, zero network traffic).
    - Never returns the raw llm_api_key value.
    """
    degraded_components: list[str] = []

    # --- Check 1: LLM key presence (never reveal the key itself) ---
    llm_configured = settings.llm_configured

    # --- Check 2: grounding module imports cleanly ---
    grounding_module_loaded: bool
    try:
        import app.core.ai_grounding  # noqa: F401
        grounding_module_loaded = True
    except Exception as exc:  # noqa: BLE001
        grounding_module_loaded = False
        degraded_components.append(f"ai_grounding ({exc})")

    # --- Check 3: context_builder imports cleanly ---
    context_builder_loaded: bool
    try:
        import app.services.ai.context_builder  # noqa: F401
        context_builder_loaded = True
    except Exception as exc:  # noqa: BLE001
        context_builder_loaded = False
        degraded_components.append(f"context_builder ({exc})")

    status = "degraded" if degraded_components else "ok"

    response: dict = {
        "status": status,
        "llm_configured": llm_configured,
        "llm_provider": settings.llm_provider,
        "grounding_module_loaded": grounding_module_loaded,
        "context_builder_loaded": context_builder_loaded,
    }

    if degraded_components:
        response["degraded_components"] = degraded_components

    return response

