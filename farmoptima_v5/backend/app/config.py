"""
Application configuration, loaded from environment variables / a .env file.
See .env.example for the full list of supported settings.
"""

from datetime import date, timedelta
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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


settings = Settings()
