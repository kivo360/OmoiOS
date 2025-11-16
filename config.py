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

    model: str = "anthropic/claude-sonnet-4-5-20250929"
    api_key: str
    base_url: Optional[str] = None


def load_llm_settings() -> LLMSettings:
    return LLMSettings()


