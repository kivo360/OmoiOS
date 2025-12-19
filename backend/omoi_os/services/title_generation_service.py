"""Title generation service using a lightweight LLM for task titles and descriptions."""

from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from omoi_os.config import (
    LLMSettings,
    TitleGenerationSettings,
    load_llm_settings,
    load_title_generation_settings,
)
from omoi_os.logging import get_logger

logger = get_logger(__name__)


class TaskTitleDescription(BaseModel):
    """Structured output for task title and description generation."""

    title: str = Field(
        ...,
        max_length=100,
        description="A concise, human-readable title for the task (max 100 chars)",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="A brief description of what the task does (optional, max 500 chars)",
    )


class TitleGenerationService:
    """Service for generating human-readable task titles using a lightweight LLM.

    Uses Fireworks.ai gpt-oss-20b model (or configured alternative) for
    cost-effective title generation. This is separate from the main analytics
    LLM to keep costs low.

    Configuration can be done via:
    - YAML: config/base.yaml -> title_generation section
    - Environment variables: TITLE_GEN_MODEL, TITLE_GEN_API_KEY, TITLE_GEN_BASE_URL
    """

    def __init__(
        self,
        settings: Optional[TitleGenerationSettings] = None,
        llm_settings: Optional[LLMSettings] = None,
    ):
        """
        Initialize title generation service.

        Args:
            settings: Optional title generation settings (defaults to loading from config)
            llm_settings: Optional LLM settings for API key fallback
        """
        self.settings = settings or load_title_generation_settings()
        self.llm_settings = llm_settings or load_llm_settings()
        self.model_name = self.settings.model

        # Get API key - priority order:
        # 1. Title generation specific key (TITLE_GEN_API_KEY)
        # 2. Fireworks API key from LLM settings (LLM_FIREWORKS_API_KEY)
        # 3. General LLM API key (LLM_API_KEY)
        api_key = (
            self.settings.api_key
            or self.llm_settings.fireworks_api_key
            or self.llm_settings.api_key
        )
        if not api_key:
            raise ValueError(
                "TITLE_GEN_API_KEY, LLM_FIREWORKS_API_KEY, or LLM_API_KEY must be set "
                "to use TitleGenerationService"
            )

        # Create provider with configured base URL
        self.provider = OpenAIProvider(
            api_key=api_key,
            base_url=self.settings.base_url,
        )

        # Create the model
        self.model = OpenAIChatModel(
            self.model_name,
            provider=self.provider,
        )

        logger.info(
            "TitleGenerationService initialized",
            model=self.model_name,
            base_url=self.settings.base_url,
        )

    async def generate_title_and_description(
        self,
        task_type: str,
        existing_description: Optional[str] = None,
        context: Optional[str] = None,
    ) -> TaskTitleDescription:
        """
        Generate a human-readable title and optionally a description for a task.

        If existing_description is provided and appears to be a detailed description,
        only a title will be generated from it. If no description exists or the
        existing description is just the task type, both title and description
        will be generated.

        Args:
            task_type: The task type (e.g., "analyze_requirements", "implement_feature")
            existing_description: Existing task description (if any)
            context: Additional context about the task (e.g., ticket info)

        Returns:
            TaskTitleDescription with generated title and optional description
        """
        # Determine if we need to generate a description
        has_meaningful_description = (
            existing_description
            and existing_description.strip()
            and existing_description.lower() != task_type.lower()
            and len(existing_description.strip()) > 20
        )

        if has_meaningful_description:
            # Only generate title from the description
            prompt = self._build_title_only_prompt(
                task_type, existing_description, context
            )
        else:
            # Generate both title and description
            prompt = self._build_full_prompt(task_type, existing_description, context)

        # Create agent with low temperature for consistent output
        agent: Agent[None, TaskTitleDescription] = Agent(
            model=self.model,
            output_type=TaskTitleDescription,
            system_prompt=(
                "You are a technical writer that creates concise, clear titles "
                "and descriptions for software development tasks. "
                "Titles should be action-oriented and descriptive. "
                "Use sentence case. Be specific but brief."
            ),
            output_retries=3,
        )

        try:
            result = await agent.run(prompt)
            generated = result.output

            # If we had a meaningful description, preserve it
            if has_meaningful_description:
                generated.description = existing_description

            logger.debug(
                "Generated title",
                task_type=task_type,
                title=generated.title,
                has_description=generated.description is not None,
            )

            return generated

        except Exception as e:
            logger.warning(
                "Failed to generate title, using fallback",
                error=str(e),
                task_type=task_type,
            )
            # Fallback: Create a simple title from the task type
            fallback_title = self._create_fallback_title(task_type)
            return TaskTitleDescription(
                title=fallback_title,
                description=existing_description,
            )

    def _build_title_only_prompt(
        self,
        task_type: str,
        description: Optional[str],
        context: Optional[str],
    ) -> str:
        """Build prompt for title-only generation."""
        parts = [
            f"Generate a concise title (max 100 chars) for this task:",
            f"Task type: {task_type}",
        ]
        if description:
            parts.append(f"Description: {description}")
        if context:
            parts.append(f"Context: {context}")
        parts.append(
            "Return only a title. Do not generate a description since one already exists."
        )
        return "\n".join(parts)

    def _build_full_prompt(
        self,
        task_type: str,
        description: Optional[str],
        context: Optional[str],
    ) -> str:
        """Build prompt for full title and description generation."""
        parts = [
            "Generate a concise title (max 100 chars) and brief description (max 500 chars) for this task:",
            f"Task type: {task_type}",
        ]
        if description:
            parts.append(f"Current description: {description}")
        if context:
            parts.append(f"Context: {context}")
        parts.append(
            "The title should be action-oriented (e.g., 'Implement user authentication flow'). "
            "The description should explain what the task accomplishes."
        )
        return "\n".join(parts)

    def _create_fallback_title(self, task_type: str) -> str:
        """Create a fallback title from the task type."""
        # Convert snake_case to Title Case
        words = task_type.replace("_", " ").replace("-", " ").split()
        return " ".join(word.capitalize() for word in words)

    async def generate_title(
        self,
        task_type: str,
        description: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        Convenience method to just get the title.

        Args:
            task_type: The task type
            description: Existing task description (if any)
            context: Additional context about the task

        Returns:
            Generated title string
        """
        result = await self.generate_title_and_description(
            task_type=task_type,
            existing_description=description,
            context=context,
        )
        return result.title


# Singleton instance (lazy initialization)
_title_service: Optional[TitleGenerationService] = None


def get_title_generation_service() -> TitleGenerationService:
    """Get the singleton title generation service instance."""
    global _title_service
    if _title_service is None:
        _title_service = TitleGenerationService()
    return _title_service
