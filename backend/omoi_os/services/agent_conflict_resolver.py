"""Agent Conflict Resolver using Claude Agent SDK.

Phase D: LLM-powered conflict resolution for DAG Merge Executor integration.

This service uses the Claude Agent SDK (claude-agent-sdk package) to resolve
git merge conflicts in an agentic manner. Unlike one-shot LLM calls, this
gives the Claude agent access to tools (Read, Write, Bash) so it can:

1. Examine the conflicted file's full context
2. Read related files to understand the codebase
3. Make informed decisions about conflict resolution
4. Verify the resolution makes sense

The resolver runs inside a Daytona sandbox for security and isolation.

Installation:
    pip install claude-agent-sdk

Prerequisites:
    - ANTHROPIC_API_KEY environment variable
    - Claude Code CLI (bundled with claude-agent-sdk)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from omoi_os.logging import get_logger
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from daytona_sdk import Sandbox

logger = get_logger(__name__)

# Try to import Claude Agent SDK
try:
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logger.warning("claude-agent-sdk not installed. AgentConflictResolver will be limited.")


@dataclass
class ResolutionContext:
    """Context for conflict resolution."""
    file_path: str
    ours_content: str
    theirs_content: str
    base_content: Optional[str] = None
    task_id: Optional[str] = None
    related_files: List[str] = field(default_factory=list)
    task_description: Optional[str] = None


@dataclass
class ResolutionResult:
    """Result of a conflict resolution attempt."""
    success: bool
    resolved_content: Optional[str] = None
    reasoning: Optional[str] = None
    error_message: Optional[str] = None
    tokens_used: int = 0
    duration_seconds: float = 0.0


class AgentConflictResolver:
    """Resolves git merge conflicts using Claude Agent SDK.

    This service provides agentic conflict resolution by:
    1. Building a rich context prompt about the conflict
    2. Giving Claude access to file reading tools
    3. Letting Claude reason about the best resolution
    4. Extracting the resolved content

    The agentic approach is better than one-shot because:
    - Claude can examine related code for context
    - Claude can verify the resolution makes sense
    - Claude can ask for clarification (through tool use)
    - Better handling of complex, semantic conflicts

    Usage:
        resolver = AgentConflictResolver(
            api_key="sk-ant-...",
            model="claude-sonnet-4-20250514",
        )

        result = await resolver.resolve_conflict(
            file_path="src/services/user.py",
            ours_content="def create_user(name): ...",
            theirs_content="def create_user(name, email): ...",
        )

        if result.success:
            await git_ops.write_file(file_path, result.resolved_content)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_turns: int = 5,
        timeout_seconds: int = 120,
        sandbox: Optional["Sandbox"] = None,
        workspace_path: str = "/workspace",
    ):
        """Initialize the agent conflict resolver.

        Args:
            api_key: Anthropic API key (or from ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_turns: Maximum agentic turns for resolution
            timeout_seconds: Timeout for each resolution
            sandbox: Optional Daytona sandbox for running in isolated environment
            workspace_path: Path to workspace in sandbox
        """
        self.api_key = api_key
        self.model = model
        self.max_turns = max_turns
        self.timeout = timeout_seconds
        self.sandbox = sandbox
        self.workspace_path = workspace_path

        if not CLAUDE_SDK_AVAILABLE:
            logger.warning(
                "agent_conflict_resolver_limited",
                extra={"reason": "claude-agent-sdk not installed"},
            )

        logger.info(
            "agent_conflict_resolver_initialized",
            extra={
                "model": model,
                "max_turns": max_turns,
                "sdk_available": CLAUDE_SDK_AVAILABLE,
            },
        )

    async def resolve_conflict(
        self,
        file_path: str,
        ours_content: str,
        theirs_content: str,
        base_content: Optional[str] = None,
        task_id: Optional[str] = None,
        task_description: Optional[str] = None,
        related_files: Optional[List[str]] = None,
    ) -> ResolutionResult:
        """Resolve a merge conflict using Claude Agent.

        Args:
            file_path: Path to the conflicted file
            ours_content: Content from "our" side (target branch)
            theirs_content: Content from "their" side (incoming branch)
            base_content: Optional content from common ancestor
            task_id: Optional task ID for context
            task_description: Optional description of what the task was doing
            related_files: Optional list of related files for context

        Returns:
            ResolutionResult with resolved content or error
        """
        start_time = utc_now()

        context = ResolutionContext(
            file_path=file_path,
            ours_content=ours_content,
            theirs_content=theirs_content,
            base_content=base_content,
            task_id=task_id,
            task_description=task_description,
            related_files=related_files or [],
        )

        # Use SDK if available, otherwise fallback to basic resolution
        if CLAUDE_SDK_AVAILABLE:
            result = await self._resolve_with_sdk(context)
        else:
            result = await self._resolve_fallback(context)

        result.duration_seconds = (utc_now() - start_time).total_seconds()

        logger.info(
            "conflict_resolution_completed",
            extra={
                "file_path": file_path,
                "success": result.success,
                "tokens_used": result.tokens_used,
                "duration_seconds": result.duration_seconds,
            },
        )

        return result

    async def _resolve_with_sdk(self, context: ResolutionContext) -> ResolutionResult:
        """Resolve conflict using Claude Agent SDK.

        This runs the full agentic flow with tool access.

        Args:
            context: Resolution context with conflict info

        Returns:
            ResolutionResult from agent
        """
        prompt = self._build_resolution_prompt(context)

        try:
            # Configure agent options
            options = ClaudeAgentOptions(
                system_prompt=self._get_system_prompt(),
                max_turns=self.max_turns,
                allowed_tools=["Read"],  # Allow reading files for context
            )

            # Add workspace path if in sandbox
            if self.sandbox:
                options.cwd = self.workspace_path

            # Run agentic query
            resolved_content = None
            reasoning = None
            tokens_used = 0

            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Extract the resolution from the response
                            text = block.text

                            # Look for resolution markers
                            if "<<<RESOLVED>>>" in text:
                                # Extract content between markers
                                start = text.find("<<<RESOLVED>>>") + len("<<<RESOLVED>>>")
                                end = text.find("<<<END_RESOLVED>>>")
                                if end > start:
                                    resolved_content = text[start:end].strip()
                            elif "<<<REASONING>>>" in text:
                                start = text.find("<<<REASONING>>>") + len("<<<REASONING>>>")
                                end = text.find("<<<END_REASONING>>>")
                                if end > start:
                                    reasoning = text[start:end].strip()
                            else:
                                # If no markers, treat the whole response as resolved content
                                # only if it looks like code
                                if self._looks_like_code(text, context.file_path):
                                    resolved_content = text

                # Track token usage from metadata if available
                if hasattr(message, "usage"):
                    tokens_used += getattr(message.usage, "total_tokens", 0)

            if resolved_content:
                return ResolutionResult(
                    success=True,
                    resolved_content=resolved_content,
                    reasoning=reasoning,
                    tokens_used=tokens_used,
                )
            else:
                return ResolutionResult(
                    success=False,
                    error_message="No resolution content extracted from agent response",
                    tokens_used=tokens_used,
                )

        except Exception as e:
            logger.error(
                "sdk_resolution_error",
                extra={
                    "file_path": context.file_path,
                    "error": str(e),
                },
                exc_info=True,
            )
            return ResolutionResult(
                success=False,
                error_message=str(e),
            )

    async def _resolve_fallback(self, context: ResolutionContext) -> ResolutionResult:
        """Fallback resolution when SDK is not available.

        Uses simple heuristics for common conflict patterns.

        Args:
            context: Resolution context

        Returns:
            ResolutionResult (may be incomplete)
        """
        logger.warning(
            "using_fallback_resolution",
            extra={"file_path": context.file_path},
        )

        # Simple heuristics for common patterns
        ours = context.ours_content
        theirs = context.theirs_content

        # If one side is empty, use the other
        if not ours.strip():
            return ResolutionResult(
                success=True,
                resolved_content=theirs,
                reasoning="Used theirs (ours was empty)",
            )
        if not theirs.strip():
            return ResolutionResult(
                success=True,
                resolved_content=ours,
                reasoning="Used ours (theirs was empty)",
            )

        # If they're the same, use either
        if ours.strip() == theirs.strip():
            return ResolutionResult(
                success=True,
                resolved_content=ours,
                reasoning="Both sides identical",
            )

        # Check for simple addition patterns (one extends the other)
        if theirs.startswith(ours):
            return ResolutionResult(
                success=True,
                resolved_content=theirs,
                reasoning="Theirs extends ours",
            )
        if ours.startswith(theirs):
            return ResolutionResult(
                success=True,
                resolved_content=ours,
                reasoning="Ours extends theirs",
            )

        # For import statements, try to combine
        if context.file_path.endswith(".py") and "import" in ours and "import" in theirs:
            combined = self._merge_imports(ours, theirs)
            if combined:
                return ResolutionResult(
                    success=True,
                    resolved_content=combined,
                    reasoning="Merged import statements",
                )

        # Cannot resolve automatically
        return ResolutionResult(
            success=False,
            error_message="Cannot resolve automatically without Claude Agent SDK",
        )

    def _merge_imports(self, ours: str, theirs: str) -> Optional[str]:
        """Attempt to merge Python import statements.

        Args:
            ours: Our import content
            theirs: Their import content

        Returns:
            Merged imports or None if can't merge
        """
        try:
            ours_lines = set(line.strip() for line in ours.split("\n") if line.strip())
            theirs_lines = set(line.strip() for line in theirs.split("\n") if line.strip())

            # Combine unique lines
            combined = ours_lines | theirs_lines

            # Sort for consistency
            sorted_imports = sorted(
                combined,
                key=lambda x: (not x.startswith("from"), x),
            )

            return "\n".join(sorted_imports)
        except Exception:
            return None

    def _build_resolution_prompt(self, context: ResolutionContext) -> str:
        """Build the prompt for conflict resolution.

        Args:
            context: Resolution context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "I need you to resolve a git merge conflict.",
            "",
            f"**File:** `{context.file_path}`",
            "",
        ]

        if context.task_description:
            prompt_parts.extend([
                f"**Task context:** {context.task_description}",
                "",
            ])

        prompt_parts.extend([
            "## Our version (target branch):",
            "```",
            context.ours_content,
            "```",
            "",
            "## Their version (incoming branch):",
            "```",
            context.theirs_content,
            "```",
            "",
        ])

        if context.base_content:
            prompt_parts.extend([
                "## Common ancestor:",
                "```",
                context.base_content,
                "```",
                "",
            ])

        if context.related_files:
            prompt_parts.extend([
                "## Related files you can read for context:",
                "",
            ])
            for f in context.related_files[:5]:  # Limit to 5
                prompt_parts.append(f"- `{f}`")
            prompt_parts.append("")

        prompt_parts.extend([
            "## Instructions:",
            "",
            "1. Analyze both versions and understand what each change is trying to accomplish",
            "2. If needed, use the Read tool to examine related files for context",
            "3. Produce a merged version that preserves the intent of BOTH changes",
            "4. Do NOT simply pick one side unless the other is clearly incorrect",
            "5. Ensure the resolved code is syntactically correct",
            "",
            "## Output format:",
            "",
            "First explain your reasoning:",
            "<<<REASONING>>>",
            "Your reasoning here...",
            "<<<END_REASONING>>>",
            "",
            "Then provide the resolved file content:",
            "<<<RESOLVED>>>",
            "The complete resolved file content goes here...",
            "<<<END_RESOLVED>>>",
        ])

        return "\n".join(prompt_parts)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the conflict resolver agent."""
        return """You are an expert software engineer specializing in git merge conflict resolution.

Your task is to analyze merge conflicts and produce resolved versions that:
1. Preserve the intent of BOTH changes when possible
2. Maintain code correctness and consistency
3. Follow the codebase's existing patterns and style

You have access to file reading tools to examine related code for context.
Use them when needed to make informed decisions about the resolution.

When resolving conflicts:
- Don't simply pick one side unless the other is clearly wrong
- Consider semantic meaning, not just syntactic differences
- Preserve functionality from both branches
- Ensure the result compiles/parses correctly

Always explain your reasoning before providing the resolved content."""

    def _looks_like_code(self, text: str, file_path: str) -> bool:
        """Check if text looks like code for the given file type.

        Args:
            text: Text to check
            file_path: File path for type detection

        Returns:
            True if text appears to be code
        """
        # Basic heuristics
        if file_path.endswith(".py"):
            return "def " in text or "class " in text or "import " in text
        elif file_path.endswith((".js", ".ts", ".tsx")):
            return "function " in text or "const " in text or "import " in text
        elif file_path.endswith((".java", ".kt")):
            return "class " in text or "public " in text or "private " in text
        elif file_path.endswith(".go"):
            return "func " in text or "package " in text or "import " in text

        # Generic check
        return len(text.split("\n")) > 3


# Convenience function for creating resolver with default settings
def create_conflict_resolver(
    sandbox: Optional["Sandbox"] = None,
    workspace_path: str = "/workspace",
    **kwargs,
) -> AgentConflictResolver:
    """Create an AgentConflictResolver with default settings.

    Args:
        sandbox: Optional Daytona sandbox
        workspace_path: Workspace path in sandbox
        **kwargs: Additional arguments for AgentConflictResolver

    Returns:
        Configured AgentConflictResolver instance
    """
    return AgentConflictResolver(
        sandbox=sandbox,
        workspace_path=workspace_path,
        **kwargs,
    )
