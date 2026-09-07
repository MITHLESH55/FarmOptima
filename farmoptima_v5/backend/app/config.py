"""
Application configuration, loaded from environment variables / a .env file.
See .env.example for the full list of supported settings.
"""

from datetime import date, timedelta
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    _PLACEHOLDER_VALUES = (
        "placeholder",
        "your_api_key_here",
        "your_openai_api_key_here",
        "sk-your_actual_api_key_here",
        "changeme",
        "example",
    )

    # Google Earth Engine
    gee_project: str | None = None

    # Derived: satellite imagery lookback window (last 60 days by default)
    @property
    def satellite_lookback_start(self) -> str:
        return (date.today() - timedelta(days=60)).strftime("%Y-%m-%d")

    @property
    def satellite_lookback_end(self) -> str:
        return date.today().strftime("%Y-%m-%d")

    # OpenWeather (optional supplement — not required for core pipeline)
    openweather_api_key: str | None = None

    # Auth — change SECRET_KEY in .env for any real deployment; this default
    # is fine only for local development.
    secret_key: str = "dev-only-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Rate limiting
    recommend_rate_limit: str = "20/minute"

    # Database — SQLite by default; set to a postgres:// URL in .env to switch
    database_url: str = "sqlite:///./farmoptima.db"

    # GPO tuning defaults (can be overridden per-request in future phases)
    gpo_population_size: int = 40
    gpo_generations: int = 60

    # ---------------------------------------------------------------------------
    # AI assistant (Phase 2 Step 2.1)
    # ---------------------------------------------------------------------------

    # Which LLM provider to use.  FarmOptima supports both the legacy
    # OpenAI-compatible path and the Groq-compatible path while keeping the
    # application config provider-neutral.
    llm_provider: str = "groq"

    # Provider-neutral API key.  This is the secret used by the selected
    # backend transport.  It remains named LLM_API_KEY to avoid breaking the
    # existing configuration architecture.
    llm_api_key: str | None = None

    # Model name to use.  Groq decommissioned llama-3.3-70b-versatile on
    # 2026-08-16.  The default is now openai/gpt-oss-120b, which is the
    # current general-purpose model available on the Groq API.
    # To override, set LLM_MODEL in your .env file.
    llm_model: str = "openai/gpt-oss-120b"

    # OpenAI-compatible base URL used by the provider transport.  Groq exposes
    # its chat completions API at https://api.groq.com/openai/v1.
    llm_base_url: str = "https://api.groq.com/openai/v1"

    @property
    def llm_configured(self) -> bool:
        """Return True only for a non-empty, non-placeholder API key."""
        value = (self.llm_api_key or "").strip()
        if not value:
            return False
        lowered = value.lower()
        return not any(token in lowered for token in self._PLACEHOLDER_VALUES)

    # Grounding strictness — MUST be True in any farmer-facing deployment.
    # If True: a failed grounding check triggers one correction attempt, then
    # a safe "not available" fallback if the correction also fails.
    # If False: log a WARNING but return the model's answer anyway (useful
    # only for local debugging; DO NOT set False in production).
    ai_grounding_strict: bool = True

    # ---------------------------------------------------------------------------
    # Voice assistant (Phase 2 Step 2.4)
    # ---------------------------------------------------------------------------
    # Speech-to-Text model name (OpenAI Whisper)
    stt_model: str = "whisper-1"

    # Text-to-Speech model and voice (OpenAI TTS)
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"

    # Maximum audio upload size (bytes) — 25MB matches OpenAI Whisper maximum
    voice_max_audio_size_bytes: int = 25 * 1024 * 1024


settings = Settings()
