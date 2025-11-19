from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_files():
    """Get environment files in priority order for PydanticSettings.

    NOTE: PydanticSettings v2.12.0 seems to have reversed priority behavior
    compared to documentation. The first file in the list gets LOWEST priority,
    not HIGHEST priority as documented. So we reverse the order to work around this.

    Intended priority: .env.local (highest) > .env > environment variables
    Actual behavior: .env (highest) > .env.local > environment variables
    """
    # Workaround: Put .env first so it gets overridden by .env.local (backwards but works)
    env_files = []

    import os

    # Check for .env first (will be overridden by .env.local due to PydanticSettings bug)
    if os.path.exists(".env"):
        env_files.append(".env")

    # Then .env.local (will take priority due to reversed behavior)
    if os.path.exists(".env.local"):
        env_files.append(".env.local")

    return env_files if env_files else None


class LLMSettings(BaseSettings):
    """
    Loads LLM_* environment variables:
      - LLM_MODEL
      - LLM_API_KEY
      - LLM_BASE_URL (optional)

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
    )

    model: str = "anthropic/claude-sonnet-4-5-20250929"
    api_key: str
    base_url: Optional[str] = None


class DatabaseSettings(BaseSettings):
    """
    Database configuration settings.

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = "postgresql://postgres:postgres@localhost:15432/app_db"


class RedisSettings(BaseSettings):
    """
    Redis configuration settings.

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = "redis://localhost:16379"


def load_llm_settings() -> LLMSettings:
    return LLMSettings()


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


def load_redis_settings() -> RedisSettings:
    return RedisSettings()


