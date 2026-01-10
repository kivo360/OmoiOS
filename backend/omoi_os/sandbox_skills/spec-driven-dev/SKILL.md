---
name: spec-driven-dev
description: Spec-driven development workflow for turning feature ideas into structured PRDs, requirements, designs, tickets, and tasks. Uses a state machine approach with EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC phases. Each phase has validation gates, checkpointing, and session transcript support for cross-sandbox resumption.
---

# Spec-Driven Development

A systematic workflow for turning feature ideas into actionable work items that AI agents can execute.

> **Architecture Note:** This skill is designed to work with a **state machine orchestrator** that executes each phase as a separate Claude SDK session. Each phase saves checkpoints to the database and can resume from any point after failure. See `docs/spec-execution-stability.md` for the full architecture.

---

## 🔴 CRITICAL: Read This Skill Document Thoroughly

**YOU MUST follow this skill document exactly.** This is not optional guidance—it is the required workflow.

### Before Creating ANY Spec Files:

1. **READ THIS ENTIRE SKILL DOCUMENT** - Don't skim. Read every section to understand the required formats.
2. **CHECK EXISTING FILES** - Run `ls -la .omoi_os/` to see what already exists. Don't duplicate.
3. **REFERENCE THE TEMPLATES** - Every file type has a specific format. Copy the exact structure.
4. **USE THE CLI TOOLS** - Validate with `python spec_cli.py validate` before syncing.

### During Spec Creation:

1. **REFER BACK TO THIS DOCUMENT OFTEN** - When unsure about format, re-read the relevant section.
2. **COPY FRONTMATTER EXACTLY** - Don't improvise. Use the exact field names shown in templates.
3. **CHECK YOUR WORK** - After creating files, run validation to catch errors early.

### Output Requirements:

- **ALL files MUST have YAML frontmatter** - No exceptions
- **ALL frontmatter fields MUST match the templates** - Use exact field names
- **ALL specs MUST be synced** - Run `python spec_cli.py sync push` when done
- **ALL IDs MUST follow conventions** - TKT-001, TSK-001, REQ-FEATURE-001, etc.

### If You're Unsure:

1. **Re-read this skill document** - The answer is here
2. **Look at the Concrete Example section** - Full file contents are provided
3. **Run validation** - `python spec_cli.py validate` will tell you what's wrong

---

## 🔄 State Machine Architecture

### Overview

Spec generation runs as a **state machine** with discrete phases. Each phase:
1. Receives context from previous phases
2. Executes a focused, time-boxed Claude SDK session
3. Validates output with evaluators
4. Saves checkpoint to database and file system
5. Stores session transcript for potential resumption

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   EXPLORE   │───▶│ REQUIREMENTS│───▶│   DESIGN    │───▶│   TASKS     │───▶│    SYNC     │
│  (codebase) │    │  (EARS fmt) │    │ (arch+data) │    │  (atomic)   │    │  (to API)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼                  ▼
   CHECKPOINT         CHECKPOINT         CHECKPOINT         CHECKPOINT         COMPLETE
```

### Phase Definitions

| Phase | Purpose | Output | Timeout | Max Turns |
|-------|---------|--------|---------|-----------|
| **EXPLORE** | Analyze codebase structure, patterns, conventions | `explore.json` | 3 min | 25 |
| **REQUIREMENTS** | Generate EARS-format requirements | `requirements.json` + `.omoi_os/requirements/*.md` | 5 min | 20 |
| **DESIGN** | Create architecture, data models, APIs | `design.json` + `.omoi_os/designs/*.md` | 5 min | 25 |
| **TASKS** | Break down into tickets and tasks | `tasks.json` + `.omoi_os/tickets/*.md` + `.omoi_os/tasks/*.md` | 3 min | 15 |
| **SYNC** | Push all artifacts to OmoiOS API | API sync complete | 2 min | 10 |

### Phase Context Flow

Each phase receives accumulated context from all previous phases:

```python
# REQUIREMENTS phase receives:
{
    "exploration_context": {
        "project_type": "Next.js + FastAPI",
        "existing_models": [...],
        "conventions": {...},
        "related_to_feature": [...]
    },
    "feature_request": "User's original request"
}

# DESIGN phase receives:
{
    "exploration_context": {...},
    "requirements": [...],  # From REQUIREMENTS phase
    "feature_name": "feature-name"
}

# TASKS phase receives:
{
    "exploration_context": {...},
    "requirements": [...],
    "design": {...},  # From DESIGN phase
    "feature_name": "feature-name"
}
```

### Evaluator Criteria

Each phase output is validated before proceeding:

| Phase | Evaluator | Pass Criteria |
|-------|-----------|---------------|
| EXPLORE | ExplorationEvaluator | Has `project_type`, `structure`, `conventions`, `related_to_feature` |
| REQUIREMENTS | RequirementEvaluator | EARS format, 2+ acceptance criteria per requirement, testable |
| DESIGN | DesignEvaluator | Has `architecture`, `data_model`, `api_endpoints` |
| TASKS | TaskEvaluator | Valid priorities, phases, no circular dependencies, no orphan tasks |

### Retry Logic

If validation fails:
1. Evaluator returns failure reasons
2. State machine retries the phase (max 3 attempts)
3. Retry prompt includes previous attempt and failure reasons
4. If all retries fail, phase is marked as failed with error details

### Session Transcript Persistence

Session transcripts are stored for cross-sandbox resumption:

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
│   └── ...
└── checkpoints/
    └── state.json             # Current state checkpoint
```

### Environment Variables

When running in a sandbox, these environment variables control execution:

| Variable | Purpose |
|----------|---------|
| `SPEC_ID` | Spec being generated |
| `SPEC_PHASE` | Current phase (explore/requirements/design/tasks/sync) |
| `PHASE_DATA_B64` | Base64-encoded previous phase outputs |
| `RESUME_SESSION_ID` | Session ID to resume |
| `SESSION_TRANSCRIPT_B64` | Transcript for cross-sandbox resumption |
| `FORK_SESSION` | "true" to fork instead of modify |

---

## 🚨 MANDATORY: YAML Frontmatter on ALL Files

**EVERY file you create in `.omoi_os/` MUST begin with YAML frontmatter.** This is NON-NEGOTIABLE.

### Why Frontmatter is Required

1. **Programmatic Parsing**: The CLI tools, API sync, and orchestrator all parse frontmatter to understand file structure
2. **Traceability**: Frontmatter enables linking requirements → designs → tickets → tasks
3. **Status Tracking**: Status, priority, and dependencies are tracked via frontmatter fields
4. **API Integration**: When syncing to backend, frontmatter provides the structured data

### Required Frontmatter by File Type

**PRDs** (`.omoi_os/docs/prd-*.md`):
```yaml
---
id: PRD-{FEATURE}-001
title: {Feature Name} PRD
feature: {feature-name}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft  # draft | review | approved
author: Claude
---
```

**Requirements** (`.omoi_os/requirements/*.md`):
```yaml
---
id: REQ-{FEATURE}-001
title: {Feature Name} Requirements
feature: {feature-name}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft  # draft | review | approved
category: functional  # functional | non-functional | constraint
priority: HIGH  # CRITICAL | HIGH | MEDIUM | LOW
prd_ref: docs/prd-{feature-name}.md
design_ref: designs/{feature-name}.md
---
```

**Designs** (`.omoi_os/designs/*.md`):
```yaml
---
id: DESIGN-{FEATURE}-001
title: {Feature Name} Design
feature: {feature-name}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: draft  # draft | review | approved
requirements:
  - REQ-{FEATURE}-001
# API endpoints (synced to Design panel)
api_endpoints:
  - method: POST
    path: /api/v1/{resource}
    description: Create a new resource
    auth_required: true
    request_body: '{"field": "value"}'
    response: '{"id": "uuid", "field": "value"}'
  - method: GET
    path: /api/v1/{resource}/{id}
    description: Get resource by ID
    auth_required: true
    path_params: [id]
# Data models (synced to Design panel)
data_models:
  - name: ResourceModel
    description: Main resource entity
    table_name: resources
    typed_fields:
      - name: id
        type: uuid
        description: Unique identifier
        constraints: [primary_key]
      - name: name
        type: string
        description: Resource name
      - name: created_at
        type: timestamp
        default: now()
    relationships:
      - belongs_to User
      - has_many Items
---
```

**Tickets** (`.omoi_os/tickets/TKT-*.md`):
```yaml
---
id: TKT-{NNN}
title: {Ticket Title}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: backlog  # backlog | analyzing | building | testing | done | blocked
priority: HIGH  # CRITICAL | HIGH | MEDIUM | LOW
estimate: M  # S | M | L | XL
design_ref: designs/{feature-name}.md
requirements:
  - REQ-{FEATURE}-FUNC-001
dependencies:
  blocked_by: []
  blocks: []
---
```

**Tasks** (`.omoi_os/tasks/TSK-*.md`):
```yaml
---
id: TSK-{NNN}
title: {Task Title}
created: {YYYY-MM-DD}
status: pending  # pending | in_progress | review | done | blocked
parent_ticket: TKT-{NNN}
estimate: S  # S | M | L
type: implementation  # implementation | refactor | test | documentation | research | bugfix
dependencies:
  depends_on: []
  blocks: []
---
```

### ❌ Files Without Frontmatter Will Fail

Files missing frontmatter will:
- Not appear in `spec_cli.py show` commands
- Not sync to the API
- Not be tracked in traceability reports
- Not be picked up by the orchestrator

### ✅ Always Start With Frontmatter

When creating ANY file in `.omoi_os/`, your FIRST action should be writing the YAML frontmatter block, THEN the content.

---

## 🚨 MANDATORY: Use Spec CLI to Sync to Server

**After creating files in `.omoi_os/`, you MUST sync them to the OmoiOS server using the spec CLI.** This is NON-NEGOTIABLE.

### Why Sync is Required

1. **Visibility**: Specs/tickets/tasks only appear in the dashboard after syncing
2. **Orchestration**: The orchestrator only picks up tasks from the database, not from files
3. **Traceability**: Server-side tracking enables dependency management and status updates
4. **Persistence**: Local files can be lost; server data persists across sandbox restarts

### Spec CLI Location

The spec CLI is located at:
```
/root/.claude/skills/spec-driven-dev/scripts/spec_cli.py
```

### Required Workflow: Create → Validate → Sync

**EVERY time you create or modify files in `.omoi_os/`, follow this workflow:**

```bash
# Step 1: Navigate to the spec CLI scripts directory
cd /root/.claude/skills/spec-driven-dev/scripts

# Step 2: Validate your specs (check for errors BEFORE syncing)
python spec_cli.py validate

# Step 3: Preview what will be synced (dry run)
# Note: OMOIOS_PROJECT_ID and OMOIOS_API_URL are auto-injected - no need to specify!
python spec_cli.py sync-specs diff

# Step 4: Sync requirements and designs to create specs
python spec_cli.py sync-specs push

# Step 5: Preview ticket/task sync
python spec_cli.py sync diff

# Step 6: Sync tickets and tasks
python spec_cli.py sync push

# Step 7: Verify traceability
python spec_cli.py api-trace
```

### Environment Variables (Auto-Injected by Sandbox)

When the sandbox is created, the orchestrator **automatically injects** environment variables so that CLI tools and scripts work without manual configuration. This design means:

1. **No manual URL configuration** - The API client knows where to connect
2. **No credential passing** - Authentication is pre-configured
3. **No project ID lookup** - The context is already set

**Auto-injected variables:**
| Variable | Description | Example Value |
|----------|-------------|---------------|
| `OMOIOS_API_URL` | API endpoint URL | `https://api.omoios.dev` |
| `OMOIOS_API_KEY` | Authentication key | `sk-...` |
| `OMOIOS_PROJECT_ID` | Current project ID | `proj-abc123` |
| `TASK_ID` | Current task being executed | `task-xyz789` |
| `AGENT_ID` | Agent executing the task | `agent-def456` |
| `EXECUTION_MODE` | Skill loading mode | `implementation` or `exploration` |

**Fallback behavior:** If running outside a sandbox (e.g., local development), the CLI falls back to `https://api.omoios.dev` as the default API URL. You can override any value by passing explicit arguments like `--api-url` or `--project-id` if needed.

**Bottom line:** Just run the commands - no configuration required inside sandboxes.

### Quick Reference Commands

```bash
# Show all local specs
python spec_cli.py show all

# Show only tickets
python spec_cli.py show tickets

# Show only tasks with blocking status
python spec_cli.py show tasks

# Show dependency graph
python spec_cli.py show graph

# Show ready tasks (not blocked)
python spec_cli.py show ready

# List projects from server (uses OMOIOS_API_URL automatically)
python spec_cli.py projects

# View project details (uses OMOIOS_PROJECT_ID and OMOIOS_API_URL automatically)
python spec_cli.py project
```

### ❌ DO NOT Skip Syncing

If you only create local files without syncing:
- Tasks won't be picked up by agents
- Tickets won't appear in the dashboard
- Dependencies won't be tracked
- Status updates won't propagate

---

## The Core Flow

The workflow maps to the state machine phases:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STATE MACHINE PHASES                                  │
│                                                                             │
│   EXPLORE ──────▶ REQUIREMENTS ──────▶ DESIGN ──────▶ TASKS ──────▶ SYNC   │
│     │                  │                 │              │            │      │
│   Analyze          Define WHAT       Define HOW     Break into    Push to  │
│   codebase         must happen       to build it    work items    API      │
│   context                                                                    │
│                                                                             │
│   explore.json   requirements/*.md  designs/*.md   tickets/*.md   API      │
│                                                    tasks/*.md     synced   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Output Directory:** All artifacts go in `.omoi_os/`
**Sync Tool:** Use `spec_cli.py` to push to the API
**State Machine:** Each phase is a separate SDK session with checkpointing

---

## Phase 1: EXPLORE (Most Important!)

> **State Machine Phase:** `EXPLORE` - Timeout: 3 min, Max Turns: 25
> **Output:** `.omoi_os/phase_data/explore.json`

### Why This Phase Matters

The quality of everything downstream depends on deeply understanding the problem AND the existing codebase first. **Never skip exploration.** Rushing to create specs without understanding leads to wasted work and specs that don't align with existing patterns.

### Step 1.1: Explore Existing Context

**BEFORE asking questions, gather context:**

```bash
# Check for existing documentation
Read docs/CLAUDE.md
Read docs/architecture/
ls .omoi_os/

# Search for related code
Grep for related service names, models, patterns
Read existing implementations this feature will integrate with

# Check for prior work
ls .omoi_os/requirements/
ls .omoi_os/tickets/
git log --oneline -20
```

### Step 1.2: Ask Discovery Questions (5-15 Questions)

**Structure your questions in categories:**

#### Problem & Value (2-3 questions)
- What specific problem does this solve? What pain exists today?
- What happens if we DON'T build this?
- How will we measure success? What metrics matter?

#### Users & Journeys (2-3 questions)
- Who are the primary users? Secondary?
- What's the happy path user journey?
- What are the edge cases and error scenarios?

#### Scope & Boundaries (2-3 questions)
- What is explicitly IN scope?
- What is explicitly OUT of scope? (Very important!)
- Are there existing features this overlaps with?

#### Technical Context (3-5 questions)
- What existing systems/services will this integrate with?
- What data does this need? Where does it come from?
- Are there performance requirements (latency, throughput, scale)?
- What security/privacy considerations apply?
- Are there any hard technical constraints?

#### Trade-offs & Risks (2-3 questions)
- Are there multiple valid approaches? Which should we explore?
- What are the trade-offs between approaches?
- What could go wrong? What are the risks?
- What's the timeline/priority?

### Step 1.3: Summarize Understanding

After questions are answered, write a summary:

```markdown
## Feature Summary

**Name**: feature-name (kebab-case)
**One-liner**: Brief description of what this does

**Problem Statement**:
[2-3 sentences about the pain point this solves]

**User Stories**:
1. As a [user], I can [action] so that [benefit]
2. As a [user], I can [action] so that [benefit]
3. ...

**Scope**:
- IN: [list what's included]
- OUT: [list what's explicitly excluded]

**Technical Constraints**:
- [constraint 1]
- [constraint 2]

**Risks Identified**:
- [risk 1]
- [risk 2]

**Success Metrics**:
- [metric 1]
- [metric 2]
```

**Get user confirmation before proceeding!**

### Step 1.4: Save Exploration Output (State Machine)

When running in the state machine, save the exploration context as JSON:

```python
# .omoi_os/phase_data/explore.json
{
    "project_type": "Next.js 15 + FastAPI backend",
    "structure": {
        "frontend": "frontend/src/",
        "backend": "backend/omoi_os/",
        "api_routes": "backend/omoi_os/api/routes/",
        "models": "backend/omoi_os/models/",
        "services": "backend/omoi_os/services/"
    },
    "existing_models": [
        {"name": "Spec", "file": "backend/omoi_os/models/spec.py", "fields": ["id", "title", "description"]},
        {"name": "Ticket", "file": "backend/omoi_os/models/ticket.py", "fields": ["id", "title", "status"]}
    ],
    "conventions": {
        "naming": "snake_case for backend, camelCase for frontend",
        "testing": "pytest for backend, vitest for frontend",
        "patterns": ["Repository pattern", "Service layer", "Pydantic schemas"]
    },
    "related_to_feature": [
        {"name": "EventBusService", "file": "services/event_bus.py", "relevance": "Publish events for webhooks"},
        {"name": "TaskQueue", "file": "services/task_queue.py", "relevance": "Background processing"}
    ],
    "feature_summary": {
        "name": "webhook-notifications",
        "problem": "External systems cannot subscribe to OmoiOS events",
        "scope_in": ["Webhook subscriptions", "HMAC signing", "Retry logic"],
        "scope_out": ["UI management", "Rate limiting (future)"]
    }
}
```

**Evaluator Criteria:**
- ✓ Has `project_type` (non-empty string)
- ✓ Has `structure` (object with at least one key)
- ✓ Has `conventions` (object with naming patterns)
- ✓ Has `related_to_feature` (list, can be empty for greenfield)

---

## Phase 2: PRD (Product Requirements Document)

### Purpose

The PRD captures the "why" and "what" at a high level. It's the vision document that everything else traces back to.

### Location

`.omoi_os/docs/prd-{feature-name}.md`

### Template

```markdown
---
id: PRD-{FEATURE}-001
title: {Feature Name} PRD
feature: {feature-name}
created: {date}
updated: {date}
status: draft
author: Claude
---

# {Feature Name}

## Executive Summary

[2-3 paragraph overview of the feature, the problem it solves, and why it matters]

## Problem Statement

### Current State
[Describe the pain point that exists today]

### Desired State
[Describe what the world looks like after this feature ships]

### Impact of Not Building
[What happens if we don't build this?]

## Goals & Success Metrics

### Primary Goals
1. [Goal 1]
2. [Goal 2]

### Success Metrics
| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| [Metric 1] | [baseline] | [target] | [method] |

## User Stories

### Primary User: {User Type}

1. **{Story Title}**
   As a {user}, I want to {action} so that {benefit}.

   Acceptance Criteria:
   - [ ] {criterion 1}
   - [ ] {criterion 2}

2. ...

## Scope

### In Scope
- [Feature/capability 1]
- [Feature/capability 2]

### Out of Scope
- [Explicitly excluded 1]
- [Explicitly excluded 2]

### Future Considerations
- [Things we might add later]

## Constraints

### Technical Constraints
- [Constraint 1]
- [Constraint 2]

### Business Constraints
- [Timeline, budget, etc.]

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | [How to mitigate] |

## Dependencies

- [Dependency 1 - what we need from other teams/systems]
- [Dependency 2]

## Open Questions

- [ ] [Question that still needs answering]
- [ ] [Another question]
```

---

## Phase 3: REQUIREMENTS

> **State Machine Phase**: `REQUIREMENTS` (Timeout: 5 min / 20 turns)
> **Transition**: `EXPLORE` → `REQUIREMENTS` (requires ExplorationEvaluator pass)
> **Next Phase**: `DESIGN` (requires RequirementEvaluator pass)

### Purpose

Requirements define the specific, testable behaviors the system must have. Use EARS format (Easy Approach to Requirements Syntax).

### Location

`.omoi_os/requirements/{feature-name}.md`

### EARS Format

```
WHEN [trigger/condition], THE SYSTEM SHALL [action/behavior].
```

Examples:
- WHEN a user submits valid credentials, THE SYSTEM SHALL create an authenticated session within 2 seconds.
- WHEN a notification is triggered, THE SYSTEM SHALL deliver it to the user within 5 seconds.
- WHEN an API rate limit is exceeded, THE SYSTEM SHALL return a 429 status with retry-after header.

### Template

```markdown
---
id: REQ-{FEATURE}-001
title: {Feature Name} Requirements
feature: {feature-name}
created: {date}
updated: {date}
status: draft
category: functional
priority: HIGH
prd_ref: docs/prd-{feature-name}.md
design_ref: designs/{feature-name}.md
---

# {Feature Name} Requirements

## Overview

[Brief description of what these requirements cover]

## Functional Requirements

### REQ-{FEATURE}-FUNC-001: {Requirement Title}

**Priority**: HIGH | MEDIUM | LOW
**Category**: Functional

WHEN {trigger condition}, THE SYSTEM SHALL {required behavior}.

**Acceptance Criteria**:
- [ ] {Testable criterion 1}
- [ ] {Testable criterion 2}

**Notes**: {Any additional context}

---

### REQ-{FEATURE}-FUNC-002: {Requirement Title}

...

## Non-Functional Requirements

### REQ-{FEATURE}-PERF-001: {Performance Requirement}

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL {performance requirement with measurable target}.

**Metrics**:
- P50 latency: < X ms
- P99 latency: < Y ms
- Throughput: > Z requests/second

---

### REQ-{FEATURE}-SEC-001: {Security Requirement}

**Priority**: HIGH
**Category**: Security

THE SYSTEM SHALL {security requirement}.

## Traceability

| Requirement ID | PRD Section | Design Section | Ticket |
|----------------|-------------|----------------|--------|
| REQ-{FEATURE}-FUNC-001 | User Stories #1 | Component A | TKT-001 |
```

### Step 3.1: Save Requirements Output (State Machine)

After completing requirements, save to `.omoi_os/phase_data/requirements.json`:

```json
{
    "requirements": [
        {
            "id": "REQ-{FEATURE}-FUNC-001",
            "category": "functional",
            "priority": "HIGH",
            "condition": "WHEN user submits form",
            "action": "THE SYSTEM SHALL validate and persist data",
            "acceptance_criteria": ["Criterion 1", "Criterion 2"]
        }
    ],
    "total_count": 15,
    "categories": {
        "functional": 10,
        "performance": 3,
        "security": 2
    }
}
```

### RequirementEvaluator Criteria

| Criterion | Threshold | Description |
|-----------|-----------|-------------|
| EARS format compliance | 100% | All requirements use WHEN/SHALL format |
| Acceptance criteria | All present | Every requirement has testable criteria |
| Traceability | Complete | Links to PRD sections documented |
| Priority distribution | Reasonable | Not all HIGH priority |
| Requirement count | 5-50 | Reasonable scope for feature |

---

## Phase 4: DESIGN

> **State Machine Phase**: `DESIGN` (Timeout: 5 min / 25 turns)
> **Transition**: `REQUIREMENTS` → `DESIGN` (requires RequirementEvaluator pass)
> **Next Phase**: `TASKS` (requires DesignEvaluator pass)

### Purpose

The design document defines HOW to implement the requirements. It covers architecture, data models, APIs, and implementation details.

### Location

`.omoi_os/designs/{feature-name}.md`

### Template

```markdown
---
id: DESIGN-{FEATURE}-001
title: {Feature Name} Design
feature: {feature-name}
created: {date}
updated: {date}
status: draft
requirements:
  - REQ-{FEATURE}-001
# API Endpoints - These sync to the Design panel's "API Specification" section
api_endpoints:
  - method: POST
    path: /api/v1/{resource}
    description: Create a new resource
    auth_required: true
    request_body: '{"name": "string", "config": {}}'
    response: '{"id": "uuid", "name": "string", "created_at": "timestamp"}'
    error_responses:
      400: Validation error
      401: Unauthorized
      409: Resource already exists
  - method: GET
    path: /api/v1/{resource}/{id}
    description: Get resource by ID
    auth_required: true
    path_params: [id]
    response: '{"id": "uuid", "name": "string", "status": "string"}'
    error_responses:
      404: Resource not found
  - method: GET
    path: /api/v1/{resource}
    description: List all resources
    auth_required: true
    query_params:
      limit: Maximum number of results
      offset: Pagination offset
      status: Filter by status
  - method: PUT
    path: /api/v1/{resource}/{id}
    description: Update resource
    auth_required: true
    path_params: [id]
  - method: DELETE
    path: /api/v1/{resource}/{id}
    description: Delete resource
    auth_required: true
    path_params: [id]
# Data Models - These sync to the Design panel's "Data Model" section
data_models:
  - name: {ResourceName}
    description: Main entity for this feature
    table_name: {table_name}
    typed_fields:
      - name: id
        type: uuid
        description: Unique identifier
        constraints: [primary_key]
      - name: name
        type: string
        description: Display name
        nullable: false
      - name: status
        type: string
        description: Current status
        default: "'pending'"
      - name: config
        type: jsonb
        description: Configuration data
        nullable: true
      - name: created_at
        type: timestamp
        default: now()
      - name: updated_at
        type: timestamp
        default: now()
    relationships:
      - belongs_to Project (project_id)
      - has_many Tasks
---

# {Feature Name} Design

## Overview

[Brief description of the technical approach]

## Architecture Overview

```mermaid
flowchart TB
    subgraph External
        User[User]
        ExtAPI[External API]
    end

    subgraph System
        API[API Layer]
        Service[Service Layer]
        DB[(Database)]
    end

    User --> API
    API --> Service
    Service --> DB
    Service --> ExtAPI
```

### Component Diagram

[Describe the main components and their responsibilities]

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| {Component 1} | {What it does} | {Stack} |

## Data Model

The data models are defined in the frontmatter above and will sync to the Design panel.
Additional SQL details can be added here:

### Database Schema

```sql
CREATE TABLE {table_name} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    {column} {type} {constraints},
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_{table}_{column} ON {table}({column});
```

### Pydantic Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class {ModelName}(BaseModel):
    id: UUID
    {field}: {type} = Field(description="{description}")
    created_at: datetime
    updated_at: datetime
```

## API Specification

The API endpoints are defined in the frontmatter above and will sync to the Design panel.
Additional request/response examples can be documented here:

### Request/Response Examples

#### POST /api/v1/{resource}

**Request:**
```json
{
  "name": "My Resource",
  "config": {}
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Resource",
  "status": "pending",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Error Response (400):**
```json
{
  "error": "validation_error",
  "message": "Field 'name' is required"
}
```

## Implementation Details

### Algorithm/Logic

[Describe any complex algorithms or business logic]

```python
# Pseudocode for complex logic
def process_feature(input):
    # Step 1: Validate
    # Step 2: Transform
    # Step 3: Persist
    # Step 4: Notify
    pass
```

### State Machine (if applicable)

```mermaid
stateDiagram-v2
    [*] --> Created
    Created --> Processing : start
    Processing --> Completed : success
    Processing --> Failed : error
    Failed --> Processing : retry
    Completed --> [*]
```

## Integration Points

| System | Integration Type | Purpose |
|--------|-----------------|---------|
| {System 1} | REST API | {Why} |
| {System 2} | Event Bus | {Why} |

## Configuration

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| {param} | {default} | {range} | {description} |

## Testing Strategy

### Unit Tests
- [ ] {Component} - {What to test}

### Integration Tests
- [ ] {Integration point} - {What to test}

### E2E Tests
- [ ] {User journey} - {What to test}

## Security Considerations

- [ ] {Security consideration 1}
- [ ] {Security consideration 2}

## Performance Considerations

- [ ] {Performance consideration 1}
- [ ] {Performance consideration 2}

## Open Questions

- [ ] {Technical question that needs resolution}
```

### Step 4.1: Save Design Output (State Machine)

After completing design, save to `.omoi_os/phase_data/design.json`:

```json
{
    "api_endpoints": [
        {
            "method": "POST",
            "path": "/api/v1/resource",
            "description": "Create resource",
            "request_schema": "ResourceCreate",
            "response_schema": "Resource"
        }
    ],
    "data_models": [
        {
            "name": "Resource",
            "table_name": "resources",
            "fields": [
                {"name": "id", "type": "uuid", "primary_key": true},
                {"name": "name", "type": "string", "nullable": false}
            ]
        }
    ],
    "components": [
        {
            "name": "ResourceService",
            "layer": "service",
            "responsibilities": ["CRUD operations", "Validation"]
        }
    ]
}
```

### DesignEvaluator Criteria

| Criterion | Threshold | Description |
|-----------|-----------|-------------|
| API endpoints defined | All from requirements | Every requirement has implementation path |
| Data models complete | All entities covered | Schema for each data entity |
| Architecture diagram | Present | High-level system overview |
| Component responsibilities | Clear | Each component has defined role |
| Security considerations | Documented | Auth, validation, etc. addressed |

---

## Phase 5: TICKETS (Combined with Tasks in State Machine)

> **Note**: In the state machine, TICKETS and TASKS are combined into a single `TASKS` phase for generation efficiency. The evaluator validates both ticket and task structures together.

### Purpose

Tickets are the parent work items that group related tasks. One ticket typically maps to one major component or capability from the design.

### Location

`.omoi_os/tickets/TKT-{NNN}.md`

### ID Convention

Generate sequential IDs: TKT-001, TKT-002, etc.

Check existing: `ls .omoi_os/tickets/`

### Template

```markdown
---
id: TKT-{NNN}
title: {Ticket Title}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: backlog
priority: HIGH
estimate: M
design_ref: designs/{feature-name}.md
requirements:
  - REQ-{FEATURE}-FUNC-001
  - REQ-{FEATURE}-FUNC-002
dependencies:
  blocked_by: []
  blocks: []
---

# TKT-{NNN}: {Ticket Title}

## Description

[Clear description of what this ticket accomplishes]

## Acceptance Criteria

- [ ] {Criterion 1 - specific and testable}
- [ ] {Criterion 2}
- [ ] {Criterion 3}
- [ ] All tests pass
- [ ] Code reviewed and approved

## Technical Notes

[Any technical context or decisions relevant to implementation]

## Tasks

- TSK-{NNN}: {Task 1 title}
- TSK-{NNN}: {Task 2 title}
- TSK-{NNN}: {Task 3 title}

## Dependencies

**Blocked By**: {List tickets that must complete first, or "None"}
**Blocks**: {List tickets waiting on this one, or "None"}

## Estimate

**Size**: S | M | L | XL
**Rationale**: {Why this estimate}
```

### Ticket Generation Rules

1. **One ticket per major component** from the design
2. **Clear acceptance criteria** mapped from requirements
3. **Dependencies explicitly listed** - what blocks this, what this blocks
4. **Reasonable scope** - if > 5 tasks, consider splitting the ticket

---

## Phase 6: TASKS

> **State Machine Phase**: `TASKS` (Timeout: 3 min / 15 turns)
> **Transition**: `DESIGN` → `TASKS` (requires DesignEvaluator pass)
> **Next Phase**: `SYNC` (requires TaskEvaluator pass)

### Purpose

Tasks are atomic units of work that an AI agent can complete in a single session. They should be specific, self-contained, and have clear deliverables.

### Location

`.omoi_os/tasks/TSK-{NNN}.md`

### ID Convention

Generate sequential IDs: TSK-001, TSK-002, etc.

Check existing: `ls .omoi_os/tasks/`

### Template

```markdown
---
id: TSK-{NNN}
title: {Task Title}
created: {YYYY-MM-DD}
status: pending
parent_ticket: TKT-{NNN}
estimate: S
type: implementation
dependencies:
  depends_on: []
  blocks: []
---

# TSK-{NNN}: {Task Title}

## Objective

[One sentence describing what this task accomplishes]

## Context

[Brief context about why this task exists and how it fits into the bigger picture]

## Deliverables

- [ ] `{path/to/file.py}` - {What this file does}
- [ ] `{path/to/test_file.py}` - {Tests for the above}

## Implementation Notes

[Specific guidance for how to implement this]

```python
# Example code structure or pseudocode
class FeatureService:
    def do_thing(self):
        pass
```

## Acceptance Criteria

- [ ] {Specific, testable criterion}
- [ ] {Another criterion}
- [ ] All new code has tests
- [ ] Tests pass

## Dependencies

**Depends On**: {List task IDs that must complete first, or "None"}
**Blocks**: {List task IDs waiting on this one, or "None"}

## Estimate

**Size**: S (< 2 hours) | M (2-4 hours) | L (4-8 hours)
```

### Task Generation Rules

1. **Atomic** - Can be completed in a single focused session (1-4 hours ideal)
2. **Self-contained** - All context needed is in the task
3. **Clear deliverable** - Specific files, tests, or outcomes
4. **Testable** - Clear acceptance criteria that can be verified
5. **Dependencies explicit** - What must complete before this can start

### Task Types

- `implementation` - Write new code
- `refactor` - Improve existing code
- `test` - Write tests
- `documentation` - Write docs
- `research` - Investigate options
- `bugfix` - Fix a specific bug

### Step 6.1: Save Tasks Output (State Machine)

After completing tasks, save to `.omoi_os/phase_data/tasks.json`:

```json
{
    "tickets": [
        {
            "id": "TKT-001",
            "title": "Implement Resource API",
            "priority": "HIGH",
            "estimate": "M",
            "tasks": ["TSK-001", "TSK-002", "TSK-003"],
            "dependencies": {"blocked_by": [], "blocks": ["TKT-002"]}
        }
    ],
    "tasks": [
        {
            "id": "TSK-001",
            "title": "Create ResourceService",
            "parent_ticket": "TKT-001",
            "type": "implementation",
            "estimate": "M",
            "deliverables": ["omoi_os/services/resource_service.py"],
            "dependencies": {"depends_on": [], "blocks": ["TSK-002"]}
        }
    ],
    "dependency_graph": {
        "TSK-001": [],
        "TSK-002": ["TSK-001"],
        "TSK-003": ["TSK-002"]
    }
}
```

### TaskEvaluator Criteria

| Criterion | Threshold | Description |
|-----------|-----------|-------------|
| Ticket coverage | All design components | Every component has a ticket |
| Task atomicity | 1-4 hours each | Tasks completable in single session |
| Dependency graph | Valid DAG | No circular dependencies |
| Deliverables specified | All tasks | Every task has file deliverables |
| Acceptance criteria | All tasks | Testable criteria for each task |
| Ticket-task ratio | 2-5 tasks/ticket | Reasonable task grouping |

---

## Phase 7: SYNC TO API

> **State Machine Phase**: `SYNC` (Timeout: 2 min / 10 turns)
> **Transition**: `TASKS` → `SYNC` (requires TaskEvaluator pass)
> **Final State**: `COMPLETE` (spec ready for execution)

### Using spec_cli.py

After creating all artifacts locally, sync them to the OmoiOS API:

```bash
# Navigate to scripts directory
cd /root/.claude/skills/spec-driven-dev/scripts

# 1. Validate local specs first
python spec_cli.py validate

# 2. Preview what you have
python spec_cli.py show all

# 3. Find your project ID (if not in env)
python spec_cli.py projects

# 4. Dry-run sync to see what would change
python spec_cli.py sync diff

# 5. Push to API
python spec_cli.py sync push

# 6. Verify in API
python spec_cli.py project
```

### Sync Behavior

- **CREATE**: New tickets/tasks are created
- **UPDATE**: Existing items with changed descriptions are updated
- **SKIP**: Items already in sync are skipped

---

## Complete Example Workflow

### User Request

> "I want to add webhook notifications so external systems can subscribe to events"

### Step 1: Discover

```
Claude: Before designing, let me explore the codebase and ask some questions.

[Reads docs/CLAUDE.md, checks .omoi_os/ for existing specs, searches for event-related code]

Found: We have an EventBusService for internal pub/sub. No existing webhook specs.

Now I need to understand the feature better:

**Problem & Value:**
1. What specific external systems need to receive notifications?
2. What events should be subscribable? (task complete, PR ready, agent stuck?)
3. What happens if a webhook delivery fails?

**Scope:**
4. Should users configure webhooks via UI, API, or both?
5. Do we need authentication for webhook endpoints (HMAC signing)?
6. Is retry logic needed? How many retries?

**Technical:**
7. Should webhooks integrate with the existing EventBusService?
8. What's the expected volume of webhook deliveries per day?
9. Do we need rate limiting per subscriber?

**Constraints:**
10. Are there any specific protocols required (Slack, Discord, custom)?
11. What's the timeline for this feature?
```

### Step 2: User Answers

> "We need Slack and Discord initially, plus generic HTTP. Events: task_completed,
> ticket_status_changed, agent_error. HMAC signing required. 3 retries with
> exponential backoff. Use existing EventBusService. Volume: ~1000/day initially."

### Step 3: Create PRD

Write `.omoi_os/docs/prd-webhook-notifications.md`

### Step 4: Create Requirements

Write `.omoi_os/requirements/webhook-notifications.md` with EARS-format requirements

### Step 5: Create Design

Write `.omoi_os/designs/webhook-notifications.md` with architecture, data models, APIs

### Step 6: Create Tickets

- `.omoi_os/tickets/TKT-001.md` - Webhook Infrastructure (models, service, delivery)
- `.omoi_os/tickets/TKT-002.md` - Slack/Discord Formatters

### Step 7: Create Tasks

For TKT-001:
- `TSK-001.md` - Add webhook URL fields to Organization model
- `TSK-002.md` - Create database migration
- `TSK-003.md` - Implement WebhookDeliveryService
- `TSK-004.md` - Implement WebhookNotificationService
- `TSK-005.md` - Update API routes for webhook management
- `TSK-006.md` - Write tests

For TKT-002:
- `TSK-007.md` - Implement SlackWebhookFormatter
- `TSK-008.md` - Implement DiscordWebhookFormatter

### Step 8: Sync to API

```bash
cd /root/.claude/skills/spec-driven-dev/scripts
python spec_cli.py validate
python spec_cli.py sync push
```

---

## Concrete Example: Full File Contents

This section shows **exact file contents** you should create. Copy these patterns for your specs.

### Example Ticket File

**File: `.omoi_os/tickets/TKT-001.md`**

```markdown
---
id: TKT-001
title: Webhook Infrastructure Setup
created: 2025-01-15
updated: 2025-01-15
status: backlog
priority: HIGH
type: feature
feature: webhook-notifications
estimate: 3d
requirements:
  - REQ-WEBHOOK-FUNC-001
  - REQ-WEBHOOK-FUNC-002
dependencies:
  blocked_by: []
  blocks:
    - TKT-002
---

# TKT-001: Webhook Infrastructure Setup

## Objective

Set up the core webhook infrastructure including database models, delivery service with retry logic, and API endpoints for webhook management.

## Scope

### In Scope
- WebhookSubscription database model
- WebhookDelivery model for tracking delivery attempts
- WebhookDeliveryService with exponential backoff retry
- CRUD API endpoints for webhook subscriptions
- HMAC signature generation for payload verification

### Out of Scope
- Platform-specific formatters (Slack, Discord) - covered in TKT-002
- UI for webhook management - future ticket

## Acceptance Criteria

- [ ] WebhookSubscription model with url, secret, events[], active fields
- [ ] WebhookDelivery model tracks each delivery attempt with status
- [ ] Service delivers webhooks with 3 retries and exponential backoff
- [ ] All endpoints require authentication
- [ ] Webhook payloads include HMAC-SHA256 signature header
- [ ] Unit tests cover delivery retry logic
- [ ] Integration tests verify end-to-end webhook delivery

## Technical Notes

- Integrate with existing EventBusService to subscribe to events
- Use background task for async delivery (don't block event processing)
- Store webhook secret encrypted at rest

## Tasks

- TSK-001: Add webhook models to database
- TSK-002: Create database migration
- TSK-003: Implement WebhookDeliveryService
- TSK-004: Implement WebhookNotificationService
- TSK-005: Add API routes for webhook CRUD
- TSK-006: Write comprehensive tests
```

### Example Task File

**File: `.omoi_os/tasks/TSK-003.md`**

```markdown
---
id: TSK-003
title: Implement WebhookDeliveryService
created: 2025-01-15
status: pending
priority: HIGH
type: implementation
parent_ticket: TKT-001
estimate: 4h
dependencies:
  depends_on:
    - TSK-001
    - TSK-002
  blocks:
    - TSK-004
---

# TSK-003: Implement WebhookDeliveryService

## Objective

Create a service that handles the actual HTTP delivery of webhook payloads with retry logic, signature generation, and delivery tracking.

## Implementation Details

### File Location
`omoi_os/services/webhook_delivery.py`

### Class Structure
```python
class WebhookDeliveryService:
    def __init__(self, db: DatabaseService):
        self.db = db
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def deliver(
        self,
        subscription: WebhookSubscription,
        event_type: str,
        payload: dict,
    ) -> WebhookDelivery:
        """Deliver webhook with retry logic."""
        ...

    def _generate_signature(self, payload: bytes, secret: str) -> str:
        """Generate HMAC-SHA256 signature."""
        ...

    async def _attempt_delivery(
        self,
        url: str,
        payload: dict,
        headers: dict,
    ) -> tuple[bool, int, str]:
        """Single delivery attempt. Returns (success, status_code, response)."""
        ...
```

### Retry Configuration
- Max retries: 3
- Backoff: exponential with jitter
- Delays: 1s, 2s, 4s (base)
- Timeout per request: 30 seconds

### Headers to Include
```
X-OmoiOS-Event: {event_type}
X-OmoiOS-Delivery: {delivery_id}
X-OmoiOS-Signature: sha256={signature}
Content-Type: application/json
```

## Verification

```bash
# Run unit tests
uv run pytest tests/unit/services/test_webhook_delivery.py -v

# Test signature generation
uv run python -c "
from omoi_os.services.webhook_delivery import WebhookDeliveryService
svc = WebhookDeliveryService(None)
sig = svc._generate_signature(b'{\"test\": true}', 'secret')
print(f'Signature: {sig}')
"
```

## Done When

- [ ] WebhookDeliveryService class implemented
- [ ] Signature generation matches standard HMAC-SHA256
- [ ] Retry logic uses exponential backoff with jitter
- [ ] Each delivery attempt is recorded in WebhookDelivery table
- [ ] Unit tests pass with 100% coverage of retry scenarios
```

### Running the Complete Flow

After creating your spec files, run these commands:

```bash
# Navigate to the scripts directory
cd /root/.claude/skills/spec-driven-dev/scripts

# Step 1: Validate all specs (checks frontmatter, references, structure)
python spec_cli.py validate

# Expected output:
# ✓ Validation passed!
# - 2 tickets validated
# - 6 tasks validated
# - All dependencies resolved
# - All references valid

# Step 2: Preview what will be synced (dry run)
python spec_cli.py sync diff

# Expected output:
# Connecting to https://api.omoios.dev...
# Connected!
#
# Sync Results:
# ------------------------------------------------------------
# [CREATE] ticket TKT-001
#          Would create: Webhook Infrastructure Setup
# [CREATE] ticket TKT-002
#          Would create: Platform-Specific Formatters
# [CREATE] task TSK-001
#          Would create: Add webhook models to database
# ... (more tasks)
# ------------------------------------------------------------
# Summary: 8 would be created, 0 updated, 0 skipped

# Step 3: Actually sync to the API
python spec_cli.py sync push

# Expected output:
# Connecting to https://api.omoios.dev...
# Connected!
# Syncing to API...
#
# Sync Results:
# ------------------------------------------------------------
# [CREATE] ticket TKT-001
#          Created with API ID: 550e8400-e29b-41d4-a716-446655440000
# [CREATE] task TSK-001
#          Created with API ID: 550e8400-e29b-41d4-a716-446655440001
# ... (more items)
# ------------------------------------------------------------
# Summary: 8 created, 0 updated, 0 skipped, 0 failed

# Step 4: Verify what's in the project
python spec_cli.py project

# Expected output:
# ══════════════════════════════════════════════════════════════
# PROJECT: My Project
# ══════════════════════════════════════════════════════════════
#
# TICKETS (2 total)
# ──────────────────────────────────────────────────────────────
# • TKT-001: Webhook Infrastructure Setup [backlog]
#   └── 6 tasks
# • TKT-002: Platform-Specific Formatters [backlog]
#   └── 2 tasks
```

### Common Issues & Solutions

**Issue: "Validation failed - missing frontmatter"**
```bash
# Check which files are missing frontmatter
python spec_cli.py validate

# Solution: Add YAML frontmatter block at the top of each file
# Every file MUST start with --- and end the frontmatter with ---
```

**Issue: "Dependency not found: TSK-099"**
```bash
# Your task references a dependency that doesn't exist
# Solution: Either create TSK-099.md or remove it from depends_on
```

**Issue: "Connection refused" or timeout**
```bash
# Check if API URL is correct
echo $OMOIOS_API_URL

# In sandbox, this should be auto-injected
# If empty, the CLI falls back to https://api.omoios.dev
```

---

## Directory Structure Summary

```
.omoi_os/
├── docs/                    # PRDs and high-level documents
│   └── prd-{feature}.md
├── requirements/            # EARS-format requirements
│   └── {feature}.md
├── designs/                 # Technical designs
│   └── {feature}.md
├── tickets/                 # Parent work items
│   ├── TKT-001.md
│   └── TKT-002.md
└── tasks/                   # Atomic work units
    ├── TSK-001.md
    ├── TSK-002.md
    └── ...
```

---

## CLI Reference

### View Local Specs

```bash
python spec_cli.py show all           # Everything
python spec_cli.py show requirements  # Just requirements
python spec_cli.py show designs       # Just designs
python spec_cli.py show tickets       # Just tickets
python spec_cli.py show tasks         # Just tasks
python spec_cli.py show graph         # Task dependency graph
python spec_cli.py show ticket-graph  # Ticket dependency graph
python spec_cli.py show traceability  # Full traceability matrix
python spec_cli.py show ready         # Tasks ready to work on
```

### Validate

```bash
python spec_cli.py validate           # Check for issues
```

### Sync to API

```bash
python spec_cli.py projects                              # List projects
python spec_cli.py sync diff --project-id <uuid>         # Preview changes
python spec_cli.py sync push --project-id <uuid>         # Push to API
python spec_cli.py project <uuid>                        # View project in API
python spec_cli.py api-trace <uuid>                      # Full API traceability
```

---

## 🔒 Sandbox Requirements

### Environment Variables

The orchestrator injects these environment variables into each sandbox session:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SPEC_ID` | Current spec being generated | `550e8400-...` |
| `SPEC_PHASE` | Current phase name | `EXPLORE`, `REQUIREMENTS`, etc. |
| `PHASE_DATA_B64` | Base64-encoded prior phase outputs | `eyJwcm9qZWN0X3R5cGUi...` |
| `RESUME_SESSION_ID` | Session ID for resumption | `session-123-abc` |
| `SESSION_TRANSCRIPT_B64` | Base64-encoded conversation history | `W3sicm9sZSI6InVz...` |
| `FORK_SESSION` | Whether to fork from existing session | `true` or `false` |
| `OMOIOS_API_URL` | API endpoint for sync | `https://api.omoios.dev` |

### Required Imports

Each sandbox MUST have access to:

```python
# Core imports for spec generation
from omoi_os.schemas.spec_generation import (
    SpecPhase,
    ExplorationContext,
    RequirementsOutput,
    DesignOutput,
    TasksOutput,
)
from omoi_os.services.spec_state_machine import SpecStateMachine
from omoi_os.evaluators import (
    ExplorationEvaluator,
    RequirementEvaluator,
    DesignEvaluator,
    TaskEvaluator,
)
```

### File System Access

Sandboxes need read/write access to:

```
./                           # Project root
./.omoi_os/                  # Spec artifacts directory
./.omoi_os/phase_data/       # JSON outputs from each phase
./.omoi_os/docs/             # PRD documents
./.omoi_os/requirements/     # Requirement documents
./.omoi_os/designs/          # Design documents
./.omoi_os/tickets/          # Ticket markdown files
./.omoi_os/tasks/            # Task markdown files
```

### Session Transcript Persistence

For cross-sandbox resumption, transcripts are saved:

```json
{
    "session_id": "session-123-abc",
    "spec_id": "550e8400-...",
    "phase": "REQUIREMENTS",
    "turn_count": 15,
    "messages": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "phase_data": {
        "explore": {...},
        "requirements": {...}
    },
    "created_at": "2025-01-10T...",
    "updated_at": "2025-01-10T..."
}
```

### Phase Timeout Handling

If a phase times out:

1. **Save current progress** to `.omoi_os/phase_data/{phase}.partial.json`
2. **Set resumption flag** in session transcript
3. **Return control** to orchestrator for retry or manual intervention
4. **On resume**: Load partial data and continue from last checkpoint

---

## Best Practices

### Discovery
- **Never skip questions** - The 5 minutes spent asking saves hours of rework
- **Get explicit scope boundaries** - "Out of scope" is as important as "in scope"
- **Identify risks early** - What could go wrong?

### PRDs
- Write for a human reader who doesn't have context
- Focus on "why" and "what", not "how"
- Keep it concise but complete

### Requirements
- Use EARS format consistently
- Make every requirement testable
- Include acceptance criteria

### Designs
- Architecture diagrams first
- Include data models with actual SQL/Pydantic
- Specify APIs completely

### Tickets
- One component per ticket
- Clear acceptance criteria
- Explicit dependencies

### Tasks
- 1-4 hours of work max
- All context included
- Specific file deliverables

---

## Recovering from Lost Context

If you lose context mid-conversation:

```bash
# 1. Check what exists locally
ls .omoi_os/
cat .omoi_os/docs/prd-*.md
cat .omoi_os/requirements/*.md
cat .omoi_os/designs/*.md

# 2. View the full state
python spec_cli.py show all

# 3. Check what's in the API
python spec_cli.py project
```

Then resume from where you left off based on what's complete and what's missing.
