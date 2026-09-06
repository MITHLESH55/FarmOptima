"""
Speech-to-Text (STT) client — Phase 2.4 Voice.

Thin provider abstraction for audio transcription.
Isolates audio format validation and OpenAI Whisper API calls from the route
and AI orchestration layers.
"""

from __future__ import annotations

import logging
import os

from app.config import settings
from app.utils.exceptions import (
    InvalidAudioError,
    EmptyTranscriptError,
    VoiceServiceUnavailableError,
)

logger = logging.getLogger(__name__)

# Explicit whitelist of audio extensions supported by Whisper
ALLOWED_EXTENSIONS = {
    ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".flac", ".ogg", ".oga"
}

# Explicit whitelist of MIME types accepted from HTTP uploads
ALLOWED_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/webm",
    "video/webm",  # Browser MediaRecorder commonly tags webm audio as video/webm
    "audio/ogg",
    "application/ogg",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
    "audio/flac",
    "audio/x-flac",
    "audio/aac",
    "application/octet-stream",  # Fallback when client doesn't set Content-Type
}


def validate_audio_payload(
    audio_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> None:
    """
    Validate uploaded audio bytes for size, non-emptiness, and supported format.

    Raises
    ------
    InvalidAudioError
        If audio is empty, oversized, or has an unsupported format.
    """
    if not audio_bytes or len(audio_bytes) == 0:
        raise InvalidAudioError("Audio payload is empty. Please provide recorded audio.")

    if len(audio_bytes) > settings.voice_max_audio_size_bytes:
        max_mb = settings.voice_max_audio_size_bytes // (1024 * 1024)
        raise InvalidAudioError(
            f"Audio file exceeds maximum allowed size of {max_mb} MB."
        )

    # Check extension if filename is present
    ext_valid = False
    if filename:
        _, ext = os.path.splitext(filename.lower())
        if ext in ALLOWED_EXTENSIONS:
            ext_valid = True

    # Check MIME content type if present
    mime_valid = False
    if content_type:
        clean_mime = content_type.lower().split(";")[0].strip()
        if clean_mime in ALLOWED_MIME_TYPES:
            mime_valid = True

    # If neither format indicator is valid, reject the file
    if not ext_valid and not mime_valid:
        raise InvalidAudioError(
            f"Unsupported audio format (filename='{filename}', content_type='{content_type}'). "
            "Supported formats: MP3, WAV, WEBM, M4A, OGG, FLAC."
        )


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    content_type: str | None = None,
) -> str:
    """
    Transcribe audio bytes to text using the configured STT provider (OpenAI Whisper).

    Parameters
    ----------
    audio_bytes:
        Raw audio file bytes.
    filename:
        Original or synthetic filename (extension aids format detection).
    content_type:
        MIME type from client upload.

    Returns
    -------
    str
        Cleaned, normalized transcription string.

    Raises
    ------
    InvalidAudioError
        If audio payload fails validation.
    EmptyTranscriptError
        If transcription result is empty or inaudible.
    VoiceServiceUnavailableError
        If LLM/STT provider is unconfigured or unreachable.
    """
    validate_audio_payload(audio_bytes, filename=filename, content_type=content_type)

    if not settings.llm_api_key:
        raise VoiceServiceUnavailableError(
            "LLM_API_KEY is not configured for voice transcription. "
            "Set LLM_API_KEY in .env."
        )

    try:
        import openai  # noqa: PLC0415

        client = openai.OpenAI(api_key=settings.llm_api_key)

        file_tuple = (filename or "audio.webm", audio_bytes, content_type or "audio/webm")

        response = client.audio.transcriptions.create(
            model=settings.stt_model,
            file=file_tuple,
        )

        transcript = (response.text or "").strip()
        if not transcript:
            raise EmptyTranscriptError(
                "Speech-to-text transcription was empty or inaudible. "
                "Please speak clearly and try again."
            )

        logger.info(
            "STT transcription succeeded. Model: %s, transcript length: %d chars",
            settings.stt_model,
            len(transcript),
        )
        return transcript

    except (InvalidAudioError, EmptyTranscriptError, VoiceServiceUnavailableError):
        raise

    except Exception as exc:  # noqa: BLE001
        logger.error("STT provider transcription failed: %s", exc)
        raise VoiceServiceUnavailableError(
            f"Speech-to-text provider failed: {exc}. "
            "Check LLM_API_KEY and network connectivity."
        ) from exc
