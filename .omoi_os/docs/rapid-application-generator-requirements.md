# Rapid Application Generator - Requirements Analysis

**Created**: 2025-01-07
**Status**: Draft Analysis
**Purpose**: Requirements analysis for enabling rapid entire application creation using the existing spec-driven-dev workflow.

---

## Executive Summary

### Feature Concept
A "Rapid Application Generator" capability that leverages the existing spec-driven-dev workflow to create entire applications quickly through natural language prompts.

### Problem Statement
The current spec-driven-dev workflow requires:
1. Manual creation of requirements, designs, tickets, and tasks
2. Multiple manual steps across different files
3. Manual coordination between phases
4. Manual agent spawning for each phase

**Goal**: Enable creation of entire applications from a single natural language description.

---

## Current System Analysis

### Existing Components

#### 1. Spec Workflow MCP Server (`backend/omoi_os/mcp/spec_workflow.py`)
**Capabilities:**
- `create_spec` - Create specification containers
- `add_requirement` - Add EARS-style requirements
- `add_acceptance_criterion` - Add acceptance criteria
- `update_design` - Update design artifacts
- `add_spec_task` - Add tasks to specifications
- `create_ticket` - Create workflow tickets
- `approve_requirements` - Transition to Design phase
- `approve_design` - Transition to Implementation phase
- `get_spec`, `get_ticket`, `get_task` - Retrieve details

**Gaps:**
- No orchestration/automation of multi-step workflows
- Each tool must be called individually
- No template-based generation
- No project scaffolding

#### 2. Spec CLI (`spec_cli.py`)
**Capabilities:**
- Parse requirements, designs, tickets, tasks from `.omoi_os/`
- Validate specs (circular dependencies, missing references)
- Show dependency graphs and traceability
- Export to JSON
- Sync to API (with `api_client.py`)

**Gaps:**
- No automated generation of specs
- Read-only workflow (no creation)
- No scaffolding capabilities

#### 3. Init Feature Script (`init_feature.py`)
**Capabilities:**
- Create stub requirement and design documents
- Initialize `.omoi_os/` directory structure

**Gaps:**
- Only creates empty templates
- No automated content generation
- No integration with spec workflow MCP tools

#### 4. Daytona Spawner (`daytona_spawner.py`)
**Capabilities:**
- Create sandboxes with proper environment variables
- Execute agents in isolated environments
- Support for different execution modes (exploration, implementation, validation)
- Git integration (clone, branch, commit, push, PR)

**Gaps:**
- No automatic spawning based on spec phase
- Manual coordination required for multi-phase workflows

#### 5. Spec-Driven-Dev Skill
**Capabilities:**
- Loaded in exploration mode for creating specs
- Loaded in implementation mode for executing tasks
- Provides context about spec-driven workflow

**Gaps:**
- No automated workflow orchestration
- Requires manual agent invocation

---

## Requirements for Rapid Application Generator

### Functional Requirements

#### REQ-RAG-CORE-001: Natural Language to Application
**WHEN** a user provides a natural language description of an application,
**THE SYSTEM SHALL** automatically generate all necessary artifacts (requirements, designs, tickets, tasks) to build that application.

**Acceptance Criteria:**
- [ ] Accept natural language prompts (1-5 paragraphs)
- [ ] Generate EARS-style requirements
- [ ] Generate design documents with architecture diagrams
- [ ] Generate tickets with proper dependencies
- [ ] Generate tasks with implementation details
- [ ] All artifacts linked for traceability

#### REQ-RAG-CORE-002: Automated Workflow Orchestration
**WHEN** an application specification is created,
**THE SYSTEM SHALL** automatically spawn agents to complete each phase (Requirements, Design, Implementation).

**Acceptance Criteria:**
- [ ] Spawn exploration agent for requirements gathering
- [ ] Spawn architect agent for design
- [ ] Spawn implementation agents for tasks
- [ ] Coordinate agent handoffs
- [ ] Track progress across phases
- [ ] Handle failures and retries

#### REQ-RAG-CORE-003: Template-Based Scaffolding
**WHEN** an application is initialized,
**THE SYSTEM SHALL** generate a complete project scaffolding based on the application type.

**Acceptance Criteria:**
- [ ] Support multiple application templates (web API, web app, CLI tool, etc.)
- [ ] Generate project structure (directories, configs)
- [ ] Generate starter code files
- [ ] Include best practices (testing, CI/CD, documentation)
- [ ] Customizable templates

#### REQ-RAG-CORE-004: Progress Tracking and Visibility
**WHEN** an application is being generated,
**THE SYSTEM SHALL** provide real-time visibility into the generation progress.

**Acceptance Criteria:**
- [ ] Show current phase (Requirements, Design, Implementation)
- [ ] Show completed/remaining artifacts
- [ ] Show agent activity logs
- [ ] Enable pause/resume of generation
- [ ] Provide rollback capability

#### REQ-RAG-CORE-005: Iterative Refinement
**WHEN** a user requests changes to the application,
**THE SYSTEM SHALL** intelligently update affected artifacts without regenerating everything.

**Acceptance Criteria:**
- [ ] Parse change requests (e.g., "add user authentication")
- [ ] Identify impacted requirements
- [ ] Generate delta changes to designs
- [ ] Create new tickets/tasks for changes
- [ ] Preserve existing completed work

---

### Non-Functional Requirements

#### REQ-RAG-NFR-001: Performance
**WHEN** generating an application,
**THE SYSTEM SHALL** complete the initial specification phase within 5 minutes for typical applications.

**Acceptance Criteria:**
- [ ] Requirements generated in < 2 minutes
- [ ] Design generated in < 2 minutes
- [ ] Initial tickets created in < 1 minute

#### REQ-RAG-NFR-002: Quality
**WHEN** generating artifacts,
**THE SYSTEM SHALL** ensure all artifacts are valid, consistent, and pass validation.

**Acceptance Criteria:**
- [ ] No circular dependencies
- [ ] All references resolve correctly
- [ ] EARS format compliance for requirements
- [ ] Traceability maintained (requirements → designs → tickets → tasks)

#### REQ-RAG-NFR-003: Extensibility
**WHEN** new application types are needed,
**THE SYSTEM SHALL** support adding new templates and generation strategies.

**Acceptance Criteria:**
- [ ] Pluggable template system
- [ ] Configurable generation strategies
- [ ] Custom prompt templates per app type

---

## Proposed Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         User Input Layer                                │
├─────────────────────────────────────────────────────────────────────────┤
│  Natural Language Prompt: "Create a task management API with auth"      │
└────────────────────────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Application Orchestrator                             │
│  (NEW COMPONENT)                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Prompt Analysis:                                               │   │
│  │  - Extract application type                                     │   │
│  │  - Identify key features                                        │   │
│  │  - Determine technical stack                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Template Selection:                                            │   │
│  │  - Select appropriate scaffold template                         │   │
│  │  - Configure generation parameters                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Phase Execution Coordinator                           │
│  (NEW COMPONENT - uses existing Spawner)                                │
└─────────────────────────────────────────────────────────────────────────┘
          │                              │                              │
          ▼                              ▼                              ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│  Requirements    │          │     Design       │          │  Implementation │
│    Phase         │          │     Phase        │          │     Phase        │
│  (exploration    │          │  (exploration    │          │  (implementation  │
│   agent)         │          │   agent)         │          │   agent)         │
│  - Uses MCP      │          │  - Uses MCP      │          │  - Spawns task   │
│    tools to      │          │    tools to      │          │    agents        │
│    create        │          │    create        │          │                  │
│    requirements  │          │    design        │          │                  │
└──────────────────┘          └──────────────────┘          └──────────────────┘
          │                              │                              │
          └──────────────────────────────┴──────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Output Artifacts                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐              │
│  │ Requirements   │  │    Designs     │  │   Tickets      │              │
│  │  (.omoi_os/    │  │   (.omoi_os/   │  │   (.omoi_os/   │              │
│  │   requirements/)│  │    designs/)   │  │    tickets/)   │              │
│  └────────────────┘  └────────────────┘  └────────────────┘              │
│  ┌────────────────┐  ┌────────────────┐                                         │
│  │     Tasks      │  │  Code Scaffold │                                         │
│  │  (.omoi_os/    │  │  (generated)   │                                         │
│  │    tasks/)     │  │                │                                         │
│  └────────────────┘  └────────────────┘                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### New Components Required

#### 1. Application Orchestrator Service
**Location**: `backend/omoi_os/services/application_orchestrator.py`

**Responsibilities:**
- Parse natural language prompts
- Extract application requirements from prompts
- Select appropriate templates
- Coordinate multi-phase generation
- Track progress and state

**Key Methods:**
```python
class ApplicationOrchestrator:
    async def generate_from_prompt(prompt: str, project_id: str) -> ApplicationSpec
    async def refine_application(spec_id: str, changes: str) -> ApplicationSpec
    async def get_progress(spec_id: str) -> GenerationProgress
    async def pause_generation(spec_id: str)
    async def resume_generation(spec_id: str)
```

#### 2. Template Engine
**Location**: `backend/omoi_os/templates/`

**Responsibilities:**
- Store application scaffolding templates
- Generate project structure
- Provide starter code templates
- Support custom templates

**Template Types:**
- `web-api/` - RESTful API with SQLAlchemy, FastAPI
- `web-app/` - React + FastAPI full-stack app
- `cli-tool/` - CLI application with Click
- `microservice/` - Event-driven microservice
- `worker/` - Background worker service

#### 3. MCP Tool: Generate Application
**Location**: `backend/omoi_os/mcp/spec_workflow.py` (add to existing)

**New Tool:**
```python
@tool(
    "generate_application",
    "Generate a complete application specification from a natural language description. "
    "This orchestrates the full spec-driven-dev workflow automatically.",
    {
        "prompt": "Natural language description of the application to create (required)",
        "project_id": "Project ID to create the application under (required)",
        "app_type": "Application type template: web-api, web-app, cli-tool, microservice (optional, auto-detected)",
        "auto_execute": "Whether to automatically spawn agents for implementation (default: false)",
    },
)
async def generate_application(args: dict[str, Any]) -> dict[str, Any]:
    """Generate a complete application from a prompt."""
    # Implementation will:
    # 1. Parse the prompt
    # 2. Generate requirements using add_requirement
    # 3. Generate design using update_design
    # 4. Create tickets using create_ticket
    # 5. Optionally spawn agents
```

#### 4. MCP Tool: Refine Application
**Location**: `backend/omoi_os/mcp/spec_workflow.py` (add to existing)

**New Tool:**
```python
@tool(
    "refine_application",
    "Refine an existing application by modifying requirements, design, or implementation. "
    "Intelligently updates only affected artifacts.",
    {
        "spec_id": "Specification ID to refine (required)",
        "changes": "Natural language description of changes to make (required)",
        "force_regenerate": "Force regeneration of all artifacts (default: false)",
    },
)
async def refine_application(args: dict[str, Any]) -> dict[str, Any]:
    """Refine an existing application specification."""
```

---

## Implementation Roadmap

### Phase 1: Core Generation (MVP)
**Goal**: Generate complete specs from prompts

**Tasks:**
1. Create `ApplicationOrchestrator` service
2. Add `generate_application` MCP tool
3. Implement prompt parsing and template selection
4. Implement requirements auto-generation using existing MCP tools
5. Implement design auto-generation using existing MCP tools
6. Implement ticket/task auto-generation
7. Add validation and traceability checks

### Phase 2: Agent Orchestration
**Goal**: Automatically spawn agents for each phase

**Tasks:**
1. Integrate with existing `DaytonaSpawnerService`
2. Implement phase handoff logic
3. Add progress tracking
4. Implement pause/resume capability
5. Add error handling and retry logic

### Phase 3: Template System
**Goal**: Provide scaffolding templates

**Tasks:**
1. Design template structure
2. Create base templates (web-api, web-app, cli-tool)
3. Implement template engine
4. Add template customization support

### Phase 4: Refinement and Iteration
**Goal**: Support incremental changes

**Tasks:**
1. Add `refine_application` MCP tool
2. Implement change impact analysis
3. Implement delta generation
4. Add rollback capability

### Phase 5: Advanced Features
**Goal**: Production-ready capabilities

**Tasks:**
1. Add progress visualization
2. Implement collaborative editing
3. Add version history for specs
4. Support multi-user sessions

---

## Open Questions

1. **Prompt Complexity**: What level of detail should prompts require? Single sentence vs. detailed description?

2. **Template Granularity**: How many templates are needed? Start with 3-5 common patterns?

3. **Agent Coordination**: Should all agents run sequentially or can some phases run in parallel?

4. **User Feedback**: How should users provide feedback between phases? Interactive vs. batch?

5. **Cost Management**: How to track and limit LLM API costs during generation?

6. **Quality Assurance**: How to validate generated code meets requirements?

---

## Success Criteria

### MVP Success
- [ ] Generate complete, valid specs from a 1-paragraph prompt
- [ ] All generated artifacts pass validation
- [ ] Generated specs can be executed by existing workflow
- [ ] Time from prompt to complete spec < 5 minutes

### Full Success
- [ ] Automatically scaffold project code
- [ ] Spawn and coordinate agents across all phases
- [ ] Support iterative refinement
- [ ] Support at least 3 application templates

---

## Related Documents

- [Spec Workflow MCP Tools](../mcp/spec_workflow.py)
- [Spec CLI](../../.claude/skills/spec-driven-dev/scripts/spec_cli.py)
- [Daytona Spawner](../../backend/omoi_os/services/daytona_spawner.py)
- [Existing Spec Examples](../requirements/webhook-notifications.md)
