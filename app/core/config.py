"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Type-safe application settings loaded from environment variables."""

    DATABASE_URL: str
    ECB_BASE_URL: str = "https://data-api.ecb.europa.eu/service/data/EXR"
    ECB_REQUEST_TIMEOUT: int = 30
    ECB_RETRY_ATTEMPTS: int = 3
    DEFAULT_CURRENCIES: list[str] = []
    LOG_LEVEL: str = "INFO"
    APP_ENV: Literal["development", "staging", "production"] = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("DEFAULT_CURRENCIES", mode="before")
    @classmethod
    def parse_currencies(cls, value: object) -> list[str]:
        """Parse comma-separated currency list from environment."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [code.strip().upper() for code in value.split(",") if code.strip()]
        if isinstance(value, list):
            return [str(code).strip().upper() for code in value if str(code).strip()]
        return []


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
