"""Typed application settings loaded from the environment."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, sourced from environment variables or a .env file.

    The .env file lives at the repository root; the second path covers commands
    run from inside backend/ (alembic, pytest).
    """

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    environment: str = "development"
    database_url: str
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    # call-arg: required fields (database_url) are populated from the environment/.env
    return Settings()  # type: ignore[call-arg]
