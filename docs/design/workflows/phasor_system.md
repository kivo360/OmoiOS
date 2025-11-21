# Phasor System: Adaptive Phase Orchestration

**Created**: 2025-01-30
**Status**: Design Document
**Purpose**: Explain Hephaestus's Phasor system and how it enables adaptive, self-building workflows in OmoiOS
**Related**: [Hephaestus Workflow Enhancements](../implementation/workflows/hephaestus_workflow_enhancements.md), [Phase Model](../../omoi_os/models/phase.py)

---

## Overview

The **Phasor System** (from Hephaestus) enables **adaptive phase orchestration** where workflows build themselves based on agent discoveries. Unlike traditional linear pipelines, Phasor allows agents to spawn tasks in **any phase** from **any phase**, creating branching workflows that adapt to reality.

**Core Principle**: "Define the types of work, not the specific work to do. Let workflows discover themselves."

---

## What is Phasor?

**Phasor** = **Phase Orchestrator** - A system that enables:

1. **Free-Form Phase Spawning**: Agents can spawn tasks in ANY phase from ANY phase
2. **Adaptive Workflows**: Workflow structure emerges from discoveries, not predefined plans
3. **Branching Trees**: Multiple parallel branches grow as agents find new work
4. **Discovery-Driven**: Agents discover work and spawn appropriate phase tasks

### Key Difference from Traditional Systems

**Traditional Workflow**:
```
Step 1 → Step 2 → Step 3 → Done
```
Rigid pipeline. If reality doesn't match plan, workflow breaks.

**Phasor Workflow**:
```
Phase 1 (Analysis)
  ↓ spawns
Phase 2 (Build) × 5 parallel
  ↓ spawns
Phase 3 (Test) × 5 parallel
  ↓ discovers optimization
Phase 1 (Investigate) ← NEW BRANCH
  ↓ spawns
Phase 2 (Implement) ← NEW BRANCH
  ↓ spawns
Phase 3 (Validate) ← NEW BRANCH
```
Adaptive tree. Structure emerges from discoveries.

---

## How Phasor Works

### 1. Phases as Job Descriptions

Phases aren't rigid steps. They're **specialized instruction sets** for different types of work:

```python
Phase 1: Requirements Analysis
  - Role: "Figure out what to build"
  - Instructions: "Read PRD, identify components"
  - Success: "Components identified, Phase 2 tasks created"

Phase 2: Implementation
  - Role: "Build one component"
  - Instructions: "Design, code, test"
  - Success: "Code created, tests passing, Phase 3 task created"

Phase 3: Validation
  - Role: "Make sure it works"
  - Instructions: "Test, verify requirements"
  - Success: "Tests pass, requirements met"
```

### 2. Free-Form Spawning

**Hephaestus Rule**: Agents can spawn tasks in **ANY phase** from **ANY phase**.

**Example**:
```
Phase 3 agent (testing API) discovers caching pattern
  ↓
Spawns Phase 1 task (investigate caching)
  ↓
Phase 1 agent investigates
  ↓
Spawns Phase 2 task (implement caching)
  ↓
New feature branch emerges
```

**Key Point**: Phase 3 agent **doesn't stop** its original work. It discovers something, spawns investigation, and continues testing.

### 3. Discovery-Driven Branching

Workflows branch when agents discover:
- **Bugs** → Spawn Phase 2 fix task
- **Optimizations** → Spawn Phase 1 investigation → Phase 2 implementation
- **Missing Requirements** → Spawn Phase 1 clarification task
- **Security Issues** → Spawn Phase 1 investigation → Phase 2 fix
- **Technical Debt** → Spawn Phase 1 analysis → Phase 2 refactor

---

## When to Use Phasor

### ✅ Use Phasor When:

1. **Building Complex Systems**
   - Multiple components with unknown dependencies
   - Requirements evolve as you build
   - Need adaptive exploration

2. **Discovery-Heavy Work**
   - Analyzing systems (find issues, optimizations)
   - Research projects (discover new approaches)
   - Exploratory development (find what's needed)

3. **Parallel Development**
   - Multiple teams/agents working independently
   - Components can be built in parallel
   - Need coordination without rigid structure

4. **Uncertain Requirements**
   - Requirements emerge during development
   - Need to adapt to discoveries
   - Can't plan everything upfront

### ❌ Don't Use Phasor When:

1. **Simple, Linear Tasks**
   - Single-step processes
   - Well-defined workflows
   - No branching needed

2. **Regulated Processes**
   - Compliance requires strict sequence
   - Approval gates at specific stages
   - Can't allow free-form spawning

3. **Time-Critical, Predictable Work**
   - Need guaranteed completion time
   - Can't allow exploratory branching
   - Must follow predefined plan

---

## Why Use Phasor?

### 1. **Workflows That Adapt to Reality**

**Problem**: Traditional workflows break when reality doesn't match plan.

**Solution**: Phasor workflows adapt as agents discover what's actually needed.

**Example**:
```
Plan: Build auth system → Build API → Build frontend

Reality: 
- Auth system needs Redis (discovered during build)
- API needs auth first (discovered dependency)
- Frontend needs API endpoints (discovered requirement)

Phasor Response:
- Spawns Redis setup task (Phase 2)
- Spawns auth-first task (Phase 2)
- Spawns API endpoint task (Phase 2)
- Workflow adapts automatically
```

### 2. **Agents Stay Focused**

**Problem**: One agent trying to do everything loses context.

**Solution**: Each agent has one focused job (their phase), spawns other work to appropriate phases.

**Example**:
```
❌ Bad: One agent tries to:
- Analyze requirements
- Design architecture
- Implement code
- Write tests
- Deploy system
→ Agent gets overwhelmed, loses context

✅ Good: Specialized agents:
- Phase 1 agent: Analyzes requirements, spawns Phase 2 tasks
- Phase 2 agents: Build components, spawn Phase 3 tasks
- Phase 3 agents: Test components, spawn fixes if needed
→ Each agent stays focused on their expertise
```

### 3. **Parallel Exploration**

**Problem**: Sequential workflows are slow.

**Solution**: Multiple branches explore different aspects simultaneously.

**Example**:
```
Phase 1: Analyze PRD
  ↓ spawns 5 components
Phase 2: Build Auth | Build API | Build Frontend | Build DB | Build Workers
  ↓ all spawn Phase 3 tasks
Phase 3: Test Auth | Test API | Test Frontend | Test DB | Test Workers
  ↓ one discovers optimization
Phase 1: Investigate Caching ← NEW BRANCH (parallel to testing)
  ↓ spawns Phase 2
Phase 2: Implement Caching ← NEW BRANCH
  ↓ spawns Phase 3
Phase 3: Validate Caching ← NEW BRANCH

Result: 8 parallel work streams instead of 1 sequential flow
```

### 4. **Knowledge Discovery**

**Problem**: Predefined workflows miss opportunities.

**Solution**: Agents discover optimizations, improvements, and new requirements as they work.

**Example**:
```
Phase 3 agent testing API discovers:
- Caching pattern could improve performance 40%
- Security vulnerability in auth flow
- Missing rate limiting

Spawns:
- Phase 1 investigation (caching)
- Phase 2 fix (security)
- Phase 1 analysis (rate limiting)

Workflow discovers and addresses issues automatically
```

---

## How OmoiOS Currently Handles Phases

### Current Implementation

**OmoiOS Phase Model** (`omoi_os/models/phase.py`):
```python
class PhaseModel(Base):
    id: str  # PHASE_IMPLEMENTATION
    name: str  # "Implementation"
    done_definitions: List[str]  # ["Component code created", "Tests passing"]
    phase_prompt: str  # "YOU ARE A SOFTWARE ENGINEER..."
    allowed_transitions: List[str]  # ["PHASE_INTEGRATION", "PHASE_BLOCKED"]
```

**Key Constraint**: `allowed_transitions` restricts which phases can be transitioned to.

**Current Flow**:
```
Phase 1 → Phase 2 → Phase 3 → Done
(Only transitions in allowed_transitions)
```

### Discovery Service

**OmoiOS DiscoveryService** (`omoi_os/services/discovery.py`):
```python
discovery_service.record_discovery_and_branch(
    source_task_id="task-123",
    discovery_type="bug",
    spawn_phase_id="PHASE_IMPLEMENTATION",  # Must be in allowed_transitions?
)
```

**Current Limitation**: Discovery spawning might be constrained by `allowed_transitions`.

---

## Implementing Phasor in OmoiOS

### Option 1: Discovery-Based Free-Phase Spawning (Recommended)

**Approach**: Allow `DiscoveryService` to spawn tasks in **ANY phase**, bypassing `allowed_transitions`.

**Implementation**:
```python
# omoi_os/services/discovery.py

def record_discovery_and_branch(
    self,
    session: Session,
    source_task_id: str,
    discovery_type: str,
    description: str,
    spawn_phase_id: str,  # Can be ANY phase
    spawn_description: str,
    priority_boost: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> tuple[TaskDiscovery, Task]:
    """
    Record discovery and spawn task in ANY phase.
    
    Discovery-based spawning bypasses allowed_transitions restriction.
    This enables adaptive workflows where agents can spawn work in any
    phase based on what they discover.
    """
    # Record discovery
    discovery = self.record_discovery(...)
    
    # Spawn task in ANY phase (no allowed_transitions check)
    spawned_task = self._create_task_in_phase(
        phase_id=spawn_phase_id,  # No restriction check
        description=spawn_description,
        parent_task_id=source_task_id,
    )
    
    # Link discovery to spawned task
    discovery.add_spawned_task(spawned_task.id)
    
    return discovery, spawned_task
```

**Benefits**:
- ✅ Enables adaptive workflows
- ✅ Maintains structured transitions for normal flow
- ✅ Allows discovery-based branching
- ✅ Backward compatible

### Option 2: Phase Configuration Flag

**Approach**: Add `allow_free_spawning` flag to phases.

**Implementation**:
```python
class PhaseModel(Base):
    # ... existing fields ...
    
    allow_free_spawning: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Allow agents to spawn tasks in this phase from any phase"
    )
```

**Usage**:
```python
# Phase 1: Requirements Analysis
allow_free_spawning=True  # Can be spawned from any phase

# Phase 2: Implementation
allow_free_spawning=False  # Only from Phase 1

# Phase 3: Validation
allow_free_spawning=False  # Only from Phase 2
```

**Benefits**:
- ✅ Granular control per phase
- ✅ Some phases can be "entry points" for discoveries
- ✅ More flexible than global free spawning

### Option 3: Hybrid Approach (Best)

**Approach**: Combine structured transitions + discovery-based free spawning.

**Rules**:
1. **Normal Flow**: Use `allowed_transitions` for structured progression
2. **Discovery Flow**: Bypass `allowed_transitions` when spawning via `DiscoveryService`
3. **Phase Prompt Guidance**: Tell agents to continue original work after spawning

**Implementation**:
```python
# Normal task creation (structured)
def enqueue_task(...):
    # Check allowed_transitions
    if not current_phase.can_transition_to(target_phase):
        raise ValueError("Transition not allowed")

# Discovery-based spawning (free-form)
def record_discovery_and_branch(...):
    # No allowed_transitions check
    # Can spawn ANY phase
    spawned_task = create_task_in_phase(phase_id=spawn_phase_id)
```

**Phase Prompt Example**:
```python
phase_prompt = """
YOU ARE A SOFTWARE ENGINEER IN PHASE 3 (VALIDATION)

STEP 1: Run comprehensive tests
STEP 2: Verify requirements are met
STEP 3: If you discover bugs, optimizations, or missing requirements:
  - Use DiscoveryService to spawn appropriate phase tasks
  - Continue your validation work (don't stop!)
STEP 4: Mark task as done when validation complete

IMPORTANT: When spawning discovery tasks, choose the appropriate phase:
- Bugs → Phase 2 (Implementation) for fixes
- Optimizations → Phase 1 (Analysis) for investigation
- Missing Requirements → Phase 1 (Analysis) for clarification
"""
```

---

## Use Cases

### Use Case 1: Building a Web Application

**Scenario**: Build web app from PRD

**Phasor Flow**:
```
Phase 1: Analyze PRD
  ↓ identifies 5 components
Phase 2: Build Auth | Build API | Build Frontend | Build DB | Build Workers
  ↓ Phase 2: Build API discovers caching opportunity
Phase 1: Investigate Caching ← NEW BRANCH
  ↓ Phase 1: Investigate Caching determines it's valuable
Phase 2: Implement Caching ← NEW BRANCH
  ↓ Phase 2: Implement Caching completes
Phase 3: Validate Caching ← NEW BRANCH
  ↓ Meanwhile, original Phase 2 tasks continue
Phase 3: Test Auth | Test API | Test Frontend | Test DB | Test Workers
```

**Result**: 9 parallel work streams, workflow adapted to discovery

### Use Case 2: Analyzing a Legacy System

**Scenario**: Understand and document legacy codebase

**Phasor Flow**:
```
Phase 1: Initial Analysis
  ↓ identifies 3 major subsystems
Phase 2: Deep Dive Subsystem A | Deep Dive B | Deep Dive C
  ↓ Phase 2: Deep Dive B discovers security vulnerability
Phase 1: Security Analysis ← NEW BRANCH
  ↓ Phase 1: Security Analysis identifies scope
Phase 2: Document Vulnerability ← NEW BRANCH
  ↓ Phase 2: Document Vulnerability completes
Phase 3: Review Documentation ← NEW BRANCH
```

**Result**: Analysis expands as issues are discovered

### Use Case 3: Research Project

**Scenario**: Research optimal architecture for new feature

**Phasor Flow**:
```
Phase 1: Research Question
  ↓ identifies 3 approaches
Phase 2: Evaluate Approach A | Evaluate B | Evaluate C
  ↓ Phase 2: Evaluate B discovers related research
Phase 1: Research Related Topic ← NEW BRANCH
  ↓ Phase 1: Research Related Topic finds new approach
Phase 2: Evaluate New Approach ← NEW BRANCH
```

**Result**: Research expands as new information is discovered

---

## Integration with OmoiOS Systems

### 1. DiscoveryService Integration

**Current**: `DiscoveryService.record_discovery_and_branch()` spawns tasks

**Enhancement**: Allow spawning in ANY phase

```python
# Phase 3 agent discovers optimization
discovery_service.record_discovery_and_branch(
    source_task_id="task-validation-123",
    discovery_type="optimization",
    description="Caching could improve performance 40%",
    spawn_phase_id="PHASE_REQUIREMENTS",  # Jump back to Phase 1
    spawn_description="Investigate Redis caching for API",
)
```

### 2. Phase Gate Integration

**Current**: Phase gates validate transitions

**Enhancement**: Discovery-based spawning bypasses phase gates

```python
# Normal transition: Check phase gate
if not phase_gate.can_transition(current_phase, target_phase):
    raise PhaseGateError("Transition not allowed")

# Discovery spawning: Skip phase gate
discovery_service.record_discovery_and_branch(
    spawn_phase_id="PHASE_REQUIREMENTS",  # No gate check
)
```

### 3. Ticket Workflow Integration

**Current**: Tickets move through phases via `allowed_transitions`

**Enhancement**: Discovery tasks can link to tickets in any phase

```python
# Discovery spawns task in different phase
discovery, task = discovery_service.record_discovery_and_branch(
    spawn_phase_id="PHASE_REQUIREMENTS",  # Different phase
    spawn_description="Phase 1: Clarify requirement - TICKET: ticket-xxx",
)

# Task links to ticket (even though different phase)
task.ticket_id = ticket_id
task.link_reason = "Discovery requires clarification"
```

### 4. Guardian Integration

**Current**: Guardian monitors agents against phase instructions

**Enhancement**: Guardian understands discovery spawning is expected

```python
# Guardian sees agent spawning Phase 1 task from Phase 3
# This is EXPECTED behavior (discovery-driven branching)
# Guardian doesn't flag as drift
```

### 5. Memory System Integration

**Current**: Agents save discoveries to memory

**Enhancement**: Memory informs phase spawning decisions

```python
# Agent searches memory before spawning
memories = memory_service.search_similar(
    query="caching optimization patterns",
    memory_types=["discovery", "decision"]
)

# If similar discovery found, reference it
if memories:
    discovery_metadata = {
        "related_memory": memories[0].id,
        "similar_discoveries": [m.id for m in memories]
    }
```

---

## UI/UX Considerations

### Phase Overview Dashboard

**Component**: `PhaseOverview.tsx`

Shows:
- Phase cards with task counts
- Active agents per phase
- Discovery indicators (new branches)
- Phase status (active, completed, idle)

**Example**:
```
┌─────────────────────────────────────────────────────────┐
│  Phase 1: Requirements Analysis                        │
│  Status: Completed | Agents: 0 active                  │
│  Tasks: Total 1 | Done 1 | Active 0                    │
│  [View Tasks →]                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Phase 2: Implementation                                │
│  Status: Active | Agents: 2 active                    │
│  Tasks: Total 28 | Done 22 | Active 2                  │
│  Discoveries: 3 new branches spawned                    │
│  [View Tasks →] [View Discoveries →]                   │
└─────────────────────────────────────────────────────────┘
```

### Workflow Graph Visualization

**Component**: `WorkflowGraph.tsx`

Shows:
- Phase columns (Phase 1, Phase 2, Phase 3)
- Task nodes with phase badges
- Discovery edges (purple) showing branching
- Normal flow edges (green) showing progression

**Features**:
- Click node → See task details
- Click edge → See discovery/reasoning
- Hover → Highlight reasoning chain
- Filter by phase, discovery type, agent

### Discovery Timeline

**Component**: `DiscoveryTimeline.tsx`

Shows chronological discovery events:
```
Oct 30, 10:25 AM  Discovery: Bug Found
  └─ Source: Phase 3 Task "Test API"
  └─ Spawned: Phase 2 Task "Fix Login Bug"
  
Oct 30, 10:28 AM  Discovery: Optimization
  └─ Source: Phase 3 Task "Test API"
  └─ Spawned: Phase 1 Task "Investigate Caching"
```

---

## Configuration Examples

### Example 1: Software Development Workflow

```python
PHASE_REQUIREMENTS = PhaseModel(
    id="PHASE_REQUIREMENTS",
    name="Requirements Analysis",
    description="Analyze PRD and identify components",
    done_definitions=[
        "Requirements extracted and documented",
        "Components identified",
        "Phase 2 tasks created for each component"
    ],
    phase_prompt="""
    YOU ARE A REQUIREMENTS ANALYST
    
    STEP 1: Read the PRD document
    STEP 2: Identify all major system components
    STEP 3: For each component, create a Phase 2 implementation task
    STEP 4: Mark task as done
    
    If you discover missing requirements or ambiguities:
    - Create Phase 1 clarification tasks
    - Continue your analysis
    """,
    expected_outputs=[
        {"type": "document", "pattern": "requirements.md", "required": True},
        {"type": "task", "pattern": "Phase 2 tasks", "min_count": 1}
    ],
    next_steps_guide=[
        "Phase 2 agents will implement each component",
        "Each Phase 2 agent will spawn Phase 3 validation tasks"
    ],
    # allow_free_spawning=True  # Can be spawned from any phase for discoveries
)

PHASE_IMPLEMENTATION = PhaseModel(
    id="PHASE_IMPLEMENTATION",
    name="Implementation",
    description="Build one component with tests",
    done_definitions=[
        "Component code files created in src/",
        "Minimum 3 test cases written",
        "Tests passing locally",
        "Phase 3 validation task created",
        "update_task_status called with status='done'"
    ],
    phase_prompt="""
    YOU ARE A SOFTWARE ENGINEER
    
    STEP 1: Understand the component requirements
    STEP 2: Design the component interface
    STEP 3: Implement the core logic
    STEP 4: Write comprehensive tests (minimum 3 cases)
    STEP 5: Run tests and verify they pass
    STEP 6: Create Phase 3 validation task
    STEP 7: Mark task as done
    
    If you discover bugs, optimizations, or missing requirements:
    - Use DiscoveryService to spawn appropriate phase tasks
    - Continue your implementation work
    """,
    expected_outputs=[
        {"type": "file", "pattern": "src/**/*.py", "required": True},
        {"type": "test", "pattern": "tests/test_*.py", "min_passing": 3}
    ],
    next_steps_guide=[
        "Phase 3 agent will run integration tests",
        "If tests pass, component is validated",
        "If tests fail, bugs will be spawned back to Phase 2"
    ],
    allowed_transitions=["PHASE_INTEGRATION", "PHASE_BLOCKED"]
)

PHASE_VALIDATION = PhaseModel(
    id="PHASE_VALIDATION",
    name="Validation",
    description="Test component and verify requirements",
    done_definitions=[
        "Integration tests written",
        "All tests passing",
        "Requirements verified",
        "Component marked as validated"
    ],
    phase_prompt="""
    YOU ARE A QA ENGINEER
    
    STEP 1: Run integration tests
    STEP 2: Verify component meets requirements
    STEP 3: Check for edge cases
    STEP 4: If tests pass → Mark component as validated
    STEP 5: If tests fail → Spawn Phase 2 bug-fix task
    
    If you discover optimizations, security issues, or improvements:
    - Spawn Phase 1 investigation tasks
    - Spawn Phase 2 implementation tasks
    - Continue your validation work
    """,
    expected_outputs=[
        {"type": "test", "pattern": "tests/integration/*.py", "required": True},
        {"type": "report", "pattern": "validation_report.md", "required": True}
    ],
    next_steps_guide=[
        "If validated → Component is complete",
        "If bugs found → Phase 2 fixes → Re-validation"
    ],
    allowed_transitions=["PHASE_DONE", "PHASE_IMPLEMENTATION"]  # Can loop back for fixes
)
```

### Example 2: Research Workflow

```python
PHASE_RESEARCH = PhaseModel(
    id="PHASE_RESEARCH",
    name="Research",
    description="Investigate topic and identify approaches",
    done_definitions=[
        "Research question defined",
        "Approaches identified",
        "Phase 2 evaluation tasks created"
    ],
    phase_prompt="""
    YOU ARE A RESEARCH ANALYST
    
    STEP 1: Understand the research question
    STEP 2: Search for existing solutions/approaches
    STEP 3: Identify 3-5 approaches to evaluate
    STEP 4: Create Phase 2 evaluation tasks for each approach
    
    If you discover related research or new questions:
    - Spawn Phase 1 research tasks to explore them
    - Continue your original research
    """,
    allow_free_spawning=True  # Research can branch freely
)

PHASE_EVALUATION = PhaseModel(
    id="PHASE_EVALUATION",
    name="Evaluation",
    description="Evaluate approach and document findings",
    done_definitions=[
        "Approach evaluated",
        "Pros/cons documented",
        "Recommendation made",
        "Phase 3 review task created"
    ],
    phase_prompt="""
    YOU ARE AN EVALUATION SPECIALIST
    
    STEP 1: Understand the approach
    STEP 2: Evaluate pros and cons
    STEP 3: Compare with alternatives
    STEP 4: Document findings
    STEP 5: Create Phase 3 review task
    
    If evaluation reveals new research needs:
    - Spawn Phase 1 research tasks
    - Continue your evaluation
    """
)
```

---

## Migration Path

### Phase 1: Enable Discovery-Based Free Spawning

**Change**: Update `DiscoveryService` to bypass `allowed_transitions`

**Impact**: Low risk, backward compatible

**Steps**:
1. Update `record_discovery_and_branch()` to skip transition checks
2. Add logging for discovery-based spawning
3. Update phase prompts to guide agents

### Phase 2: Add Phase Configuration

**Change**: Add `allow_free_spawning` flag to phases

**Impact**: Medium risk, requires migration

**Steps**:
1. Add column to `phases` table
2. Update PhaseModel
3. Configure phases appropriately
4. Update UI to show free-spawning phases

### Phase 3: Enhance UI

**Change**: Add Phasor-specific views

**Impact**: Low risk, new features

**Steps**:
1. Build Phase Overview dashboard
2. Enhance workflow graph with discovery edges
3. Add discovery timeline view
4. Add diagnostic reasoning integration

---

## Best Practices

### 1. Write Clear Phase Prompts

**Bad**:
```
"Build the component"
```

**Good**:
```
"YOU ARE A SOFTWARE ENGINEER IN PHASE 2 (IMPLEMENTATION)

STEP 1: Understand component requirements from ticket
STEP 2: Design component interface
STEP 3: Implement core logic
STEP 4: Write tests (minimum 3 cases)
STEP 5: Verify tests pass
STEP 6: Create Phase 3 validation task
STEP 7: Mark task as done

If you discover bugs, optimizations, or missing requirements:
- Use DiscoveryService to spawn appropriate phase tasks
- Continue your implementation work (don't stop!)
"
```

### 2. Define Concrete Done Definitions

**Bad**:
```
done_definitions=["Finish the feature"]
```

**Good**:
```
done_definitions=[
    "Component code files created in src/",
    "Minimum 3 test cases written",
    "Tests passing locally",
    "Phase 3 validation task created",
    "update_task_status called with status='done'"
]
```

### 3. Guide Discovery Spawning

**In Phase Prompts**:
```
"If you discover:
- Bugs → Spawn Phase 2 fix tasks
- Optimizations → Spawn Phase 1 investigation → Phase 2 implementation
- Missing Requirements → Spawn Phase 1 clarification tasks
- Security Issues → Spawn Phase 1 analysis → Phase 2 fixes"
```

### 4. Monitor Branching

**Track**:
- Discovery rate per phase
- Branching depth
- Parallel work streams
- Discovery-to-completion time

**Alerts**:
- Too many branches (might indicate unclear requirements)
- Deep nesting (might indicate complex dependencies)
- Stalled branches (might need intervention)

---

## Related Documents

- [Hephaestus Workflow Enhancements](../implementation/workflows/hephaestus_workflow_enhancements.md) - Discovery tracking implementation
- [Phase Model](../../omoi_os/models/phase.py) - Current phase model
- [Discovery Service](../../omoi_os/services/discovery.py) - Discovery tracking service
- [Diagnostic Reasoning View](../frontend/diagnostic_reasoning_view.md) - Understanding WHY workflows branch

---

## Summary

**Phasor System** enables adaptive, self-building workflows where:

1. **Phases are job descriptions** - Define types of work, not rigid steps
2. **Agents spawn freely** - Can spawn tasks in any phase from any phase
3. **Workflows adapt** - Structure emerges from discoveries
4. **Parallel exploration** - Multiple branches work simultaneously

**When to Use**:
- Complex systems with unknown dependencies
- Discovery-heavy work (analysis, research)
- Parallel development needs
- Uncertain requirements

**Why It Matters**:
- Workflows adapt to reality instead of breaking
- Agents stay focused on their expertise
- Parallel exploration speeds up work
- Knowledge discovery happens automatically

**Implementation**:
- Enable discovery-based free spawning in `DiscoveryService`
- Add phase configuration for granular control
- Enhance UI with phase overview and discovery visualization
- Guide agents via phase prompts

This transforms OmoiOS from "structured workflow execution" to "adaptive workflow discovery" - workflows that build themselves as agents find what needs to be done.

