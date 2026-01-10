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
7. [Session Persistence & Cross-Phase Resumption](#session-persistence--cross-phase-resumption)
8. [Implementation Guide](#implementation-guide)
9. [Evaluators & Quality Gates](#evaluators--quality-gates)
10. [Integration with Existing Skill Scripts](#integration-with-existing-skill-scripts)
11. [API Considerations](#api-considerations)
12. [File Structure & Dependencies](#file-structure--dependencies)
13. [Migration Path](#migration-path)
14. [Summary](#summary)
15. [Next Steps](#next-steps)
16. [Appendix A: Quick Reference](#appendix-quick-reference)
17. [Appendix B: Complete Sandbox Import Inventory](#appendix-b-complete-sandbox-import-inventory)
18. [Appendix C: Local Testing Strategy](#appendix-c-local-testing-strategy)
19. [Appendix D: Reference Templates Quick Reference](#appendix-d-reference-templates-quick-reference)
20. [Appendix E: One-Shot Execution Readiness Checklist](#appendix-e-one-shot-execution-readiness-checklist)

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

1. **Single long-running session** that can fail at any point (CRITICAL)
2. **No checkpoint/resume capability** - despite having session transcript infrastructure (CRITICAL)
3. **No codebase context gathering** before generation (HIGH)
4. **Weak validation** that runs only at the end (MEDIUM)
5. **No deterministic model configuration** (MEDIUM)
6. **Existing skill scripts not leveraged** - parse_specs.py, validate_specs.py exist but unused (MEDIUM)

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
- **Session transcripts are stored** for cross-sandbox resumption
- **File-based checkpoints** provide additional resilience (`.omoi_os/phase_data/`)

### Why Agent SDK (Not Direct API)

The Agent SDK provides critical capabilities we need:

| Capability                    | Agent SDK       | Direct API       |
| ----------------------------- | --------------- | ---------------- |
| Read existing code            | ✓ Built-in      | ✗ Must implement |
| Explore codebase (Glob, Grep) | ✓ Built-in      | ✗ Must implement |
| Understand patterns           | ✓ Context-aware | ✗ No file access |
| Write files                   | ✓ Built-in      | ✗ Must implement |
| MCP tool integration          | ✓ Built-in      | ✗ Must implement |

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

| File                           | Location                          | Purpose                      |
| ------------------------------ | --------------------------------- | ---------------------------- |
| `specs.py`                     | `backend/omoi_os/api/routes/`     | Spec CRUD API (1300 lines)   |
| `spec.py`                      | `backend/omoi_os/models/`         | Database models              |
| `spec_workflow.py`             | `backend/omoi_os/mcp/`            | MCP tools (585 lines)        |
| `claude_sandbox_worker.py`     | `backend/omoi_os/workers/`        | Main SDK worker (4300 lines) |
| `continuous_sandbox_worker.py` | `backend/omoi_os/workers/`        | Iterative mode (1200 lines)  |
| `orchestrator_worker.py`       | `backend/omoi_os/workers/`        | Task assignment (800 lines)  |
| `SKILL.md`                     | `.claude/skills/spec-driven-dev/` | Workflow skill (1440 lines)  |

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

| Problem               | How State Machine Solves It                |
| --------------------- | ------------------------------------------ |
| Sandbox exits early   | Each phase is short (2-5 min), not 30+ min |
| Work is lost          | Saved to DB after each phase               |
| Can't resume          | Restart from last saved phase              |
| No codebase awareness | Explore phase gathers full context         |
| New code doesn't fit  | Design phase reads existing patterns       |
| Inconsistent output   | Validation gates with retry                |
| No visibility         | Clear phase progression, logged attempts   |

---

## The Exploration Phase

This is the **most critical phase** - it gathers context that makes all subsequent phases codebase-aware.

### What Exploration Discovers

````python
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
````

"""

````

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
````

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

````python
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
````

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

````

---

## Session Persistence & Cross-Phase Resumption

This section documents the **existing infrastructure** for session persistence and how the state machine leverages it for reliable cross-phase and cross-sandbox resumption.

### Existing Session Transcript Infrastructure

The system already has robust session transcript capabilities in `daytona_spawner.py` and `claude_sandbox_worker.py`:

#### Environment Variables for Resumption

| Variable | Purpose | Example |
|----------|---------|---------|
| `RESUME_SESSION_ID` | Session ID to resume a previous conversation | `"abc123-session-id"` |
| `FORK_SESSION` | Create new branch from resumed session (don't modify original) | `"true"` |
| `SESSION_TRANSCRIPT_B64` | Base64-encoded transcript for cross-sandbox transfer | `"eyJtZXNzYWdlcyI6...` |
| `CONVERSATION_CONTEXT` | Text summary for conversation hydration (alternative) | `"Previous phase explored..."` |

#### Claude Agent SDK Resumption Parameters

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

options = ClaudeAgentOptions(
    # Resume a previous session by ID
    resume="previous-session-id",

    # Fork instead of continuing (creates new session branch)
    fork_session=True,

    # Continue conversation within same session
    continue_conversation=True,

    # File tools for reading/writing checkpoints
    allowed_tools=["Read", "Write", "Glob", "Grep", "Bash"],

    # Working directory for file operations
    cwd="/workspace",

    # Auto-accept file edits for checkpoint writes
    permission_mode="acceptEdits",
)
````

### Session Transcript Storage Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Phase Execution Flow                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. START PHASE                                                              │
│     ├── Load previous phase data from DB                                    │
│     ├── Check for RESUME_SESSION_ID in environment                          │
│     └── If resuming: Load SESSION_TRANSCRIPT_B64                            │
│                                                                              │
│  2. EXECUTE PHASE (Agent SDK Session)                                        │
│     ├── Short focused session (2-5 minutes)                                 │
│     ├── Agent reads codebase, generates output                              │
│     └── Session ID captured from ResultMessage                              │
│                                                                              │
│  3. SAVE CHECKPOINT                                                          │
│     ├── Extract session transcript from ~/.claude/projects/<key>/<id>.jsonl │
│     ├── Base64 encode transcript                                            │
│     ├── Save to database: spec.session_transcripts[phase] = transcript_b64  │
│     ├── Save phase output to database: spec.phase_data[phase] = {...}       │
│     └── Write to file: .omoi_os/phase_data/{phase}.json (backup)            │
│                                                                              │
│  4. NEXT PHASE or RESUME                                                     │
│     ├── If continuing: Pass RESUME_SESSION_ID + SESSION_TRANSCRIPT_B64      │
│     ├── If new sandbox: Reconstruct from DB transcript                      │
│     └── fork_session=True to avoid modifying original                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Transcript Storage in Database

```python
# backend/omoi_os/models/spec.py - ADDITIONS

class Spec(Base):
    __tablename__ = "specs"

    # Existing fields...

    # NEW: Session transcript storage for cross-phase resumption
    session_transcripts = Column(JSON, default={})
    # Structure:
    # {
    #     "explore": {
    #         "session_id": "abc123",
    #         "transcript_b64": "eyJtZXNzYWdlcyI6Li4u",
    #         "completed_at": "2025-01-10T12:00:00Z"
    #     },
    #     "requirements": {
    #         "session_id": "def456",
    #         "transcript_b64": "eyJtZXNzYWdlcyI6Li4u",
    #         "completed_at": "2025-01-10T12:05:00Z"
    #     }
    # }
```

### Cross-Sandbox Resumption

When a sandbox fails or times out mid-phase, the system can resume in a **new sandbox**:

```python
# In daytona_spawner.py - spawn_for_task() modifications

async def spawn_for_phase(
    self,
    spec_id: str,
    phase: SpecPhase,
    resume_from_failure: bool = False,
) -> str:
    """Spawn sandbox for a specific phase with resumption support."""

    # Load spec and check for previous session
    spec = await self.load_spec(spec_id)

    extra_env = {
        "SPEC_ID": spec_id,
        "SPEC_PHASE": phase.value,
        "PHASE_DATA_B64": base64.b64encode(
            json.dumps(spec.phase_data).encode()
        ).decode(),
    }

    # If resuming from failure, pass the session transcript
    if resume_from_failure and phase.value in spec.session_transcripts:
        transcript_data = spec.session_transcripts[phase.value]
        extra_env["RESUME_SESSION_ID"] = transcript_data["session_id"]
        extra_env["SESSION_TRANSCRIPT_B64"] = transcript_data["transcript_b64"]
        extra_env["FORK_SESSION"] = "true"  # Don't modify original

        logger.info(
            f"Resuming phase {phase.value} from session {transcript_data['session_id'][:8]}..."
        )

    return await self.spawn_for_task(
        task_id=f"spec-{spec_id}-{phase.value}",
        agent_id=f"spec-agent-{spec_id}",
        phase_id=phase.value,
        runtime="claude",
        execution_mode="exploration",
        extra_env=extra_env,
    )
```

### File-Based Checkpoints (Backup)

In addition to database storage, phases write checkpoints to the filesystem for resilience:

```
.omoi_os/
├── phase_data/
│   ├── explore.json           # Exploration context
│   ├── requirements.json      # Generated requirements
│   ├── design.json            # Design document
│   └── tasks.json             # Generated tasks
├── session_transcripts/
│   ├── explore.jsonl          # Raw session transcript
│   ├── requirements.jsonl
│   ├── design.jsonl
│   └── tasks.jsonl
└── checkpoints/
    └── state.json             # Current phase + attempt counts
```

**Checkpoint File Format:**

```json
// .omoi_os/checkpoints/state.json
{
  "spec_id": "uuid-here",
  "current_phase": "design",
  "completed_phases": ["explore", "requirements"],
  "phase_attempts": {
    "explore": 1,
    "requirements": 2,
    "design": 0
  },
  "last_checkpoint_at": "2025-01-10T12:05:00Z",
  "last_error": null
}
```

### Why Both DB and File Checkpoints?

| Storage         | Pros                                           | Cons                       |
| --------------- | ---------------------------------------------- | -------------------------- |
| **Database**    | Centralized, queryable, survives sandbox death | Requires network, can fail |
| **File System** | Fast, works offline, in-sandbox                | Lost if sandbox deleted    |

**Strategy:** Write to files first (fast, local), then sync to DB. On resume, prefer DB (authoritative) but fall back to files if DB unavailable.

### Session Transcript Extraction

The worker extracts transcripts from Claude's session storage:

```python
# In claude_sandbox_worker.py

def get_session_transcript_path(self, session_id: str) -> Path:
    """Get path to session transcript file."""
    # Claude stores sessions in ~/.claude/projects/<project_key>/<session_id>.jsonl
    project_key = hashlib.sha256(self.cwd.encode()).hexdigest()[:16]
    return Path.home() / ".claude" / "projects" / project_key / f"{session_id}.jsonl"

def export_session_transcript(self, session_id: str) -> Optional[str]:
    """Export session transcript as base64-encoded string."""
    transcript_path = self.get_session_transcript_path(session_id)
    if transcript_path.exists():
        content = transcript_path.read_bytes()
        return base64.b64encode(content).decode('utf-8')
    return None
```

### Hydrating from Transcript

When resuming in a new sandbox:

```python
def hydrate_session_transcript(self) -> bool:
    """Restore session transcript for resumption."""
    if not self.session_transcript_b64 or not self.resume_session_id:
        return False

    try:
        # Decode and write transcript to expected location
        transcript_bytes = base64.b64decode(self.session_transcript_b64)
        transcript_path = self.get_session_transcript_path(self.resume_session_id)

        # Ensure directory exists
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_bytes(transcript_bytes)

        logger.info(f"Hydrated session transcript: {self.resume_session_id[:8]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to hydrate transcript: {e}")
        self.resume_session_id = None  # Reset to avoid resume failure
        return False
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

````python
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
````

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

````

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
````

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

## Integration with Existing Skill Scripts

The project already has a comprehensive set of scripts in `.claude/skills/spec-driven-dev/scripts/` that should be leveraged by the state machine rather than reimplemented.

### Available Skill Scripts

| Script              | Purpose                                                         | Usage in State Machine  |
| ------------------- | --------------------------------------------------------------- | ----------------------- |
| `parse_specs.py`    | Parse markdown files with YAML frontmatter from `.omoi_os/`     | SYNC phase reads output |
| `validate_specs.py` | Detect circular dependencies, missing refs, format issues       | Evaluators call this    |
| `api_client.py`     | Sync local specs to OmoiOS API (create/update/skip)             | SYNC phase uses this    |
| `spec_cli.py`       | CLI wrapper for all operations                                  | Manual debugging        |
| `models.py`         | Data classes: ParsedTicket, ParsedTask, ParsedRequirement, etc. | Shared types            |
| `generate_ids.py`   | Generate TKT-XXX, TSK-XXX identifiers                           | Task generation         |
| `init_feature.py`   | Initialize new feature structure in `.omoi_os/`                 | EXPLORE phase may call  |

### Script Integration Points

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        State Machine Phase Integration                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EXPLORE Phase                                                               │
│  └── Uses: init_feature.py (optional, if .omoi_os/ doesn't exist)           │
│                                                                              │
│  REQUIREMENTS Phase                                                          │
│  └── Writes: .omoi_os/requirements/*.md                                     │
│  └── Uses: generate_ids.py for REQ-XXX IDs                                  │
│                                                                              │
│  DESIGN Phase                                                                │
│  └── Writes: .omoi_os/designs/*.md                                          │
│                                                                              │
│  TASKS Phase                                                                 │
│  └── Writes: .omoi_os/tickets/TKT-*.md, .omoi_os/tasks/TSK-*.md            │
│  └── Uses: generate_ids.py for TKT-XXX, TSK-XXX IDs                        │
│                                                                              │
│  SYNC Phase                                                                  │
│  └── Uses: parse_specs.py (SpecParser.parse_all())                          │
│  └── Uses: validate_specs.py (detect_circular_dependencies, etc.)           │
│  └── Uses: api_client.py (OmoiOSClient.sync())                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### SpecParser Usage in SYNC Phase

```python
# In spec_state_machine.py - SYNC phase

from parse_specs import SpecParser
from validate_specs import detect_circular_dependencies, detect_missing_refs
from api_client import OmoiOSClient

async def run_sync_phase(self, spec_id: str) -> PhaseResult:
    """Phase 5: Validate and sync to API using existing scripts."""

    # 1. Parse all generated specs using existing parser
    parser = SpecParser(root_dir=self.working_directory)
    parse_result = parser.parse_all()

    logger.info(
        f"Parsed: {len(parse_result.tickets)} tickets, "
        f"{len(parse_result.tasks)} tasks, "
        f"{len(parse_result.requirements)} requirements"
    )

    # 2. Validate using existing validation functions
    errors = []
    errors.extend(detect_circular_dependencies(parse_result))
    errors.extend(detect_missing_refs(parse_result))

    if errors:
        error_msgs = [f"{e.type}: {e.message}" for e in errors]
        logger.error(f"Validation failed: {error_msgs}")
        raise ValidationError(f"Spec validation failed: {error_msgs}")

    # 3. Sync to API using existing client
    client = OmoiOSClient(
        base_url=os.environ.get("OMOIOS_API_URL"),
        api_key=os.environ.get("OMOIOS_API_KEY"),
    )

    try:
        summary = await client.sync(parse_result)
        logger.info(
            f"Sync complete: {summary.created} created, "
            f"{summary.updated} updated, {summary.skipped} skipped"
        )
    finally:
        await client.close()

    return PhaseResult(
        phase=SpecPhase.SYNC,
        data={
            "tickets_synced": len(parse_result.tickets),
            "tasks_synced": len(parse_result.tasks),
            "requirements_synced": len(parse_result.requirements),
            "sync_summary": {
                "created": summary.created,
                "updated": summary.updated,
                "skipped": summary.skipped,
            }
        },
    )
```

### Evaluator Integration with validate_specs.py

Rather than reimplementing validation, evaluators can call existing scripts:

```python
# In evals/task_eval.py

from validate_specs import detect_circular_dependencies, detect_orphan_tasks

class TaskEvaluator(BaseEvaluator):
    """Uses existing validation scripts for consistency."""

    def evaluate(self, tasks: List[dict]) -> EvalResult:
        checks = []

        # Basic structural checks (inline)
        has_tasks = len(tasks) >= 1
        checks.append(("has_tasks", has_tasks))

        # Convert to ParseResult format for script compatibility
        parse_result = self._to_parse_result(tasks)

        # Use existing circular dependency detection
        circular_errors = detect_circular_dependencies(parse_result)
        no_circular = len(circular_errors) == 0
        checks.append(("no_circular_deps", no_circular))

        # Use existing orphan detection
        orphan_errors = detect_orphan_tasks(parse_result)
        no_orphans = len(orphan_errors) == 0
        checks.append(("no_orphan_tasks", no_orphans))

        return self._make_result(checks)
```

### models.py Shared Types

The `models.py` in the skill scripts defines data classes that should be used consistently:

```python
# From .claude/skills/spec-driven-dev/scripts/models.py

@dataclass
class ParsedTicket:
    id: str
    title: str
    description: str
    status: str
    priority: str
    tasks: list[str]  # Task IDs
    dependencies: TicketDependencies
    source_file: str

@dataclass
class ParsedTask:
    id: str
    title: str
    description: str
    status: str
    estimate: str
    ticket_id: str
    dependencies: TaskDependencies
    acceptance_criteria: list[str]
    source_file: str

@dataclass
class ParsedRequirement:
    id: str
    title: str
    description: str
    acceptance_criteria: list[AcceptanceCriterion]
    priority: str
    category: str
    source_file: str

@dataclass
class ParseResult:
    tickets: list[ParsedTicket]
    tasks: list[ParsedTask]
    requirements: list[ParsedRequirement]
    designs: list[ParsedDesign]
    errors: list[ParseError]
```

### API Client Environment Variables

The `api_client.py` expects these environment variables (already set by `daytona_spawner.py`):

| Variable            | Purpose                            | Set By               |
| ------------------- | ---------------------------------- | -------------------- |
| `OMOIOS_API_URL`    | Base URL for OmoiOS API            | `daytona_spawner.py` |
| `OMOIOS_API_KEY`    | API key for authentication         | `daytona_spawner.py` |
| `OMOIOS_PROJECT_ID` | Project ID for spec ownership      | `daytona_spawner.py` |
| `OMOIOS_TOKEN`      | JWT token (alternative to API key) | Optional             |

### Benefits of Using Existing Scripts

1. **DRY Principle**: No duplicate validation/parsing logic
2. **Battle-tested**: Scripts already work locally and in skill context
3. **Consistent Output**: Same parsing logic = same data structures
4. **Easier Maintenance**: Fix in one place, works everywhere
5. **Skill Compatibility**: Agents using the skill get same behavior as state machine

---

## API Considerations

### Claude Agent SDK Capabilities (Complete Reference)

The Claude Agent SDK (`claude-agent-sdk` / `claude_agent_sdk`) provides these capabilities:

#### ClaudeAgentOptions Parameters

| Parameter               | Available | Type        | Notes                                              |
| ----------------------- | --------- | ----------- | -------------------------------------------------- |
| `model`                 | ✅ Yes    | `str`       | e.g., `"claude-sonnet-4-20250514"`                 |
| `max_turns`             | ✅ Yes    | `int`       | Limit session length (default: 50)                 |
| `cwd`                   | ✅ Yes    | `str`       | Working directory for file operations              |
| `allowed_tools`         | ✅ Yes    | `list[str]` | `["Read", "Write", "Glob", "Grep", "Bash", "LSP"]` |
| `permission_mode`       | ✅ Yes    | `str`       | `"acceptEdits"`, `"bypassPermissions"`, etc.       |
| `resume`                | ✅ Yes    | `str`       | Session ID to resume previous conversation         |
| `fork_session`          | ✅ Yes    | `bool`      | Fork from resumed session (don't modify original)  |
| `continue_conversation` | ✅ Yes    | `bool`      | Continue within same session                       |
| `mcp_servers`           | ✅ Yes    | `list`      | MCP servers for custom tools                       |
| `hooks`                 | ✅ Yes    | `dict`      | PreToolUse, PostToolUse hooks                      |
| `max_budget_usd`        | ✅ Yes    | `float`     | Cost limit per session                             |
| `temperature`           | ❌ No     | -           | Hardcoded internally                               |
| `seed`                  | ❌ No     | -           | Not exposed                                        |
| `max_tokens`            | ❌ No     | -           | Model default                                      |
| `structured_output`     | ❌ No     | -           | Must parse JSON from text                          |

#### Session Resumption Parameters (Critical for State Machine)

```python
options = ClaudeAgentOptions(
    # Resume from a specific session
    resume="previous-session-id",

    # Create new branch instead of modifying original session
    fork_session=True,

    # Continue conversation (same session)
    continue_conversation=True,
)
```

**Important:** When resuming across sandboxes:

1. Extract session transcript from `~/.claude/projects/<hash>/<session_id>.jsonl`
2. Base64 encode and pass via `SESSION_TRANSCRIPT_B64` env var
3. Hydrate to same path in new sandbox before resumption
4. Use `fork_session=True` to avoid corrupting original session

#### Built-in Tools

| Tool       | Purpose                  | State Machine Usage                |
| ---------- | ------------------------ | ---------------------------------- |
| `Read`     | Read file contents       | All phases read codebase           |
| `Write`    | Create/overwrite files   | Write phase outputs to `.omoi_os/` |
| `Edit`     | Edit existing files      | Modify specs during retry          |
| `Glob`     | Find files by pattern    | EXPLORE discovers structure        |
| `Grep`     | Search file contents     | EXPLORE finds patterns             |
| `Bash`     | Execute shell commands   | Run validation scripts             |
| `LSP`      | Language Server Protocol | Code intelligence (optional)       |
| `WebFetch` | Fetch web content        | External docs (optional)           |
| `Task`     | Spawn subagents          | Not used in state machine          |

#### Message Types

```python
from claude_agent_sdk import (
    AssistantMessage,    # Claude's responses
    UserMessage,         # User prompts
    SystemMessage,       # System context
    ResultMessage,       # Final result with session_id
    TextBlock,           # Text content
    ToolUseBlock,        # Tool invocations
    ToolResultBlock,     # Tool outputs
    ThinkingBlock,       # Extended thinking
)
```

### Mitigations for SDK Limitations

| Limitation             | Mitigation Strategy                         |
| ---------------------- | ------------------------------------------- |
| No temperature control | Shorter, focused prompts reduce variability |
| No structured output   | Clear JSON schemas + evaluator validation   |
| No seed parameter      | Validation gates catch inconsistent outputs |
| No max_tokens          | Keep prompts focused, use max_turns         |

### Hooks for Validation

The SDK supports hooks that can be used for inline validation:

```python
from claude_agent_sdk import HookMatcher, ClaudeAgentOptions

async def validate_json_output(input_data, tool_use_id, context):
    """PostToolUse hook to validate Write tool outputs."""
    if input_data.get("tool_name") == "Write":
        content = input_data.get("tool_input", {}).get("content", "")
        # Check if writing to .omoi_os/ with valid frontmatter
        if ".omoi_os/" in input_data.get("tool_input", {}).get("path", ""):
            if not content.startswith("---"):
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "validationError": "Missing YAML frontmatter",
                    }
                }
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PostToolUse": [
            HookMatcher(matcher="Write", hooks=[validate_json_output]),
        ],
    }
)
```

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

## File Structure & Dependencies

### Complete File Structure

This section provides a definitive list of all files to create or modify:

```
backend/omoi_os/
├── workers/
│   ├── spec_state_machine.py       # NEW: Main state machine orchestrator
│   ├── claude_sandbox_worker.py    # MODIFY: Add phase-aware execution
│   └── orchestrator_worker.py      # MODIFY: Phase-based task scheduling
├── evals/
│   ├── __init__.py                 # NEW: Export all evaluators
│   ├── base.py                     # NEW: BaseEvaluator ABC
│   ├── exploration_eval.py         # NEW: Validate exploration context
│   ├── requirement_eval.py         # NEW: Validate EARS requirements
│   ├── design_eval.py              # NEW: Validate design structure
│   └── task_eval.py                # NEW: Validate task dependencies
├── schemas/
│   └── spec_generation.py          # EXISTS: Pydantic schemas (already created)
├── services/
│   └── daytona_spawner.py          # MODIFY: Add spawn_for_phase() method
├── models/
│   └── spec.py                     # MODIFY: Add phase tracking columns
└── api/routes/
    └── specs.py                    # MODIFY: Add phase status endpoints

.claude/skills/spec-driven-dev/scripts/   # EXISTS: Used by state machine
├── api_client.py                   # Used by SYNC phase
├── parse_specs.py                  # Used by SYNC phase
├── validate_specs.py               # Used by evaluators
├── models.py                       # Shared data classes
├── generate_ids.py                 # Used by TASKS phase
├── init_feature.py                 # Used by EXPLORE phase
└── spec_cli.py                     # CLI for debugging

.omoi_os/                           # Generated by state machine
├── phase_data/                     # File-based checkpoints
│   ├── explore.json
│   ├── requirements.json
│   ├── design.json
│   └── tasks.json
├── session_transcripts/            # Session transcripts for resumption
│   ├── explore.jsonl
│   ├── requirements.jsonl
│   ├── design.jsonl
│   └── tasks.jsonl
├── checkpoints/
│   └── state.json                  # Current phase state
├── requirements/                   # Generated requirements
│   └── REQ-*.md
├── designs/                        # Generated designs
│   └── design-*.md
├── tickets/                        # Generated tickets
│   └── TKT-*.md
└── tasks/                          # Generated tasks
    └── TSK-*.md
```

### New Files to Create

#### 1. `spec_state_machine.py` (~400 lines)

Main state machine orchestrator:

```python
# Key classes and methods
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
    eval_score: float
    attempts: int
    session_id: Optional[str]
    transcript_b64: Optional[str]

class SpecStateMachine:
    async def run(self) -> bool: ...
    async def execute_phase(self, phase: SpecPhase) -> PhaseResult: ...
    async def save_checkpoint(self, phase: SpecPhase, result: PhaseResult): ...
    async def resume_from_checkpoint(self, spec_id: str): ...
```

#### 2. `evals/__init__.py`

```python
from .base import BaseEvaluator, EvalResult
from .exploration_eval import ExplorationEvaluator
from .requirement_eval import RequirementEvaluator
from .design_eval import DesignEvaluator
from .task_eval import TaskEvaluator

__all__ = [
    "BaseEvaluator", "EvalResult",
    "ExplorationEvaluator", "RequirementEvaluator",
    "DesignEvaluator", "TaskEvaluator",
]
```

#### 3. `evals/base.py` (~50 lines)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

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
        passed = all(c[1] for c in checks)
        score = sum(c[1] for c in checks) / len(checks) if checks else 0.0
        failures = [c[0] for c in checks if not c[1]]
        return EvalResult(passed=passed, score=score, failures=failures, details=dict(checks))
```

#### 4. `evals/exploration_eval.py` (~60 lines)

```python
class ExplorationEvaluator(BaseEvaluator):
    def evaluate(self, context: dict) -> EvalResult:
        checks = [
            ("has_project_type", bool(context.get("project_type"))),
            ("has_structure", bool(context.get("structure"))),
            ("has_existing_models", len(context.get("existing_models", [])) >= 0),
            ("has_conventions", bool(context.get("conventions"))),
            ("has_related_features", bool(context.get("related_to_feature"))),
        ]
        return self._make_result(checks)
```

### Files to Modify

#### 1. `models/spec.py` - Add Columns

```python
# NEW columns for state machine
current_phase = Column(String, default="explore")
phase_data = Column(JSON, default={})           # {phase: output_data}
session_transcripts = Column(JSON, default={})  # {phase: {session_id, transcript_b64}}
last_checkpoint_at = Column(DateTime, nullable=True)
last_error = Column(Text, nullable=True)
phase_attempts = Column(JSON, default={})       # {phase: attempt_count}
```

#### 2. `daytona_spawner.py` - Add Method

```python
async def spawn_for_phase(
    self,
    spec_id: str,
    phase: SpecPhase,
    resume_from_failure: bool = False,
) -> str:
    """Spawn sandbox for a specific spec generation phase."""
    # Implementation in Session Persistence section
```

#### 3. `claude_sandbox_worker.py` - Phase Awareness

```python
# Read phase from environment
spec_phase = os.environ.get("SPEC_PHASE")
phase_data_b64 = os.environ.get("PHASE_DATA_B64")

if spec_phase:
    # Phase-specific execution
    phase_data = json.loads(base64.b64decode(phase_data_b64))
    # Build phase-specific prompt...
```

### Database Migration

```python
# alembic/versions/xxx_add_spec_phase_tracking.py

def upgrade():
    op.add_column('specs', sa.Column('current_phase', sa.String(), server_default='explore'))
    op.add_column('specs', sa.Column('phase_data', sa.JSON(), server_default='{}'))
    op.add_column('specs', sa.Column('session_transcripts', sa.JSON(), server_default='{}'))
    op.add_column('specs', sa.Column('last_checkpoint_at', sa.DateTime(), nullable=True))
    op.add_column('specs', sa.Column('last_error', sa.Text(), nullable=True))
    op.add_column('specs', sa.Column('phase_attempts', sa.JSON(), server_default='{}'))

def downgrade():
    op.drop_column('specs', 'phase_attempts')
    op.drop_column('specs', 'last_error')
    op.drop_column('specs', 'last_checkpoint_at')
    op.drop_column('specs', 'session_transcripts')
    op.drop_column('specs', 'phase_data')
    op.drop_column('specs', 'current_phase')
```

### Dependencies

The state machine requires these packages (already in project):

| Package            | Purpose              | Version   |
| ------------------ | -------------------- | --------- |
| `claude-agent-sdk` | Agent SDK for Claude | `>=0.1.0` |
| `pydantic`         | Schema validation    | `>=2.0`   |
| `sqlalchemy`       | Database ORM         | `>=2.0`   |
| `httpx`            | Async HTTP client    | `>=0.25`  |
| `pyyaml`           | YAML parsing         | `>=6.0`   |

### Pydantic Schemas (Already Exist)

The schemas in `backend/omoi_os/schemas/spec_generation.py` are already created and should be used:

```python
from omoi_os.schemas import (
    # Enums
    SpecPhase, SpecStatus, RequirementCategory, Priority,
    TicketStatus, TaskStatus, TaskType, Estimate,
    # Exploration
    ExplorationContext, CodebasePattern, ExistingComponent, DatabaseSchema,
    # Requirements
    Requirement, AcceptanceCriterion, RequirementsOutput,
    # Design
    ApiEndpoint, DataModel, DataModelField, DesignOutput,
    # Tasks
    Task, Ticket, TaskDependencies, TicketDependencies, TasksOutput,
    # State Machine
    PhaseResult, SpecGenerationState, EvaluationResult,
)
```

---

## Migration Path

### Phase 1: Database Migration (Day 1)

Add new fields to Spec model (see File Structure & Dependencies for full migration):

```python
# Alembic migration
def upgrade():
    op.add_column('specs', sa.Column('current_phase', sa.String(), server_default='explore'))
    op.add_column('specs', sa.Column('phase_data', sa.JSON(), server_default='{}'))
    op.add_column('specs', sa.Column('session_transcripts', sa.JSON(), server_default='{}'))  # NEW
    op.add_column('specs', sa.Column('last_checkpoint_at', sa.DateTime(), nullable=True))
    op.add_column('specs', sa.Column('last_error', sa.Text(), nullable=True))
    op.add_column('specs', sa.Column('phase_attempts', sa.JSON(), server_default='{}'))
```

### Phase 2: Create State Machine (Days 2-3)

1. Create `spec_state_machine.py` with core logic
2. Create evaluators in `evals/` directory
3. Add unit tests for each component
4. Integrate existing skill scripts (`parse_specs.py`, `validate_specs.py`, `api_client.py`)

### Phase 3: Integration (Days 4-5)

1. Add `spawn_for_phase()` method to `daytona_spawner.py`
2. Modify `claude_sandbox_worker.py` to support phase-aware execution
3. Update `orchestrator_worker.py` for phase-based scheduling
4. Add API endpoints for phase status/retry/resume

### Phase 4: Testing & Rollout (Days 6-7)

1. Test with sample specs locally
2. Test session transcript storage/resumption
3. Test cross-sandbox resumption (kill mid-phase, resume in new sandbox)
4. Monitor phase completion rates
5. Tune timeouts and retry counts

---

## Summary

### Key Principles

1. **Short sessions beat long sessions** - Each phase is 2-5 minutes, not 30+
2. **Save early, save often** - Database + file checkpoints after each phase
3. **Context is king** - Exploration phase makes everything else work
4. **Validate before proceeding** - Catch issues early with evaluators
5. **Retry with feedback** - Self-correct when validation fails
6. **Session transcripts enable resumption** - Store and hydrate for cross-sandbox recovery
7. **Leverage existing scripts** - Don't reimplement parsing/validation/sync

### Expected Outcomes

| Metric               | Before               | After                         |
| -------------------- | -------------------- | ----------------------------- |
| Completion rate      | ~40-60%              | 90%+                          |
| Resume capability    | None                 | Any phase, any sandbox        |
| Codebase awareness   | None                 | Full exploration context      |
| Average runtime      | 30+ min (or timeout) | 15-20 min total               |
| Debugging visibility | Minimal              | Full phase logs + checkpoints |
| Failure recovery     | Start over           | Resume from last checkpoint   |

### Files to Create/Modify (Complete List)

| File                               | Action | Priority | Purpose                |
| ---------------------------------- | ------ | -------- | ---------------------- |
| `workers/spec_state_machine.py`    | CREATE | CRITICAL | Main orchestrator      |
| `evals/__init__.py`                | CREATE | HIGH     | Export evaluators      |
| `evals/base.py`                    | CREATE | HIGH     | BaseEvaluator ABC      |
| `evals/exploration_eval.py`        | CREATE | HIGH     | Validate exploration   |
| `evals/requirement_eval.py`        | CREATE | HIGH     | Validate requirements  |
| `evals/design_eval.py`             | CREATE | HIGH     | Validate design        |
| `evals/task_eval.py`               | CREATE | HIGH     | Validate tasks         |
| `models/spec.py`                   | MODIFY | CRITICAL | Add phase columns      |
| `services/daytona_spawner.py`      | MODIFY | HIGH     | Add spawn_for_phase()  |
| `workers/claude_sandbox_worker.py` | MODIFY | MEDIUM   | Phase-aware execution  |
| `workers/orchestrator_worker.py`   | MODIFY | MEDIUM   | Phase scheduling       |
| `api/routes/specs.py`              | MODIFY | LOW      | Phase status endpoints |

### Existing Assets to Leverage

| Asset                       | Location                                         | Usage                |
| --------------------------- | ------------------------------------------------ | -------------------- |
| `parse_specs.py`            | `.claude/skills/spec-driven-dev/scripts/`        | SYNC phase parsing   |
| `validate_specs.py`         | `.claude/skills/spec-driven-dev/scripts/`        | Evaluator validation |
| `api_client.py`             | `.claude/skills/spec-driven-dev/scripts/`        | SYNC phase API calls |
| `models.py`                 | `.claude/skills/spec-driven-dev/scripts/`        | Shared data classes  |
| `spec_generation.py`        | `backend/omoi_os/schemas/`                       | Pydantic schemas     |
| Session transcript handling | `daytona_spawner.py`, `claude_sandbox_worker.py` | Already implemented  |

---

## Next Steps

1. **Review this document** - Ensure no gaps remain
2. **Create database migration** - Add all phase tracking columns including `session_transcripts`
3. **Implement evaluators** - Start with `base.py`, then specific evaluators
4. **Implement state machine** - Core `SpecStateMachine` class
5. **Add `spawn_for_phase()`** - Modify `daytona_spawner.py`
6. **Test locally** - Run phases individually, verify checkpointing
7. **Test resumption** - Kill mid-phase, verify cross-sandbox resume works
8. **Deploy to sandbox environment**
9. **Monitor and tune** - Adjust timeouts, retry counts based on real-world data

---

## Appendix A: Quick Reference

### Environment Variables for Phase Execution

| Variable                 | Purpose                                                |
| ------------------------ | ------------------------------------------------------ |
| `SPEC_ID`                | Spec being generated                                   |
| `SPEC_PHASE`             | Current phase (explore/requirements/design/tasks/sync) |
| `PHASE_DATA_B64`         | Base64-encoded previous phase outputs                  |
| `RESUME_SESSION_ID`      | Session ID to resume                                   |
| `SESSION_TRANSCRIPT_B64` | Transcript for cross-sandbox resumption                |
| `FORK_SESSION`           | "true" to fork instead of modify                       |

### Phase Timeouts

| Phase        | Timeout      | Max Turns |
| ------------ | ------------ | --------- |
| EXPLORE      | 180s (3 min) | 25        |
| REQUIREMENTS | 300s (5 min) | 20        |
| DESIGN       | 300s (5 min) | 25        |
| TASKS        | 180s (3 min) | 15        |
| SYNC         | 120s (2 min) | 10        |

### Evaluator Pass Criteria

| Evaluator    | Key Checks                                  |
| ------------ | ------------------------------------------- |
| Exploration  | Has project_type, structure, conventions    |
| Requirements | EARS format, 2+ criteria per req, testable  |
| Design       | Has architecture, data_model, api_endpoints |
| Tasks        | Valid priorities, phases, no circular deps  |

---

## Appendix B: Complete Sandbox Import Inventory

This section provides the **definitive list of all files that must be available in the sandbox** for the state machine to work correctly. Missing any of these files will cause failures.

### Files Copied to Sandbox (from Repository)

#### 1. Skill Files (REQUIRED)

These files provide templates, validation, and API integration:

| Source Path                                                | Sandbox Destination                                                   | Purpose                                |
| ---------------------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------- |
| `.claude/skills/spec-driven-dev/SKILL.md`                  | `/workspace/.claude/skills/spec-driven-dev/SKILL.md`                  | Main skill workflow instructions       |
| `.claude/skills/spec-driven-dev/scripts/api_client.py`     | `/workspace/.claude/skills/spec-driven-dev/scripts/api_client.py`     | SYNC phase API integration             |
| `.claude/skills/spec-driven-dev/scripts/parse_specs.py`    | `/workspace/.claude/skills/spec-driven-dev/scripts/parse_specs.py`    | Parse spec files with frontmatter      |
| `.claude/skills/spec-driven-dev/scripts/validate_specs.py` | `/workspace/.claude/skills/spec-driven-dev/scripts/validate_specs.py` | Validate spec structure/dependencies   |
| `.claude/skills/spec-driven-dev/scripts/models.py`         | `/workspace/.claude/skills/spec-driven-dev/scripts/models.py`         | Shared data classes                    |
| `.claude/skills/spec-driven-dev/scripts/generate_ids.py`   | `/workspace/.claude/skills/spec-driven-dev/scripts/generate_ids.py`   | Generate unique IDs for specs          |
| `.claude/skills/spec-driven-dev/scripts/init_feature.py`   | `/workspace/.claude/skills/spec-driven-dev/scripts/init_feature.py`   | Initialize feature directory structure |
| `.claude/skills/spec-driven-dev/scripts/spec_cli.py`       | `/workspace/.claude/skills/spec-driven-dev/scripts/spec_cli.py`       | CLI for debugging/manual sync          |

#### 2. Reference Templates (REQUIRED)

These templates define the expected format for each artifact type:

| Source Path                                                          | Sandbox Destination                                                             | Used By                   |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------- |
| `.claude/skills/spec-driven-dev/references/requirements_template.md` | `/workspace/.claude/skills/spec-driven-dev/references/requirements_template.md` | REQUIREMENTS phase        |
| `.claude/skills/spec-driven-dev/references/design_template.md`       | `/workspace/.claude/skills/spec-driven-dev/references/design_template.md`       | DESIGN phase              |
| `.claude/skills/spec-driven-dev/references/ticket_template.md`       | `/workspace/.claude/skills/spec-driven-dev/references/ticket_template.md`       | TASKS phase               |
| `.claude/skills/spec-driven-dev/references/task_template.md`         | `/workspace/.claude/skills/spec-driven-dev/references/task_template.md`         | TASKS phase               |
| `.claude/skills/spec-driven-dev/references/claude_sdk_patterns.md`   | `/workspace/.claude/skills/spec-driven-dev/references/claude_sdk_patterns.md`   | All phases (SDK patterns) |

#### 3. Pydantic Schemas (REQUIRED for Validation)

These schemas define the expected structure of outputs:

| Source Path                                  | Sandbox Destination                                     | Purpose                 |
| -------------------------------------------- | ------------------------------------------------------- | ----------------------- |
| `backend/omoi_os/schemas/spec_generation.py` | `/workspace/backend/omoi_os/schemas/spec_generation.py` | Phase output validation |
| `backend/omoi_os/schemas/__init__.py`        | `/workspace/backend/omoi_os/schemas/__init__.py`        | Export schemas          |

**Note:** The evaluators use these schemas to validate phase outputs. They must be importable in the sandbox.

#### 4. Evaluators (NEW - Created During Implementation)

These will be created during implementation and must be available:

| File                                        | Sandbox Path                                           | Purpose                      |
| ------------------------------------------- | ------------------------------------------------------ | ---------------------------- |
| `backend/omoi_os/evals/__init__.py`         | `/workspace/backend/omoi_os/evals/__init__.py`         | Export evaluators            |
| `backend/omoi_os/evals/base.py`             | `/workspace/backend/omoi_os/evals/base.py`             | BaseEvaluator ABC            |
| `backend/omoi_os/evals/exploration_eval.py` | `/workspace/backend/omoi_os/evals/exploration_eval.py` | Validate EXPLORE output      |
| `backend/omoi_os/evals/requirement_eval.py` | `/workspace/backend/omoi_os/evals/requirement_eval.py` | Validate REQUIREMENTS output |
| `backend/omoi_os/evals/design_eval.py`      | `/workspace/backend/omoi_os/evals/design_eval.py`      | Validate DESIGN output       |
| `backend/omoi_os/evals/task_eval.py`        | `/workspace/backend/omoi_os/evals/task_eval.py`        | Validate TASKS output        |

### Files Passed via Environment Variables

These are passed as Base64-encoded data, not copied:

| Variable                 | Contains               | Decoded To                                  |
| ------------------------ | ---------------------- | ------------------------------------------- |
| `PHASE_DATA_B64`         | Previous phase outputs | `.omoi_os/phase_data/{phase}.json`          |
| `SESSION_TRANSCRIPT_B64` | Session for resumption | `~/.claude/projects/{hash}/{session}.jsonl` |
| `SPEC_CONFIG_B64`        | Spec configuration     | `.omoi_os/config.json`                      |

### Files Generated in Sandbox (Outputs)

These are created by the state machine during execution:

```
.omoi_os/
├── phase_data/
│   ├── explore.json           # EXPLORE phase output
│   ├── requirements.json      # REQUIREMENTS phase output
│   ├── design.json            # DESIGN phase output
│   └── tasks.json             # TASKS phase output
├── session_transcripts/
│   ├── explore.jsonl          # EXPLORE session transcript
│   ├── requirements.jsonl     # REQUIREMENTS session transcript
│   ├── design.jsonl           # DESIGN session transcript
│   └── tasks.jsonl            # TASKS session transcript
├── checkpoints/
│   └── state.json             # Current state checkpoint
├── docs/
│   └── prd-{feature}.md       # Generated PRD
├── requirements/
│   └── {feature}.md           # Generated requirements
├── designs/
│   └── {feature}.md           # Generated design
├── tickets/
│   └── TKT-{NUM}.md           # Generated tickets
└── tasks/
    └── TSK-{NUM}.md           # Generated tasks
```

### Sandbox Setup Script

The following script should be run by `daytona_spawner.py` to prepare the sandbox:

```python
async def setup_sandbox_for_spec_generation(
    workspace_path: str,
    spec_id: str,
    phase: SpecPhase,
    phase_data: dict,
    resume_session_id: Optional[str] = None,
    session_transcript_b64: Optional[str] = None,
) -> None:
    """Setup sandbox with all required files for spec generation."""

    # 1. Copy skill files (CRITICAL)
    skill_files = [
        ".claude/skills/spec-driven-dev/SKILL.md",
        ".claude/skills/spec-driven-dev/scripts/api_client.py",
        ".claude/skills/spec-driven-dev/scripts/parse_specs.py",
        ".claude/skills/spec-driven-dev/scripts/validate_specs.py",
        ".claude/skills/spec-driven-dev/scripts/models.py",
        ".claude/skills/spec-driven-dev/scripts/generate_ids.py",
        ".claude/skills/spec-driven-dev/scripts/init_feature.py",
        ".claude/skills/spec-driven-dev/scripts/spec_cli.py",
    ]
    for src in skill_files:
        dest = Path(workspace_path) / src
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PROJECT_ROOT / src, dest)

    # 2. Copy reference templates (CRITICAL)
    template_files = [
        ".claude/skills/spec-driven-dev/references/requirements_template.md",
        ".claude/skills/spec-driven-dev/references/design_template.md",
        ".claude/skills/spec-driven-dev/references/ticket_template.md",
        ".claude/skills/spec-driven-dev/references/task_template.md",
        ".claude/skills/spec-driven-dev/references/claude_sdk_patterns.md",
    ]
    for src in template_files:
        dest = Path(workspace_path) / src
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PROJECT_ROOT / src, dest)

    # 3. Copy schema files for validation
    schema_files = [
        "backend/omoi_os/schemas/__init__.py",
        "backend/omoi_os/schemas/spec_generation.py",
    ]
    for src in schema_files:
        dest = Path(workspace_path) / src
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PROJECT_ROOT / src, dest)

    # 4. Copy evaluator files
    eval_files = [
        "backend/omoi_os/evals/__init__.py",
        "backend/omoi_os/evals/base.py",
        "backend/omoi_os/evals/exploration_eval.py",
        "backend/omoi_os/evals/requirement_eval.py",
        "backend/omoi_os/evals/design_eval.py",
        "backend/omoi_os/evals/task_eval.py",
    ]
    for src in eval_files:
        dest = Path(workspace_path) / src
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PROJECT_ROOT / src, dest)

    # 5. Create output directories
    output_dirs = [
        ".omoi_os/phase_data",
        ".omoi_os/session_transcripts",
        ".omoi_os/checkpoints",
        ".omoi_os/docs",
        ".omoi_os/requirements",
        ".omoi_os/designs",
        ".omoi_os/tickets",
        ".omoi_os/tasks",
    ]
    for dir_path in output_dirs:
        (Path(workspace_path) / dir_path).mkdir(parents=True, exist_ok=True)

    # 6. Write phase data from previous phases
    if phase_data:
        for phase_name, data in phase_data.items():
            phase_file = Path(workspace_path) / f".omoi_os/phase_data/{phase_name}.json"
            with open(phase_file, "w") as f:
                json.dump(data, f, indent=2)

    # 7. Hydrate session transcript if resuming
    if session_transcript_b64 and resume_session_id:
        project_hash = compute_project_hash(workspace_path)
        transcript_dir = Path.home() / ".claude/projects" / project_hash
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = transcript_dir / f"{resume_session_id}.jsonl"
        transcript_bytes = base64.b64decode(session_transcript_b64)
        with open(transcript_file, "wb") as f:
            f.write(transcript_bytes)

    logger.info(f"Sandbox setup complete for spec {spec_id}, phase {phase}")
```

### Import Verification Checklist

Before executing any phase, verify these files exist:

```python
def verify_sandbox_imports(workspace_path: str) -> List[str]:
    """Verify all required files are present. Returns list of missing files."""
    required_files = [
        # Skill files
        ".claude/skills/spec-driven-dev/SKILL.md",
        ".claude/skills/spec-driven-dev/scripts/api_client.py",
        ".claude/skills/spec-driven-dev/scripts/parse_specs.py",
        ".claude/skills/spec-driven-dev/scripts/validate_specs.py",
        ".claude/skills/spec-driven-dev/scripts/models.py",
        # Reference templates
        ".claude/skills/spec-driven-dev/references/requirements_template.md",
        ".claude/skills/spec-driven-dev/references/design_template.md",
        ".claude/skills/spec-driven-dev/references/ticket_template.md",
        ".claude/skills/spec-driven-dev/references/task_template.md",
        # Schemas
        "backend/omoi_os/schemas/spec_generation.py",
        # Evaluators
        "backend/omoi_os/evals/base.py",
    ]

    missing = []
    for file_path in required_files:
        full_path = Path(workspace_path) / file_path
        if not full_path.exists():
            missing.append(file_path)

    return missing
```

---

## Appendix C: Local Testing Strategy

Testing the state machine locally before deploying to a sandbox is **critical** for catching issues early. This section describes how to test each component.

### Why Local Testing First

1. **Faster iteration** - No sandbox startup delay (30s+ saved per test)
2. **Better debugging** - Full access to logs, breakpoints, file system
3. **Cheaper** - No Daytona costs during development
4. **Reproducible** - Easier to reproduce and fix issues
5. **One-shot confidence** - Higher chance of sandbox execution succeeding

### Local Testing Setup

#### 1. Create Test Environment

```bash
# Create a test workspace (simulates sandbox)
mkdir -p /tmp/test-spec-workspace
cd /tmp/test-spec-workspace

# Initialize with required structure
mkdir -p .claude/skills/spec-driven-dev/{scripts,references}
mkdir -p backend/omoi_os/{schemas,evals}
mkdir -p .omoi_os/{phase_data,session_transcripts,checkpoints,docs,requirements,designs,tickets,tasks}

# Copy skill files from repository
cp -r $REPO_ROOT/.claude/skills/spec-driven-dev/* .claude/skills/spec-driven-dev/

# Copy schemas
cp $REPO_ROOT/backend/omoi_os/schemas/spec_generation.py backend/omoi_os/schemas/
cp $REPO_ROOT/backend/omoi_os/schemas/__init__.py backend/omoi_os/schemas/
```

#### 2. Set Up Environment Variables

```bash
# Create .env file for local testing
cat > .env << 'EOF'
# API (for SYNC phase)
OMOIOS_API_URL=http://localhost:8000
OMOIOS_API_KEY=test-api-key
OMOIOS_PROJECT_ID=test-project-123

# Spec configuration
SPEC_ID=spec-test-001
SPEC_PHASE=explore  # Change for each phase test

# Optional: Resume from previous session
# RESUME_SESSION_ID=xxx
# SESSION_TRANSCRIPT_B64=...
EOF

source .env
```

### Testing Individual Components

#### Test 1: Validate Skill Scripts Work

```bash
# Test parsing
cd /tmp/test-spec-workspace

# Create a sample spec file
cat > .omoi_os/requirements/test.md << 'EOF'
---
id: REQ-TEST-001
title: Test Requirement
feature: test-feature
created: 2025-01-10
updated: 2025-01-10
status: draft
category: functional
priority: HIGH
---

# Test Requirement

## 1. Core Requirements

#### REQ-TEST-CORE-001: Example
THE SYSTEM SHALL do something.
EOF

# Test parsing
python .claude/skills/spec-driven-dev/scripts/parse_specs.py .omoi_os/

# Expected output: Parsed requirements, no errors
```

#### Test 2: Validate Schemas Work

```python
# test_schemas.py
import sys
sys.path.insert(0, "/tmp/test-spec-workspace")

from backend.omoi_os.schemas.spec_generation import (
    ExplorationContext,
    RequirementsOutput,
    DesignOutput,
    TasksOutput,
    SpecPhase,
)

# Test exploration context
context = ExplorationContext(
    project_type="Next.js + FastAPI",
    structure={"frontend": "Next.js", "backend": "FastAPI"},
    existing_models=[{"name": "User", "file": "models/user.py"}],
    conventions={"naming": "snake_case"},
    related_to_feature=["existing_feature"],
)
print(f"Exploration context valid: {context.project_type}")

# Test requirements output
reqs = RequirementsOutput(
    requirements=[],
    feature_name="test-feature",
)
print(f"Requirements output valid: {reqs.feature_name}")

print("All schemas validated successfully!")
```

#### Test 3: Validate Evaluators Work

```python
# test_evaluators.py
import sys
sys.path.insert(0, "/tmp/test-spec-workspace")

from backend.omoi_os.evals import (
    ExplorationEvaluator,
    RequirementEvaluator,
    DesignEvaluator,
    TaskEvaluator,
)

# Test exploration evaluator
exp_eval = ExplorationEvaluator()
result = exp_eval.evaluate({
    "project_type": "Next.js",
    "structure": {"frontend": "src/"},
    "conventions": {"naming": "camelCase"},
    "related_to_feature": [],
})
print(f"Exploration eval: passed={result.passed}, score={result.score}")

# Expected: passed=True (or close), with specific failures listed if any
```

#### Test 4: Test Phase Execution Locally (Without SDK)

```python
# test_phase_local.py
"""Test phase logic without invoking Claude SDK."""

import json
from pathlib import Path

# Simulate EXPLORE phase output
explore_output = {
    "project_type": "Next.js 15 + FastAPI backend",
    "structure": {
        "frontend": "frontend/src/",
        "backend": "backend/omoi_os/",
        "api_routes": "backend/omoi_os/api/routes/",
    },
    "existing_models": [
        {"name": "Spec", "file": "backend/omoi_os/models/spec.py"},
        {"name": "Ticket", "file": "backend/omoi_os/models/ticket.py"},
    ],
    "conventions": {
        "naming": "snake_case for backend, camelCase for frontend",
        "testing": "pytest for backend, vitest for frontend",
    },
    "related_to_feature": ["spec workflow", "ticket management"],
}

# Save to phase_data
Path(".omoi_os/phase_data").mkdir(parents=True, exist_ok=True)
with open(".omoi_os/phase_data/explore.json", "w") as f:
    json.dump(explore_output, f, indent=2)

# Validate with evaluator
from backend.omoi_os.evals import ExplorationEvaluator

evaluator = ExplorationEvaluator()
result = evaluator.evaluate(explore_output)

print(f"Phase: EXPLORE")
print(f"Passed: {result.passed}")
print(f"Score: {result.score:.2f}")
print(f"Failures: {result.failures}")

if result.passed:
    print("\n✅ Ready to proceed to REQUIREMENTS phase")
else:
    print("\n❌ Fix failures before proceeding")
```

#### Test 5: Test Full Pipeline Locally

```bash
#!/bin/bash
# test_full_pipeline.sh

set -e

WORKSPACE="/tmp/test-spec-workspace"
cd "$WORKSPACE"

echo "=== Testing Full Spec Generation Pipeline ==="

# Phase 1: EXPLORE
echo "Phase 1: EXPLORE"
python -c "
import json
from pathlib import Path

output = {
    'project_type': 'Test Project',
    'structure': {'src': 'src/'},
    'existing_models': [],
    'conventions': {'naming': 'snake_case'},
    'related_to_feature': [],
}
Path('.omoi_os/phase_data').mkdir(parents=True, exist_ok=True)
with open('.omoi_os/phase_data/explore.json', 'w') as f:
    json.dump(output, f)
print('EXPLORE phase output saved')
"

# Validate
python -c "
from backend.omoi_os.evals import ExplorationEvaluator
import json
with open('.omoi_os/phase_data/explore.json') as f:
    data = json.load(f)
result = ExplorationEvaluator().evaluate(data)
print(f'EXPLORE validation: passed={result.passed}, score={result.score:.2f}')
assert result.passed, 'EXPLORE validation failed'
"

echo "✅ All phases validated locally"
echo "Ready for sandbox execution"
```

### Testing with Claude SDK Locally

For testing the actual Claude SDK integration locally (without Daytona):

```python
# test_sdk_local.py
"""Test Claude SDK phase execution locally."""

import asyncio
import os
from pathlib import Path

# Set environment
os.environ["SPEC_ID"] = "test-spec-001"
os.environ["SPEC_PHASE"] = "explore"

async def test_explore_phase():
    """Run EXPLORE phase with Claude SDK locally."""
    from claude_agent_sdk import ClaudeAgentSDKClient, ClaudeAgentOptions

    workspace = Path("/tmp/test-spec-workspace")

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-20250514",
        max_turns=10,  # Low for testing
        cwd=str(workspace),
        allowed_tools=["Read", "Glob", "Grep"],  # Read-only for EXPLORE
        permission_mode="acceptEdits",
    )

    client = ClaudeAgentSDKClient(options)

    prompt = """
    You are in the EXPLORE phase. Analyze the workspace structure and identify:
    1. Project type (frameworks, languages)
    2. Directory structure
    3. Existing models/components
    4. Naming conventions
    5. Related features

    Output your findings as JSON to .omoi_os/phase_data/explore.json
    """

    result = await client.query(prompt)

    # Check output file was created
    output_file = workspace / ".omoi_os/phase_data/explore.json"
    if output_file.exists():
        print(f"✅ EXPLORE phase completed, output at: {output_file}")
        with open(output_file) as f:
            print(f"Content: {f.read()[:500]}...")
    else:
        print("❌ EXPLORE phase did not produce output file")

    return result

if __name__ == "__main__":
    asyncio.run(test_explore_phase())
```

### Pre-Sandbox Checklist

Before deploying to sandbox, verify:

```markdown
## Local Testing Checklist

### Files

- [ ] All skill scripts copied and importable
- [ ] All reference templates present
- [ ] Pydantic schemas importable
- [ ] Evaluators importable and passing

### Component Tests

- [ ] `parse_specs.py` parses sample files correctly
- [ ] `validate_specs.py` detects errors in invalid files
- [ ] `api_client.py` can connect to local API
- [ ] All evaluators return sensible results

### Integration Tests

- [ ] EXPLORE phase produces valid JSON
- [ ] REQUIREMENTS phase uses EARS format
- [ ] DESIGN phase includes architecture diagram
- [ ] TASKS phase creates tickets and tasks

### SDK Tests (Optional but Recommended)

- [ ] Claude SDK can be invoked locally
- [ ] Phase prompts produce expected outputs
- [ ] Validation catches malformed outputs

### Environment

- [ ] All required env vars documented
- [ ] No hardcoded paths
- [ ] Works on clean workspace
```

---

## Appendix D: Reference Templates Quick Reference

The skill includes templates that define the **exact format** expected for each artifact. Using these templates ensures:

1. Consistent frontmatter structure
2. Parseable output for validation
3. Traceability between artifacts

### Template Locations

| Template     | Path                                                                 | Used By            |
| ------------ | -------------------------------------------------------------------- | ------------------ |
| Requirements | `.claude/skills/spec-driven-dev/references/requirements_template.md` | REQUIREMENTS phase |
| Design       | `.claude/skills/spec-driven-dev/references/design_template.md`       | DESIGN phase       |
| Ticket       | `.claude/skills/spec-driven-dev/references/ticket_template.md`       | TASKS phase        |
| Task         | `.claude/skills/spec-driven-dev/references/task_template.md`         | TASKS phase        |

### Required Frontmatter Fields (Summary)

#### Requirements (`REQ-{DOMAIN}-{NUM}`)

```yaml
---
id: REQ-{DOMAIN}-001
title: {Feature Name} Requirements
feature: {feature-name}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft
category: functional
priority: HIGH
design_ref: designs/{feature-name}.md
condition: "{EARS WHEN clause}"
action: "{EARS SHALL clause}"
---
```

#### Designs (`DESIGN-{FEATURE}-{NUM}`)

```yaml
---
id: DESIGN-{FEATURE}-001
title: {Feature Name} Design
feature: {feature-name}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft
requirements:
  - REQ-{DOMAIN}-001
---
```

#### Tickets (`TKT-{NUM}`)

```yaml
---
id: TKT-{NUM}
title: { Ticket Title }
status: backlog
priority: MEDIUM
estimate: M
created: { YYYY-MM-DD }
updated: { YYYY-MM-DD }
feature: { feature-name }
requirements:
  - REQ-XXX-YYY
design_ref: designs/{feature-name}.md
tasks:
  - TSK-{NUM}
dependencies:
  blocked_by: []
  blocks: []
  related: []
---
```

#### Tasks (`TSK-{NUM}`)

```yaml
---
id: TSK-{NUM}
title: { Task Title }
status: pending
parent_ticket: TKT-{NUM}
estimate: M
created: { YYYY-MM-DD }
assignee: null
dependencies:
  depends_on: []
  blocks: []
---
```

### How Templates Are Used

1. **REQUIREMENTS phase**: Claude reads `requirements_template.md` and generates files matching the format
2. **DESIGN phase**: Claude reads `design_template.md` and generates design docs
3. **TASKS phase**: Claude reads both ticket and task templates, creates both

### Template Injection in Prompts

Each phase prompt should include template context:

```python
def build_requirements_prompt(exploration_context: dict, feature_name: str) -> str:
    template_path = ".claude/skills/spec-driven-dev/references/requirements_template.md"

    return f"""
    You are in the REQUIREMENTS phase.

    ## Context from Exploration
    {json.dumps(exploration_context, indent=2)}

    ## Task
    Generate requirements for feature: {feature_name}

    ## Format
    Read the template at {template_path} and follow its exact structure.

    Key requirements:
    - Use EARS format (WHEN... THE SYSTEM SHALL...)
    - Include YAML frontmatter with all required fields
    - Reference the design doc that will be created
    - Each requirement must be testable

    Output to: .omoi_os/requirements/{feature_name}.md
    """
```

---

## Appendix E: One-Shot Execution Readiness Checklist

This checklist ensures the implementation is ready for reliable one-shot execution in production.

### Pre-Implementation Verification

| Category          | Check                               | Status |
| ----------------- | ----------------------------------- | ------ |
| **Documentation** | All phases documented with prompts  | ☐      |
| **Documentation** | Evaluator criteria clearly defined  | ☐      |
| **Documentation** | Environment variables documented    | ☐      |
| **Documentation** | File structure fully specified      | ☐      |
| **Schemas**       | All Pydantic schemas created        | ☐      |
| **Schemas**       | Schemas match expected outputs      | ☐      |
| **Templates**     | All reference templates present     | ☐      |
| **Templates**     | Templates have required frontmatter | ☐      |

### Implementation Verification

| Category          | Check                             | Status |
| ----------------- | --------------------------------- | ------ |
| **State Machine** | `spec_state_machine.py` created   | ☐      |
| **State Machine** | All phases implemented            | ☐      |
| **State Machine** | Checkpoint save/restore works     | ☐      |
| **Evaluators**    | All evaluators implemented        | ☐      |
| **Evaluators**    | Evaluators use existing scripts   | ☐      |
| **Database**      | Migration created                 | ☐      |
| **Database**      | Phase columns added to Spec model | ☐      |
| **Spawner**       | `spawn_for_phase()` implemented   | ☐      |
| **Spawner**       | All files copied to sandbox       | ☐      |
| **Worker**        | Phase-aware execution added       | ☐      |

### Local Testing Verification

| Category        | Check                        | Status |
| --------------- | ---------------------------- | ------ |
| **Unit Tests**  | Evaluators have unit tests   | ☐      |
| **Unit Tests**  | State machine has unit tests | ☐      |
| **Integration** | Full pipeline tested locally | ☐      |
| **Integration** | Checkpoint resume tested     | ☐      |
| **SDK Tests**   | Claude SDK invocation tested | ☐      |
| **SDK Tests**   | Phase outputs validated      | ☐      |

### Sandbox Testing Verification

| Category       | Check                        | Status |
| -------------- | ---------------------------- | ------ |
| **Setup**      | All files copied correctly   | ☐      |
| **Setup**      | Directories created          | ☐      |
| **Setup**      | Environment variables passed | ☐      |
| **Execution**  | EXPLORE phase completes      | ☐      |
| **Execution**  | REQUIREMENTS phase completes | ☐      |
| **Execution**  | DESIGN phase completes       | ☐      |
| **Execution**  | TASKS phase completes        | ☐      |
| **Execution**  | SYNC phase completes         | ☐      |
| **Resumption** | Session transcript saved     | ☐      |
| **Resumption** | Cross-sandbox resume works   | ☐      |

### Production Readiness

| Category        | Check                       | Status |
| --------------- | --------------------------- | ------ |
| **Monitoring**  | Phase progress logged       | ☐      |
| **Monitoring**  | Errors captured to Sentry   | ☐      |
| **API**         | Phase status endpoint works | ☐      |
| **API**         | Retry endpoint works        | ☐      |
| **Performance** | Phase timeouts appropriate  | ☐      |
| **Performance** | No memory leaks             | ☐      |

### Final Sign-Off

- [ ] All local tests pass
- [ ] All sandbox tests pass
- [ ] Documentation complete and accurate
- [ ] Ready for production deployment
