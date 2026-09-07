"""
Voice interaction orchestrator — Phase 2.4 Voice.

Coordinates the end-to-end voice question pipeline:
  1. Authorization: Enforces Recommendation ownership via Phase 2.3A primitive
     BEFORE audio transcription, context loading, LLM, or TTS calls.
  2. STT: Converts farmer speech audio to plain text via stt_client.
  3. AI Service: Delegates to Phase 2.2 answer_question_for_recommendation()
     which uses Phase 2.1 grounding and persists AIInteraction audit records.
  4. TTS: Optionally synthesizes the grounded answer to audio.
"""

from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.models import User
from app.api.deps import get_authorized_recommendation
from app.schemas.ai import VoiceAnswerResponse
from app.services.voice import stt_client as _stt_client
from app.services.voice import tts_client as _tts_client

logger = logging.getLogger(__name__)


def process_voice_question(
    recommendation_id: int,
    audio_bytes: bytes,
    filename: str,
    content_type: str | None,
    db: Session,
    current_user: User,
    enable_tts: bool = True,
) -> VoiceAnswerResponse:
    """
    Process an authenticated voice question about a recommendation.

    Order of operations (strictly enforced for security and correctness):
      1. Recommendation ownership authorization — throws RecommendationNotFoundError (404)
         if recommendation does not exist or does not belong to current_user.
      2. STT transcription — converts audio to normalized text.
      3. AI Question Answering — loads recommendation context, runs grounded LLM Q&A,
         and records AIInteraction audit row with real recommendation_id.
      4. TTS synthesis — generates speech audio for the grounded answer.

    Parameters
    ----------
    recommendation_id:
        ID of the recommendation to query.
    audio_bytes:
        Raw uploaded audio bytes.
    filename:
        Original filename of the audio upload.
    content_type:
        MIME content type of the upload.
    db:
        Active SQLAlchemy database session.
    current_user:
        Authenticated User record.
    enable_tts:
        Whether to attempt TTS audio synthesis for the answer.

    Returns
    -------
    VoiceAnswerResponse
        Contains transcript, grounded text answer, audit fields, and optional audio.
    """
    # STEP 1: Authorize recommendation ownership FIRST.
    # If unauthorized or not found, raises RecommendationNotFoundError (HTTP 404).
    # This guarantees STT, context loader, LLM, and TTS are NEVER invoked for unauthorized requests.
    get_authorized_recommendation(recommendation_id, current_user, db)

    # STEP 2: Validate audio payload (size, format, non-empty)
    _stt_client.validate_audio_payload(
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
    )

    # STEP 3: STT Transcription
    transcript = _stt_client.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
    )

    # STEP 3: Existing AI Service (Phase 2.2 + Phase 2.1 pipeline)
    from app.services.ai.assistant_service import answer_question_for_recommendation

    ai_resp = answer_question_for_recommendation(
        recommendation_id=recommendation_id,
        question=transcript,
        db=db,
    )

    # STEP 4: Optional TTS Synthesis (happens AFTER grounded answer exists)
    audio_base64: str | None = None
    if enable_tts:
        audio_base64 = _tts_client.synthesize_speech(ai_resp.answer)

    return VoiceAnswerResponse(
        transcript=transcript,
        answer=ai_resp.answer,
        grounded_fields_used=ai_resp.grounded_fields_used,
        context_snapshot_id=ai_resp.context_snapshot_id,
        audio_base64=audio_base64,
    )
