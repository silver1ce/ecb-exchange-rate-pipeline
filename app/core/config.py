"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Type-safe application settings loaded from environment variables."""

    DATABASE_URL: str
    ECB_BASE_URL: str = "https://data-api.ecb.europa.eu/service/data/EXR"
    ECB_REQUEST_TIMEOUT: int = 30
    ECB_RETRY_ATTEMPTS: int = 3
    DEFAULT_CURRENCIES: str = Field(
        default="",
        description="Comma-separated ISO codes; empty means all currencies",
    )
    LOG_LEVEL: str = "INFO"
    APP_ENV: Literal["development", "staging", "production"] = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def currency_codes(self) -> list[str]:
        """Return parsed currency filter list."""
        if not self.DEFAULT_CURRENCIES.strip():
            return []
        return [
            code.strip().upper()
            for code in self.DEFAULT_CURRENCIES.split(",")
            if code.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
