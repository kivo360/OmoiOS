"""Simple LLM service for text completion and structured outputs.

This service provides a unified interface for calling LLMs:
- Simple text completion
- Structured outputs (using Pydantic models)

Note: This does NOT handle workspace execution - that's handled separately
by AgentExecutor when needed.
"""

import asyncio
import random
from typing import Optional, TypeVar

from omoi_os.config import LLMSettings, load_llm_settings
from omoi_os.logging import get_logger
from omoi_os.services.pydantic_ai_service import PydanticAIService

logger = get_logger(__name__)

T = TypeVar("T")

# HTTP status codes that are retryable (transient errors)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMService:
    """Simple service for LLM text completion and structured outputs.

    Use this for:
    - Memory operations
    - Analysis tasks
    - Classification
    - Any LLM call that doesn't need workspace execution
    """

    def __init__(self, settings: Optional[LLMSettings] = None):
        """
        Initialize LLM service.

        Args:
            settings: Optional LLM settings (defaults to loading from environment)
        """
        self.settings = settings or load_llm_settings()

        # Initialize PydanticAI service for structured outputs
        self._pydantic_ai_service: Optional[PydanticAIService] = None

    @property
    def _pydantic_ai(self) -> PydanticAIService:
        """Get or create PydanticAI service instance."""
        if self._pydantic_ai_service is None:
            self._pydantic_ai_service = PydanticAIService(settings=self.settings)
        return self._pydantic_ai_service

    async def complete(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        """
        Simple text completion - just get text back from the LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional arguments (ignored for now)

        Returns:
            Text response from the LLM

        Example:
            >>> llm = get_llm_service()
            >>> result = await llm.complete("What is the capital of France?")
            >>> print(result)  # "The capital of France is Paris."
        """
        from pydantic_ai import Agent
        from pydantic_ai.models.openai import OpenAIChatModel

        # Use PydanticAI for simple completion
        model = OpenAIChatModel(
            self._pydantic_ai.model_string,
            provider=self._pydantic_ai.provider,
            settings=self._pydantic_ai.model_settings,
        )
        # Only pass system_prompt if provided
        agent_kwargs = {"model": model}
        if system_prompt:
            agent_kwargs["system_prompt"] = system_prompt
        agent = Agent(**agent_kwargs)
        result = await agent.run(prompt)
        return result.output

    async def structured_output(
        self,
        prompt: str,
        output_type: type[T],
        system_prompt: Optional[str] = None,
        output_retries: int = 5,
        http_retries: int = 3,
        **kwargs,
    ) -> T:
        """
        Get structured output matching a Pydantic model.

        Includes automatic retry with exponential backoff for transient HTTP errors
        (503, 429, etc.) that can occur with LLM providers like Fireworks.

        Args:
            prompt: User prompt
            output_type: Pydantic model class for structured output
            system_prompt: Optional system prompt
            output_retries: Number of retries for structured output validation
            http_retries: Number of retries for transient HTTP errors (503, 429, etc.)
            **kwargs: Additional arguments (ignored for now)

        Returns:
            Instance of output_type with structured data

        Example:
            >>> from pydantic import BaseModel
            >>> class Analysis(BaseModel):
            ...     sentiment: str
            ...     confidence: float
            >>> llm = get_llm_service()
            >>> result = await llm.structured_output(
            ...     "Analyze: I love this!",
            ...     output_type=Analysis
            ... )
            >>> print(result.sentiment)  # "positive"
        """
        agent = self._pydantic_ai.create_agent(
            output_type=output_type,
            system_prompt=system_prompt,
            output_retries=output_retries,
        )

        last_error = None
        for attempt in range(http_retries + 1):
            try:
                result = await agent.run(prompt)
                return result.output
            except Exception as e:
                error_str = str(e).lower()
                # Check if this is a retryable HTTP error
                is_retryable = any(
                    indicator in error_str
                    for indicator in [
                        "503",
                        "502",
                        "500",
                        "504",
                        "429",
                        "service unavailable",
                        "bad gateway",
                        "gateway timeout",
                        "rate limit",
                        "too many requests",
                    ]
                )

                if is_retryable and attempt < http_retries:
                    # Exponential backoff with jitter: 1s, 2s, 4s + random jitter
                    base_delay = 2**attempt
                    jitter = random.uniform(0, 0.5 * base_delay)
                    delay = base_delay + jitter
                    logger.warning(
                        f"LLM HTTP error (attempt {attempt + 1}/{http_retries + 1}), "
                        f"retrying in {delay:.1f}s",
                        extra={
                            "error": str(e)[:200],
                            "attempt": attempt + 1,
                            "max_attempts": http_retries + 1,
                            "delay_seconds": delay,
                        },
                    )
                    await asyncio.sleep(delay)
                    last_error = e
                else:
                    # Not retryable or exhausted retries
                    raise

        # Should not reach here, but if we do, raise the last error
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected state in structured_output retry loop")


# Global singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service(settings: Optional[LLMSettings] = None) -> LLMService:
    """
    Get the global LLM service instance (singleton pattern).

    This is the main way to get an LLM service anywhere in the codebase.
    Just call this function and use the returned service.

    Args:
        settings: Optional LLM settings (only used on first call)

    Returns:
        LLMService instance

    Example:
        >>> from omoi_os.services.llm_service import get_llm_service
        >>> llm = get_llm_service()
        >>> result = await llm.complete("Hello!")
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(settings=settings)
    return _llm_service


def reset_llm_service():
    """Reset the global LLM service instance (useful for testing)."""
    global _llm_service
    _llm_service = None
