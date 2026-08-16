"""
context_loader — loads a persisted recommendation from the database and
turns it into a FarmContext ready for AI grounding.

Design principles (critical for patent/report documentation):

1. REAL STORED OUTPUT — the context is built from full_result, which is
   the exact JSON that was returned to the API client at recommendation
   time (see recommend.py line: full_result=response.model_dump()).
   We do NOT re-query MCDM/NSGA-II, re-fetch weather/soil/satellite, or
   re-run any algorithm. The grounding context is byte-for-byte the same
   data the farmer already saw.

2. ROUND-TRIP INTEGRITY — validating full_result back through
   RecommendationResponse.model_validate() proves the stored JSON is
   schema-conformant. If the schema and the stored data ever diverge (e.g.
   a migration added a required field), this raises a clear Pydantic
   ValidationError rather than silently producing a malformed context.

3. EXPLICIT NOT-FOUND — if the id does not exist in the database,
   RecommendationNotFoundError (404) is raised immediately. The caller
   never receives None or an empty context.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.schemas.recommendation import RecommendationResponse
from app.schemas.ai import FarmContext
from app.services.ai.context_builder import build_farm_context
from app.utils.exceptions import RecommendationNotFoundError

logger = logging.getLogger(__name__)


def get_context_for_recommendation(
    recommendation_id: int,
    db: Session,
) -> FarmContext:
    """
    Load a persisted recommendation from the database and build a FarmContext.

    Parameters
    ----------
    recommendation_id:
        The primary-key id returned by a previous /api/recommend call.
    db:
        An active SQLAlchemy session.

    Returns
    -------
    FarmContext
        Ready to pass directly to answer_farm_question() or
        build_grounding_prompt() — grounded against the EXACT data the
        farmer already received.

    Raises
    ------
    RecommendationNotFoundError
        If no Recommendation row with the given id exists.  Status 404,
        error_code "recommendation_not_found".
    pydantic.ValidationError
        If the stored full_result JSON fails RecommendationResponse schema
        validation (indicates a data-integrity or migration issue — should
        be surfaced, not swallowed).
    """
    record: Recommendation | None = db.get(Recommendation, recommendation_id)

    if record is None:
        raise RecommendationNotFoundError(
            f"Recommendation id={recommendation_id} was not found. "
            "Ensure the id was returned by a previous /api/recommend call."
        )

    if record.full_result is None:
        # Defensive guard: full_result should always be set by recommend.py,
        # but if an old/partial record exists without it we raise clearly.
        raise RecommendationNotFoundError(
            f"Recommendation id={recommendation_id} exists but has no stored "
            "full_result JSON. This record cannot be used for AI grounding."
        )

    # Validate the stored JSON back through the Pydantic schema — this is
    # the round-trip integrity proof: same schema, same data, same object.
    rec_response = RecommendationResponse.model_validate(record.full_result)

    # The id column is separate from full_result (it was set after the JSON
    # was written — see recommend.py: response.id = record.id, AFTER commit).
    # Restore it so FarmContext.recommendation_id is the real DB id.
    rec_response.id = record.id

    logger.debug(
        "Loaded recommendation id=%s from DB; top_crop=%s, "
        "ahp_cr=%.4f, crops=%s",
        recommendation_id,
        record.top_crop,
        record.ahp_consistency_ratio or 0.0,
        [cs.crop for cs in rec_response.crop_ranking],
    )

    return build_farm_context(rec_response)
