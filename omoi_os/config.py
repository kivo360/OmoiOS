"""Configuration settings for OmoiOS"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """
    Loads LLM_* environment variables:
      - LLM_MODEL
      - LLM_API_KEY
      - LLM_BASE_URL (optional)
    """

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=(".env",),
        env_file_encoding="utf-8",
    )

    model: str = "openhands/claude-sonnet-4-5-20250929"
    api_key: str
    base_url: Optional[str] = None


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=(".env",),
        env_file_encoding="utf-8",
    )

    url: str = "postgresql+psycopg://postgres:postgres@localhost:15432/app_db"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=(".env",),
        env_file_encoding="utf-8",
    )

    url: str = "redis://localhost:16379"


def load_llm_settings() -> LLMSettings:
    return LLMSettings()


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


def load_redis_settings() -> RedisSettings:
    return RedisSettings()
