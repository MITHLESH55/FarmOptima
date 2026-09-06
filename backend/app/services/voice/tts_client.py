"""
Text-to-Speech (TTS) client — Phase 2.4 Voice.

Thin provider abstraction for synthesizing grounded text answers into audio.
Isolates OpenAI TTS API calls from the route and AI orchestration layers.
Supports graceful fallback: if TTS fails, the grounded text answer is preserved
and audio_base64 is set to None.
"""

from __future__ import annotations

import base64
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def synthesize_speech(text: str, raise_on_failure: bool = False) -> str | None:
    """
    Synthesize text into speech audio using OpenAI TTS (tts-1).

    Parameters
    ----------
    text:
        The grounded answer text to convert to speech.
    raise_on_failure:
        If True, re-raises any provider exception.
        If False (default), logs a warning and returns None for graceful degradation.

    Returns
    -------
    str | None
        Base64-encoded MP3 audio string, or None if TTS is unconfigured/failed.
    """
    if not text or not text.strip():
        return None

    if not settings.llm_api_key:
        logger.warning("TTS skipped: LLM_API_KEY is not configured.")
        if raise_on_failure:
            from app.utils.exceptions import VoiceServiceUnavailableError
            raise VoiceServiceUnavailableError("LLM_API_KEY is not configured for TTS.")
        return None

    try:
        import openai  # noqa: PLC0415

        client = openai.OpenAI(api_key=settings.llm_api_key)

        response = client.audio.speech.create(
            model=settings.tts_model,
            voice=settings.tts_voice,
            input=text,
            response_format="mp3",
        )

        audio_bytes = response.content
        if not audio_bytes:
            logger.warning("TTS returned empty audio content.")
            return None

        audio_base64 = base64.b64encode(audio_bytes).decode("ascii")
        logger.info(
            "TTS synthesis succeeded. Model: %s, voice: %s, audio size: %d bytes",
            settings.tts_model,
            settings.tts_voice,
            len(audio_bytes),
        )
        return audio_base64

    except Exception as exc:  # noqa: BLE001
        logger.warning("TTS synthesis failed (graceful degradation): %s", exc)
        if raise_on_failure:
            from app.utils.exceptions import VoiceServiceUnavailableError
            raise VoiceServiceUnavailableError(f"TTS synthesis failed: {exc}") from exc
        return None
