"""
Spec-driven development state machine.

Orchestrates the multi-phase spec generation workflow:
EXPLORE -> REQUIREMENTS -> DESIGN -> TASKS -> SYNC -> COMPLETE

Each phase:
- Runs as a separate Agent SDK session (short, focused)
- Has access to codebase tools (Glob, Read, Grep)
- Saves to database before proceeding
- Can be resumed from any checkpoint
- Has validation gates with retry

Usage:
    from omoi_os.workers.spec_state_machine import SpecStateMachine

    machine = SpecStateMachine(
        spec_id="spec-xxx",
        db_session=db,
        working_directory="/workspace",
    )
    success = await machine.run()
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from omoi_os.evals import (
    DesignEvaluator,
    EvalResult,
    ExplorationEvaluator,
    RequirementEvaluator,
    TaskEvaluator,
)
from omoi_os.schemas.spec_generation import SpecPhase

logger = logging.getLogger(__name__)


class PhaseResult(BaseModel):
    """Result of executing a phase."""

    phase: SpecPhase
    data: dict[str, Any]
    eval_score: float = 1.0
    attempts: int = 1
    duration_seconds: float = 0.0
    error: Optional[str] = None
    session_id: Optional[str] = None
    transcript_b64: Optional[str] = None


class _MockSpec:
    """Mock spec object for sandbox environments without database access.

    When running in a sandbox without DATABASE_URL or when pgvector is not
    installed, we need a mock spec object that mimics the essential attributes
    of the real Spec model. Phase data is stored in local files instead of
    the database.
    """

    def __init__(self, spec_id: str, title: str = "Local Spec", description: str = ""):
        self.id = spec_id
        self.title = title
        self.description = description
        self.current_phase = SpecPhase.EXPLORE.value
        self.phase_data: dict = {}
        self.phase_attempts: dict = {}
        self.session_transcripts: dict = {}
        self.last_checkpoint_at: Optional[datetime] = None
        self.status = "processing"
        self.is_mock = True  # Flag to identify mock specs

    def __repr__(self):
        return f"_MockSpec(id={self.id}, phase={self.current_phase})"


class SpecStateMachine:
    """
    State machine for reliable spec generation using Claude Agent SDK.

    Each phase:
    - Runs as a SEPARATE Agent SDK session (short, focused)
    - Has access to codebase tools (Glob, Read, Grep)
    - Saves to database before proceeding
    - Can be resumed from any checkpoint
    - Has validation gates with retry
    """

    PHASE_ORDER = [
        SpecPhase.EXPLORE,
        SpecPhase.REQUIREMENTS,
        SpecPhase.DESIGN,
        SpecPhase.TASKS,
        SpecPhase.SYNC,
        SpecPhase.COMPLETE,
    ]

    # Timeouts per phase (seconds)
    PHASE_TIMEOUTS = {
        SpecPhase.EXPLORE: 180,       # 3 minutes
        SpecPhase.REQUIREMENTS: 300,  # 5 minutes
        SpecPhase.DESIGN: 300,        # 5 minutes
        SpecPhase.TASKS: 180,         # 3 minutes
        SpecPhase.SYNC: 120,          # 2 minutes
    }

    # Max turns per phase (keeps sessions short)
    PHASE_MAX_TURNS = {
        SpecPhase.EXPLORE: 25,
        SpecPhase.REQUIREMENTS: 20,
        SpecPhase.DESIGN: 25,
        SpecPhase.TASKS: 15,
        SpecPhase.SYNC: 10,
    }

    def __init__(
        self,
        spec_id: str,
        db_session: Any,
        working_directory: str = "/workspace",
        max_retries: int = 3,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the state machine.

        Args:
            spec_id: ID of the spec being generated
            db_session: SQLAlchemy async session
            working_directory: Working directory for file operations
            max_retries: Maximum retry attempts per phase
            model: Claude model to use
        """
        self.spec_id = spec_id
        self.db = db_session
        self.working_directory = working_directory
        self.max_retries = max_retries
        self.model = model

        # Initialize evaluators
        self.evaluators = {
            SpecPhase.EXPLORE: ExplorationEvaluator(),
            SpecPhase.REQUIREMENTS: RequirementEvaluator(),
            SpecPhase.DESIGN: DesignEvaluator(),
            SpecPhase.TASKS: TaskEvaluator(),
        }

    async def run(self) -> bool:
        """
        Run state machine from current phase to completion.

        Returns True if completed successfully, False if failed.
        """
        spec = await self.load_spec()
        if not spec:
            logger.error(f"Spec {self.spec_id} not found")
            return False

        current_phase = spec.current_phase or SpecPhase.EXPLORE.value
        logger.info(f"Starting spec {self.spec_id} from phase {current_phase}")

        try:
            current_idx = self.PHASE_ORDER.index(SpecPhase(current_phase))
        except ValueError:
            current_idx = 0

        for phase in self.PHASE_ORDER[current_idx:]:
            if phase == SpecPhase.COMPLETE:
                await self.mark_complete(spec)
                logger.info(f"Spec {self.spec_id} completed successfully")
                break

            logger.info(f"Executing phase: {phase.value}")
            start_time = datetime.now(timezone.utc)

            try:
                result = await asyncio.wait_for(
                    self.execute_phase(phase, spec),
                    timeout=self.PHASE_TIMEOUTS.get(phase, 300)
                )

                result.duration_seconds = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds()

                await self.save_phase_result(spec, phase, result)
                spec.current_phase = self.next_phase(phase).value
                await self.save_checkpoint(spec)

                logger.info(
                    f"Phase {phase.value} complete in {result.duration_seconds:.1f}s. "
                    f"Score: {result.eval_score:.2f}, Attempts: {result.attempts}"
                )

            except asyncio.TimeoutError:
                logger.error(f"Phase {phase.value} timed out")
                await self.save_error(spec, phase, "Timeout")
                return False

            except Exception as e:
                logger.error(f"Phase {phase.value} failed: {e}")
                await self.save_error(spec, phase, str(e))
                return False

        return True

    async def execute_phase(self, phase: SpecPhase, spec: Any) -> PhaseResult:
        """Execute a single phase with eval-driven retry loop."""
        evaluator = self.evaluators.get(phase)
        prompt = await self.get_phase_prompt(phase, spec)

        for attempt in range(self.max_retries):
            logger.debug(f"Phase {phase.value} attempt {attempt + 1}/{self.max_retries}")

            try:
                # Execute the phase using Claude Agent SDK
                response, session_id = await self._execute_agent_query(phase, prompt)
                result = self.extract_structured_output(response)

                # Skip eval for phases without evaluators (sync)
                if evaluator is None:
                    return PhaseResult(
                        phase=phase,
                        data=result,
                        attempts=attempt + 1,
                        session_id=session_id,
                    )

                eval_result = evaluator.evaluate(result)

                if eval_result.passed:
                    return PhaseResult(
                        phase=phase,
                        data=result,
                        eval_score=eval_result.score,
                        attempts=attempt + 1,
                        session_id=session_id,
                    )

                logger.warning(
                    f"Phase {phase.value} eval failed (attempt {attempt + 1}): "
                    f"{eval_result.failures}"
                )

                # Build retry prompt with failure feedback
                prompt = self.build_retry_prompt(
                    phase, spec, result, eval_result
                )

            except Exception as e:
                logger.error(f"Phase {phase.value} attempt {attempt + 1} error: {e}")
                if attempt == self.max_retries - 1:
                    raise

        raise Exception(
            f"Phase {phase.value} failed after {self.max_retries} attempts"
        )

    async def _execute_agent_query(
        self, phase: SpecPhase, prompt: str
    ) -> tuple[str, Optional[str]]:
        """
        Execute a query using Claude Agent SDK.

        Returns:
            Tuple of (response_text, session_id)
        """
        try:
            from claude_code_sdk import query, ClaudeCodeOptions

            # Create options object for the query
            options = ClaudeCodeOptions(
                max_turns=self.PHASE_MAX_TURNS.get(phase, 20),
                cwd=self.working_directory,
                allowed_tools=["Read", "Write", "Glob", "Grep", "Bash"],
                permission_mode="bypassPermissions",  # Sandbox runs without user interaction
                model=self.model,
            )

            # Use the SDK's query function for one-shot execution
            response_text = ""
            session_id = None

            async for event in query(prompt=prompt, options=options):
                # Handle different event types
                if hasattr(event, "content"):
                    # AssistantMessage has content blocks
                    for block in event.content:
                        if hasattr(block, "text"):
                            response_text += block.text
                elif hasattr(event, "text"):
                    response_text += event.text
                if hasattr(event, "session_id"):
                    session_id = event.session_id

            return response_text, session_id

        except ImportError as e:
            # Fallback for environments without SDK
            logger.warning(f"Claude SDK not available ({e}), using mock response")
            return self._mock_phase_response(phase), None

    def _mock_phase_response(self, phase: SpecPhase) -> str:
        """Generate mock response for testing without SDK."""
        if phase == SpecPhase.EXPLORE:
            return json.dumps({
                "project_type": "fastapi",
                "structure": {"models_dir": "backend/omoi_os/models"},
                "existing_models": [{"name": "Spec", "file": "spec.py", "fields": ["id", "title"]}],
                "conventions": {"naming": "snake_case"},
                "explored_files": ["spec.py"],
                "tech_stack": {"backend": "FastAPI"},
            })
        elif phase == SpecPhase.REQUIREMENTS:
            return json.dumps([{
                "title": "Mock Requirement",
                "condition": "WHEN user creates spec",
                "action": "THE SYSTEM SHALL generate requirements",
                "criteria": [
                    {"text": "Requirements should be generated", "testable": True},
                    {"text": "Requirements should be valid", "testable": True},
                ],
                "priority": "high",
            }])
        elif phase == SpecPhase.DESIGN:
            return json.dumps({
                "architecture": "The system uses a state machine pattern for reliable spec generation. " * 3,
                "data_model": [{"name": "Spec", "fields": [{"name": "id", "type": "uuid"}]}],
                "api_endpoints": [{
                    "method": "POST",
                    "path": "/api/v1/specs",
                    "description": "Create new spec",
                }],
            })
        elif phase == SpecPhase.TASKS:
            return json.dumps([{
                "title": "Implement spec model",
                "description": "Add new fields to spec model",
                "phase": "backend",
                "priority": "high",
                "dependencies": [],
                "acceptance_criteria": ["Model updated"],
            }])
        else:
            return json.dumps({"status": "complete"})

    async def get_phase_prompt(self, phase: SpecPhase, spec: Any) -> str:
        """Get the prompt for a specific phase, including context from previous phases."""
        if phase == SpecPhase.EXPLORE:
            return self._get_explore_prompt(spec)

        elif phase == SpecPhase.REQUIREMENTS:
            exploration = await self.load_phase_data("explore")
            return self._get_requirements_prompt(spec, exploration)

        elif phase == SpecPhase.DESIGN:
            exploration = await self.load_phase_data("explore")
            requirements = await self.load_phase_data("requirements")
            return self._get_design_prompt(spec, exploration, requirements)

        elif phase == SpecPhase.TASKS:
            exploration = await self.load_phase_data("explore")
            requirements = await self.load_phase_data("requirements")
            design = await self.load_phase_data("design")
            return self._get_tasks_prompt(spec, exploration, requirements, design)

        elif phase == SpecPhase.SYNC:
            return self._get_sync_prompt(spec)

        else:
            raise ValueError(f"Unknown phase: {phase}")

    def _get_explore_prompt(self, spec: Any) -> str:
        """Generate exploration phase prompt."""
        title = getattr(spec, 'title', 'Unknown Feature')
        description = getattr(spec, 'description', 'No description provided')

        return f"""
# Codebase Exploration

You are analyzing a codebase to understand its structure, patterns, and conventions.
This context will be used to generate a feature spec that integrates well with existing code.

## Feature Being Planned

Title: {title}
Description: {description}

## Your Task

Use the available tools (Glob, Read, Grep) to discover:

1. **Project Structure**: Main directories, where models/routes/services/tests live
2. **Existing Models**: All model/schema definitions, their fields and relationships
3. **API Patterns**: Route organization, authentication, response formats
4. **Existing Specs**: Check .omoi_os/ for any existing feature specs
5. **Conventions**: Naming (camelCase/snake_case), ID formats, timestamp patterns

## Required Output

After exploration, output a JSON object with this structure:

```json
{{
  "project_type": "fastapi|nextjs|express|...",
  "structure": {{
    "models_dir": "path/to/models",
    "routes_dir": "path/to/routes",
    "tests_dir": "path/to/tests"
  }},
  "existing_models": [
    {{"name": "ModelName", "file": "path", "fields": ["field1", "field2"]}}
  ],
  "existing_routes": [
    {{"path": "/api/endpoint", "methods": ["GET", "POST"]}}
  ],
  "conventions": {{
    "naming": "snake_case",
    "id_format": "uuid",
    "testing": "pytest"
  }},
  "explored_files": ["list", "of", "files", "read"],
  "tech_stack": {{"backend": "FastAPI", "frontend": "Next.js"}},
  "related_to_feature": {{
    "relevant_models": ["Model1", "Model2"],
    "relevant_routes": ["/api/relevant"],
    "integration_points": ["Description of how new feature connects"]
  }}
}}
```

Begin exploration now.
"""

    def _get_requirements_prompt(self, spec: Any, exploration: dict) -> str:
        """Generate requirements phase prompt."""
        title = getattr(spec, 'title', 'Unknown Feature')
        description = getattr(spec, 'description', 'No description provided')

        return f"""
# Requirements Generation

Generate EARS-format requirements for a new feature, based on codebase exploration.

## Codebase Context

{json.dumps(exploration, indent=2)}

## Feature Request

Title: {title}
Description: {description}

## Your Task

Generate requirements that:

1. **Integrate with existing models** - Reference existing entities
2. **Follow conventions** - Match naming, ID formats, patterns
3. **Extend existing routes** - Follow same API structure
4. **Are testable** - Each criterion can be verified

## EARS Format

Each requirement should follow:

- WHEN [condition], THE SYSTEM SHALL [action]
- Include 3-5 acceptance criteria per requirement
- Criteria should be Given/When/Then format

## Required Output

```json
[
  {{
    "title": "Requirement title",
    "condition": "WHEN user does X",
    "action": "THE SYSTEM SHALL do Y",
    "criteria": [
      {{"text": "Given A, when B, then C", "testable": true}},
      {{"text": "Response includes field X", "testable": true}}
    ],
    "integrates_with": ["ExistingModel1"],
    "priority": "high|medium|low"
  }}
]
```

Generate requirements now.
"""

    def _get_design_prompt(
        self, spec: Any, exploration: dict, requirements: Any
    ) -> str:
        """Generate design phase prompt."""
        return f"""
# Design Generation

Create a technical design for implementing the requirements.

## Codebase Context

{json.dumps(exploration, indent=2)}

## Requirements to Implement

{json.dumps(requirements, indent=2)}

## Your Task

Create a design that:

1. **Fits existing architecture** - Follow established patterns
2. **Extends existing models** - Add to, don't duplicate
3. **Follows API conventions** - Match existing route patterns
4. **Is implementable** - Concrete enough to code from

If needed, use Read tool to examine existing architecture files.

## Required Output

```json
{{
  "architecture": "Markdown description of component architecture, how new components fit with existing ones (100+ chars)",
  "data_model": [
    {{
      "name": "NewModel",
      "fields": [{{"name": "id", "type": "uuid"}}, {{"name": "title", "type": "string"}}]
    }}
  ],
  "api_endpoints": [
    {{
      "method": "POST",
      "path": "/api/v1/resource",
      "description": "Create new resource",
      "request_body": {{"field": "type"}},
      "response": {{"field": "type"}},
      "auth": "required"
    }}
  ],
  "error_handling": "Error handling strategy",
  "security_considerations": "Security notes",
  "testing_strategy": "Testing approach"
}}
```

Generate design now.
"""

    def _get_tasks_prompt(
        self,
        spec: Any,
        exploration: dict,
        requirements: Any,
        design: dict,
    ) -> str:
        """Generate tasks phase prompt."""
        return f"""
# Task Generation

Break down the design into implementable tasks.

## Codebase Context

{json.dumps(exploration, indent=2)}

## Requirements

{json.dumps(requirements, indent=2)}

## Design

{json.dumps(design, indent=2)}

## Your Task

Create atomic, implementable tasks that:

1. **Are small enough** - Each completable in 1-4 hours
2. **Have clear scope** - Exactly what to implement
3. **Have dependencies** - Which tasks must complete first
4. **Follow existing patterns** - Reference conventions from exploration

## Required Output

```json
[
  {{
    "title": "Create Model",
    "description": "Add SQLAlchemy model following existing patterns",
    "phase": "backend|frontend|integration|testing",
    "priority": "high|medium|low",
    "estimated_hours": 2,
    "dependencies": [],
    "acceptance_criteria": ["Model created", "Migration added", "Tests pass"],
    "deliverables": ["path/to/file.py"]
  }},
  {{
    "title": "Add routes",
    "description": "Create CRUD routes following existing auth patterns",
    "phase": "backend",
    "priority": "high",
    "estimated_hours": 3,
    "dependencies": ["Create Model"],
    "acceptance_criteria": ["Routes created", "Auth applied", "Tests pass"]
  }}
]
```

Generate tasks now.
"""

    def _get_sync_prompt(self, spec: Any) -> str:
        """Generate sync phase prompt."""
        return """
# Sync to API

All phases are complete. The spec data has been saved to the database.

Output a confirmation message summarizing what was created:

- Number of requirements
- Key design decisions
- Number of tasks
- Ready for implementation

No further action needed - just confirm completion.
"""

    def build_retry_prompt(
        self,
        phase: SpecPhase,
        spec: Any,
        previous_output: Any,
        eval_result: EvalResult,
    ) -> str:
        """Build a retry prompt with feedback about what failed."""
        feedback = eval_result.feedback_for_retry or "\n".join(
            f"- {f}" for f in eval_result.failures
        )

        return f"""
# Retry: {phase.value}

Your previous output failed validation. Please fix and try again.

## Failed Checks

{feedback}

## Your Previous Output

{json.dumps(previous_output, indent=2)}

## Instructions

Fix the issues identified above and regenerate. Make sure:

- All required fields are present
- Formats match the schema exactly
- Content meets quality criteria

Try again now.
"""

    def next_phase(self, current: SpecPhase) -> SpecPhase:
        """Get next phase in order."""
        idx = self.PHASE_ORDER.index(current)
        if idx + 1 >= len(self.PHASE_ORDER):
            return SpecPhase.COMPLETE
        return self.PHASE_ORDER[idx + 1]

    def extract_structured_output(self, response: str) -> dict | list:
        """Extract JSON from agent response."""
        text = str(response)

        # Try to find JSON in code blocks first
        json_match = re.search(
            r'```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```',
            text,
        )
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        obj_match = re.search(r'(\{[\s\S]*\})', text)
        if obj_match:
            try:
                return json.loads(obj_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON array
        arr_match = re.search(r'(\[[\s\S]*\])', text)
        if arr_match:
            try:
                return json.loads(arr_match.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError("Could not extract JSON from response")

    # =========================================================================
    # Database Operations
    # =========================================================================

    async def load_spec(self) -> Any:
        """Load spec from database or create mock if database unavailable.

        In sandbox environments without DATABASE_URL or pgvector, this returns
        a _MockSpec object that stores data in local files instead of database.
        """
        try:
            from omoi_os.models.spec import Spec
            from sqlalchemy import select

            result = await self.db.execute(
                select(Spec).where(Spec.id == self.spec_id)
            )
            spec = result.scalar_one_or_none()

            # If database query returns None but we're in a sandbox, use mock
            if spec is None and hasattr(self.db, '_pending_operations'):
                logger.info(
                    f"No spec found in mock DB for {self.spec_id}, "
                    "creating mock spec for sandbox execution"
                )
                return self._load_or_create_mock_spec()

            return spec

        except ImportError as e:
            # pgvector or sqlalchemy not available - use mock spec
            logger.warning(
                f"Database models unavailable ({e}), using mock spec for "
                f"sandbox execution"
            )
            return self._load_or_create_mock_spec()

        except Exception as e:
            # Other database errors - try mock if it looks like connection issue
            logger.warning(f"Database error: {e}, attempting mock spec fallback")
            return self._load_or_create_mock_spec()

    def _load_or_create_mock_spec(self) -> _MockSpec:
        """Load existing mock spec from checkpoint or create new one.

        Attempts to restore state from file checkpoints if they exist.
        """
        state_file = Path(self.working_directory) / ".omoi_os" / "checkpoints" / "state.json"

        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                mock_spec = _MockSpec(
                    spec_id=self.spec_id,
                    title=state.get("title", "Restored Spec"),
                    description=state.get("description", ""),
                )
                mock_spec.current_phase = state.get("current_phase", SpecPhase.EXPLORE.value)
                mock_spec.phase_data = state.get("phase_data", {})
                mock_spec.phase_attempts = state.get("phase_attempts", {})
                mock_spec.session_transcripts = state.get("session_transcripts", {})
                logger.info(f"Restored mock spec from checkpoint: phase={mock_spec.current_phase}")
                return mock_spec
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}, creating fresh mock spec")

        return _MockSpec(spec_id=self.spec_id)

    async def load_phase_data(self, phase: str) -> dict:
        """Load data from a specific phase."""
        spec = await self.load_spec()
        if not spec or not spec.phase_data:
            return {}
        return spec.phase_data.get(phase, {})

    async def save_phase_result(
        self, spec: Any, phase: SpecPhase, result: PhaseResult
    ) -> None:
        """Save phase result to spec."""
        if spec.phase_data is None:
            spec.phase_data = {}
        spec.phase_data[phase.value] = result.data

        if spec.phase_attempts is None:
            spec.phase_attempts = {}
        spec.phase_attempts[phase.value] = result.attempts

        # Save session transcript if available
        if result.session_id:
            if spec.session_transcripts is None:
                spec.session_transcripts = {}
            spec.session_transcripts[phase.value] = {
                "session_id": result.session_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            if result.transcript_b64:
                spec.session_transcripts[phase.value]["transcript_b64"] = result.transcript_b64

        await self.db.commit()

        # Also write to file checkpoint
        await self._write_file_checkpoint(phase, result.data)

    async def save_checkpoint(self, spec: Any) -> None:
        """Save current state to database."""
        spec.last_checkpoint_at = datetime.now(timezone.utc)
        spec.last_error = None
        await self.db.commit()

        # Write state checkpoint file
        checkpoint_path = Path(self.working_directory) / ".omoi_os" / "checkpoints" / "state.json"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_data = {
            "spec_id": self.spec_id,
            "current_phase": spec.current_phase,
            "completed_phases": [
                p.value for p in self.PHASE_ORDER
                if self.PHASE_ORDER.index(p) < self.PHASE_ORDER.index(SpecPhase(spec.current_phase))
            ],
            "last_checkpoint_at": datetime.now(timezone.utc).isoformat(),
        }
        checkpoint_path.write_text(json.dumps(checkpoint_data, indent=2))

    async def save_error(self, spec: Any, phase: SpecPhase, error: str) -> None:
        """Save error state."""
        spec.last_error = f"{phase.value}: {error}"
        await self.db.commit()

    async def mark_complete(self, spec: Any) -> None:
        """Mark spec as complete."""
        spec.status = "completed"
        spec.current_phase = SpecPhase.COMPLETE.value
        await self.db.commit()

    async def _write_file_checkpoint(self, phase: SpecPhase, data: Any) -> None:
        """Write phase data to file checkpoint."""
        checkpoint_dir = Path(self.working_directory) / ".omoi_os" / "phase_data"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_path = checkpoint_dir / f"{phase.value}.json"
        checkpoint_path.write_text(json.dumps(data, indent=2))

    # =========================================================================
    # Session Transcript Handling
    # =========================================================================

    def get_session_transcript_path(self, session_id: str) -> Path:
        """Get path to session transcript file."""
        project_key = hashlib.sha256(self.working_directory.encode()).hexdigest()[:16]
        return Path.home() / ".claude" / "projects" / project_key / f"{session_id}.jsonl"

    def export_session_transcript(self, session_id: str) -> Optional[str]:
        """Export session transcript as base64-encoded string."""
        transcript_path = self.get_session_transcript_path(session_id)
        if transcript_path.exists():
            content = transcript_path.read_bytes()
            return base64.b64encode(content).decode('utf-8')
        return None

    def hydrate_session_transcript(
        self, session_id: str, transcript_b64: str
    ) -> bool:
        """Restore session transcript for resumption."""
        try:
            transcript_bytes = base64.b64decode(transcript_b64)
            transcript_path = self.get_session_transcript_path(session_id)

            transcript_path.parent.mkdir(parents=True, exist_ok=True)
            transcript_path.write_bytes(transcript_bytes)

            logger.info(f"Hydrated session transcript: {session_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to hydrate transcript: {e}")
            return False


# =========================================================================
# Entry Point for Direct Execution
# =========================================================================


async def run_spec_state_machine(spec_id: str) -> bool:
    """
    Entry point for running the state machine.

    This is called by the orchestrator worker or can be run directly.
    """
    from omoi_os.services.database import DatabaseService

    db_service = DatabaseService()

    async with db_service.async_session() as session:
        machine = SpecStateMachine(
            spec_id=spec_id,
            db_session=session,
            working_directory=os.getcwd(),
        )
        return await machine.run()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python spec_state_machine.py <spec_id>")
        sys.exit(1)

    spec_id = sys.argv[1]
    success = asyncio.run(run_spec_state_machine(spec_id))
    sys.exit(0 if success else 1)
