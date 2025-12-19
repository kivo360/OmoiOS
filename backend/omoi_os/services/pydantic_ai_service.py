"""Centralized PydanticAI service using Fireworks.ai backend."""

from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from omoi_os.config import LLMSettings, load_llm_settings


class PydanticAIService:
    """Central service for PydanticAI using Fireworks.ai.

    Provides a unified interface for creating PydanticAI agents with structured outputs.
    Uses Fireworks.ai as the LLM provider.
    """

    def __init__(self, settings: Optional[LLMSettings] = None):
        """
        Initialize PydanticAI service.

        Args:
            settings: Optional LLM settings (defaults to loading from environment)
        """
        self.settings = settings or load_llm_settings()
        self.model_string = self._get_fireworks_model()

        # Get API key - prefer dedicated Fireworks key, fallback to general LLM key
        api_key = self.settings.fireworks_api_key or self.settings.api_key
        if not api_key:
            raise ValueError(
                "fireworks_api_key or LLM api_key must be set to use PydanticAI service"
            )

        # Create Fireworks provider
        self.provider = OpenAIProvider(
            api_key=api_key,
            base_url="https://api.fireworks.ai/inference/v1",
        )

        # Create model settings with JSON mode enabled for better structured output support
        self.model_settings = OpenAIChatModelSettings()

    def _get_fireworks_model(self) -> str:
        """
        Get Fireworks model name from settings.

        Defaults to minimax-m2 if not specified.

        Returns:
            Fireworks model string (e.g., "accounts/fireworks/models/minimax-m2")
        """
        # If model is already a Fireworks model, use it
        if (
            "fireworks" in self.settings.model.lower()
            or "accounts/fireworks" in self.settings.model
        ):
            return self.settings.model

        # Default to GPT-OSS-120B (cost-effective alternative to kimi-k2)
        return "accounts/fireworks/models/gpt-oss-120b"

    def create_agent(
        self,
        output_type: type,
        system_prompt: Optional[str] = None,
        output_retries: int = 5,
    ) -> Agent:
        """
        Create a PydanticAI agent with structured output.

        Args:
            output_type: Pydantic model class for structured output
            system_prompt: Optional system prompt to customize agent behavior
            output_retries: Number of retries for structured output validation (default: 3)

        Returns:
            Configured PydanticAI Agent instance
        """
        # Create model with Fireworks provider
        model = OpenAIChatModel(
            self.model_string,
            provider=self.provider,
            settings=self.model_settings,
        )
        # Only pass system_prompt if provided
        agent_kwargs = {
            "model": model,
            "output_type": output_type,
            "output_retries": output_retries,
        }
        if system_prompt:
            agent_kwargs["system_prompt"] = system_prompt
        return Agent(**agent_kwargs)
