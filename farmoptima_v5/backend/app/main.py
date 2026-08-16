"""
FarmOptima backend — application entry point.

This file is deliberately thin: it wires together configuration, the
database, logging, error handling, and the API routes. All real logic
lives in services/ (data retrieval), core/ (MCDM + GPO algorithms), and
api/routes/ (thin HTTP handlers). This is the "solid foundation" layering
from the roadmap — every new feature (a new data source, a new algorithm)
gets its own file in the matching layer rather than growing main.py.

Run:
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Then open http://localhost:8000/docs for interactive Swagger docs.
"""

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.utils.logging_config import configure_logging
from app.utils.exceptions import FarmOptimaError
from app.utils.responses import error_response
from app.utils.rate_limit import limiter
from app.database import init_db
from app.api.router import api_router

configure_logging()
logger = logging.getLogger("farmoptima")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized. FarmOptima API v%s ready.", app.version)
    yield


app = FastAPI(
    title="FarmOptima API",
    description="AI-powered smart crop decision support — layered architecture, real MCDM + GPO pipeline",
    version="0.3.0-phase1-layered",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Standardized error handling: every error, regardless of source, comes
# back in the same {"success": false, "error": {...}} shape. ---

@app.exception_handler(RateLimitExceeded)
def handle_rate_limit_error(request: Request, exc: RateLimitExceeded):
    return error_response(429, "rate_limit_exceeded", f"Rate limit exceeded: {exc.detail}")


@app.exception_handler(FarmOptimaError)
def handle_app_error(request: Request, exc: FarmOptimaError):
    logger.warning("Handled application error: %s (%s)", exc.message, exc.error_code)
    return error_response(exc.status_code, exc.error_code, exc.message)


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError):
    return error_response(422, "validation_error", str(exc.errors()))


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return error_response(500, "internal_error", "An unexpected error occurred.")


@app.get("/")
def root():
    return {"status": "ok", "service": "FarmOptima API", "version": app.version}


app.include_router(api_router, prefix="/api")
