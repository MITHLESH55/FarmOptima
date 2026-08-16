"""
AIInteraction — audit table for every AI assistant interaction.

Every call to answer_farm_question() persists exactly one row here.
This table is the reproducibility evidence for the project report /
patent documentation: "here are N real interactions, here's the exact
recommendation context each was grounded against, here's whether the
grounding check passed."

Design mirrors the existing Recommendation model:
  - recommendation_id FK makes every interaction traceable to the exact
    recommendation run (and thus to the exact environmental data) it was
    grounded against.
  - grounding_passed (bool) is the auditable outcome of the deterministic
    grounding check — a non-LLM, testable claim.
  - grounded_fields_used (JSON list) records which context fields the
    answer drew from, for field-level audit.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from app.database import Base


class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id = Column(Integer, primary_key=True, index=True)

    # FK to recommendations — nullable because in theory the service
    # could be called with a context not yet persisted (e.g. in unit tests).
    # In production use via the API this will always be set.
    recommendation_id = Column(
        Integer,
        ForeignKey("recommendations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # The exact question asked (stored for audit / reproducibility)
    question = Column(Text, nullable=False)

    # The answer returned to the caller (post-grounding-check)
    answer = Column(Text, nullable=False)

    # JSON list of context field names identified as referenced in the answer
    grounded_fields_used = Column(JSON, nullable=False, default=list)

    # True iff validate_answer_is_grounded() returned passed=True
    # (or the safe fallback was used when it returned False)
    grounding_passed = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
