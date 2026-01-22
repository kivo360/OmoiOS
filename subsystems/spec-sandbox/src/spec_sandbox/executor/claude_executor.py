"""Claude Agent SDK executor for phase execution.

This module wraps the Claude Agent SDK to execute spec phases.
Each phase gets a specific prompt and context, and the executor
handles streaming, tool usage, and result extraction.

The executor uses a file-based output approach for reliable JSON extraction:
- Agent writes JSON to a designated temp file
- Executor reads and validates the file after execution
- This is more reliable than parsing JSON from text output
"""

import asyncio
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional

from spec_sandbox.config import SpecSandboxSettings
from spec_sandbox.prompts.phases import get_phase_prompt
from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event, EventTypes
from spec_sandbox.schemas.spec import SpecPhase


@dataclass
class ExecutorConfig:
    """Configuration for the Claude executor.

    Attributes:
        model: Claude model to use
        max_turns: Maximum agentic turns per phase
        max_budget_usd: Maximum cost per phase
        allowed_tools: List of tools the agent can use
        cwd: Working directory for the agent
        timeout_seconds: Timeout for phase execution
        use_mock: Force mock execution (for testing without SDK)
    """

    model: str = "claude-sonnet-4-5-20250929"
    max_turns: int = 45  # Enough turns for exploration + write
    max_budget_usd: float = 20.0  # Allow thorough exploration
    allowed_tools: list[str] = field(
        default_factory=lambda: ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "Task", "Explore", "Agent", "Skill"]
    )
    cwd: Optional[Path] = None
    timeout_seconds: int = 900  # 15 minutes per phase (increased for TASKS phase)
    use_mock: bool = False  # Force mock execution for testing


@dataclass
class ExecutionResult:
    """Result from phase execution.

    Attributes:
        success: Whether execution completed successfully
        output: Parsed output from the agent
        raw_output: Raw text output from the agent
        cost_usd: Total cost in USD
        duration_ms: Execution duration in milliseconds
        error: Error message if failed
        tool_uses: Number of tool calls made
    """

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    raw_output: str = ""
    cost_usd: float = 0.0
    duration_ms: int = 0
    error: Optional[str] = None
    tool_uses: int = 0


class ClaudeExecutor:
    """Executes spec phases using Claude Agent SDK.

    The executor:
    1. Builds phase-specific prompts with context
    2. Creates a Claude Agent with appropriate tools
    3. Streams execution, emitting progress events
    4. Extracts and validates structured output
    5. Returns parsed results

    Usage:
        executor = ClaudeExecutor(config, reporter)
        result = await executor.execute_phase(
            phase=SpecPhase.EXPLORE,
            spec_title="My Feature",
            spec_description="Build X that does Y",
            context={"explore": previous_output},
        )
    """

    def __init__(
        self,
        config: Optional[ExecutorConfig] = None,
        reporter: Optional[Reporter] = None,
        spec_id: Optional[str] = None,
    ):
        self.config = config or ExecutorConfig()
        self.reporter = reporter
        self.spec_id = spec_id

    async def execute_phase(
        self,
        phase: SpecPhase,
        spec_title: str,
        spec_description: str,
        context: Optional[dict[str, Any]] = None,
        eval_feedback: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute a spec phase using Claude Agent SDK.

        Args:
            phase: The phase to execute
            spec_title: Title of the spec
            spec_description: Description of what to build
            context: Previous phase outputs for context
            eval_feedback: Feedback from previous evaluation failure (for retries)

        Returns:
            ExecutionResult with parsed output or error
        """
        import time

        start_time = time.time()
        context = context or {}

        # Build the prompt with context and eval feedback
        prompt = self._build_prompt(phase, spec_title, spec_description, context, eval_feedback)

        # Use mock if configured
        if self.config.use_mock:
            await self._emit_progress(phase, "Using mock execution (configured)")
            result = await self._mock_execute(phase, spec_title)
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result

        try:
            # Try to use Claude Agent SDK
            result = await asyncio.wait_for(
                self._execute_with_sdk(phase, prompt),
                timeout=self.config.timeout_seconds,
            )
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result

        except ImportError:
            # SDK not available - return mock for testing
            await self._emit_progress(
                phase, "Claude Agent SDK not available, using mock execution"
            )
            result = await self._mock_execute(phase, spec_title)
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                error=f"Phase execution timed out after {self.config.timeout_seconds}s",
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    def _build_prompt(
        self,
        phase: SpecPhase,
        spec_title: str,
        spec_description: str,
        context: dict[str, Any],
        eval_feedback: Optional[str] = None,
    ) -> str:
        """Build the prompt for a phase with context and optional eval feedback."""
        template = get_phase_prompt(phase)

        # Build context strings for each previous phase
        explore_context = json.dumps(context.get("explore", {}), indent=2)
        prd_context = json.dumps(context.get("prd", {}), indent=2)
        requirements_context = json.dumps(context.get("requirements", {}), indent=2)
        design_context = json.dumps(context.get("design", {}), indent=2)
        tasks_context = json.dumps(context.get("tasks", {}), indent=2)

        # Format the template
        prompt = template.format(
            spec_title=spec_title,
            spec_description=spec_description,
            explore_context=explore_context,
            prd_context=prd_context,
            requirements_context=requirements_context,
            design_context=design_context,
            tasks_context=tasks_context,
        )

        # Add evaluation feedback if retrying
        if eval_feedback:
            prompt += f"""

---
## ⚠️ PREVIOUS ATTEMPT FAILED EVALUATION

Your previous output did not pass the quality evaluation. Please address the following issues:

{eval_feedback}

**Fix these issues in your output before writing the JSON file.**
"""

        return prompt

    async def _execute_with_sdk(
        self,
        phase: SpecPhase,
        prompt: str,
    ) -> ExecutionResult:
        """Execute using Claude Agent SDK with file-based output.

        Uses a temp file for JSON output which is more reliable than
        parsing JSON from text output.
        """
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ClaudeSDKClient,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
        )

        # Create temp directory for output file - use a persistent path in cwd
        # so the SDK subprocess can write to it
        cwd = Path(self.config.cwd) if self.config.cwd else Path.cwd()
        output_dir = cwd / ".spec_sandbox_output"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{phase.value}_output.json"

        # Clean up any previous output file
        if output_file.exists():
            output_file.unlink()

        # Build environment variables - pass through auth tokens
        env_vars = {}
        for key in ["CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"]:
            if key in os.environ:
                env_vars[key] = os.environ[key]

        # Configure the agent with file output instructions
        options = ClaudeAgentOptions(
            model=self.config.model,
            max_turns=self.config.max_turns,
            max_budget_usd=self.config.max_budget_usd,
            allowed_tools=self.config.allowed_tools,
            cwd=self.config.cwd,
            permission_mode="bypassPermissions",  # Auto-approve in sandbox
            system_prompt=self._get_system_prompt(phase, output_file),
            env=env_vars,  # Pass auth tokens to subprocess
        )

        tool_uses = 0
        raw_output_parts: list[str] = []
        cost_usd = 0.0

        try:
            async with ClaudeSDKClient(options=options) as client:
                # Add output file path to prompt with emphasis
                full_prompt = f"""{prompt}

---
🚨 REQUIRED ACTION: Write your JSON output to: {output_file}
Use the Write tool to create this file when your analysis is complete.
The task is NOT finished until the JSON file has been written."""
                await client.query(full_prompt)

                # Use receive_messages() which is the correct method
                async for message in client.receive_messages():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                raw_output_parts.append(block.text)
                                # Emit progress for significant text
                                if len(block.text) > 50:
                                    await self._emit_progress(
                                        phase, f"Agent output: {block.text[:100]}..."
                                    )
                            elif isinstance(block, ToolUseBlock):
                                tool_uses += 1
                                await self._emit_progress(
                                    phase, f"Tool use: {block.name}"
                                )

                    elif isinstance(message, ResultMessage):
                        cost_usd = message.total_cost_usd or 0.0
                        # ResultMessage signals end of response
                        break

            # Join all text output
            raw_output = "\n".join(raw_output_parts)

            # Read JSON from output file (preferred) or fall back to text parsing
            parsed_output = self._read_output_file(output_file, raw_output)

            return ExecutionResult(
                success=True,
                output=parsed_output,
                raw_output=raw_output,
                cost_usd=cost_usd,
                tool_uses=tool_uses,
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                error=f"Phase execution timed out after {self.config.timeout_seconds}s",
                tool_uses=tool_uses,
            )
        finally:
            # Clean up output file after reading
            if output_file.exists():
                output_file.unlink()

    def _get_system_prompt(self, phase: SpecPhase, output_file: Path) -> str:
        """Get system prompt for phase execution with file output instructions."""
        return f"""You are a spec-driven development agent executing the {phase.value} phase.

## Your Workflow

1. **EXPLORE using Task tool**: Use the Task tool with subagent_type="Explore" to analyze the codebase.
   This sub-agent can search, read files, and understand patterns efficiently.

2. **WRITE OUTPUT FILE**: After analysis, use the Write tool to save your JSON output.

## Output File (REQUIRED)

🚨 Output path: {output_file}

Your analysis MUST be written to this file using the Write tool.
The task is NOT complete until the JSON file exists at this path.

## Available Tools

- **Task** (with subagent_type="Explore") - Use this for codebase exploration
- **Read/Glob/Grep** - Direct file access if needed
- **Write** - Create the output JSON file

## Current Phase: {phase.value}

Start by exploring, then write the JSON output file.
"""

    def _read_output_file(self, output_file: Path, raw_output: str) -> dict[str, Any]:
        """Read JSON from output file, falling back to text extraction.

        Args:
            output_file: Path to the expected JSON output file
            raw_output: Raw text output as fallback

        Returns:
            Parsed JSON dict from file or fallback extraction
        """
        # Try to read from file first (preferred)
        if output_file.exists():
            try:
                content = output_file.read_text()
                parsed = json.loads(content)
                parsed["_output_source"] = "file"
                return parsed
            except json.JSONDecodeError as e:
                # File exists but invalid JSON - include partial content
                return {
                    "raw_text": content[:1000],
                    "parse_error": f"Invalid JSON in output file: {e}",
                    "_output_source": "file_error",
                }

        # Fall back to text extraction if file not created
        parsed = self._extract_json(raw_output)
        parsed["_output_source"] = "text_fallback"
        return parsed

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from agent output (fallback method).

        Handles JSON in code blocks or bare JSON.
        """
        # Try to find JSON in code blocks first
        json_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(json_block_pattern, text)

        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # Try to find bare JSON object
        # Look for outermost { ... } that forms valid JSON
        brace_count = 0
        start_idx = -1

        for i, char in enumerate(text):
            if char == "{":
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0 and start_idx >= 0:
                    try:
                        return json.loads(text[start_idx : i + 1])
                    except json.JSONDecodeError:
                        start_idx = -1
                        continue

        # If no JSON found, return empty with raw text
        return {"raw_text": text, "parse_error": "Could not extract JSON from output"}

    async def _emit_progress(self, phase: SpecPhase, message: str) -> None:
        """Emit a progress event."""
        if self.reporter is not None:
            event = Event(
                event_type=EventTypes.PROGRESS,
                spec_id=self.spec_id or "unknown",
                phase=phase.value,
                data={"message": message},
            )
            await self.reporter.report(event)

    async def _mock_execute(
        self, phase: SpecPhase, spec_title: str
    ) -> ExecutionResult:
        """Mock execution when SDK not available.

        Mock outputs are designed to pass evaluators with reasonable scores.
        These outputs include all fields required by the enhanced evaluators.
        """
        await asyncio.sleep(0.1)  # Simulate work

        mock_outputs = {
            SpecPhase.EXPLORE: {
                "codebase_summary": f"This is a comprehensive mock analysis for {spec_title}. The codebase follows modern Python patterns with a clear separation of concerns between API routes, services, and data models. Testing is done with pytest.",
                "project_type": "web_application with REST API",
                "tech_stack": ["Python 3.12+", "FastAPI", "PostgreSQL", "SQLAlchemy", "Pydantic"],
                "key_files": [
                    {"path": "src/main.py", "purpose": "Application entry point and FastAPI app creation"},
                    {"path": "src/api/routes.py", "purpose": "API endpoint definitions"},
                    {"path": "src/services/core.py", "purpose": "Core business logic services"},
                    {"path": "src/models/base.py", "purpose": "SQLAlchemy model definitions"},
                ],
                "relevant_patterns": [
                    {"pattern": "Repository pattern", "description": "Data access abstraction", "files": ["src/repositories/"]},
                ],
                "entry_points": ["src/main.py"],
                "test_structure": "pytest in tests/ with fixtures in conftest.py",
                "notes": "Mock exploration - SDK not available",
                # New fields required by enhanced evaluators
                "structure": {
                    "api": ["src/api/"],
                    "services": ["src/services/"],
                    "models": ["src/models/"],
                    "tests": ["tests/"],
                },
                "discovery_questions": {
                    "problem_value": [
                        "What specific problem does this feature solve?",
                        "Who experiences this problem most acutely?",
                        "What is the cost of not solving this problem?",
                    ],
                    "users_journeys": [
                        "Who are the primary users of this feature?",
                        "What is their current workflow without this feature?",
                        "What would the ideal user journey look like?",
                    ],
                    "scope_boundaries": [
                        "What is explicitly out of scope for this implementation?",
                        "Are there any hard constraints we must work within?",
                        "What is the minimum viable version of this feature?",
                    ],
                    "technical_context": [
                        "What existing systems does this need to integrate with?",
                        "Are there performance requirements we need to meet?",
                        "What data migrations might be required?",
                    ],
                    "risks_tradeoffs": [
                        "What are the biggest technical risks?",
                        "What tradeoffs are we willing to make?",
                        "What would cause this project to fail?",
                    ],
                },
                "feature_summary": {
                    "name": spec_title,
                    "scope_in": ["Core functionality", "Basic validation", "API endpoints"],
                    "scope_out": ["Advanced analytics", "Mobile support", "Third-party integrations"],
                    "problem_statement": f"Users need {spec_title} to improve their workflow efficiency",
                    "technical_constraints": ["Must work with existing auth system", "Database schema backward compatible"],
                },
                "conventions": {
                    "naming": "snake_case for Python, camelCase for API",
                    "testing": "pytest with fixtures, 80% coverage target",
                    "patterns": ["Repository pattern", "Service layer", "Dependency injection"],
                },
            },
            SpecPhase.PRD: {
                "overview": {
                    "feature_name": spec_title,
                    "one_liner": f"A comprehensive solution for {spec_title} that improves user workflow efficiency",
                    "problem_statement": f"Users currently lack an efficient way to handle {spec_title}. This causes delays, errors, and frustration in their daily workflows. Without a proper solution, productivity suffers and user satisfaction decreases.",
                    "solution_summary": f"We will implement {spec_title} as a robust, user-friendly feature that integrates seamlessly with existing systems. The solution includes a clean API, proper validation, and comprehensive error handling to ensure a smooth user experience.",
                },
                "goals": {
                    "primary": [
                        f"Enable users to efficiently perform {spec_title} operations",
                        "Reduce time spent on manual workflows by 50%",
                        "Provide clear feedback and error handling for all operations",
                    ],
                    "secondary": [
                        "Lay groundwork for future feature extensions",
                        "Improve overall system reliability",
                        "Enhance user satisfaction with the platform",
                    ],
                    "success_metrics": [
                        {
                            "metric": "Task completion time",
                            "target": "50% reduction from baseline",
                            "measurement": "Average time tracked via analytics",
                        },
                        {
                            "metric": "Error rate",
                            "target": "< 1% of operations",
                            "measurement": "Error logs and user reports",
                        },
                        {
                            "metric": "User satisfaction",
                            "target": "> 4.0/5.0 rating",
                            "measurement": "Post-feature survey",
                        },
                    ],
                },
                "users": {
                    "primary": [
                        {
                            "role": "End User",
                            "description": "Regular users who need to perform daily operations efficiently",
                            "needs": [
                                "Quick access to core functionality",
                                "Clear feedback on operation status",
                                "Minimal learning curve",
                            ],
                        },
                    ],
                    "secondary": [
                        {
                            "role": "Administrator",
                            "description": "Users who manage system configuration and user access",
                            "needs": [
                                "Ability to configure feature settings",
                                "Access to usage analytics",
                                "User management capabilities",
                            ],
                        },
                    ],
                },
                "user_stories": [
                    {
                        "id": "US-001",
                        "role": "End User",
                        "want": f"to quickly initiate {spec_title} operations",
                        "benefit": "I can complete my work faster and with fewer errors",
                        "priority": "must",
                        "acceptance_criteria": [
                            "User can access the feature from the main navigation",
                            "Operation can be initiated with 3 or fewer clicks",
                            "Clear confirmation is shown upon completion",
                        ],
                    },
                    {
                        "id": "US-002",
                        "role": "End User",
                        "want": "to receive clear feedback when operations fail",
                        "benefit": "I can understand what went wrong and how to fix it",
                        "priority": "must",
                        "acceptance_criteria": [
                            "Error messages are displayed in plain language",
                            "Suggested remediation steps are provided",
                            "User can retry the operation easily",
                        ],
                    },
                    {
                        "id": "US-003",
                        "role": "Administrator",
                        "want": "to view usage statistics for the feature",
                        "benefit": "I can understand adoption and identify issues",
                        "priority": "should",
                        "acceptance_criteria": [
                            "Dashboard shows daily/weekly/monthly usage",
                            "Error rates are visible and filterable",
                            "Data can be exported for reporting",
                        ],
                    },
                ],
                "scope": {
                    "in_scope": [
                        f"Core {spec_title} functionality",
                        "API endpoints for all operations",
                        "Input validation and error handling",
                        "Basic usage logging",
                        "Unit and integration tests",
                    ],
                    "out_of_scope": [
                        "Mobile application support",
                        "Real-time notifications",
                        "Third-party integrations",
                        "Advanced analytics dashboard",
                        "Internationalization (i18n)",
                    ],
                    "dependencies": [
                        "Existing authentication system",
                        "PostgreSQL database",
                        "Redis cache (optional optimization)",
                    ],
                },
                "assumptions": [
                    "Users have valid authentication credentials",
                    "Database is available and performant",
                    "Existing API patterns will be followed",
                    "Feature will be deployed to existing infrastructure",
                ],
                "constraints": {
                    "technical": [
                        "Must work with Python 3.12+",
                        "Must use existing FastAPI framework",
                        "Database schema must be backward compatible",
                        "API must follow existing REST conventions",
                    ],
                    "business": [
                        "Must be completed within planned timeline",
                        "Must not require additional infrastructure costs",
                        "Must maintain existing SLA commitments",
                    ],
                },
                "risks": [
                    {
                        "description": "Integration complexity with existing systems",
                        "impact": "medium",
                        "mitigation": "Early integration testing and incremental rollout",
                    },
                    {
                        "description": "Performance degradation under load",
                        "impact": "high",
                        "mitigation": "Load testing before release and caching strategy",
                    },
                    {
                        "description": "User adoption challenges",
                        "impact": "medium",
                        "mitigation": "Clear documentation and gradual feature introduction",
                    },
                ],
                "open_questions": [
                    "Should we support bulk operations in the initial release?",
                    "What is the expected peak load for this feature?",
                    "Are there any compliance requirements we need to consider?",
                ],
            },
            SpecPhase.REQUIREMENTS: {
                "requirements": [
                    {
                        "id": "REQ-FEAT-CORE-001",
                        "type": "functional",
                        "category": "Core",
                        "text": f"WHEN a user requests {spec_title}, THE SYSTEM SHALL process the request and return the expected result",
                        "priority": "must",
                        "acceptance_criteria": [
                            "Request is validated before processing",
                            "Response includes all required fields",
                            "Errors are handled gracefully",
                        ],
                        "dependencies": [],
                    },
                    {
                        "id": "REQ-FEAT-PERF-002",
                        "type": "non_functional",
                        "category": "Performance",
                        "text": "THE SYSTEM SHALL respond to requests within 500ms under normal load",
                        "priority": "should",
                        "acceptance_criteria": [
                            "P95 latency under 500ms",
                            "Handles 100 concurrent requests",
                        ],
                        "dependencies": ["REQ-FEAT-CORE-001"],
                    },
                ],
                "assumptions": [
                    "SDK available in production",
                    "Database connection is reliable",
                ],
                "out_of_scope": ["UI components", "Mobile application", "Real-time notifications"],
                "open_questions": [],
                # New fields required by enhanced evaluators
                "traceability": {
                    "REQ-FEAT-CORE-001": {
                        "source": "discovery_questions.problem_value",
                        "stakeholder": "Product Owner",
                    },
                    "REQ-FEAT-PERF-002": {
                        "source": "technical_constraints",
                        "stakeholder": "Engineering Lead",
                    },
                },
            },
            SpecPhase.DESIGN: {
                "architecture_overview": f"The design for {spec_title} follows a layered architecture with clear separation between API, service, and data layers. The API layer handles HTTP concerns, the service layer contains business logic, and the data layer manages persistence.",
                "components": [
                    {
                        "name": "FeatureService",
                        "type": "service",
                        "responsibility": "Core business logic for the feature",
                        "file_path": "src/services/feature.py",
                        "interfaces": [{"method": "process", "inputs": {"data": "dict"}, "outputs": {"result": "dict"}, "description": "Process feature request"}],
                        "dependencies": ["DatabaseService"],
                    },
                    {
                        "name": "FeatureRepository",
                        "type": "repository",
                        "responsibility": "Data access for feature entities",
                        "file_path": "src/repositories/feature.py",
                        "interfaces": [{"method": "save", "inputs": {"entity": "Feature"}, "outputs": {"id": "str"}, "description": "Persist entity"}],
                        "dependencies": [],
                    },
                ],
                "data_models": [
                    {
                        "name": "Feature",
                        "fields": {"id": "uuid", "name": "str", "created_at": "datetime"},
                        "purpose": "Main feature entity",
                        "indexes": ["id", "created_at"],
                        "constraints": ["name NOT NULL", "id PRIMARY KEY"],
                    },
                ],
                "api_endpoints": [
                    {
                        "method": "POST",
                        "path": "/api/v1/features",
                        "purpose": "Create new feature",
                        "request_schema": {"name": "str"},
                        "response_schema": {"id": "uuid", "name": "str"},
                        "auth_required": True,
                        "rate_limit": "100/minute",
                    },
                ],
                "integration_points": [
                    {"system": "Database", "protocol": "PostgreSQL", "purpose": "Data persistence"},
                    {"system": "Cache", "protocol": "Redis", "purpose": "Response caching"},
                ],
                "error_handling": {
                    "strategy": "Exception hierarchy with custom error types",
                    "error_types": ["ValidationError", "NotFoundError", "AuthorizationError"],
                    "logging": "Structured JSON logging to stdout",
                },
                "security_considerations": [
                    "Input validation on all endpoints",
                    "Authentication required for write operations",
                    "Rate limiting to prevent abuse",
                    "SQL injection prevention via parameterized queries",
                ],
                "testing_strategy": "Unit tests for services, integration tests for API endpoints, using pytest fixtures for test data",
                "migration_plan": None,
            },
            SpecPhase.TASKS: {
                "tickets": [
                    {
                        "id": "TKT-001",
                        "title": "Core Feature Implementation",
                        "description": f"Implement the core functionality for {spec_title} including data models, service layer, and API endpoints",
                        "priority": "HIGH",
                        "requirements": ["REQ-FEAT-CORE-001", "REQ-FEAT-PERF-002"],
                        "tasks": ["TSK-001", "TSK-002", "TSK-003"],
                        "dependencies": [],
                    },
                ],
                "tasks": [
                    {
                        "id": "TSK-001",
                        "title": "Create data model",
                        "description": "Define SQLAlchemy model for the feature entity with all required fields",
                        "parent_ticket": "TKT-001",
                        "type": "implementation",
                        "priority": "HIGH",
                        "files_to_modify": [],
                        "files_to_create": ["src/models/feature.py"],
                        "dependencies": {"depends_on": []},
                        "requirements_addressed": ["REQ-FEAT-CORE-001"],
                        "acceptance_criteria": ["Model has all required fields", "Migrations run successfully"],
                        "estimated_hours": 2,
                    },
                    {
                        "id": "TSK-002",
                        "title": "Implement service layer",
                        "description": "Create FeatureService with business logic for processing requests",
                        "parent_ticket": "TKT-001",
                        "type": "implementation",
                        "priority": "HIGH",
                        "files_to_modify": [],
                        "files_to_create": ["src/services/feature.py"],
                        "dependencies": {"depends_on": ["TSK-001"]},
                        "requirements_addressed": ["REQ-FEAT-CORE-001"],
                        "acceptance_criteria": ["Service handles all use cases", "Unit tests pass"],
                        "estimated_hours": 3,
                    },
                    {
                        "id": "TSK-003",
                        "title": "Add API endpoint",
                        "description": "Create FastAPI route for the feature with validation",
                        "parent_ticket": "TKT-001",
                        "type": "implementation",
                        "priority": "MEDIUM",
                        "files_to_modify": ["src/api/routes.py"],
                        "files_to_create": [],
                        "dependencies": {"depends_on": ["TSK-002"]},
                        "requirements_addressed": ["REQ-FEAT-CORE-001", "REQ-FEAT-PERF-002"],
                        "acceptance_criteria": ["Endpoint returns correct response", "Integration tests pass"],
                        "estimated_hours": 2,
                    },
                ],
                "total_estimated_hours": 7,
                "critical_path": ["TSK-001", "TSK-002", "TSK-003"],
                "parallel_tracks": [],
            },
            SpecPhase.SYNC: {
                "validation_results": {
                    "all_requirements_covered": True,
                    "all_components_have_tasks": True,
                    "dependency_order_valid": True,
                    "no_circular_dependencies": True,
                    "issues_found": [],
                },
                "coverage_matrix": [
                    {
                        "requirement_id": "REQ-FEAT-CORE-001",
                        "covered_by_tasks": ["TSK-001", "TSK-002", "TSK-003"],
                        "status": "fully_covered",
                    },
                    {
                        "requirement_id": "REQ-FEAT-PERF-002",
                        "covered_by_tasks": ["TSK-003"],
                        "status": "fully_covered",
                    },
                ],
                "traceability_stats": {
                    "requirements": {
                        "total": 2,
                        "linked": 2,
                        "coverage": 100.0,
                    },
                    "tasks": {
                        "total": 3,
                        "done": 0,
                        "in_progress": 0,
                        "pending": 3,
                    },
                    "tickets": {
                        "total": 1,
                        "backlog": 1,
                        "in_progress": 0,
                        "done": 0,
                    },
                    "orphans": {
                        "requirements": [],
                    },
                },
                "dependency_analysis": {
                    "critical_path_length": 3,
                    "parallelizable_tasks": 0,
                    "blocking_tasks": ["TSK-001"],
                    "risk_assessment": "Low - linear dependency chain with no complex interdependencies",
                },
                "recommendations": [
                    "Consider adding integration tests for API endpoints early",
                    "Database migrations should be tested in staging first",
                    "Monitor performance metrics after deployment",
                ],
                "spec_summary": {
                    "total_requirements": 2,
                    "total_tickets": 1,
                    "total_tasks": 3,
                    "total_estimated_hours": 7,
                    "files_to_modify": 1,
                    "files_to_create": 2,
                    "requirement_coverage_percent": 100.0,
                },
                "ready_for_execution": True,
                "blockers": [],
            },
        }

        output = mock_outputs.get(phase, {})
        output["_mock"] = True

        return ExecutionResult(
            success=True,
            output=output,
            raw_output=json.dumps(output, indent=2),
            cost_usd=0.0,
            duration_ms=100,
            tool_uses=0,
        )
