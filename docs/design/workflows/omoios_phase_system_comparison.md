# OmoiOS Phase System vs Hephaestus Phasor: Comparison

**Created**: 2025-01-30
**Status**: Analysis Document
**Purpose**: Compare OmoiOS's phase system with Hephaestus's Phasor system, showing similarities, differences, and how default vs custom phases work
**Related**: [Phasor System](./phasor_system.md), [Phase Model](../../omoi_os/models/phase.py), [Phase Loader](../../omoi_os/services/phase_loader.py)

---

## Overview

Both OmoiOS and Hephaestus use **phase-based orchestration**, but they differ in:
- **Phase structure** (default phases vs custom phases)
- **Spawning flexibility** (structured transitions vs free-form spawning)
- **Configuration** (database + YAML vs Python objects + YAML)
- **Discovery integration** (structured discovery vs free-form branching)

---

## OmoiOS Phase System

### Default Phases

OmoiOS comes with **8 default phases** seeded in the database:

```python
# From migration 006_memory_learning.py

PHASE_BACKLOG        # Initial ticket triage and prioritization
PHASE_REQUIREMENTS   # Gather and analyze requirements
PHASE_DESIGN         # Create technical design and architecture
PHASE_IMPLEMENTATION # Develop and implement features
PHASE_TESTING        # Test and validate implementation
PHASE_DEPLOYMENT     # Deploy to production
PHASE_DONE           # Ticket completed (terminal)
PHASE_BLOCKED        # Ticket blocked by external dependencies (terminal)
```

**Default Flow**:
```
PHASE_BACKLOG → PHASE_REQUIREMENTS → PHASE_DESIGN → PHASE_IMPLEMENTATION → 
PHASE_TESTING → PHASE_DEPLOYMENT → PHASE_DONE
```

**Allowed Transitions** (structured):
- Each phase defines `allowed_transitions` (e.g., `PHASE_IMPLEMENTATION` can transition to `PHASE_TESTING` or `PHASE_BLOCKED`)
- `PHASE_TESTING` can loop back to `PHASE_IMPLEMENTATION` (for bug fixes)
- `PHASE_BLOCKED` can transition back to any active phase

### Custom Phases

Users can create **custom phases** via:

1. **YAML Configuration** (`omoi_os/config/workflows/*.yaml`):
```yaml
phases:
  - id: "PHASE_CUSTOM_ANALYSIS"
    name: "Custom Analysis"
    description: "Specialized analysis phase"
    sequence_order: 1
    allowed_transitions:
      - "PHASE_IMPLEMENTATION"
    done_definitions:
      - "Analysis complete"
      - "Report generated"
    phase_prompt: |
      YOU ARE A CUSTOM ANALYST
      STEP 1: Perform specialized analysis
      STEP 2: Generate report
    expected_outputs:
      - type: "document"
        pattern: "analysis_report.md"
        required: true
```

2. **API Endpoints** (planned):
```python
POST /api/phases
{
  "id": "PHASE_CUSTOM_ANALYSIS",
  "name": "Custom Analysis",
  "description": "...",
  "sequence_order": 1,
  "allowed_transitions": ["PHASE_IMPLEMENTATION"],
  "done_definitions": [...],
  "phase_prompt": "...",
  "expected_outputs": [...]
}
```

3. **Database Direct**:
```python
phase = PhaseModel(
    id="PHASE_CUSTOM_ANALYSIS",
    name="Custom Analysis",
    sequence_order=1,
    allowed_transitions=["PHASE_IMPLEMENTATION"],
    done_definitions=["Analysis complete"],
    phase_prompt="YOU ARE A CUSTOM ANALYST..."
)
session.add(phase)
session.commit()
```

### Phase Model Structure

**OmoiOS PhaseModel** (`omoi_os/models/phase.py`):
```python
class PhaseModel(Base):
    id: str                    # PHASE_IMPLEMENTATION
    name: str                  # "Implementation"
    description: Optional[str] # "Develop and implement features"
    sequence_order: int        # 3 (order in sequence)
    allowed_transitions: List[str]  # ["PHASE_TESTING", "PHASE_BLOCKED"]
    is_terminal: bool          # False (except PHASE_DONE, PHASE_BLOCKED)
    
    # Hephaestus-inspired enhancements
    done_definitions: List[str]  # ["Component code created", "Tests passing"]
    expected_outputs: List[Dict]  # [{"type": "file", "pattern": "src/*.py"}]
    phase_prompt: Optional[str]   # "YOU ARE A SOFTWARE ENGINEER..."
    next_steps_guide: List[str]  # ["Phase 3 agent will run integration tests"]
    configuration: Dict[str, Any]  # Phase-specific config
```

### Phase Loading

**PhaseLoader Service** (`omoi_os/services/phase_loader.py`):
- Loads phases from YAML files (`omoi_os/config/workflows/*.yaml`)
- Validates phase definitions
- Saves to database (`PhaseModel`)
- Supports overwrite mode

**Example YAML** (`omoi_os/config/workflows/software_development.yaml`):
```yaml
phases:
  - id: "PHASE_REQUIREMENTS"
    name: "Requirements Analysis"
    description: "Gather and analyze requirements"
    sequence_order: 1
    allowed_transitions:
      - "PHASE_DESIGN"
      - "PHASE_BLOCKED"
    done_definitions:
      - "Requirements extracted and documented"
      - "Components identified"
      - "Phase 2 tasks created"
    phase_prompt: |
      YOU ARE A REQUIREMENTS ANALYST
      STEP 1: Read the PRD document
      STEP 2: Identify all major system components
      STEP 3: For each component, create a Phase 2 implementation task
    expected_outputs:
      - type: "document"
        pattern: "requirements.md"
        required: true
```

### Discovery Integration

**OmoiOS DiscoveryService** (`omoi_os/services/discovery.py`):
- Records agent discoveries (`TaskDiscovery` model)
- Spawns tasks in **ANY phase** (bypasses `allowed_transitions`)
- Links discoveries to spawned tasks

**Example**:
```python
discovery_service.record_discovery_and_branch(
    source_task_id="task-123",
    discovery_type="optimization",
    description="Caching could improve performance 40%",
    spawn_phase_id="PHASE_REQUIREMENTS",  # Can be ANY phase
    spawn_description="Investigate Redis caching",
)
```

**Key Point**: Discovery-based spawning **bypasses** `allowed_transitions`, enabling adaptive workflows.

---

## Hephaestus Phasor System

### Phase Structure

**Hephaestus** uses **3-5 generic phases** (not predefined):

```python
Phase 1: Requirements Analysis
Phase 2: Implementation
Phase 3: Validation
Phase 4: Deployment (optional)
Phase 5: Done (optional)
```

**No Default Phases**: Users define phases per workflow (Python objects or YAML).

### Phase Definition

**Hephaestus Phase** (Python):
```python
PHASE_1_REQUIREMENTS = Phase(
    id=1,
    name="requirements_analysis",
    description="Extract requirements from PRD",
    done_definitions=[
        "Requirements extracted",
        "Components identified",
        "Phase 2 tasks created"
    ],
    working_directory=".",
    additional_notes="Read PRD.md and identify system components..."
)
```

**Hephaestus Phase** (YAML):
```yaml
description: "Extract requirements from PRD"
Done_Definitions:
  - "Requirements extracted and documented"
  - "Components identified"
  - "Phase 2 tasks created"
working_directory: "."
Additional_Notes: |
  Read the PRD file and extract all requirements.
  Identify the system components.
  Create one Phase 2 task per component.
```

### Free-Form Spawning

**Hephaestus Rule**: Agents can spawn tasks in **ANY phase** from **ANY phase**. No restrictions.

**Example**:
```
Phase 3 agent (testing) discovers optimization
  ↓
Spawns Phase 1 task (investigation) immediately
  ↓
No approval needed - workflow adapts automatically
```

**No `allowed_transitions`**: Phases don't restrict which phases can be spawned.

---

## Comparison Table

| Feature | OmoiOS | Hephaestus Phasor |
|---------|--------|-------------------|
| **Default Phases** | ✅ 8 default phases (BACKLOG, REQUIREMENTS, DESIGN, IMPLEMENTATION, TESTING, DEPLOYMENT, DONE, BLOCKED) | ❌ No defaults - users define per workflow |
| **Custom Phases** | ✅ Via YAML config, API (planned), or database | ✅ Via Python objects or YAML |
| **Phase Structure** | ✅ Database model (`PhaseModel`) + YAML config | ✅ Python objects or YAML files |
| **Done Definitions** | ✅ `done_definitions` (JSONB) | ✅ `Done_Definitions` (list) |
| **Phase Prompts** | ✅ `phase_prompt` (text) | ✅ `Additional_Notes` (text) |
| **Expected Outputs** | ✅ `expected_outputs` (JSONB) | ✅ `outputs` (list) |
| **Next Steps Guide** | ✅ `next_steps_guide` (JSONB) | ✅ `next_steps` (list) |
| **Structured Transitions** | ✅ `allowed_transitions` (restricts normal flow) | ❌ No transition restrictions |
| **Free-Form Spawning** | ✅ Via `DiscoveryService` (bypasses `allowed_transitions`) | ✅ Built-in (no restrictions) |
| **Discovery Integration** | ✅ `TaskDiscovery` model tracks discoveries | ✅ Discovery spawns tasks directly |
| **Phase Sequence** | ✅ `sequence_order` (for display/ordering) | ✅ Implicit (via phase IDs) |
| **Terminal Phases** | ✅ `is_terminal` flag (DONE, BLOCKED) | ✅ Terminal phases defined per workflow |
| **Configuration** | ✅ Database + YAML | ✅ Python objects + YAML |
| **Phase Loading** | ✅ `PhaseLoader` service | ✅ Direct Python/YAML loading |

---

## Key Differences

### 1. Default vs Custom Phases

**OmoiOS**:
- ✅ **8 default phases** ready to use
- ✅ Users can create **custom phases** via YAML/API
- ✅ Default phases provide **common workflow patterns**

**Hephaestus**:
- ❌ **No default phases** - users define per workflow
- ✅ **Complete flexibility** - define phases per project
- ✅ **No assumptions** - phases match project needs

**When to Use**:
- **OmoiOS defaults**: Good for standard software development workflows
- **Custom phases**: Good for specialized workflows (research, analysis, etc.)

### 2. Structured vs Free-Form Spawning

**OmoiOS**:
- ✅ **Structured transitions** via `allowed_transitions` (normal flow)
- ✅ **Free-form spawning** via `DiscoveryService` (discovery-driven branching)
- ✅ **Hybrid approach**: Structured for normal flow, free-form for discoveries

**Hephaestus**:
- ✅ **Always free-form** - agents can spawn any phase from any phase
- ✅ **No restrictions** - complete flexibility
- ✅ **Discovery-driven** - workflows adapt automatically

**When to Use**:
- **OmoiOS hybrid**: Good for regulated workflows with controlled branching
- **Hephaestus free-form**: Good for exploratory, research, or adaptive workflows

### 3. Configuration Approach

**OmoiOS**:
- ✅ **Database-first**: Phases stored in `phases` table
- ✅ **YAML config**: Load phases from YAML files
- ✅ **API**: Create phases via API (planned)
- ✅ **Persistence**: Phases persist across projects

**Hephaestus**:
- ✅ **Code-first**: Phases defined as Python objects
- ✅ **YAML config**: Alternative YAML configuration
- ✅ **Per-workflow**: Phases defined per workflow instance
- ✅ **Ephemeral**: Phases exist for workflow duration

**When to Use**:
- **OmoiOS database**: Good for reusable phase libraries across projects
- **Hephaestus code**: Good for dynamic, workflow-specific phases

---

## How OmoiOS Phases Work

### Default Phase Usage

**Most agents use default phases**:

```python
# Agent registration
agent = register_agent(
    agent_type="worker",
    phase_id="PHASE_IMPLEMENTATION",  # Default phase
    capabilities=["implementation", "testing"],
)

# Task creation
task = enqueue_task(
    ticket_id="ticket-123",
    phase_id="PHASE_IMPLEMENTATION",  # Default phase
    task_type="implement_feature",
    description="Implement authentication system",
)
```

### Custom Phase Creation

**Step 1: Define in YAML** (`config/workflows/custom_workflow.yaml`):
```yaml
phases:
  - id: "PHASE_RESEARCH"
    name: "Research"
    description: "Investigate topic and identify approaches"
    sequence_order: 0
    allowed_transitions:
      - "PHASE_EVALUATION"
    done_definitions:
      - "Research question defined"
      - "Approaches identified"
    phase_prompt: |
      YOU ARE A RESEARCH ANALYST
      STEP 1: Understand the research question
      STEP 2: Search for existing solutions
      STEP 3: Identify 3-5 approaches to evaluate
```

**Step 2: Load into Database**:
```python
from omoi_os.services.phase_loader import PhaseLoader

phase_loader = PhaseLoader()
with db.get_session() as session:
    phases = phase_loader.load_phases_to_db(
        session=session,
        config_file="custom_workflow.yaml",
        overwrite=False
    )
```

**Step 3: Use Custom Phase**:
```python
# Agent registration
agent = register_agent(
    agent_type="researcher",
    phase_id="PHASE_RESEARCH",  # Custom phase
    capabilities=["research", "analysis"],
)

# Task creation
task = enqueue_task(
    ticket_id="ticket-456",
    phase_id="PHASE_RESEARCH",  # Custom phase
    task_type="research_topic",
    description="Research optimal architecture",
)
```

### Phase Prompt Integration

**AgentExecutor** loads phase prompts automatically:

```python
# omoi_os/services/agent_executor.py

class AgentExecutor:
    def __init__(self, phase_id: str, ...):
        self.phase_id = phase_id
        phase_context = self._load_phase_context()
        phase_instructions = self._build_phase_instructions(phase_context)
        
    def _build_phase_instructions(self, phase_context):
        # Extracts phase_prompt from PhaseModel
        phase_prompt = phase_context.get("phase_prompt")
        # Adds to agent system message
        return phase_prompt
```

**Result**: Agents automatically receive phase-specific instructions.

---

## Discovery-Based Free Spawning

### How It Works

**OmoiOS** enables **free-form spawning** via `DiscoveryService`:

```python
# Phase 3 agent discovers optimization
discovery_service.record_discovery_and_branch(
    source_task_id="task-validation-123",
    discovery_type="optimization",
    description="Caching could improve performance 40%",
    spawn_phase_id="PHASE_REQUIREMENTS",  # Can be ANY phase
    spawn_description="Investigate Redis caching",
)
```

**Key Point**: `spawn_phase_id` can be **ANY phase**, bypassing `allowed_transitions`.

### Comparison with Hephaestus

**OmoiOS**:
- Normal flow: Uses `allowed_transitions` (structured)
- Discovery flow: Bypasses `allowed_transitions` (free-form)
- **Hybrid approach**

**Hephaestus**:
- All spawning: Free-form (no restrictions)
- **Always adaptive**

**Result**: Both enable adaptive workflows, but OmoiOS provides **structured defaults** with **free-form discovery**.

---

## Use Cases

### Use Case 1: Standard Software Development

**OmoiOS Default Phases**:
```
PHASE_BACKLOG → PHASE_REQUIREMENTS → PHASE_DESIGN → 
PHASE_IMPLEMENTATION → PHASE_TESTING → PHASE_DEPLOYMENT → PHASE_DONE
```

**Best For**:
- Standard software development workflows
- Teams that want ready-to-use phases
- Projects following traditional SDLC

### Use Case 2: Research Project

**Custom Phases**:
```
PHASE_RESEARCH → PHASE_EVALUATION → PHASE_DOCUMENTATION → PHASE_DONE
```

**Best For**:
- Research projects
- Exploratory work
- Non-standard workflows

### Use Case 3: Adaptive Discovery

**Discovery-Based Branching**:
```
Phase 3 (Testing) discovers optimization
  ↓ spawns Phase 1 (Investigation)
  ↓ spawns Phase 2 (Implementation)
  ↓ spawns Phase 3 (Validation)
```

**Best For**:
- Complex systems with unknown dependencies
- Discovery-heavy work
- Adaptive workflows

---

## Recommendations

### For OmoiOS Users

1. **Start with Default Phases**:
   - Use `PHASE_BACKLOG`, `PHASE_REQUIREMENTS`, `PHASE_IMPLEMENTATION`, etc.
   - Most workflows fit default phases

2. **Create Custom Phases When Needed**:
   - Define in YAML (`config/workflows/custom.yaml`)
   - Load via `PhaseLoader`
   - Use for specialized workflows

3. **Enable Discovery-Based Branching**:
   - Use `DiscoveryService` for adaptive workflows
   - Bypasses `allowed_transitions` for discoveries
   - Enables Hephaestus-style free-form spawning

4. **Configure Phase Prompts**:
   - Write clear `phase_prompt` instructions
   - Define concrete `done_definitions`
   - Specify `expected_outputs`

### For Hephaestus Users Migrating to OmoiOS

1. **Map Hephaestus Phases to OmoiOS**:
   - Phase 1 (Analysis) → `PHASE_REQUIREMENTS`
   - Phase 2 (Building) → `PHASE_IMPLEMENTATION`
   - Phase 3 (Validation) → `PHASE_TESTING`

2. **Use DiscoveryService for Free Spawning**:
   - `DiscoveryService.record_discovery_and_branch()` enables free-form spawning
   - Bypasses `allowed_transitions` restriction

3. **Create Custom Phases if Needed**:
   - Define in YAML (similar to Hephaestus)
   - Load via `PhaseLoader`

---

---

## Deep Technical Comparison

### 1. Agent Assignment & Phase Matching

#### OmoiOS: Phase-Based Agent Matching

**Agent Registration**:
```python
# Agent registered with phase_id
agent = register_agent(
    agent_type="worker",
    phase_id="PHASE_IMPLEMENTATION",  # Agent specializes in this phase
    capabilities=["implementation", "testing"],
)
```

**Task Assignment** (`omoi_os/services/task_queue.py`):
```python
def get_next_task(self, phase_id: str, agent_capabilities: Optional[List[str]] = None):
    """Get highest-scored pending task for a phase."""
    tasks = session.query(Task).filter(
        Task.status == "pending",
        Task.phase_id == phase_id  # Match task phase to agent phase
    ).all()
    
    # Filter by capability matching
    if agent_capabilities:
        available_tasks = [
            t for t in tasks 
            if self._check_capability_match(t, agent_capabilities)
        ]
```

**Orchestrator Loop** (`omoi_os/api/main.py`):
```python
# Get available agent
available_agent = session.query(Agent).filter(
    Agent.status == AgentStatus.IDLE.value
).first()

# Get task matching agent's phase
task = queue.get_next_task(
    phase_id=available_agent.phase_id,  # Match by phase
    agent_capabilities=available_agent.capabilities
)
```

**Key Points**:
- Agents are **phase-specialized** (one phase per agent)
- Task queue filters by `phase_id` match
- Capability matching adds additional filtering
- **Strict phase matching** - agent can only get tasks from its phase

#### Hephaestus: Capability-Based Matching

**Hephaestus Approach**:
- Agents matched by **capabilities**, not phases
- Phase is a **task property**, not agent property
- Same agent can work on tasks from different phases
- **Flexible assignment** - agents adapt to task needs

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Agent Specialization** | Phase-specialized (one phase per agent) | Capability-specialized (multi-phase capable) |
| **Task Matching** | Phase ID match required | Capability match sufficient |
| **Flexibility** | Lower (agent locked to phase) | Higher (agent can work any phase) |
| **Parallelism** | Requires multiple agents per phase | Single agent can handle multiple phases |

---

### 2. Phase Prompt Injection & Agent Instructions

#### OmoiOS: Database-Driven Phase Instructions

**Phase Context Loading** (`omoi_os/services/agent_executor.py`):
```python
class AgentExecutor:
    def __init__(self, phase_id: str, db: DatabaseService):
        self.phase_id = phase_id
        self.db = db
        
        # Load phase context from database
        phase_context = self._load_phase_context()
        phase_instructions = self._build_phase_instructions(phase_context)
        
        # Inject into agent system message
        if phase_instructions:
            agent_context = AgentContext(
                system_message_suffix=phase_instructions
            )
    
    def _load_phase_context(self):
        """Load PhaseModel from database."""
        with self.db.get_session() as session:
            phase = session.query(PhaseModel).filter_by(
                id=self.phase_id
            ).first()
            return phase.to_dict() if phase else None
    
    def _build_phase_instructions(self, phase_context):
        """Build formatted instructions from phase context."""
        instructions = []
        
        # Phase name and description
        instructions.append(f"# Phase: {phase_context['name']}")
        instructions.append(phase_context['description'])
        
        # Phase prompt (main instructions)
        if phase_context.get('phase_prompt'):
            instructions.append(f"## Phase Instructions\n{phase_context['phase_prompt']}")
        
        # Done definitions (completion criteria)
        if phase_context.get('done_definitions'):
            instructions.append("## Completion Criteria")
            for criterion in phase_context['done_definitions']:
                instructions.append(f"- {criterion}")
        
        # Expected outputs
        if phase_context.get('expected_outputs'):
            instructions.append("## Expected Outputs")
            for output in phase_context['expected_outputs']:
                instructions.append(f"- {output['type']}: {output['pattern']}")
        
        return "\n".join(instructions)
```

**Result**: Agents receive **structured, database-driven** phase instructions automatically.

#### Hephaestus: Workflow-Specific Phase Prompts

**Hephaestus Approach**:
- Phase prompts defined **per workflow** (in Python objects or YAML)
- Prompts loaded when workflow starts
- **Workflow-specific** instructions (not database-driven)
- **Ephemeral** - prompts exist only during workflow execution

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Source** | Database (`PhaseModel`) | Workflow config (Python/YAML) |
| **Persistence** | Persistent across projects | Ephemeral (workflow-scoped) |
| **Reusability** | High (shared phase library) | Low (per-workflow) |
| **Dynamic Updates** | Can update database, affects all agents | Must update workflow config |
| **Structure** | Structured (done_definitions, expected_outputs) | Flexible (free-form prompts) |

---

### 3. Phase Gate Validation

#### OmoiOS: Structured Phase Gate System

**Phase Gate Service** (`omoi_os/services/phase_gate.py`):
```python
PHASE_GATE_REQUIREMENTS = {
    "PHASE_REQUIREMENTS": {
        "required_artifacts": ["requirements_document"],
        "required_tasks_completed": True,
        "validation_criteria": {
            "requirements_document": {
                "min_length": 500,
                "required_sections": ["scope", "acceptance_criteria"],
            }
        },
    },
    "PHASE_IMPLEMENTATION": {
        "required_artifacts": ["code_changes", "test_coverage"],
        "validation_criteria": {
            "test_coverage": {"min_percentage": 80},
            "code_changes": {"must_have_tests": True},
        },
    },
}

class PhaseGateService:
    def validate_gate(self, ticket_id: str, phase_id: str) -> PhaseGateResult:
        """Validate phase gate requirements."""
        # Collect artifacts from completed tasks
        artifacts = self.collect_artifacts(ticket_id, phase_id)
        
        # Check required artifacts
        missing = self._check_missing_artifacts(phase_id, artifacts)
        
        # Validate against criteria
        validation_passed = self._evaluate_validation_criteria(
            phase_id, artifacts
        )
        
        # Return gate result
        return PhaseGateResult(
            gate_status="passed" if validation_passed else "failed",
            blocking_reasons=missing if not validation_passed else []
        )
```

**Artifact Collection**:
- Automatically collects artifacts from completed tasks
- Stores in `PhaseGateArtifact` table
- Validates against phase-specific criteria
- **Structured validation** with configurable rules

#### Hephaestus: Done Definitions Validation

**Hephaestus Approach**:
- Uses `done_definitions` as completion criteria
- **Manual verification** (agent checks criteria)
- No structured artifact collection
- **Self-reported** completion

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Validation Method** | Structured gate service + artifact collection | Self-reported done definitions |
| **Artifact Tracking** | Automatic (PhaseGateArtifact table) | Manual (agent reports) |
| **Validation Criteria** | Configurable rules (min_length, min_percentage) | Free-form criteria (text descriptions) |
| **Gate Enforcement** | System-enforced (blocks transitions) | Agent-enforced (self-check) |
| **Automation** | High (automatic artifact collection) | Low (manual verification) |

---

### 4. Ticket-Phase Mapping & Kanban Integration

#### OmoiOS: Dual Mapping System

**Phase-to-Status Mapping** (`omoi_os/services/ticket_workflow.py`):
```python
PHASE_TO_STATUS = {
    "PHASE_BACKLOG": TicketStatus.BACKLOG.value,
    "PHASE_REQUIREMENTS": TicketStatus.ANALYZING.value,
    "PHASE_DESIGN": TicketStatus.ANALYZING.value,
    "PHASE_IMPLEMENTATION": TicketStatus.BUILDING.value,
    "PHASE_TESTING": TicketStatus.TESTING.value,
    "PHASE_DEPLOYMENT": TicketStatus.DONE.value,
}

STATUS_TO_PHASE = {
    TicketStatus.BACKLOG.value: "PHASE_BACKLOG",
    TicketStatus.ANALYZING.value: "PHASE_REQUIREMENTS",
    TicketStatus.BUILDING.value: "PHASE_IMPLEMENTATION",
    TicketStatus.TESTING.value: "PHASE_TESTING",
    TicketStatus.DONE.value: "PHASE_DEPLOYMENT",
}
```

**Board Column Mapping** (`omoi_os/services/board.py`):
```python
default_columns = [
    {
        "id": "analyzing",
        "phase_mapping": ["PHASE_REQUIREMENTS", "PHASE_DESIGN"],  # Multiple phases → one column
        "wip_limit": 5,
    },
    {
        "id": "building",
        "phase_mapping": ["PHASE_IMPLEMENTATION"],  # One phase → one column
        "wip_limit": 10,
    },
]
```

**Key Points**:
- **Dual mapping**: Phase ↔ Status ↔ Board Column
- **Many-to-one**: Multiple phases can map to one board column
- **WIP limits** per column (not per phase)
- **Automatic progression** via `auto_transition_to`

#### Hephaestus: Direct Phase Visualization

**Hephaestus Approach**:
- Phases shown **directly** in workflow graph
- No status/column mapping layer
- **Phase-centric** visualization
- **No Kanban board** (workflow graph only)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Visualization** | Kanban board + workflow graph | Workflow graph only |
| **Mapping Layers** | Phase → Status → Column | Phase → Graph node |
| **WIP Limits** | Per column (aggregated phases) | Not applicable |
| **Status Tracking** | Ticket status + phase | Phase only |
| **Board Integration** | Full Kanban integration | No board |

---

### 5. Discovery Implementation Details

#### OmoiOS: Explicit Discovery Service

**Discovery Service** (`omoi_os/services/discovery.py`):
```python
class DiscoveryService:
    def record_discovery_and_branch(
        self,
        session: Session,
        source_task_id: str,
        discovery_type: str,
        description: str,
        spawn_phase_id: str,  # Can be ANY phase
        spawn_description: str,
    ) -> tuple[TaskDiscovery, Task]:
        """
        IMPORTANT: This method bypasses PhaseModel.allowed_transitions
        restrictions for discovery-based spawning.
        """
        # Record discovery
        discovery = self.record_discovery(...)
        
        # Create spawned task (NO allowed_transitions check)
        spawned_task = Task(
            ticket_id=source_task.ticket_id,
            phase_id=spawn_phase_id,  # Can be ANY phase
            task_type=f"discovery_{discovery_type}",
            description=spawn_description,
            status="pending",
            result={"triggered_by_discovery": discovery.id},
        )
        
        # Link discovery to spawned task
        discovery.add_spawned_task(spawned_task.id)
        
        return discovery, spawned_task
```

**Discovery Types** (`omoi_os/models/task_discovery.py`):
```python
class DiscoveryType:
    BUG_FOUND = "bug_found"
    OPTIMIZATION_OPPORTUNITY = "optimization_opportunity"
    CLARIFICATION_NEEDED = "clarification_needed"
    NEW_COMPONENT = "new_component"
    SECURITY_ISSUE = "security_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    TECHNICAL_DEBT = "technical_debt"
    INTEGRATION_ISSUE = "integration_issue"
    DIAGNOSTIC_NO_RESULT = "diagnostic_no_result"
```

**Key Points**:
- **Explicit discovery tracking** (`TaskDiscovery` model)
- **Bypasses `allowed_transitions`** for discovery spawning
- **Structured discovery types** (bug, optimization, etc.)
- **Workflow graph building** via `get_workflow_graph()`

#### Hephaestus: Implicit Discovery Spawning

**Hephaestus Approach**:
- Agents spawn tasks **directly** (no discovery service)
- **No discovery tracking** (implicit in workflow graph)
- **No type classification** (free-form spawning)
- **Workflow graph** shows branching naturally

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Discovery Tracking** | Explicit (`TaskDiscovery` model) | Implicit (workflow graph) |
| **Discovery Types** | Structured (bug, optimization, etc.) | Free-form (no types) |
| **Spawning Method** | `DiscoveryService.record_discovery_and_branch()` | Direct task creation |
| **Reasoning Capture** | Yes (discovery.description) | No (implicit in graph) |
| **Diagnostic Value** | High (can query by type) | Low (must analyze graph) |

---

### 6. Phase Context Loading & Usage

#### OmoiOS: Database-Driven Context

**Phase Context Loading**:
```python
# AgentExecutor loads phase context
phase_context = self._load_phase_context()  # From database

# Guardian uses phase context for monitoring
phase_context = self._get_phase_context(agent.phase_id)

# Phase prompts injected into agent system messages
phase_instructions = self._build_phase_instructions(phase_context)
```

**Guardian Integration** (`omoi_os/services/intelligent_guardian.py`):
```python
def _get_phase_context(self, phase_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Get phase context for Guardian analysis."""
    with self.db.get_session() as session:
        phase = session.query(PhaseModel).filter_by(id=phase_id).first()
        return phase.to_dict() if phase else None

# Guardian uses phase context to validate agent alignment
phase_context = self._get_phase_context(agent.phase_id)
alignment_score = self._analyze_alignment(
    agent_behavior=trajectory,
    phase_context=phase_context,  # Compare against phase requirements
)
```

**Key Points**:
- Phase context loaded **from database** (persistent)
- Used by **multiple services** (AgentExecutor, Guardian, PhaseGate)
- **Shared context** across agents in same phase
- **Dynamic updates** possible (update database, affects all agents)

#### Hephaestus: Workflow-Scoped Context

**Hephaestus Approach**:
- Phase context defined **per workflow** (in config)
- **Workflow-scoped** (not shared across workflows)
- **Ephemeral** (exists only during workflow execution)
- **No cross-workflow** phase sharing

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Context Source** | Database (persistent) | Workflow config (ephemeral) |
| **Sharing** | Shared across projects/workflows | Workflow-scoped only |
| **Updates** | Update database, affects all | Update workflow config |
| **Guardian Integration** | Yes (uses phase context for validation) | No (no Guardian system) |
| **Multi-Service Usage** | Yes (AgentExecutor, Guardian, PhaseGate) | No (workflow-scoped) |

---

### 7. Task Queue Integration

#### OmoiOS: Phase-Filtered Task Queue

**Task Queue Service** (`omoi_os/services/task_queue.py`):
```python
def get_next_task(
    self, 
    phase_id: str,  # Required phase filter
    agent_capabilities: Optional[List[str]] = None
) -> Task | None:
    """Get highest-scored pending task for a phase."""
    tasks = session.query(Task).filter(
        Task.status == "pending",
        Task.phase_id == phase_id  # Phase filter required
    ).all()
    
    # Filter by dependencies and capabilities
    available_tasks = [
        t for t in tasks
        if self._check_dependencies_complete(t) and
           self._check_capability_match(t, agent_capabilities)
    ]
    
    # Score and return highest
    return max(available_tasks, key=lambda t: t.score)
```

**Orchestrator Integration**:
```python
# Orchestrator matches agent phase to task phase
task = queue.get_next_task(
    phase_id=available_agent.phase_id,  # Must match
    agent_capabilities=available_agent.capabilities
)
```

**Key Points**:
- **Phase filtering** required (strict matching)
- **Capability matching** adds additional filter
- **Dependency checking** ensures prerequisites met
- **Scoring** prioritizes tasks within phase

#### Hephaestus: Capability-Based Queue

**Hephaestus Approach**:
- Task queue filters by **capabilities**, not phases
- **No phase filtering** (phase is task property, not filter)
- **Flexible assignment** (agent can work any phase)
- **Capability-first** matching

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Primary Filter** | Phase ID (required) | Capabilities (primary) |
| **Secondary Filter** | Capabilities (optional) | Phase (not used for filtering) |
| **Agent Specialization** | Phase-specialized | Capability-specialized |
| **Assignment Flexibility** | Lower (phase-locked) | Higher (multi-phase capable) |

---

### 8. Workflow Orchestration

#### OmoiOS: Ticket Workflow Orchestrator

**Ticket Workflow Orchestrator** (`omoi_os/services/ticket_workflow.py`):
```python
class TicketWorkflowOrchestrator:
    def transition_status(
        self,
        ticket_id: str,
        to_status: str,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Ticket:
        """Transition ticket with phase gate validation."""
        ticket = session.get(Ticket, ticket_id)
        
        # Validate transition
        if not is_valid_transition(ticket.status, to_status):
            raise InvalidTransitionError(...)
        
        # Update phase based on status
        ticket.status = to_status
        ticket.phase_id = self.STATUS_TO_PHASE[to_status]
        
        # Record phase history
        phase_history = PhaseHistory(
            ticket_id=ticket.id,
            from_phase=previous_phase_id,
            to_phase=ticket.phase_id,
            transition_reason=reason,
        )
        
        return ticket
    
    def check_and_progress_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Auto-progress ticket when phase gate criteria met."""
        ticket = session.get(Ticket, ticket_id)
        
        # Check phase gate
        can_transition, blocking = self.phase_gate.can_transition(
            ticket_id, ticket.phase_id
        )
        
        if can_transition:
            # Auto-progress to next phase
            next_status = self._get_next_status(ticket.status)
            return self.transition_status(ticket_id, next_status)
```

**Key Points**:
- **State machine enforcement** (validates transitions)
- **Phase gate integration** (blocks invalid transitions)
- **Automatic progression** (when gate criteria met)
- **Phase history tracking** (audit trail)

#### Hephaestus: Free-Form Orchestration

**Hephaestus Approach**:
- **No state machine** (free-form transitions)
- **No phase gates** (agents decide when to spawn)
- **No automatic progression** (agent-driven)
- **No history tracking** (workflow graph shows history)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **State Machine** | Yes (enforced transitions) | No (free-form) |
| **Phase Gates** | Yes (structured validation) | No (agent-driven) |
| **Auto-Progression** | Yes (when criteria met) | No (agent-driven) |
| **History Tracking** | Yes (`PhaseHistory` model) | No (graph only) |
| **Control** | System-controlled | Agent-controlled |

---

### 9. Memory System Integration

#### OmoiOS: Phase-Aware Memory Storage & Retrieval

**Memory Storage** (`omoi_os/models/task_memory.py`):
```python
class TaskMemory(Base):
    task_id: str  # Links to Task (which has phase_id)
    memory_type: str  # error_fix, discovery, decision, learning, warning, codebase_knowledge
    execution_summary: str
    goal: Optional[str]  # What agent was trying to accomplish
    result: Optional[str]  # What actually happened
    feedback: Optional[str]  # Environment output
    context_embedding: List[float]  # Semantic embedding for search
```

**Memory Retrieval** (`omoi_os/services/memory.py`):
```python
def find_memories(
    self,
    query: str,
    project_id: str,
    phase_id: Optional[str] = None,  # Filter by phase
    memory_type: Optional[str] = None,
    limit: int = 20,
) -> List[TaskMemory]:
    """Find memories using hybrid search (semantic + keyword)."""
    # Semantic search using embeddings
    semantic_results = self._semantic_search(query, project_id, phase_id)
    
    # Keyword search using tsvector
    keyword_results = self._keyword_search(query, project_id, phase_id)
    
    # Combine using RRF (Reciprocal Rank Fusion)
    return self._combine_results(semantic_results, keyword_results, limit)
```

**Phase-Specific Memory Pre-loading**:
```python
# Agents pre-loaded with top 20 memories from their phase
def preload_memories_for_agent(agent_id: str, phase_id: str):
    """Pre-load relevant memories for agent's phase."""
    agent = get_agent(agent_id)
    
    # Get top memories for this phase
    memories = memory_service.find_memories(
        query=f"{phase_id} common patterns",
        project_id=agent.project_id,
        phase_id=phase_id,
        limit=20,
    )
    
    # Embed in agent's initial prompt
    return format_memories_for_prompt(memories)
```

**Key Points**:
- Memories **linked to tasks** (which have `phase_id`)
- **Phase-filtered search** enables phase-specific memory retrieval
- **Pre-loading** provides 80% coverage (common patterns)
- **Dynamic search** handles edge cases (20% coverage)

#### Hephaestus: Workflow-Scoped Memory

**Hephaestus Approach**:
- Memory **workflow-scoped** (not phase-scoped)
- **No phase filtering** (memories shared across phases)
- **Workflow-level** memory sharing
- **No pre-loading** (agents search as needed)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Memory Scope** | Phase-aware (can filter by phase) | Workflow-scoped (no phase filtering) |
| **Pre-loading** | Yes (top 20 memories per phase) | No (search as needed) |
| **Memory Types** | Structured (6 types) | Free-form (no types) |
| **Search Method** | Hybrid (semantic + keyword) | Semantic only |
| **Cross-Phase Sharing** | Yes (can search across phases) | Yes (workflow-scoped) |

---

### 10. Event System Integration

#### OmoiOS: Comprehensive Phase Event Publishing

**Phase Transition Events** (`omoi_os/services/ticket_workflow.py`):
```python
def transition_status(self, ticket_id: str, to_status: str):
    """Transition ticket and publish event."""
    ticket = session.get(Ticket, ticket_id)
    previous_phase_id = ticket.phase_id
    
    # Update phase
    ticket.phase_id = self.STATUS_TO_PHASE[to_status]
    
    # Record phase history
    phase_history = PhaseHistory(
        ticket_id=ticket.id,
        from_phase=previous_phase_id,
        to_phase=ticket.phase_id,
        transition_reason=reason,
    )
    
    # Publish event
    event_bus.publish(SystemEvent(
        event_type="ticket.status_transitioned",
        entity_type="ticket",
        entity_id=str(ticket.id),
        payload={
            "from_status": from_status,
            "to_status": to_status,
            "from_phase": previous_phase_id,
            "to_phase": ticket.phase_id,
            "initiated_by": initiated_by,
            "reason": reason,
        },
    ))
```

**Discovery Events** (`omoi_os/services/discovery.py`):
```python
def record_discovery_and_branch(...):
    """Record discovery and publish events."""
    discovery = self.record_discovery(...)
    
    # Publish discovery recorded event
    event_bus.publish(SystemEvent(
        event_type="discovery.recorded",
        entity_type="task_discovery",
        entity_id=str(discovery.id),
        payload={
            "source_task_id": source_task_id,
            "discovery_type": discovery_type,
            "spawn_phase": spawn_phase_id,  # Phase context
        },
    ))
    
    # Publish branch created event
    event_bus.publish(SystemEvent(
        event_type="discovery.branch_created",
        entity_type="task_discovery",
        entity_id=str(discovery.id),
        payload={
            "spawned_task_id": spawned_task.id,
            "spawn_phase": spawn_phase_id,  # Phase context
        },
    ))
```

**Phase Gate Events** (`omoi_os/services/phase_gate.py`):
```python
def validate_gate(self, ticket_id: str, phase_id: str):
    """Validate gate and publish result."""
    result = self.validate_gate(...)
    
    # Event published by TicketWorkflowOrchestrator
    # when gate validation completes
```

**Event Types**:
- `ticket.status_transitioned` - Phase transition events
- `discovery.recorded` - Discovery events (with phase context)
- `discovery.branch_created` - Branch spawning events (with phase context)
- `phase_gate.validated` - Gate validation events
- `task.assigned` - Task assignment (includes phase_id)
- `task.completed` - Task completion (includes phase_id)

**WebSocket Integration**:
- All phase events **broadcast via WebSocket**
- UI updates **in real-time** when phases change
- **Phase-specific subscriptions** possible

#### Hephaestus: Minimal Event System

**Hephaestus Approach**:
- **No structured event system** (workflow graph shows changes)
- **No phase transition events** (graph updates show transitions)
- **No discovery events** (graph shows branching)
- **No WebSocket integration** (polling or graph refresh)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Event System** | Comprehensive (Redis pub/sub + WebSocket) | Minimal (graph updates) |
| **Phase Events** | Yes (transition, gate, discovery) | No (graph only) |
| **Real-Time Updates** | Yes (WebSocket) | No (polling) |
| **Event Payload** | Structured (phase context included) | N/A |
| **Audit Trail** | Yes (PhaseHistory + events) | No (graph only) |

---

### 11. Validation System Integration

#### OmoiOS: Phase-Aware Validation Orchestrator

**Validation Orchestrator** (`omoi_os/services/validation_orchestrator.py`):
```python
class ValidationOrchestrator:
    def spawn_validator(self, task_id: str) -> Optional[str]:
        """Spawn validator agent for task."""
        task = session.get(Task, task_id)
        
        # Spawn validator for same phase as task
        validator = self.agent_registry.register_agent(
            agent_type="validator",
            phase_id=task.phase_id,  # Validator matches task phase
            capabilities=["validation", "code_review", "testing"],
        )
        
        return validator.id
```

**Phase-Specific Validation**:
- Validators **match task phase** (Phase 2 task → Phase 2 validator)
- **Phase context** informs validation criteria
- **Phase gate integration** (validation results feed phase gates)

**Validation State Machine**:
```python
# Validation states per phase
VALIDATION_STATES = {
    "pending": "Waiting for validation",
    "validation_in_progress": "Validator reviewing",
    "under_review": "Review complete, awaiting feedback",
    "needs_work": "Validation failed, needs fixes",
    "approved": "Validation passed",
}
```

**Key Points**:
- Validators **phase-specialized** (match task phase)
- **Phase context** guides validation criteria
- **Phase gate integration** (validation feeds gates)

#### Hephaestus: No Structured Validation

**Hephaestus Approach**:
- **No validation orchestrator** (agents self-validate)
- **No phase-specific validators** (agents validate their own work)
- **No validation state machine** (done definitions checked by agent)
- **Self-reported** completion

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Validation System** | Structured (ValidationOrchestrator) | Self-reported (agent checks) |
| **Phase Matching** | Yes (validator matches task phase) | N/A |
| **Validation States** | Yes (state machine) | No (done definitions only) |
| **Phase Gate Integration** | Yes (validation feeds gates) | No (no gates) |

---

### 12. Diagnostic System Integration

#### OmoiOS: Phase-Aware Diagnostic Recovery

**Diagnostic Service** (`omoi_os/services/diagnostic.py`):
```python
def diagnose_stuck_workflow(self, workflow_id: str):
    """Diagnose stuck workflow and spawn recovery tasks."""
    # Analyze workflow state
    analysis = self._analyze_workflow(workflow_id)
    
    # Determine suggested phase from recommendations
    suggested_phase = "PHASE_IMPLEMENTATION"  # Default
    
    if analysis.recommendations:
        rec_desc = analysis.recommendations[0].description.lower()
        if "test" in rec_desc or "validate" in rec_desc:
            suggested_phase = "PHASE_TESTING"
        elif "requirement" in rec_desc or "clarify" in rec_desc:
            suggested_phase = "PHASE_REQUIREMENTS"
        elif "implement" in rec_desc or "build" in rec_desc:
            suggested_phase = "PHASE_IMPLEMENTATION"
    
    # Spawn recovery tasks via DiscoveryService
    spawned_tasks = self.discovery.spawn_diagnostic_recovery(
        ticket_id=workflow_id,
        suggested_phase=suggested_phase,  # Phase-aware recovery
        suggested_priority="HIGH",
    )
```

**Phase Inference**:
- Diagnostic system **infers appropriate phase** from recommendations
- **Phase-aware recovery** (spawns tasks in correct phase)
- **Discovery-based spawning** (bypasses `allowed_transitions`)

**Key Points**:
- Diagnostics **phase-aware** (suggests appropriate phase)
- **Recovery tasks** spawned in correct phase
- **Discovery integration** (uses DiscoveryService for spawning)

#### Hephaestus: No Diagnostic System

**Hephaestus Approach**:
- **No diagnostic system** (workflow graph shows state)
- **No recovery spawning** (agents spawn as needed)
- **No phase inference** (agents decide phase)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Diagnostic System** | Yes (DiagnosticService) | No (graph analysis) |
| **Phase Inference** | Yes (from recommendations) | N/A |
| **Recovery Spawning** | Yes (phase-aware) | No (agent-driven) |
| **Discovery Integration** | Yes (uses DiscoveryService) | N/A |

---

### 13. Cost Tracking & Resource Management

#### OmoiOS: Phase-Level Cost Tracking

**Cost Tracking** (`omoi_os/models/cost_record.py`):
```python
class CostRecord(Base):
    task_id: str  # Links to Task (which has phase_id)
    agent_id: str
    cost_amount: float
    cost_currency: str
    model_name: str
    tokens_input: int
    tokens_output: int
    # Phase inferred from task.phase_id
```

**Phase-Level Cost Aggregation**:
```python
def get_phase_costs(self, project_id: str, phase_id: str) -> Dict[str, float]:
    """Get cost breakdown by phase."""
    with self.db.get_session() as session:
        costs = session.query(
            func.sum(CostRecord.cost_amount),
            Task.phase_id
        ).join(Task).filter(
            Task.project_id == project_id,
            Task.phase_id == phase_id
        ).group_by(Task.phase_id).all()
        
        return {phase: cost for phase, cost in costs}
```

**Resource Baselines** (`omoi_os/models/agent_baseline.py`):
```python
class AgentBaseline(Base):
    agent_type: str
    phase_id: Optional[str]  # Phase-specific baselines
    latency_ms: float
    error_rate: float
    cpu_usage_percent: float
    memory_usage_mb: float
```

**Key Points**:
- Costs **tracked per task** (phase inferred from task)
- **Phase-level aggregation** enables phase cost analysis
- **Phase-specific baselines** for anomaly detection
- **Resource monitoring** per phase

#### Hephaestus: No Cost Tracking

**Hephaestus Approach**:
- **No cost tracking** (workflow-focused, not cost-focused)
- **No resource baselines** (no monitoring system)
- **No phase-level metrics** (phase is task property)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Cost Tracking** | Yes (per task, aggregated by phase) | No |
| **Resource Baselines** | Yes (phase-specific) | No |
| **Phase Metrics** | Yes (cost, latency, error rate) | No |
| **Budget Enforcement** | Yes (per project/organization) | No |

---

### 14. Performance Metrics & Monitoring

#### OmoiOS: Phase-Level Metrics Collection

**Metrics Collection** (`omoi_os/services/monitor.py`):
```python
def collect_task_metrics(self, phase_id: Optional[str] = None) -> Dict[str, MetricSample]:
    """Collect task-related metrics, optionally filtered by phase."""
    # Queue depth by phase
    queue_stats = session.query(
        Task.phase_id,
        Task.priority,
        func.count(Task.id).label("count")
    ).filter(Task.status == "pending")
    
    if phase_id:
        query = query.filter(Task.phase_id == phase_id)  # Phase filter
    
    # Completed tasks by phase
    completed_stats = session.query(
        Task.phase_id,
        func.count(Task.id).label("count")
    ).filter(Task.status == "completed")
    
    if phase_id:
        completed_query = completed_query.filter(Task.phase_id == phase_id)
```

**Standard Metrics** (`omoi_os/telemetry/__init__.py`):
```python
STANDARD_METRICS = [
    MetricDefinition(
        name="tasks_queued_total",
        labels=["phase_id", "priority"],  # Phase-aware
    ),
    MetricDefinition(
        name="tasks_completed_total",
        labels=["phase_id", "agent_id"],  # Phase-aware
    ),
    MetricDefinition(
        name="task_duration_seconds",
        labels=["phase_id", "task_type"],  # Phase-aware
    ),
    MetricDefinition(
        name="agents_active",
        labels=["agent_type", "phase_id"],  # Phase-aware
    ),
]
```

**Phase-Level Dashboards**:
- **Phase overview** shows metrics per phase
- **Phase comparison** (which phases are slowest)
- **Phase bottlenecks** (queue depth per phase)
- **Phase efficiency** (completion rate per phase)

**Key Points**:
- Metrics **phase-labeled** (all metrics include phase_id)
- **Phase filtering** enables phase-specific analysis
- **Phase dashboards** show phase-level performance
- **Anomaly detection** per phase (using phase-specific baselines)

#### Hephaestus: No Metrics System

**Hephaestus Approach**:
- **No metrics collection** (workflow graph shows progress)
- **No phase-level metrics** (phase is visualization only)
- **No performance monitoring** (no monitoring system)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Metrics Collection** | Yes (phase-labeled) | No |
| **Phase Filtering** | Yes (filter by phase) | N/A |
| **Phase Dashboards** | Yes (phase overview) | No |
| **Anomaly Detection** | Yes (phase-specific baselines) | No |

---

### 15. Error Handling & Retry Logic

#### OmoiOS: Phase-Aware Error Handling

**Task Model** (`omoi_os/models/task.py`):
```python
class Task(Base):
    retry_count: int = 0  # Current retry attempt
    max_retries: int = 3  # Maximum allowed retries
    timeout_seconds: Optional[int] = None  # Phase-specific timeout
    error_message: Optional[str] = None
```

**Phase-Specific Configuration** (`omoi_os/models/phase.py`):
```python
class PhaseModel(Base):
    configuration: Optional[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Phase-specific configuration (timeouts, requirements, etc.)"
    )
    # Example configuration:
    # {
    #   "timeout_seconds": 3600,  # Phase-specific timeout
    #   "max_retries": 5,  # Phase-specific retry limit
    #   "retry_backoff": "exponential",  # Retry strategy
    # }
```

**Retry Logic** (`omoi_os/services/task_queue.py`):
```python
def get_retryable_tasks(self, phase_id: str | None = None) -> list[Task]:
    """Get tasks that can be retried, optionally filtered by phase."""
    query = session.query(Task).filter(
        Task.status == "failed",
        Task.retry_count < Task.max_retries
    )
    
    if phase_id:
        query = query.filter(Task.phase_id == phase_id)  # Phase filter
    
    return query.all()
```

**Error Classification**:
- **Retryable errors**: Network timeouts, temporary failures
- **Permanent errors**: Syntax errors, authentication failures
- **Phase-specific handling**: Different error handling per phase

**Key Points**:
- **Phase-specific timeouts** (via `phase.configuration`)
- **Phase-specific retry limits** (via `phase.configuration`)
- **Phase-filtered retry queue** (retry tasks by phase)
- **Error classification** (retryable vs permanent)

#### Hephaestus: Agent-Driven Error Handling

**Hephaestus Approach**:
- **No structured retry logic** (agents handle errors themselves)
- **No phase-specific timeouts** (no timeout system)
- **No error classification** (agents decide retry)
- **Self-healing** (agents spawn fix tasks)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Retry Logic** | Structured (exponential backoff) | Agent-driven (self-healing) |
| **Phase-Specific Timeouts** | Yes (via phase.configuration) | No |
| **Error Classification** | Yes (retryable vs permanent) | No |
| **Retry Queue** | Yes (phase-filtered) | No (agent-driven) |

---

### 16. MCP Tools Integration

#### OmoiOS: Phase-Aware MCP Tools

**MCP Tools** (`omoi_os/mcp/fastmcp_server.py`):
```python
@mcp_tool()
def create_task(
    ticket_id: str,
    phase_id: str,  # Phase required for task creation
    description: str,
    priority: str = "MEDIUM",
) -> dict:
    """Create a task in a specific phase."""
    task = task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id=phase_id,  # Phase specified
        task_type="custom",
        description=description,
        priority=priority,
    )
    return {"task_id": task.id, "phase_id": phase_id}

@mcp_tool()
def change_ticket_status(
    ticket_id: str,
    new_status: str,
    comment: str,
) -> dict:
    """Change ticket status (phase inferred from status)."""
    # Status → Phase mapping handled by TicketWorkflowOrchestrator
    ticket = ticket_workflow.transition_status(
        ticket_id=ticket_id,
        to_status=new_status,
        reason=comment,
    )
    return {"ticket_id": ticket.id, "phase_id": ticket.phase_id}
```

**Phase Context in Tools**:
- Tools **receive phase context** via task.phase_id
- **Phase-aware operations** (create tasks in specific phases)
- **Phase validation** (tools validate phase transitions)

**Tool Authorization** (`omoi_os/models/mcp_policy.py`):
```python
class MCPPolicy(Base):
    agent_type: str
    phase_id: Optional[str]  # Phase-specific tool permissions
    allowed_tools: List[str]  # Tools allowed for this phase
    denied_tools: List[str]  # Tools denied for this phase
```

**Key Points**:
- MCP tools **phase-aware** (can specify/create tasks in phases)
- **Phase-specific permissions** (via MCPPolicy)
- **Phase validation** (tools enforce phase rules)

#### Hephaestus: Phase-Agnostic Tools

**Hephaestus Approach**:
- Tools **phase-agnostic** (phase is task property, not tool concern)
- **No phase-specific permissions** (capability-based only)
- **No phase validation** (agents decide phase)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Phase Awareness** | Yes (tools specify phase) | No (phase-agnostic) |
| **Phase Permissions** | Yes (MCPPolicy per phase) | No (capability-based) |
| **Phase Validation** | Yes (tools validate transitions) | No (agent-driven) |

---

### 17. Workspace Isolation Integration

#### OmoiOS: Phase-Aware Workspace Management

**Workspace Model** (`omoi_os/models/workspace.py`):
```python
class AgentWorkspace(Base):
    agent_id: str  # Links to Agent (which has phase_id)
    workspace_path: str
    git_branch: str
    # Phase inferred from agent.phase_id
```

**Workspace Creation** (`omoi_os/services/workspace_manager.py`):
```python
def create_workspace(self, agent_id: str) -> AgentWorkspace:
    """Create workspace for agent."""
    agent = session.get(Agent, agent_id)
    
    # Workspace inherits agent's phase context
    workspace = AgentWorkspace(
        agent_id=agent_id,
        workspace_path=f"{workspace_root}/{agent_id}",
        git_branch=f"phase-{agent.phase_id}-{agent_id}",  # Phase in branch name
    )
    
    return workspace
```

**Phase-Specific Workspaces**:
- Each agent gets **isolated workspace**
- **Git branch** includes phase identifier
- **Workspace isolation** per phase (agents don't interfere)
- **Phase-specific commits** (commits tagged with phase)

**Key Points**:
- Workspaces **phase-labeled** (branch includes phase)
- **Isolation** per agent (phase context preserved)
- **Git integration** (phase in branch names)

#### Hephaestus: Workflow-Scoped Workspaces

**Hephaestus Approach**:
- Workspaces **workflow-scoped** (not phase-scoped)
- **No phase in branch names** (workflow identifier only)
- **Shared workspaces** possible (agents can share)

**Comparison**:
| Aspect | OmoiOS | Hephaestus |
|--------|--------|------------|
| **Workspace Scope** | Agent-scoped (phase-labeled) | Workflow-scoped |
| **Phase in Branches** | Yes (phase-{phase_id}-{agent_id}) | No (workflow identifier) |
| **Isolation** | Per agent (phase-preserved) | Per workflow (shared) |
| **Git Integration** | Yes (phase-labeled branches) | Yes (workflow branches) |

---

## Summary

**OmoiOS Phase System**:
- ✅ **8 default phases** for common workflows
- ✅ **Custom phases** via YAML/API/database
- ✅ **Structured transitions** via `allowed_transitions`
- ✅ **Free-form spawning** via `DiscoveryService` (bypasses restrictions)
- ✅ **Hephaestus-inspired** features (done_definitions, phase_prompt, expected_outputs)
- ✅ **Database persistence** for reusable phase libraries
- ✅ **Phase gate validation** with artifact collection
- ✅ **Kanban board integration** (phase → status → column mapping)
- ✅ **Guardian integration** (phase context for monitoring)
- ✅ **Structured discovery tracking** (`TaskDiscovery` model)

**Hephaestus Phasor System**:
- ✅ **No default phases** - users define per workflow
- ✅ **Always free-form** spawning (no restrictions)
- ✅ **Python objects or YAML** configuration
- ✅ **Workflow-specific** phases (ephemeral)
- ✅ **Capability-based** agent matching (not phase-based)
- ✅ **Direct phase visualization** (workflow graph)
- ✅ **Agent-controlled** orchestration (no state machine)
- ✅ **Implicit discovery** (no tracking model)

**Key Differences**:

1. **Agent Assignment**:
   - **OmoiOS**: Phase-specialized agents (strict phase matching)
   - **Hephaestus**: Capability-specialized agents (flexible phase assignment)

2. **Phase Instructions**:
   - **OmoiOS**: Database-driven, persistent, shared across projects
   - **Hephaestus**: Workflow-scoped, ephemeral, per-workflow

3. **Phase Gates**:
   - **OmoiOS**: Structured validation with artifact collection
   - **Hephaestus**: Self-reported done definitions

4. **Discovery**:
   - **OmoiOS**: Explicit tracking (`TaskDiscovery` model) with structured types
   - **Hephaestus**: Implicit (workflow graph shows branching)

5. **Orchestration**:
   - **OmoiOS**: System-controlled (state machine + phase gates)
   - **Hephaestus**: Agent-controlled (free-form spawning)

6. **Visualization**:
   - **OmoiOS**: Kanban board + workflow graph (dual visualization)
   - **Hephaestus**: Workflow graph only (phase-centric)

**Best of Both Worlds**:
- **OmoiOS** provides **structured defaults** with **discovery-based branching** for adaptive workflows
- **Hephaestus** provides **complete flexibility** for exploratory, research workflows
- **OmoiOS** adds **enterprise features** (phase gates, artifact tracking, Guardian integration)
- **Hephaestus** focuses on **simplicity** and **agent autonomy**

---

## Related Documents

- [Phasor System](./phasor_system.md) - Hephaestus Phasor system documentation
- [Phase Model](../../omoi_os/models/phase.py) - OmoiOS PhaseModel implementation
- [Phase Loader](../../omoi_os/services/phase_loader.py) - Phase loading service
- [Discovery Service](../../omoi_os/services/discovery.py) - Discovery-based task spawning
- [Phase Gate Service](../../omoi_os/services/phase_gate.py) - Phase gate validation
- [Ticket Workflow Orchestrator](../../omoi_os/services/ticket_workflow.py) - Workflow orchestration
- [Agent Executor](../../omoi_os/services/agent_executor.py) - Phase prompt injection
- [Software Development Workflow](../../omoi_os/config/workflows/software_development.yaml) - Example phase configuration

