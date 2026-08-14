"""
Standard response formatting.

Design decision: successful responses use FastAPI's typed `response_model`
directly (better OpenAPI/Swagger docs, real validation) rather than being
wrapped in a generic envelope — wrapping would hide the actual schema from
`/docs`. Errors, however, ALWAYS come back in this one consistent shape,
regardless of where they were raised, so client code only needs to handle
one error format:

    {
      "success": false,
      "error": {"code": "invalid_location", "message": "..."}
    }
"""

from fastapi.responses import JSONResponse


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )
