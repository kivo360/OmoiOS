"""Centralized PydanticAI service using infer_model backend."""

import os
from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.models import infer_model

from omoi_os.config import LLMSettings, load_llm_settings


class PydanticAIService:
    """Central service for PydanticAI using model inference.
    
    Provides a unified interface for creating PydanticAI agents with structured outputs.
    Uses PydanticAI's infer_model to support multiple LLM providers.
    """

    def __init__(self, settings: Optional[LLMSettings] = None):
        """
        Initialize PydanticAI service.

        Args:
            settings: Optional LLM settings (defaults to loading from environment)
        """
        self.settings = settings or load_llm_settings()
        self.model_string = self._map_model_name(self.settings.model)
        
        # Ensure API key is set in environment if provided
        if self.settings.api_key:
            # Map LLM_API_KEY to appropriate provider key
            if "anthropic" in self.model_string.lower():
                if not os.getenv("ANTHROPIC_API_KEY"):
                    os.environ["ANTHROPIC_API_KEY"] = self.settings.api_key

    def _map_model_name(self, model: str) -> str:
        """
        Map OpenHands model names to PydanticAI format.
        
        Supports gateway format: gateway/anthropic:claude-sonnet-4-5
        which gets converted to: anthropic:claude-sonnet-4-5

        Args:
            model: Model name (e.g., "openhands/claude-sonnet-4-5-20250929" or "gateway/anthropic:claude-sonnet-4-5")

        Returns:
            PydanticAI-compatible model string (e.g., "anthropic:claude-sonnet-4-5-20250929")
        """
        # Handle gateway format - strip gateway/ prefix
        if model.startswith("gateway/"):
            # gateway/anthropic:claude-sonnet-4-5 -> anthropic:claude-sonnet-4-5
            return model.replace("gateway/", "")
        
        if model.startswith("openhands/"):
            # Map openhands/claude-sonnet-4-5-20250929 -> anthropic:claude-sonnet-4-5-20250929
            model_name = model.replace("openhands/", "")
            return f"anthropic:{model_name}"
        elif model.startswith("anthropic/"):
            # Map anthropic/claude-sonnet-4-5-20250929 -> anthropic:claude-sonnet-4-5-20250929
            model_name = model.replace("anthropic/", "")
            return f"anthropic:{model_name}"
        elif ":" in model:
            # Already in correct format (e.g., "anthropic:claude-sonnet-4-5")
            return model
        else:
            # Default to anthropic
            return f"anthropic:{model}"

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
        # Use infer_model to get the correct model instance
        model = infer_model(self.model_string)
        return Agent(
            model,
            output_type=output_type,
            system_prompt=system_prompt,
        )
