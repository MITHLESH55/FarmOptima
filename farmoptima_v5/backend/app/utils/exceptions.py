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
