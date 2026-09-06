"""
Custom exception types. Raising one of these anywhere in the service/route
layers gets automatically converted into the standard error response format
by the handler registered in main.py — routes never need to build error
JSON by hand.
"""


class FarmOptimaError(Exception):
    """Base class for all application-specific errors."""
    status_code = 500
    error_code = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidLocationError(FarmOptimaError):
    status_code = 400
    error_code = "invalid_location"


class UpstreamDataError(FarmOptimaError):
    """Raised when a live data source fails AND no mock fallback is possible."""
    status_code = 502
    error_code = "upstream_data_error"


class NotFoundError(FarmOptimaError):
    status_code = 404
    error_code = "not_found"


class AIServiceUnavailableError(FarmOptimaError):
    """Raised when the configured LLM API is unreachable or returns an error.

    Analogous to UpstreamDataError for weather/soil/satellite services.
    HTTP 502 signals to the caller that the problem is with an upstream
    dependency, not with the request itself.
    """
    status_code = 502
    error_code = "ai_service_unavailable"


class RecommendationNotFoundError(NotFoundError):
    """Raised by context_loader when the requested recommendation_id does not
    exist in the database.

    Subclasses NotFoundError (404) rather than FarmOptimaError directly so
    that a route handler can catch either the broad or the specific type,
    and so the error_code is distinct enough for the client to identify
    that it was specifically the recommendation lookup that failed (not a
    generic "thing not found").
    """
    status_code = 404
    error_code = "recommendation_not_found"


class InvalidAudioError(FarmOptimaError):
    """Raised when uploaded audio is empty, corrupt, unsupported, or exceeds size limits."""
    status_code = 400
    error_code = "invalid_audio"


class EmptyTranscriptError(FarmOptimaError):
    """Raised when STT speech-to-text produces an empty or inaudible transcription."""
    status_code = 400
    error_code = "empty_transcript"


class VoiceServiceUnavailableError(AIServiceUnavailableError):
    """Raised when STT or TTS voice services fail or are unconfigured."""
    status_code = 502
    error_code = "voice_service_unavailable"

