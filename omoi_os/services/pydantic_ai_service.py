"""Centralized PydanticAI service using LiteLLM backend."""

from typing import Optional

from pydantic_ai import Agent
from pydantic_ai_litellm import LiteLLMModel

from omoi_os.config import LLMSettings, load_llm_settings


class PydanticAIService:
    """Central service for PydanticAI with LiteLLM backend.
    
    Provides a unified interface for creating PydanticAI agents with structured outputs.
    Uses LiteLLM to support multiple LLM providers through a single interface.
    """

    def __init__(self, settings: Optional[LLMSettings] = None):
        """
        Initialize PydanticAI service.

        Args:
            settings: Optional LLM settings (defaults to loading from environment)
        """
        self.settings = settings or load_llm_settings()
        model_name = self._map_model_name(self.settings.model)
        
        # Initialize LiteLLM model
        self.model = LiteLLMModel(
            model_name=model_name,
            api_key=self.settings.api_key,
            base_url=self.settings.base_url,
        )

    def _map_model_name(self, model: str) -> str:
        """
        Map OpenHands model names to LiteLLM format.

        Args:
            model: Model name (e.g., "openhands/claude-sonnet-4-5-20250929")

        Returns:
            LiteLLM-compatible model name (e.g., "anthropic/claude-sonnet-4-5-20250929")
        """
        if model.startswith("openhands/"):
            # Map openhands/* to anthropic/* for LiteLLM
            return model.replace("openhands/", "anthropic/")
        return model

    def create_agent(
        self,
        output_type: type,
        system_prompt: Optional[str] = None,
    ) -> Agent:
        """
        Create a PydanticAI agent with structured output.

        Args:
            output_type: Pydantic model class for structured output
            system_prompt: Optional system prompt to customize agent behavior

        Returns:
            Configured PydanticAI Agent instance
        """
        return Agent(
            model=self.model,
            output_type=output_type,
            system_prompt=system_prompt,
        )

