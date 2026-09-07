"""
LLM client — thin wrapper around one configurable LLM API call.

Design contract (matches existing services like weather_service.py):
  - Reads all credentials from `settings` (pydantic-settings), never from
    hardcoded values or local constants.
  - On *any* failure (network, auth, rate limit, malformed response) raises
    AIServiceUnavailableError (HTTP 502) — exactly as weather_service and
    satellite_service raise UpstreamDataError for their upstream failures.
  - There is NO mock / fallback return value.  If the LLM is unavailable
    the caller learns about it explicitly and immediately.

Provider note:
  The default provider is OpenAI (gpt-4o-mini).  The `llm_provider` config
  field is reserved for future providers (e.g. Google Gemini in step 2.2).
  In this step only "openai" is implemented; other values raise
  AIServiceUnavailableError with a helpful message.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.utils.exceptions import AIServiceUnavailableError

logger = logging.getLogger(__name__)


def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Send a system prompt + user message to the configured LLM and return
    the response text.

    Parameters
    ----------
    system_prompt:
        The grounding-context prompt produced by build_grounding_prompt().
    user_message:
        The farmer's question (or a correction instruction on retry).

    Returns
    -------
    str
        The model's raw text response.

    Raises
    ------
    AIServiceUnavailableError
        On any failure: missing API key, network error, rate-limit, bad
        response structure, or unsupported provider.  The message includes
        enough detail for the caller to log and act on.
    """
    provider = (settings.llm_provider or "groq").lower().strip()

    if provider in {"openai", "groq"}:
        return _call_provider(system_prompt, user_message, provider)

    raise AIServiceUnavailableError(
        f"LLM provider '{provider}' is not supported in this release. "
        "Set LLM_PROVIDER=groq or LLM_PROVIDER=openai in .env."
    )


def _call_provider(system_prompt: str, user_message: str, provider: str) -> str:
    """Call the configured, OpenAI-compatible provider endpoint."""
    if not settings.llm_configured:
        raise AIServiceUnavailableError(
            "LLM_API_KEY is not set or still contains a placeholder value. "
            "Add a real provider key to .env before using the AI assistant."
        )

    default_base_url = "https://api.groq.com/openai/v1" if provider == "groq" else None
    base_url = (settings.llm_base_url or default_base_url).strip() if (settings.llm_base_url or default_base_url) else None

    try:
        import openai  # noqa: PLC0415

        client = openai.OpenAI(api_key=settings.llm_api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        answer = response.choices[0].message.content
        if not answer:
            raise AIServiceUnavailableError(
                f"{provider.upper()} returned an empty response. The model may have refused "
                "to answer or the response was truncated."
            )
        logger.info(
            "LLM call succeeded via %s. Model: %s, prompt_tokens: %s, completion_tokens: %s",
            provider.upper(),
            settings.llm_model,
            response.usage.prompt_tokens if response.usage else "?",
            response.usage.completion_tokens if response.usage else "?",
        )
        return answer

    except AIServiceUnavailableError:
        raise

    except Exception as exc:  # noqa: BLE001
        logger.error("%s API call failed: %s", provider.upper(), exc)
        raise AIServiceUnavailableError(
            f"{provider.upper()} API call failed: {exc}. "
            "Check LLM_API_KEY, LLM_MODEL, and network connectivity."
        ) from exc
