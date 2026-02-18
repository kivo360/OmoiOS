# Hephaestus vs OmoiOS: Key Differences

**Created**: 2025-01-30  
**Status**: Comparison Document  
**Purpose**: Understand differences between Hephaestus phase system and OmoiOS spec-driven workflow

---

## Executive Summary

Both systems use **phase-based agent orchestration**, but they differ significantly in:
- **Workflow structure** (spec-driven vs PRD-driven)
- **Phase model** (3-phase vs 5-phase)
- **Terminology** (tasks vs tickets/tasks)
- **Discovery mechanism** (any-phase spawning vs structured discovery)
- **User experience** (technical workflow vs product dashboard)

---

## Core Philosophy Differences

### Hephaestus: "Workflows That Build Themselves"
**Core Idea**: Agents discover work and spawn tasks in any phase based on what they find.

```
PRD → Phase 1 Analysis → Phase 2 Build → Phase 3 Validate
                              ↓
                    (Discovers optimization)
                              ↓
                    Spawns Phase 1 Investigation
                              ↓
                    New branch emerges
```

**Key Principle**: Define **types of work** (phases), not specific work to do. Workflow structure emerges from discoveries.

### OmoiOS: "Spec-Driven Autonomous Engineering"
**Core Idea**: Structured spec-driven workflow with strategic approval gates.

```
Natural Language → Requirements → Design → Tasks → Execution
     (EARS)         (Architecture)  (Plan)   (Agents)
```

**Key Principle**: Users provide **strategic oversight** at approval gates. System executes autonomously within phases.

---

## Phase Structure Comparison

### Hephaestus Phase Model

**3-Phase System:**
```
Phase 1: Requirements Analysis
  - Read PRD
  - Identify components
  - Spawn Phase 2 tasks

Phase 2: Implementation
  - Build one component
  - Write tests
  - Spawn Phase 3 validation

Phase 3: Validation
  - Test component
  - Verify requirements
  - Mark complete
```

**Characteristics:**
- Simple, focused phases
- Each phase has clear role
- Agents can spawn tasks in **any phase** from any phase
- Workflow branches dynamically

### OmoiOS Phase Model

**5-Phase System:**
```
PHASE_INITIAL → PHASE_IMPLEMENTATION → PHASE_INTEGRATION → PHASE_REFACTORING → DONE
```

**Characteristics:**
- More granular phases
- Structured progression through phases
- Phase gates require user approval
- Discovery creates new tasks but within structured workflow

**Phase Definitions:**
```python
# OmoiOS phases have:
- done_definitions: ["Component code files created", "Tests passing"]
- expected_outputs: [{"type": "file", "pattern": "src/**/*.py"}]
- phase_prompt: "YOU ARE A SOFTWARE ENGINEER IN THE IMPLEMENTATION PHASE..."
- next_steps_guide: ["Phase 3 agent will run integration tests"]
```

---

## Workflow Discovery Mechanisms

### Hephaestus: Free-Form Phase Spawning

**How It Works:**
```
Phase 3 agent (testing) discovers optimization
  ↓
Spawns Phase 1 task (investigation) immediately
  ↓
New branch grows from middle of workflow
  ↓
No approval needed - workflow adapts automatically
```

**Key Feature**: Agents can spawn tasks in **any phase** from any phase. No restrictions.

**Example:**
- Phase 3 agent testing API discovers caching pattern
- Spawns Phase 1 investigation task
- Investigation spawns Phase 2 implementation
- New feature branch emerges

### OmoiOS: Structured Discovery Service

**How It Works:**
```
Agent working on Task A discovers bug
  ↓
Calls DiscoveryService.record_discovery_and_branch()
  ↓
Creates TaskDiscovery record (type: "bug")
  ↓
Spawns new Task B (fix bug) in appropriate phase
  ↓
Links Task B as child of Task A
  ↓
Dashboard updates (graph, timeline, board)
```

**Key Feature**: Discovery is **tracked and structured**. Types include: bug, optimization, missing requirement, security issue, etc.

**Discovery Types:**
- Bug found
- Optimization opportunity
- Missing requirement
- Security issue
- Performance issue
- Technical debt
- Integration issue

**Workflow Graph:**
- OmoiOS tracks discovery → task relationships
- Shows branching structure
- Maintains parent-child relationships
- Visualizes workflow evolution

---

## Terminology Differences

### Hephaestus
- **Task**: The unit of work (agents work on tasks)
- **Phase**: Type of work (Analysis, Building, Validation)
- **PRD**: Product Requirements Document (starting point)
- **Workflow**: The branching tree of tasks across phases

### OmoiOS
- **Spec**: Complete specification (Requirements → Design → Tasks → Execution)
- **Ticket**: Work item container (parent)
- **Task**: Execution unit within ticket (child)
- **Phase**: Workflow stage (INITIAL → IMPLEMENTATION → INTEGRATION → REFACTORING)
- **Discovery**: Structured record of agent findings

**Hierarchy:**
```
Spec (Top Level)
  └─ Requirements (Phase 1)
  └─ Design (Phase 2)
  └─ Tickets (Phase 3) - Work items
      └─ Tasks (Execution units within tickets)
  └─ Execution (Phase 4) - Task execution
```

---

## User Experience Differences

### Hephaestus: Technical Workflow Tool

**Primary Interface:**
- Workflow graph visualization
- Phase overview dashboard
- Task list with phase badges
- Agent activity logs

**User Role:**
- Define phases (Python objects or YAML)
- Monitor workflow execution
- Review agent discoveries
- Less hands-on approval

**Focus:**
- Workflow structure
- Agent coordination
- Discovery visualization

### OmoiOS: Product Dashboard

**Primary Interface:**
- Dashboard with specs grid
- Kanban board (tickets)
- Spec workspace (multi-tab)
- Dependency graph
- Activity timeline
- Agent status monitoring

**User Role:**
- Create specs (natural language)
- Review and approve requirements/design
- Approve phase transitions
- Review PRs
- Strategic oversight

**Focus:**
- User-friendly dashboard
- Approval gates
- Real-time monitoring
- PR review workflow

---

## Configuration Differences

### Hephaestus Configuration

**Python Objects:**
```python
from src.sdk.models import Phase

PHASE_1_REQUIREMENTS = Phase(
    id=1,
    name="requirements_analysis",
    description="Extract requirements from PRD",
    done_definitions=[
        "Requirements extracted",
        "Components identified",
        "Phase 2 tasks created"
    ],
    additional_notes="Read PRD.md and identify system components..."
)
```

**YAML Files:**
```yaml
description: "Extract requirements from PRD"
Done_Definitions:
  - "Requirements extracted and documented"
  - "Components identified"
Additional_Notes: |
  Read the PRD file and extract all requirements.
```

**Characteristics:**
- Code-based or file-based configuration
- Version-controlled YAML
- Reusable across projects
- Dynamic phase creation possible

### OmoiOS Configuration

**Database-Driven:**
```python
class PhaseModel(Base):
    id: str  # PHASE_IMPLEMENTATION
    name: str
    description: str
    done_definitions: List[str]  # JSONB
    expected_outputs: List[Dict]  # JSONB
    phase_prompt: str
    next_steps_guide: List[str]  # JSONB
```

**YAML Configuration:**
```yaml
# config/base.yaml
phases:
  implementation:
    done_definitions:
      - "Component code files created"
      - "Minimum 3 test cases passing"
```

**Characteristics:**
- Database storage with YAML defaults
- Per-project phase customization
- UI-driven configuration
- Integration with approval gates

---

## Approval & Control Differences

### Hephaestus: Autonomous Discovery

**Approval Points:**
- Minimal user intervention
- Agents spawn work autonomously
- Guardian monitors and corrects drift
- Workflow adapts without approval

**Control:**
- Define phases upfront
- Monitor execution
- Review discoveries
- Less gate-keeping

### OmoiOS: Strategic Oversight

**Approval Points:**
- Requirements approval
- Design approval
- Phase transition approval
- PR review and merge

**Control:**
- Review specs before execution
- Approve phase transitions
- Review code changes
- Strategic gate-keeping

---

## Guardian System Comparison

### Hephaestus Guardian

**How It Works:**
- Monitors agents every 60 seconds
- Uses phase instructions as validation criteria
- Sends targeted corrections when agents drift
- Phase instructions become monitoring criteria

**Focus:**
- Alignment with phase instructions
- Workflow coherence
- Agent trajectory analysis

### OmoiOS Guardian

**How It Works:**
- Monitors agent trajectories every 60 seconds
- Calculates alignment scores
- Sends interventions via ConversationInterventionService
- Real-time steering without interrupting execution

**Intervention Types:**
- Prioritize: Focus on specific area
- Stop: Halt current work
- Refocus: Change direction
- Add constraint: Add new requirement
- Inject tool call: Force specific action

**Focus:**
- Goal alignment
- Trajectory analysis
- Real-time course correction
- Dashboard integration

---

## Integration Differences

### Hephaestus Integrations

**Core Integrations:**
- Guardian monitoring (phase-based validation)
- Ticket tracking (Kanban board mapping)
- Validation agents (automated checks)
- Memory system (RAG for discoveries)

**Focus:**
- Workflow coordination
- Knowledge transfer
- Agent validation

### OmoiOS Integrations

**Core Integrations:**
- GitHub/GitLab (repository connection, webhooks, PRs)
- WebSocket (real-time updates)
- EventBusService (Redis pub/sub)
- DiscoveryService (structured discovery tracking)
- ApprovalService (phase gate approvals)
- CostTrackingService (LLM cost tracking)

**Focus:**
- Developer workflow integration
- Real-time collaboration
- Cost management
- Audit trails

---

## Use Case Differences

### Hephaestus Best For:

**Scenarios:**
- Building software from PRD
- Exploratory problem-solving
- Research and analysis workflows
- Systems where structure emerges from problem

**User Type:**
- Technical teams
- Research organizations
- Exploratory development
- Teams comfortable with workflow graphs

**Example:**
```
"Build a web app from this PRD"
→ Agents discover components
→ Workflow branches as agents find optimizations
→ Structure emerges from discoveries
```

### OmoiOS Best For:

**Scenarios:**
- Feature development with approval gates
- Structured engineering workflows
- Teams needing strategic oversight
- Production software development

**User Type:**
- Engineering managers
- Product teams
- Organizations needing approval workflows
- Teams wanting dashboard visibility

**Example:**
```
"Add payment processing with Stripe"
→ Generate spec (Requirements → Design → Tasks)
→ User approves plan
→ Agents execute autonomously
→ User reviews PRs
→ Feature ships
```

---

## Key Architectural Differences

### Hephaestus Architecture

**Core Components:**
- Phase definitions (Python/YAML)
- Task spawning system
- Workflow graph builder
- Guardian monitoring
- Memory system (RAG)

**Data Model:**
- Tasks (with phase assignment)
- Phases (instruction sets)
- Workflow graph (task relationships)

**Storage:**
- File-based (YAML) or code-based (Python)
- Optional database for task tracking

### OmoiOS Architecture

**Core Components:**
- Spec workspace (Requirements/Design/Tasks/Execution)
- Ticket/Task system
- DiscoveryService (structured discovery)
- ApprovalService (phase gates)
- ConversationInterventionService (Guardian)
- EventBusService (real-time events)

**Data Model:**
- Specs (Requirements, Design, Tasks)
- Tickets (work items)
- Tasks (execution units)
- TaskDiscoveries (structured findings)
- PhaseHistory (transition tracking)

**Storage:**
- PostgreSQL (tickets, tasks, specs)
- Redis (events, real-time updates)
- Optional S3 (document storage)

---

## Summary Table

| Aspect | Hephaestus | OmoiOS |
|--------|-----------|--------|
| **Phase Model** | 3 phases (Analysis/Build/Validate) | 5 phases (Initial → Implementation → Integration → Refactoring → Done) |
| **Workflow Structure** | Emerges from discoveries | Spec-driven with approval gates |
| **Discovery** | Free-form phase spawning | Structured DiscoveryService |
| **Approval** | Minimal (Guardian monitors) | Strategic (phase gates, PR reviews) |
| **Terminology** | Tasks, Phases | Specs, Tickets, Tasks, Phases |
| **User Interface** | Workflow graph, phase dashboard | Product dashboard, Kanban, spec workspace |
| **Configuration** | Python objects or YAML files | Database + YAML config |
| **Starting Point** | PRD document | Natural language feature request |
| **User Role** | Define phases, monitor | Create specs, approve, review PRs |
| **Best For** | Exploratory development | Structured feature development |

---

## Key Takeaways

### Hephaestus Philosophy:
- **"Workflows that build themselves"**
- Agents discover and spawn work freely
- Structure emerges from problem
- Minimal user intervention
- Technical workflow tool

### OmoiOS Philosophy:
- **"Spec-driven autonomous engineering"**
- Structured workflow with approval gates
- Users provide strategic oversight
- Dashboard-driven product experience
- Production software development focus

### When to Use Each:

**Choose Hephaestus if:**
- You want maximum agent autonomy
- Workflow structure should emerge from discoveries
- You're comfortable with technical interfaces
- You need exploratory problem-solving

**Choose OmoiOS if:**
- You need approval workflows
- You want dashboard visibility
- You're building production features
- You need strategic oversight points

---

## Potential Hybrid Approach

**Could OmoiOS adopt Hephaestus concepts?**

1. **Free-Phase Spawning**: Allow agents to spawn tasks in any phase (not just structured discovery)
2. **Simpler Phase Model**: Consider 3-phase model for simpler workflows
3. **PRD-Driven Mode**: Add option to start from PRD instead of natural language
4. **Workflow Graph Focus**: Enhance graph visualization to show free-form branching

**Could Hephaestus adopt OmoiOS concepts?**

1. **Spec-Driven Workflow**: Add structured Requirements → Design → Tasks flow
2. **Approval Gates**: Add user approval points for phase transitions
3. **Dashboard UI**: Build product-focused dashboard (not just workflow graph)
4. **Structured Discovery**: Add DiscoveryService for tracking findings

---

## Related Documents

- [User Journey](./user_journey.md) - OmoiOS complete user flow
- [Hephaestus Workflow Enhancements](./implementation/workflows/hephaestus_workflow_enhancements.md) - OmoiOS phase system implementation
- [Product Vision](./product_vision.md) - OmoiOS product concept
