# Spec Execution Stability Analysis & Solutions

> **Purpose:** Document the current spec-driven development system's architecture, identify sources of instability, and provide actionable solutions for consistent, reliable spec generation.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture](#current-architecture)
3. [Sources of Instability](#sources-of-instability)
4. [Recommended Solution: Agent SDK State Machine](#recommended-solution-agent-sdk-state-machine)
5. [The Exploration Phase](#the-exploration-phase)
6. [Context Flow Between Phases](#context-flow-between-phases)
7. [Implementation Guide](#implementation-guide)
8. [Evaluators & Quality Gates](#evaluators--quality-gates)
9. [API Considerations](#api-considerations)
10. [Migration Path](#migration-path)

---

## Executive Summary

### The Problem

The current spec-driven development system uses Claude Agent SDK to generate specs, requirements, designs, and tasks. However, the execution is **stochastic and unreliable**:

- Sandbox exits prematurely before completion
- Results are inconsistent across runs
- Local execution works better than sandbox execution
- No clear validation or retry mechanisms
- New specs don't align with existing codebase patterns

### Root Causes

1. **Single long-running session** that can fail at any point (HIGH)
2. **No checkpoint/resume capability** (HIGH)
3. **No codebase context gathering** before generation (HIGH)
4. **Weak validation** that runs only at the end (MEDIUM)
5. **No deterministic model configuration** (MEDIUM)

### Recommended Solution

Implement a **State Machine with Agent SDK** that:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   EXPLORE   │───▶│ REQUIREMENTS│───▶│   DESIGN    │───▶│   TASKS     │───▶│    SYNC     │
│  (codebase) │    │  (EARS fmt) │    │ (arch+data) │    │  (atomic)   │    │  (to API)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼                  ▼
   DB SAVE            DB SAVE            DB SAVE            DB SAVE            DB SAVE
```

**Key Principles:**
- Each phase is a **separate Agent SDK invocation** (short, focused)
- Each phase **saves to database** before proceeding
- Each phase can **read codebase** for context (Glob, Read, Grep, LSP)
- Each phase has **validation gates** with retry
- System can **resume from any checkpoint** after failure

### Why Agent SDK (Not Direct API)

The Agent SDK provides critical capabilities we need:

| Capability | Agent SDK | Direct API |
|------------|-----------|------------|
| Read existing code | ✓ Built-in | ✗ Must implement |
| Explore codebase (Glob, Grep) | ✓ Built-in | ✗ Must implement |
| Understand patterns | ✓ Context-aware | ✗ No file access |
| Write files | ✓ Built-in | ✗ Must implement |
| MCP tool integration | ✓ Built-in | ✗ Must implement |

**The fix is not to abandon Agent SDK, but to use it in shorter, focused sessions with checkpoints.**

---

## Current Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           API Layer                                  │
│  POST /api/v1/specs           ← Create spec                         │
│  POST /api/v1/specs/{id}/tasks ← Add tasks                          │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Orchestrator Worker                             │
│  - Polls task queue for pending tasks                               │
│  - Classifies execution mode (exploration/implementation/validation)│
│  - Creates Daytona sandbox                                          │
│  - Spawns claude_sandbox_worker.py                                  │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Daytona Sandbox (Container)                       │
│                                                                      │
│  claude_sandbox_worker.py                                           │
│  ├── Load config from environment                                   │
│  ├── Build system prompt (with optional skill injection)            │
│  ├── Create ClaudeSDKClient                                         │
│  ├── Register MCP servers (spec_workflow tools)                     │
│  ├── Invoke SDK: client.chat()  ← SINGLE LONG SESSION (PROBLEM)    │
│  └── Validate output in PostToolUse hooks                           │
│                                                                      │
│  Generated Artifacts → .omoi_os/                                    │
│  ├── docs/prd-*.md                                                  │
│  ├── requirements/*.md                                              │
│  ├── designs/*.md                                                   │
│  ├── tickets/TKT-*.md                                               │
│  └── tasks/TSK-*.md                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Location | Purpose |
|------|----------|---------|
| `specs.py` | `backend/omoi_os/api/routes/` | Spec CRUD API (1300 lines) |
| `spec.py` | `backend/omoi_os/models/` | Database models |
| `spec_workflow.py` | `backend/omoi_os/mcp/` | MCP tools (585 lines) |
| `claude_sandbox_worker.py` | `backend/omoi_os/workers/` | Main SDK worker (4300 lines) |
| `continuous_sandbox_worker.py` | `backend/omoi_os/workers/` | Iterative mode (1200 lines) |
| `orchestrator_worker.py` | `backend/omoi_os/workers/` | Task assignment (800 lines) |
| `SKILL.md` | `.claude/skills/spec-driven-dev/` | Workflow skill (1440 lines) |

### Current Data Flow (What's Wrong)

1. **User creates spec** via API with title/description
2. **Orchestrator picks up task** from queue
3. **Execution mode classified** (LLM-based or hardcoded fallback)
4. **Sandbox created** with environment variables
5. **Claude SDK invoked** with system prompt + MCP tools
   - ⚠️ **PROBLEM: Single session, 30+ minutes, can timeout**
   - ⚠️ **PROBLEM: No codebase exploration first**
   - ⚠️ **PROBLEM: No intermediate saves**
6. **Claude generates artifacts** in `.omoi_os/` directory
7. **Validation runs** in PostToolUse hooks (too late!)
8. **Results synced** back to API database

---

## Sources of Instability

### 1. Single Long Session (CRITICAL)

**Problem:** One SDK invocation for entire spec generation.

```python
# Current approach - PROBLEMATIC
result = await client.chat(
    initial_prompt="Generate complete spec...",
    max_turns=50,
    # Runs for potentially 30+ minutes
    # Any failure = start over from scratch
)
```

**Impact:**
- Sandbox timeout = all work lost
- No intermediate saves
- Can't resume from failure
- No visibility into progress

### 2. No Codebase Context (CRITICAL)

**Problem:** Specs generated without understanding existing code.

**Impact:**
- New code doesn't match existing patterns
- Duplicate functionality created
- Inconsistent naming conventions
- Missing integration points

### 3. Execution Mode Classification (HIGH)

**Problem:** Inconsistent mode determination with silent fallbacks.

```python
# Current (orchestrator_worker.py)
async def analyze_task_requirements(task_description, task_type, ...):
    try:
        result = await task_analyzer.analyze(...)  # LLM-based
    except:
        # Silent fallback to hardcoded mapping
        if task_type in EXPLORATION_TASK_TYPES:
            return "exploration"
        return "implementation"  # Default - often wrong!
```

### 4. System Prompt Construction (HIGH)

**Problem:** Conditional skill injection creates variable prompts.

```python
# Current (claude_sandbox_worker.py)
if os.environ.get("REQUIRE_SPEC_SKILL") == "true":
    skill_content = get_spec_skill_content()  # May fail silently
    system_prompt += skill_content
```

### 5. Validation Timing (MEDIUM)

**Problem:** Validation only runs at the end, no retry loop.

### 6. Model Configuration (MEDIUM)

**Problem:** No temperature/seed control in Agent SDK.

**Note:** Claude Agent SDK does NOT expose temperature parameter. This is a known limitation. The state machine approach mitigates this by:
- Using shorter, focused prompts (less variability)
- Adding validation gates (catch bad outputs)
- Enabling retries (self-correct)

---

## Recommended Solution: Agent SDK State Machine

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Phase 1: EXPLORE                                 │
│                                                                      │
│  Agent SDK Session #1 (short, focused, ~2-3 min)                    │
│  ├── Glob: Find all models, routes, services                       │
│  ├── Read: Key files (schemas, existing specs)                     │
│  ├── Grep: Find patterns, conventions                              │
│  └── Output: exploration_context (JSON)                            │
│                                                                      │
│  → SAVE TO DATABASE → Can resume from here                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Phase 2: REQUIREMENTS                              │
│                                                                      │
│  Agent SDK Session #2 (uses saved exploration, ~3-5 min)            │
│  ├── Input: exploration_context + user_request                     │
│  ├── Generate: EARS requirements that fit existing patterns        │
│  ├── Validate: Check format, criteria count, testability           │
│  └── Output: requirements (JSON)                                    │
│                                                                      │
│  → SAVE TO DATABASE → Can resume from here                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Phase 3: DESIGN                                  │
│                                                                      │
│  Agent SDK Session #3 (uses exploration + requirements, ~3-5 min)   │
│  ├── Input: exploration + requirements                              │
│  ├── Read: Existing architecture files if needed                   │
│  ├── Generate: Design that integrates with existing code           │
│  ├── Validate: Has architecture, data model, API spec              │
│  └── Output: design (JSON)                                          │
│                                                                      │
│  → SAVE TO DATABASE → Can resume from here                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Phase 4: TASKS                                   │
│                                                                      │
│  Agent SDK Session #4 (uses all previous context, ~2-3 min)         │
│  ├── Input: exploration + requirements + design                    │
│  ├── Generate: Atomic tasks with dependencies                      │
│  ├── Validate: Has descriptions, valid priorities, no cycles       │
│  └── Output: tasks (JSON)                                           │
│                                                                      │
│  → SAVE TO DATABASE → Can resume from here                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Phase 5: SYNC                                    │
│                                                                      │
│  Agent SDK Session #5 (or direct API calls, ~1 min)                 │
│  ├── Push requirements to API                                       │
│  ├── Push design to API                                             │
│  ├── Push tasks to API                                              │
│  └── Update spec status                                             │
│                                                                      │
│  → MARK COMPLETE                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Why This Solves The Problems

| Problem | How State Machine Solves It |
|---------|----------------------------|
| Sandbox exits early | Each phase is short (2-5 min), not 30+ min |
| Work is lost | Saved to DB after each phase |
| Can't resume | Restart from last saved phase |
| No codebase awareness | Explore phase gathers full context |
| New code doesn't fit | Design phase reads existing patterns |
| Inconsistent output | Validation gates with retry |
| No visibility | Clear phase progression, logged attempts |

---

## The Exploration Phase

This is the **most critical phase** - it gathers context that makes all subsequent phases codebase-aware.

### What Exploration Discovers

```python
EXPLORE_PROMPT = """
You are analyzing a codebase to understand its structure and conventions.

## Your Task

Use the available tools (Glob, Read, Grep) to discover:

### 1. Project Structure
- What are the main directories?
- Where are models, routes, services, tests?
- What framework is used (FastAPI, Express, Django, etc.)?

### 2. Existing Models
- Find all model/schema definitions
- What fields and relationships exist?
- What patterns are used (SQLAlchemy, Prisma, etc.)?

### 3. API Patterns
- How are routes organized?
- What authentication is used?
- What response formats are standard?

### 4. Existing Specs
- Check .omoi_os/ directory for existing specs
- What features are already defined?
- What's the current state of implementation?

### 5. Conventions
- Naming conventions (camelCase, snake_case)?
- File organization patterns?
- Testing patterns?

## Output Format

Produce a JSON object with your findings:
```json
{
  "project_type": "fastapi|nextjs|express|django|...",
  "framework_version": "0.100.0",
  "structure": {
    "models_dir": "backend/models",
    "routes_dir": "backend/api/routes",
    "services_dir": "backend/services",
    "tests_dir": "tests"
  },
  "existing_models": [
    {
      "name": "User",
      "file": "backend/models/user.py",
      "fields": ["id", "email", "name", "created_at"],
      "relationships": ["has_many: projects"]
    },
    {
      "name": "Project",
      "file": "backend/models/project.py",
      "fields": ["id", "name", "owner_id", "created_at"],
      "relationships": ["belongs_to: user"]
    }
  ],
  "existing_routes": [
    {"path": "/api/v1/users", "methods": ["GET", "POST"], "auth": "required"},
    {"path": "/api/v1/projects", "methods": ["GET", "POST", "PATCH", "DELETE"], "auth": "required"}
  ],
  "existing_specs": [
    {"title": "User Authentication", "status": "completed"},
    {"title": "Project Management", "status": "in_progress"}
  ],
  "conventions": {
    "naming": "snake_case",
    "id_format": "uuid",
    "timestamp_fields": ["created_at", "updated_at"],
    "soft_delete": true,
    "testing_framework": "pytest",
    "api_versioning": "/api/v1/"
  },
  "tech_stack": {
    "backend": "FastAPI + SQLAlchemy + PostgreSQL",
    "frontend": "Next.js + React + TailwindCSS",
    "auth": "JWT + Keycloak"
  }
}
```
"""
```

### Exploration Implementation

```python
class SpecStateMachine:
    async def run_explore_phase(self, spec_id: str) -> dict:
        """Phase 1: Explore codebase for context."""

        result = await self.agent_sdk.query(
            prompt=EXPLORE_PROMPT,
            max_turns=20,  # Short session, focused task
        )

        # Extract structured context from agent's response
        context = self.extract_json_from_response(result)

        # Save to database - this is our checkpoint
        await self.save_phase_data(spec_id, "explore", context)

        return context
```

### Why Exploration Matters

Without exploration, specs are generated in a vacuum:

```
❌ WITHOUT EXPLORATION:
User: "Add a notifications feature"
Claude: *generates notification models with random field names*
        *creates routes that don't match existing patterns*
        *uses different auth approach than rest of app*

✅ WITH EXPLORATION:
User: "Add a notifications feature"
Claude: *reads existing models, sees snake_case + UUID ids*
        *reads routes, sees /api/v1/ prefix + JWT auth*
        *generates notifications that match existing patterns*
```

---

## Context Flow Between Phases

### Database Schema for Phase Data

```python
# backend/omoi_os/models/spec.py

class Spec(Base):
    __tablename__ = "specs"

    # Existing fields
    id = Column(UUID, primary_key=True, default=uuid4)
    project_id = Column(UUID, ForeignKey("projects.id"))
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="draft")

    # NEW: State machine fields
    current_phase = Column(String, default="explore")
    phase_data = Column(JSON, default={})  # Stores all phase outputs
    last_checkpoint_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    phase_attempts = Column(JSON, default={})  # Track retry counts

    # Relationships
    requirements = relationship("SpecRequirement", back_populates="spec")
    tasks = relationship("SpecTask", back_populates="spec")
```

### How Context Accumulates

```python
# After EXPLORE phase:
spec.phase_data = {
    "explore": {
        "project_type": "fastapi",
        "existing_models": [...],
        "conventions": {...}
    }
}

# After REQUIREMENTS phase:
spec.phase_data = {
    "explore": {...},  # Preserved
    "requirements": [
        {
            "title": "Notification Creation",
            "condition": "WHEN a user triggers a notifiable event",
            "action": "THE SYSTEM SHALL create a notification record",
            "criteria": [...]
        }
    ]
}

# After DESIGN phase:
spec.phase_data = {
    "explore": {...},      # Preserved
    "requirements": [...], # Preserved
    "design": {
        "architecture": "...",
        "data_model": "...",
        "api_endpoints": [...]
    }
}

# After TASKS phase:
spec.phase_data = {
    "explore": {...},
    "requirements": [...],
    "design": {...},
    "tasks": [
        {
            "title": "Create Notification model",
            "description": "...",
            "phase": "backend",
            "priority": "high",
            "dependencies": []
        }
    ]
}
```

### Passing Context to Next Phase

```python
async def run_requirements_phase(self, spec_id: str, user_request: str) -> dict:
    """Phase 2: Generate requirements using codebase context."""

    # Load context from previous phase
    exploration = await self.load_phase_data(spec_id, "explore")

    prompt = f"""
## Codebase Context

You are generating requirements for a codebase with the following characteristics:

Project Type: {exploration['project_type']}
Tech Stack: {json.dumps(exploration.get('tech_stack', {}), indent=2)}

### Existing Models
{json.dumps(exploration.get('existing_models', []), indent=2)}

### Existing Routes
{json.dumps(exploration.get('existing_routes', []), indent=2)}

### Conventions
{json.dumps(exploration.get('conventions', {}), indent=2)}

---

## Feature Request

{user_request}

---

## Your Task

Generate EARS-format requirements for this feature that:

1. **Integrate with existing models** - Reference existing entities where applicable
2. **Follow existing conventions** - Use same naming, ID formats, patterns
3. **Extend existing routes** - Follow same API structure and auth patterns
4. **Are testable** - Each criterion can be verified programmatically

### Output Format

Produce a JSON array of requirements:
```json
[
  {{
    "title": "Requirement title",
    "condition": "WHEN [specific condition]",
    "action": "THE SYSTEM SHALL [specific action]",
    "criteria": [
      {{"text": "Given X, when Y, then Z", "testable": true}},
      {{"text": "The response includes field A", "testable": true}}
    ],
    "integrates_with": ["User", "Project"],  // Existing models referenced
    "extends_routes": ["/api/v1/users"]       // Existing routes extended
  }}
]
```
"""

    result = await self.agent_sdk.query(
        prompt=prompt,
        max_turns=15,
    )

    requirements = self.extract_json_from_response(result)

    # Validate before saving
    eval_result = self.requirement_evaluator.evaluate(requirements)
    if not eval_result.passed:
        # Retry with feedback
        requirements = await self.retry_with_feedback(
            phase="requirements",
            previous_output=requirements,
            failures=eval_result.failures
        )

    await self.save_phase_data(spec_id, "requirements", requirements)
    return requirements
```

---

## Implementation Guide

### File Structure

```
backend/omoi_os/
├── workers/
│   ├── spec_state_machine.py     # NEW: Main state machine
│   ├── claude_sandbox_worker.py  # MODIFY: Use state machine
│   └── orchestrator_worker.py    # MODIFY: Phase-aware scheduling
├── evals/
│   ├── __init__.py               # NEW
│   ├── base.py                   # NEW: BaseEvaluator
│   ├── requirement_eval.py       # NEW: RequirementEvaluator
│   ├── design_eval.py            # NEW: DesignEvaluator
│   └── task_eval.py              # NEW: TaskEvaluator
├── schemas/
│   └── spec_schemas.py           # NEW: Pydantic schemas for phases
└── models/
    └── spec.py                   # MODIFY: Add phase fields
```

### Core State Machine Implementation

```python
# backend/omoi_os/workers/spec_state_machine.py

import asyncio
import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

from claude_sdk import ClaudeSDKClient, ClaudeAgentOptions
from ..evals import RequirementEvaluator, DesignEvaluator, TaskEvaluator

logger = logging.getLogger(__name__)


class SpecPhase(str, Enum):
    EXPLORE = "explore"
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    TASKS = "tasks"
    SYNC = "sync"
    COMPLETE = "complete"


class PhaseResult(BaseModel):
    phase: SpecPhase
    data: Dict[str, Any]
    eval_score: float = 1.0
    attempts: int = 1
    duration_seconds: float = 0.0
    error: Optional[str] = None


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
        db_session,
        working_directory: str = "/workspace",
        max_retries: int = 3,
    ):
        self.spec_id = spec_id
        self.db = db_session
        self.working_directory = working_directory
        self.max_retries = max_retries

        # Initialize evaluators
        self.evaluators = {
            SpecPhase.REQUIREMENTS: RequirementEvaluator(),
            SpecPhase.DESIGN: DesignEvaluator(),
            SpecPhase.TASKS: TaskEvaluator(),
        }

    def _create_agent_client(self, phase: SpecPhase) -> ClaudeSDKClient:
        """Create a fresh Agent SDK client for each phase."""
        return ClaudeSDKClient(ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",  # Faster for focused tasks
            max_turns=self.PHASE_MAX_TURNS.get(phase, 20),
            cwd=self.working_directory,
            permission_mode="bypassPermissions",
            # Tools available: Read, Write, Glob, Grep, Bash, LSP
        ))

    async def run(self) -> bool:
        """
        Run state machine from current phase to completion.

        Returns True if completed successfully, False if failed.
        """
        spec = await self.load_spec()
        logger.info(f"Starting spec {self.spec_id} from phase {spec.current_phase}")

        try:
            current_idx = self.PHASE_ORDER.index(SpecPhase(spec.current_phase))
        except ValueError:
            current_idx = 0

        for phase in self.PHASE_ORDER[current_idx:]:
            if phase == SpecPhase.COMPLETE:
                await self.mark_complete(spec)
                logger.info(f"Spec {self.spec_id} completed successfully")
                break

            logger.info(f"Executing phase: {phase.value}")
            start_time = datetime.utcnow()

            try:
                result = await asyncio.wait_for(
                    self.execute_phase(phase, spec),
                    timeout=self.PHASE_TIMEOUTS.get(phase, 300)
                )

                result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

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

    async def execute_phase(self, phase: SpecPhase, spec) -> PhaseResult:
        """Execute a single phase with eval-driven retry loop."""

        evaluator = self.evaluators.get(phase)
        prompt = await self.get_phase_prompt(phase, spec)

        for attempt in range(self.max_retries):
            logger.debug(f"Phase {phase.value} attempt {attempt + 1}/{self.max_retries}")

            # Create fresh client for each attempt
            client = self._create_agent_client(phase)

            try:
                response = await client.query(prompt)
                result = self.extract_structured_output(response)

                # Skip eval for phases without evaluators (explore, sync)
                if evaluator is None:
                    return PhaseResult(
                        phase=phase,
                        data=result,
                        attempts=attempt + 1
                    )

                eval_result = evaluator.evaluate(result)

                if eval_result.passed:
                    return PhaseResult(
                        phase=phase,
                        data=result,
                        eval_score=eval_result.score,
                        attempts=attempt + 1
                    )

                logger.warning(
                    f"Phase {phase.value} eval failed (attempt {attempt + 1}): "
                    f"{eval_result.failures}"
                )

                # Build retry prompt with failure feedback
                prompt = self.build_retry_prompt(
                    phase, spec, result, eval_result.failures
                )

            finally:
                await client.close()

        raise Exception(
            f"Phase {phase.value} failed after {self.max_retries} attempts"
        )

    async def get_phase_prompt(self, phase: SpecPhase, spec) -> str:
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

    def _get_explore_prompt(self, spec) -> str:
        return f"""
# Codebase Exploration

You are analyzing a codebase to understand its structure, patterns, and conventions.
This context will be used to generate a feature spec that integrates well with existing code.

## Feature Being Planned

Title: {spec.title}
Description: {spec.description or 'No description provided'}

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
  "related_to_feature": {{
    "relevant_models": ["Model1", "Model2"],
    "relevant_routes": ["/api/relevant"],
    "integration_points": ["Description of how new feature connects"]
  }}
}}
```

Begin exploration now.
"""

    def _get_requirements_prompt(self, spec, exploration: dict) -> str:
        return f"""
# Requirements Generation

Generate EARS-format requirements for a new feature, based on codebase exploration.

## Codebase Context

{json.dumps(exploration, indent=2)}

## Feature Request

Title: {spec.title}
Description: {spec.description or 'No description provided'}

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

    def _get_design_prompt(self, spec, exploration: dict, requirements: list) -> str:
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
  "architecture": "Markdown description of component architecture, how new components fit with existing ones",
  "data_model": "Mermaid diagram or description of new/modified models",
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
  "integration_notes": "How this integrates with existing code"
}}
```

Generate design now.
"""

    def _get_tasks_prompt(self, spec, exploration: dict, requirements: list, design: dict) -> str:
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
    "title": "Create NotificationPreference model",
    "description": "Add SQLAlchemy model following existing patterns (snake_case, UUID pk, timestamps)",
    "phase": "backend|frontend|integration|testing",
    "priority": "high|medium|low",
    "estimated_hours": 2,
    "dependencies": [],
    "acceptance_criteria": ["Model created", "Migration added", "Tests pass"]
  }},
  {{
    "title": "Add notification routes",
    "description": "Create CRUD routes at /api/v1/notifications following existing auth patterns",
    "phase": "backend",
    "priority": "high",
    "estimated_hours": 3,
    "dependencies": ["Create NotificationPreference model"],
    "acceptance_criteria": ["Routes created", "Auth applied", "Tests pass"]
  }}
]
```

Generate tasks now.
"""

    def _get_sync_prompt(self, spec) -> str:
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
        spec,
        previous_output: Any,
        failures: List[str]
    ) -> str:
        """Build a retry prompt with feedback about what failed."""
        return f"""
# Retry: {phase.value}

Your previous output failed validation. Please fix and try again.

## Failed Checks

{json.dumps(failures, indent=2)}

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

    def extract_structured_output(self, response) -> dict:
        """Extract JSON from agent response."""
        # Implementation: Parse response text for JSON blocks
        # Handle both ```json blocks and raw JSON
        import json
        import re

        text = str(response)

        # Try to find JSON in code blocks first
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```', text)
        if json_match:
            return json.loads(json_match.group(1))

        # Try to find raw JSON
        for pattern in [r'(\{[\s\S]*\})', r'(\[[\s\S]*\])']:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        raise ValueError("Could not extract JSON from response")

    # Database operations (implement based on your ORM)

    async def load_spec(self):
        """Load spec from database."""
        # return await self.db.query(Spec).filter(Spec.id == self.spec_id).first()
        pass

    async def load_phase_data(self, phase: str) -> dict:
        """Load data from a specific phase."""
        spec = await self.load_spec()
        return spec.phase_data.get(phase, {})

    async def save_phase_result(self, spec, phase: SpecPhase, result: PhaseResult):
        """Save phase result to spec."""
        if spec.phase_data is None:
            spec.phase_data = {}
        spec.phase_data[phase.value] = result.data

        if spec.phase_attempts is None:
            spec.phase_attempts = {}
        spec.phase_attempts[phase.value] = result.attempts

        await self.db.commit()

    async def save_checkpoint(self, spec):
        """Save current state to database."""
        spec.last_checkpoint_at = datetime.utcnow()
        spec.last_error = None
        await self.db.commit()

    async def save_error(self, spec, phase: SpecPhase, error: str):
        """Save error state."""
        spec.last_error = f"{phase.value}: {error}"
        await self.db.commit()

    async def mark_complete(self, spec):
        """Mark spec as complete."""
        spec.status = "completed"
        spec.current_phase = SpecPhase.COMPLETE.value
        await self.db.commit()
```

---

## Evaluators & Quality Gates

### Base Evaluator

```python
# backend/omoi_os/evals/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any, Dict


@dataclass
class EvalResult:
    passed: bool
    score: float  # 0.0 to 1.0
    failures: List[str]
    details: Dict[str, bool]


class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, data: Any) -> EvalResult:
        pass

    def _make_result(self, checks: List[tuple]) -> EvalResult:
        """Helper to build EvalResult from list of (name, passed) tuples."""
        passed = all(c[1] for c in checks)
        score = sum(c[1] for c in checks) / len(checks) if checks else 0.0
        failures = [c[0] for c in checks if not c[1]]
        details = dict(checks)
        return EvalResult(passed=passed, score=score, failures=failures, details=details)
```

### Requirement Evaluator

```python
# backend/omoi_os/evals/requirement_eval.py

from .base import BaseEvaluator, EvalResult
from typing import List


class RequirementEvaluator(BaseEvaluator):
    """Evaluates generated requirements for quality and format."""

    def evaluate(self, requirements: List[dict]) -> EvalResult:
        if not requirements:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["no_requirements"],
                details={"no_requirements": False}
            )

        checks = []

        # Check 1: Has requirements
        has_requirements = len(requirements) >= 1
        checks.append(("has_requirements", has_requirements))

        # Check 2: EARS format (WHEN...SHALL)
        ears_valid = all(
            "WHEN" in req.get("condition", "").upper() or
            "when" in req.get("condition", "").lower()
            for req in requirements
        )
        checks.append(("ears_format", ears_valid))

        # Check 3: Has acceptance criteria (at least 2 per requirement)
        has_criteria = all(
            len(req.get("criteria", [])) >= 2
            for req in requirements
        )
        checks.append(("has_criteria", has_criteria))

        # Check 4: No duplicate titles
        titles = [req.get("title", "") for req in requirements]
        no_duplicates = len(set(titles)) == len(titles)
        checks.append(("no_duplicates", no_duplicates))

        # Check 5: All have titles and actions
        complete = all(
            req.get("title") and req.get("action")
            for req in requirements
        )
        checks.append(("complete_fields", complete))

        # Check 6: Criteria are testable (have action words)
        testable_words = ["should", "must", "will", "returns", "displays",
                         "creates", "updates", "deletes", "within", "less than"]
        criteria_testable = all(
            any(word in c.get("text", "").lower() for word in testable_words)
            for req in requirements
            for c in req.get("criteria", [])
        ) if any(req.get("criteria") for req in requirements) else False
        checks.append(("testable_criteria", criteria_testable))

        return self._make_result(checks)
```

### Design Evaluator

```python
# backend/omoi_os/evals/design_eval.py

from .base import BaseEvaluator, EvalResult


class DesignEvaluator(BaseEvaluator):
    """Evaluates generated design for completeness."""

    def evaluate(self, design: dict) -> EvalResult:
        if not design:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["no_design"],
                details={"no_design": False}
            )

        checks = []

        # Check 1: Has architecture description
        has_arch = bool(design.get("architecture"))
        checks.append(("has_architecture", has_arch))

        # Check 2: Architecture is substantive (not just a few words)
        arch_text = design.get("architecture", "")
        arch_substantive = len(arch_text) > 100
        checks.append(("architecture_substantive", arch_substantive))

        # Check 3: Has data model
        has_data = bool(design.get("data_model"))
        checks.append(("has_data_model", has_data))

        # Check 4: Has API endpoints
        endpoints = design.get("api_endpoints", [])
        has_api = len(endpoints) > 0
        checks.append(("has_api_spec", has_api))

        # Check 5: Endpoints have required fields
        endpoints_complete = all(
            e.get("method") and e.get("path") and e.get("description")
            for e in endpoints
        ) if endpoints else True
        checks.append(("endpoints_complete", endpoints_complete))

        # Check 6: API methods are valid
        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        methods_valid = all(
            e.get("method", "").upper() in valid_methods
            for e in endpoints
        ) if endpoints else True
        checks.append(("valid_methods", methods_valid))

        return self._make_result(checks)
```

### Task Evaluator

```python
# backend/omoi_os/evals/task_eval.py

from .base import BaseEvaluator, EvalResult
from typing import List


class TaskEvaluator(BaseEvaluator):
    """Evaluates generated tasks for quality and implementability."""

    def evaluate(self, tasks: List[dict]) -> EvalResult:
        if not tasks:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["no_tasks"],
                details={"no_tasks": False}
            )

        checks = []

        # Check 1: Has tasks
        has_tasks = len(tasks) >= 1
        checks.append(("has_tasks", has_tasks))

        # Check 2: Tasks have descriptions
        has_descriptions = all(
            bool(t.get("description"))
            for t in tasks
        )
        checks.append(("has_descriptions", has_descriptions))

        # Check 3: Tasks have valid priorities
        valid_priorities = {"low", "medium", "high", "critical"}
        has_priorities = all(
            t.get("priority", "").lower() in valid_priorities
            for t in tasks
        )
        checks.append(("valid_priorities", has_priorities))

        # Check 4: Tasks have valid phases
        valid_phases = {"backend", "frontend", "integration", "testing", "devops", "documentation"}
        has_phases = all(
            t.get("phase", "").lower() in valid_phases
            for t in tasks
        )
        checks.append(("valid_phases", has_phases))

        # Check 5: No duplicate titles
        titles = [t.get("title", "") for t in tasks]
        no_duplicates = len(set(titles)) == len(titles)
        checks.append(("no_duplicates", no_duplicates))

        # Check 6: Dependencies reference valid tasks
        task_titles = set(t.get("title", "") for t in tasks)
        deps_valid = all(
            all(dep in task_titles for dep in t.get("dependencies", []))
            for t in tasks
        )
        checks.append(("valid_dependencies", deps_valid))

        # Check 7: No circular dependencies (simplified check)
        # Full cycle detection would require graph traversal
        no_self_deps = all(
            t.get("title") not in t.get("dependencies", [])
            for t in tasks
        )
        checks.append(("no_self_dependencies", no_self_deps))

        return self._make_result(checks)
```

---

## API Considerations

### Claude Agent SDK Limitations

The Claude Agent SDK has some constraints to be aware of:

| Parameter | Available? | Notes |
|-----------|------------|-------|
| `temperature` | ❌ No | Hardcoded internally |
| `seed` | ❌ No | Not exposed |
| `max_turns` | ✅ Yes | Use to limit session length |
| `max_tokens` | ❌ No | Model default |
| `structured_output` | ❌ No | Must parse JSON from text |
| `tools` | ✅ Yes | Read, Write, Glob, Grep, Bash, etc. |

### Mitigations for Limitations

1. **No temperature control** → Use shorter, more focused prompts (less room for variability)
2. **No structured output** → Provide clear JSON schemas in prompts, validate with evaluators
3. **Can't reduce variability** → Add validation gates and retry on failure

### Context Window Considerations

Claude models have large context windows (200K tokens), but:

- **Exploration context can be large** - Summarize if needed
- **Phase prompts accumulate context** - Keep phase data JSON minimal
- **Don't include full file contents** - Reference files, don't inline them

```python
# Good: Reference files
"existing_models": [{"name": "User", "file": "models/user.py", "fields": ["id", "email"]}]

# Bad: Inline full files
"existing_models": [{"name": "User", "content": "... 500 lines of code ..."}]
```

---

## Migration Path

### Phase 1: Database Migration (Day 1)

Add new fields to Spec model:

```python
# Alembic migration
def upgrade():
    op.add_column('specs', sa.Column('current_phase', sa.String(), default='explore'))
    op.add_column('specs', sa.Column('phase_data', sa.JSON(), default={}))
    op.add_column('specs', sa.Column('last_checkpoint_at', sa.DateTime(), nullable=True))
    op.add_column('specs', sa.Column('last_error', sa.Text(), nullable=True))
    op.add_column('specs', sa.Column('phase_attempts', sa.JSON(), default={}))
```

### Phase 2: Create State Machine (Days 2-3)

1. Create `spec_state_machine.py` with core logic
2. Create evaluators in `evals/` directory
3. Add unit tests for each component

### Phase 3: Integration (Days 4-5)

1. Modify `claude_sandbox_worker.py` to use state machine
2. Update `orchestrator_worker.py` for phase-aware scheduling
3. Add API endpoints for phase status/retry

### Phase 4: Testing & Rollout (Days 6-7)

1. Test with sample specs locally
2. Test in sandbox environment
3. Monitor phase completion rates
4. Tune timeouts and retry counts

---

## Summary

### Key Principles

1. **Short sessions beat long sessions** - Each phase is 2-5 minutes, not 30+
2. **Save early, save often** - Database checkpoint after each phase
3. **Context is king** - Exploration phase makes everything else work
4. **Validate before proceeding** - Catch issues early with evaluators
5. **Retry with feedback** - Self-correct when validation fails

### Expected Outcomes

| Metric | Before | After |
|--------|--------|-------|
| Completion rate | ~40-60% | 90%+ |
| Resume capability | None | Any phase |
| Codebase awareness | None | Full |
| Average runtime | 30+ min (or timeout) | 15-20 min total |
| Debugging visibility | Minimal | Full phase logs |

### Files to Create/Modify

| File | Action | Priority |
|------|--------|----------|
| `spec_state_machine.py` | CREATE | HIGH |
| `evals/__init__.py` | CREATE | HIGH |
| `evals/base.py` | CREATE | HIGH |
| `evals/requirement_eval.py` | CREATE | HIGH |
| `evals/design_eval.py` | CREATE | HIGH |
| `evals/task_eval.py` | CREATE | HIGH |
| `models/spec.py` | MODIFY | HIGH |
| `claude_sandbox_worker.py` | MODIFY | MEDIUM |
| `orchestrator_worker.py` | MODIFY | MEDIUM |

---

## Next Steps

1. Review this document with team
2. Create database migration for phase fields
3. Implement state machine core
4. Implement evaluators
5. Test with simple spec locally
6. Deploy to sandbox environment
7. Monitor and tune
