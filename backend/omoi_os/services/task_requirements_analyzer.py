"""Task Requirements Analyzer Service.

Uses LLM structured output to analyze task descriptions and determine:
1. What type of work this task involves (exploration, implementation, validation)
2. Whether the task will produce code changes
3. What validation requirements are needed (commit, push, PR)

This replaces hardcoded task type mappings with intelligent analysis.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from omoi_os.logging import get_logger
from omoi_os.services.llm_service import LLMService, get_llm_service

logger = get_logger(__name__)


class ExecutionMode(str, Enum):
    """Execution mode determines sandbox behavior and skill loading."""

    EXPLORATION = "exploration"
    """Research, analysis, planning tasks. Creates specs/docs, not code."""

    IMPLEMENTATION = "implementation"
    """Code writing tasks. Creates/modifies source files."""

    VALIDATION = "validation"
    """Review and testing tasks. Verifies existing code."""


class TaskOutputType(str, Enum):
    """What type of output the task produces."""

    ANALYSIS = "analysis"
    """Research findings, answers to questions. No files created."""

    DOCUMENTATION = "documentation"
    """Markdown docs, specs, designs. May create .md files."""

    CODE = "code"
    """Source code changes. Creates/modifies code files."""

    TESTS = "tests"
    """Test files. Creates/modifies test code."""

    CONFIGURATION = "configuration"
    """Config files, environment setup."""

    MIXED = "mixed"
    """Combination of documentation and code."""


class TaskRequirements(BaseModel):
    """LLM-analyzed requirements for executing a task.

    This model is populated by the LLM analyzing the task description
    to determine what validation and git workflow requirements apply.
    """

    execution_mode: ExecutionMode = Field(
        description=(
            "The execution mode for this task. "
            "'exploration' for research/analysis/planning that doesn't write code. "
            "'implementation' for tasks that write or modify code. "
            "'validation' for code review, testing, or verification tasks."
        )
    )

    output_type: TaskOutputType = Field(
        description=(
            "What type of output this task will produce. "
            "'analysis' = findings/answers only, no files. "
            "'documentation' = markdown/spec files. "
            "'code' = source code changes. "
            "'tests' = test files. "
            "'configuration' = config files. "
            "'mixed' = combination of docs and code."
        )
    )

    requires_code_changes: bool = Field(
        description=(
            "Whether this task requires modifying or creating source code files. "
            "True for implementation tasks, False for pure research/analysis."
        )
    )

    requires_git_commit: bool = Field(
        description=(
            "Whether the task output should be committed to git. "
            "True if the task creates files that should be version controlled."
        )
    )

    requires_git_push: bool = Field(
        description=(
            "Whether changes should be pushed to remote repository. "
            "True for tasks that produce deliverables to share."
        )
    )

    requires_pull_request: bool = Field(
        description=(
            "Whether a Pull Request should be created for review. "
            "True for code changes that need review before merging. "
            "False for research, analysis, or draft documentation."
        )
    )

    requires_tests: bool = Field(
        description=(
            "Whether the task output requires tests to be written or run. "
            "True for implementation tasks, False for research/docs."
        )
    )

    reasoning: str = Field(
        description=(
            "Brief explanation of why these requirements were determined. "
            "Helps with debugging and transparency."
        )
    )


# System prompt for the task analyzer
TASK_ANALYZER_SYSTEM_PROMPT = """You are a task requirements analyzer for a software development system.

Your job is to analyze task descriptions and determine:
1. What type of work the task involves (research, coding, testing, etc.)
2. What deliverables the task will produce (analysis, docs, code, etc.)
3. What validation requirements apply (commit, push, PR, tests)

Guidelines for analysis:

## Execution Mode
- **exploration**: Research, analysis, investigation, planning, creating specs/designs
  - Examples: "How does X work?", "Analyze the codebase", "Create a design doc", "What billing system exists?"
  - Does NOT write source code, only reads/analyzes

- **implementation**: Writing or modifying source code
  - Examples: "Implement feature X", "Fix bug Y", "Add endpoint Z", "Refactor module W"
  - Creates/modifies code files that need to be committed

- **validation**: Reviewing, testing, or verifying existing code
  - Examples: "Review PR #123", "Run tests", "Verify implementation meets requirements"
  - May run tests but doesn't write new features

## Output Type
- **analysis**: Pure research with no file output (answers, findings, explanations)
- **documentation**: Creates markdown files, specs, designs (but not source code)
- **code**: Creates or modifies source code files
- **tests**: Creates or modifies test files
- **configuration**: Creates config files, env setup, infrastructure
- **mixed**: Combination of documentation and code

## Validation Requirements
- **requires_code_changes**: True only if source code files will be created/modified
- **requires_git_commit**: True if ANY files should be version controlled
- **requires_git_push**: True if deliverables should be shared (not just local analysis)
- **requires_pull_request**: True only for code changes that need review
  - Research/analysis tasks should NOT require PR
  - Documentation-only changes may or may not need PR depending on context
- **requires_tests**: True for code changes that should have test coverage

Be conservative with PR requirements - only require PRs for actual code changes that need review."""


class TaskRequirementsAnalyzer:
    """Analyzes task descriptions to determine execution requirements.

    Uses LLM structured output to intelligently determine what type of
    task this is and what validation requirements should apply.

    Usage:
        analyzer = TaskRequirementsAnalyzer()
        requirements = await analyzer.analyze(
            task_description="Analyze how billing works in this codebase",
            task_type="analyze_requirements",  # optional hint
        )

        if requirements.requires_pull_request:
            # Enable PR validation
            ...
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize the analyzer.

        Args:
            llm_service: Optional LLM service instance. If not provided,
                        uses the default singleton.
        """
        self.llm = llm_service or get_llm_service()

    async def analyze(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        ticket_title: Optional[str] = None,
        ticket_description: Optional[str] = None,
    ) -> TaskRequirements:
        """Analyze a task to determine its requirements.

        Args:
            task_description: The full task description/prompt
            task_type: Optional task type hint (e.g., "analyze_requirements")
            ticket_title: Optional parent ticket title for context
            ticket_description: Optional parent ticket description

        Returns:
            TaskRequirements with execution mode and validation settings
        """
        # Build the analysis prompt
        prompt_parts = ["Analyze the following task and determine its requirements:\n"]

        if ticket_title:
            prompt_parts.append(f"**Ticket Title:** {ticket_title}\n")

        if ticket_description:
            # Truncate long descriptions
            desc = ticket_description[:1000]
            if len(ticket_description) > 1000:
                desc += "..."
            prompt_parts.append(f"**Ticket Description:** {desc}\n")

        if task_type:
            prompt_parts.append(f"**Task Type:** {task_type}\n")

        prompt_parts.append(f"**Task Description:**\n{task_description[:2000]}")

        prompt = "\n".join(prompt_parts)

        try:
            requirements = await self.llm.structured_output(
                prompt=prompt,
                output_type=TaskRequirements,
                system_prompt=TASK_ANALYZER_SYSTEM_PROMPT,
                output_retries=3,
            )

            logger.info(
                "Analyzed task requirements",
                extra={
                    "execution_mode": requirements.execution_mode.value,
                    "output_type": requirements.output_type.value,
                    "requires_pr": requirements.requires_pull_request,
                    "requires_code": requirements.requires_code_changes,
                    "reasoning": requirements.reasoning[:100],
                },
            )

            return requirements

        except Exception as e:
            logger.error(
                "Failed to analyze task requirements, using defaults",
                extra={"error": str(e), "task_type": task_type},
            )
            # Return safe defaults that assume implementation
            return self._get_default_requirements(task_type)

    def _get_default_requirements(
        self, task_type: Optional[str] = None
    ) -> TaskRequirements:
        """Get default requirements when LLM analysis fails.

        Falls back to the original hardcoded logic as a safety net.
        """
        # Known exploration types (from original EXPLORATION_TASK_TYPES)
        exploration_types = {
            "explore_codebase",
            "analyze_codebase",
            "analyze_requirements",
            "analyze_dependencies",
            "create_spec",
            "create_requirements",
            "create_design",
            "create_tickets",
            "create_tasks",
            "define_feature",
            "research",
            "discover",
            "investigate",
        }

        validation_types = {
            "validate",
            "validate_implementation",
            "review_code",
            "run_tests",
        }

        if task_type in exploration_types:
            return TaskRequirements(
                execution_mode=ExecutionMode.EXPLORATION,
                output_type=TaskOutputType.ANALYSIS,
                requires_code_changes=False,
                requires_git_commit=False,
                requires_git_push=False,
                requires_pull_request=False,
                requires_tests=False,
                reasoning="Fallback: Task type is in known exploration types",
            )
        elif task_type in validation_types:
            return TaskRequirements(
                execution_mode=ExecutionMode.VALIDATION,
                output_type=TaskOutputType.ANALYSIS,
                requires_code_changes=False,
                requires_git_commit=False,
                requires_git_push=False,
                requires_pull_request=False,
                requires_tests=True,
                reasoning="Fallback: Task type is in known validation types",
            )
        else:
            # Default to implementation (requires full git workflow)
            return TaskRequirements(
                execution_mode=ExecutionMode.IMPLEMENTATION,
                output_type=TaskOutputType.CODE,
                requires_code_changes=True,
                requires_git_commit=True,
                requires_git_push=True,
                requires_pull_request=True,
                requires_tests=True,
                reasoning="Fallback: Unknown task type, assuming implementation",
            )


# Singleton instance
_analyzer_instance: Optional[TaskRequirementsAnalyzer] = None


def get_task_requirements_analyzer() -> TaskRequirementsAnalyzer:
    """Get the singleton TaskRequirementsAnalyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = TaskRequirementsAnalyzer()
    return _analyzer_instance
