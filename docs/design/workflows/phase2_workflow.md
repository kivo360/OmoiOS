# Phase 2 Agent Assignments - Multi-Phase Workflow

**Created**: 2025-11-20
**Purpose**: Design specification for Phase 2 multi-phase workflow, including state machine, task generation, database schema, and API endpoints.
**Related**: docs/design/workflows/phase1_workflow.md, docs/requirements/workflows/phase2_requirements.md, docs/implementation/workflows/phase2_implementation.md, docs/architecture/decision_records/adr_phase_workflow.md

---


**Status**: Ready for Planning  
**Timeline**: Weeks 3-4  
**Goal**: Implement complete workflow with phase transitions

---

## Overview

Phase 2 introduces multi-phase workflow capabilities:
- **Phase Definitions**: Standardized phase constants and state machine
- **Task Generation**: Phase-specific task templates and decomposition
- **Phase Gates**: Validation and artifact checking before phase transitions
- **Context Passing**: Cross-phase context aggregation and summarization

---

## 🎯 Stream E: Phase Definitions & State Machine (Week 3)

**Agent Assignment**: Agent E  
**Priority**: CRITICAL (blocks other streams)  
**Can Start**: ✅ Immediately (no dependencies)

### Files to Create/Modify

**New Files**:
- `omoi_os/models/phases.py` - Phase constants and enums
- `omoi_os/services/phase_service.py` - Phase state machine logic
- `omoi_os/models/phase_history.py` - Phase transition history model
- `tests/test_phase_state_machine.py` - State machine tests

**Modified Files**:
- `omoi_os/models/ticket.py` - Add phase transition tracking
- `omoi_os/api/routes/tickets.py` - Add phase transition endpoint
- `migrations/versions/003_phase_workflow.py` - Database migration

### Database Changes

**New Table: `phase_history`**
```sql
CREATE TABLE phase_history (
    id UUID PRIMARY KEY,
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
    from_phase VARCHAR(50),
    to_phase VARCHAR(50),
    transition_reason TEXT,
    transitioned_by VARCHAR(255),  -- agent_id or system
    artifacts JSONB,  -- Artifacts at transition time
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_phase_history_ticket ON phase_history(ticket_id);
CREATE INDEX idx_phase_history_created ON phase_history(created_at);
```

**Ticket Model Changes**:
- Add `previous_phase_id` field (optional, for rollback tracking)
- No other changes needed (phase_id already exists)

### Phase Constants

```python
# omoi_os/models/phases.py
from enum import Enum

class Phase(str, Enum):
    """Workflow phases for ticket lifecycle."""
    BACKLOG = "PHASE_BACKLOG"
    REQUIREMENTS = "PHASE_REQUIREMENTS"
    DESIGN = "PHASE_DESIGN"
    IMPLEMENTATION = "PHASE_IMPLEMENTATION"
    TESTING = "PHASE_TESTING"
    DEPLOYMENT = "PHASE_DEPLOYMENT"
    DONE = "PHASE_DONE"
    BLOCKED = "PHASE_BLOCKED"

# Valid phase transitions
PHASE_TRANSITIONS = {
    Phase.BACKLOG: [Phase.REQUIREMENTS],
    Phase.REQUIREMENTS: [Phase.DESIGN, Phase.BLOCKED],
    Phase.DESIGN: [Phase.IMPLEMENTATION, Phase.BLOCKED],
    Phase.IMPLEMENTATION: [Phase.TESTING, Phase.BLOCKED],
    Phase.TESTING: [Phase.DEPLOYMENT, Phase.IMPLEMENTATION, Phase.BLOCKED],  # Can regress
    Phase.DEPLOYMENT: [Phase.DONE, Phase.BLOCKED],
    Phase.BLOCKED: [Phase.REQUIREMENTS, Phase.DESIGN, Phase.IMPLEMENTATION, Phase.TESTING],  # Can unblock to any
    Phase.DONE: [],  # Terminal state
}
```

### Key Methods to Implement

```python
# PhaseService
class PhaseService:
    def can_transition(self, from_phase: str, to_phase: str) -> bool:
        """Check if phase transition is valid"""
        
    def transition_ticket(self, ticket_id: str, to_phase: str, reason: str, transitioned_by: str) -> bool:
        """Transition ticket to new phase, record history"""
        
    def get_phase_history(self, ticket_id: str) -> list[PhaseHistory]:
        """Get phase transition history for ticket"""
        
    def get_valid_transitions(self, current_phase: str) -> list[str]:
        """Get list of valid next phases"""
```

### API Endpoints

```python
# POST /api/v1/tickets/{ticket_id}/transition
# Body: {"to_phase": "PHASE_IMPLEMENTATION", "reason": "Requirements complete"}
# Returns: Updated ticket with new phase

# GET /api/v1/tickets/{ticket_id}/phase-history
# Returns: List of phase transitions with timestamps
```

### Success Criteria

- ✅ Phase constants defined and used throughout codebase
- ✅ State machine enforces valid transitions only
- ✅ Invalid transitions rejected with clear error messages
- ✅ Phase history tracked for all transitions
- ✅ API endpoints functional
- ✅ All tests pass

---

## 🔧 Stream F: Phase-Specific Task Generation (Week 3)

**Agent Assignment**: Agent F  
**Priority**: HIGH  
**Can Start**: ⚠️ After Stream E defines phase constants (can start in parallel once constants exist)

### Files to Create/Modify

**New Files**:
- `omoi_os/services/task_generator.py` - Task generation service
- `omoi_os/services/task_templates.py` - Phase-specific task templates
- `omoi_os/models/task_template.py` - Task template model (optional, for configurable templates)
- `tests/test_task_generation.py` - Task generation tests

**Modified Files**:
- `omoi_os/api/routes/tickets.py` - Add task generation endpoint
- `omoi_os/services/task_queue.py` - Integration with task generator

### Database Changes

**Optional: `task_templates` table** (for configurable templates)
```sql
CREATE TABLE task_templates (
    id UUID PRIMARY KEY,
    phase_id VARCHAR(50) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    template_description TEXT NOT NULL,
    default_priority VARCHAR(20) DEFAULT 'MEDIUM',
    required_capabilities JSONB,  -- ["analysis", "implementation"]
    dependencies_template JSONB,  -- Template for dependencies
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_task_templates_phase ON task_templates(phase_id);
```

### Task Templates by Phase

```python
# omoi_os/services/task_templates.py
PHASE_TASK_TEMPLATES = {
    Phase.REQUIREMENTS: [
        {
            "task_type": "analyze_requirements",
            "description_template": "Analyze and clarify requirements for: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["analysis"],
        },
        {
            "task_type": "create_requirements_doc",
            "description_template": "Create requirements document for: {ticket_title}",
            "priority": "MEDIUM",
            "capabilities": ["documentation"],
        },
    ],
    Phase.DESIGN: [
        {
            "task_type": "design_architecture",
            "description_template": "Design architecture for: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["design"],
        },
    ],
    Phase.IMPLEMENTATION: [
        {
            "task_type": "implement_feature",
            "description_template": "Implement feature: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["implementation"],
        },
    ],
    Phase.TESTING: [
        {
            "task_type": "write_tests",
            "description_template": "Write tests for: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["testing"],
        },
        {
            "task_type": "run_tests",
            "description_template": "Run test suite for: {ticket_title}",
            "priority": "MEDIUM",
            "capabilities": ["testing"],
        },
    ],
    Phase.DEPLOYMENT: [
        {
            "task_type": "deploy_feature",
            "description_template": "Deploy feature: {ticket_title}",
            "priority": "CRITICAL",
            "capabilities": ["deployment"],
        },
    ],
}
```

### Key Methods to Implement

```python
# TaskGeneratorService
class TaskGeneratorService:
    def generate_phase_tasks(self, ticket_id: str, phase_id: str) -> list[Task]:
        """Generate all tasks for a phase based on templates"""
        
    def generate_task_from_template(self, ticket: Ticket, template: dict) -> Task:
        """Generate single task from template"""
        
    def get_templates_for_phase(self, phase_id: str) -> list[dict]:
        """Get task templates for a phase"""
```

### API Endpoints

```python
# POST /api/v1/tickets/{ticket_id}/generate-tasks
# Body: {"phase_id": "PHASE_IMPLEMENTATION"} (optional, defaults to ticket's current phase)
# Returns: List of generated tasks

# GET /api/v1/task-templates?phase_id=PHASE_IMPLEMENTATION
# Returns: Available task templates for phase
```

### Success Criteria

- ✅ Tasks generated automatically when ticket enters phase
- ✅ Task templates configurable per phase
- ✅ Generated tasks linked to correct phase
- ✅ Templates support variable substitution (ticket title, description)
- ✅ API endpoints functional
- ✅ All tests pass

---

## 🚪 Stream G: Phase Gates & Validation (Week 4)

**Agent Assignment**: Agent G  
**Priority**: HIGH  
**Can Start**: ⚠️ After Stream E defines phase definitions (can start in parallel with Stream F)

### Files to Create/Modify

**New Files**:
- `omoi_os/services/phase_gate.py` - Phase gate validation service
- `omoi_os/services/validation_agent.py` - Validation agent (separate from worker)
- `omoi_os/models/phase_gate_artifact.py` - Artifact tracking model
- `omoi_os/models/phase_gate_result.py` - Gate validation result model
- `tests/test_phase_gates.py` - Phase gate tests

**Modified Files**:
- `omoi_os/api/routes/phases.py` - New routes file for phase operations
- `omoi_os/services/phase_service.py` - Integration with gate validation

### Database Changes

**New Table: `phase_gate_artifacts`**
```sql
CREATE TABLE phase_gate_artifacts (
    id UUID PRIMARY KEY,
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
    phase_id VARCHAR(50) NOT NULL,
    artifact_type VARCHAR(100) NOT NULL,  -- requirements_doc, test_results, etc.
    artifact_path TEXT,  -- File path or reference
    artifact_content JSONB,  -- Structured content
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    collected_by VARCHAR(255)  -- agent_id
);
CREATE INDEX idx_gate_artifacts_ticket_phase ON phase_gate_artifacts(ticket_id, phase_id);
```

**New Table: `phase_gate_results`**
```sql
CREATE TABLE phase_gate_results (
    id UUID PRIMARY KEY,
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
    phase_id VARCHAR(50) NOT NULL,
    gate_status VARCHAR(50) NOT NULL,  -- passed, failed, pending
    validation_result JSONB,  -- Detailed validation results
    validated_at TIMESTAMP WITH TIME ZONE,
    validated_by VARCHAR(255),  -- validation_agent_id
    blocking_reasons TEXT[]  -- Reasons gate failed
);
CREATE INDEX idx_gate_results_ticket_phase ON phase_gate_results(ticket_id, phase_id);
```

### Phase Gate Requirements

```python
# omoi_os/services/phase_gate.py
PHASE_GATE_REQUIREMENTS = {
    Phase.REQUIREMENTS: {
        "required_artifacts": ["requirements_document"],
        "required_tasks_completed": True,  # All phase tasks must be done
        "validation_criteria": {
            "requirements_document": {
                "min_length": 500,
                "required_sections": ["scope", "acceptance_criteria"],
            }
        }
    },
    Phase.IMPLEMENTATION: {
        "required_artifacts": ["code_changes", "test_coverage"],
        "required_tasks_completed": True,
        "validation_criteria": {
            "test_coverage": {"min_percentage": 80},
            "code_changes": {"must_have_tests": True},
        }
    },
    Phase.TESTING: {
        "required_artifacts": ["test_results", "test_evidence"],
        "required_tasks_completed": True,
        "validation_criteria": {
            "test_results": {"all_passed": True},
        }
    },
}
```

### Key Methods to Implement

```python
# PhaseGateService
class PhaseGateService:
    def check_gate_requirements(self, ticket_id: str, phase_id: str) -> dict:
        """Check if gate requirements are met"""
        
    def validate_gate(self, ticket_id: str, phase_id: str) -> PhaseGateResult:
        """Run full gate validation"""
        
    def collect_artifacts(self, ticket_id: str, phase_id: str) -> list[PhaseGateArtifact]:
        """Collect artifacts from completed tasks"""
        
    def can_transition(self, ticket_id: str, to_phase: str) -> tuple[bool, list[str]]:
        """Check if ticket can transition (returns can_transition, blocking_reasons)"""

# ValidationAgent (separate from worker)
class ValidationAgent:
    def validate_phase_completion(self, ticket_id: str, phase_id: str) -> dict:
        """Use OpenHands agent to validate phase completion"""
```

### API Endpoints

```python
# POST /api/v1/tickets/{ticket_id}/validate-gate
# Body: {"phase_id": "PHASE_IMPLEMENTATION"}
# Returns: Gate validation result

# GET /api/v1/tickets/{ticket_id}/gate-status
# Returns: Current gate status and requirements

# POST /api/v1/tickets/{ticket_id}/artifacts
# Body: {"artifact_type": "requirements_doc", "artifact_path": "...", "content": {...}}
# Returns: Created artifact
```

### Success Criteria

- ✅ Phase gates check required artifacts
- ✅ Validation agent reviews phase completion
- ✅ Gates can block or allow transitions
- ✅ Artifacts collected and stored
- ✅ Validation results persisted
- ✅ All tests pass

---

## 📚 Stream H: Cross-Phase Context Passing (Week 4)

**Agent Assignment**: Agent H  
**Priority**: HIGH  
**Can Start**: ⚠️ After Stream E defines phase definitions (can start in parallel with Streams F and G)

### Files to Create/Modify

**New Files**:
- `omoi_os/services/context_service.py` - Context aggregation service
- `omoi_os/services/context_summarizer.py` - Context summarization logic
- `tests/test_context_passing.py` - Context passing tests

**Modified Files**:
- `omoi_os/models/ticket.py` - Add context storage fields
- `migrations/versions/003_phase_workflow.py` - Add context fields

### Database Changes

**Ticket Model Changes**:
```sql
ALTER TABLE tickets ADD COLUMN context JSONB;  -- Aggregated context from all phases
ALTER TABLE tickets ADD COLUMN context_summary TEXT;  -- Summarized context for next phase
```

**New Table: `phase_context`** (optional, for detailed phase context)
```sql
CREATE TABLE phase_context (
    id UUID PRIMARY KEY,
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
    phase_id VARCHAR(50) NOT NULL,
    context_data JSONB NOT NULL,  -- Full context from phase
    context_summary TEXT,  -- Summarized version
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_phase_context_ticket ON phase_context(ticket_id);
```

### Context Structure

```python
# Context format
{
    "requirements_phase": {
        "requirements_doc": "...",
        "key_decisions": ["decision1", "decision2"],
        "scope_clarifications": ["clarification1"],
    },
    "design_phase": {
        "architecture_doc": "...",
        "design_decisions": ["decision1"],
    },
    "implementation_phase": {
        "code_changes_summary": "...",
        "key_implementations": ["feature1", "feature2"],
    },
    "summary": "Summarized context for next phase (token-optimized)",
}
```

### Key Methods to Implement

```python
# ContextService
class ContextService:
    def aggregate_phase_context(self, ticket_id: str, phase_id: str) -> dict:
        """Aggregate context from completed phase tasks"""
        
    def summarize_context(self, context: dict, max_tokens: int = 2000) -> str:
        """Summarize context to reduce token usage"""
        
    def get_context_for_phase(self, ticket_id: str, target_phase: str) -> dict:
        """Get aggregated context from all previous phases"""
        
    def update_ticket_context(self, ticket_id: str, phase_id: str) -> None:
        """Update ticket's context with new phase data"""
```

### Context Summarization Strategy

```python
# ContextSummarizer
class ContextSummarizer:
    def summarize_using_llm(self, context: dict) -> str:
        """Use LLM to summarize context (if needed)"""
        
    def summarize_structured(self, context: dict) -> str:
        """Summarize structured context (key decisions, artifacts)"""
        
    def extract_key_points(self, context: dict) -> list[str]:
        """Extract key points from context"""
```

### API Endpoints

```python
# GET /api/v1/tickets/{ticket_id}/context
# Returns: Full aggregated context

# GET /api/v1/tickets/{ticket_id}/context-summary
# Returns: Summarized context for next phase

# POST /api/v1/tickets/{ticket_id}/update-context
# Body: {"phase_id": "PHASE_IMPLEMENTATION"}
# Updates context from phase completion
```

### Success Criteria

- ✅ Context from previous phases available
- ✅ Context summarized to reduce token usage
- ✅ Context passed to next phase tasks
- ✅ Context stored in ticket model
- ✅ Summarization preserves key information
- ✅ All tests pass

---

## Coordination Points

### Week 3 Coordination

**Stream E (Phase Definitions) - CRITICAL PATH**:
- Must complete phase constants first (Day 1-2)
- Other streams can start once constants are defined

**Stream F (Task Generation)**:
- Can start Day 2-3 (after E defines constants)
- Uses phase constants from Stream E

### Week 4 Coordination

**Stream G (Phase Gates)**:
- Can start Week 4 Day 1 (after E completes)
- Uses phase definitions from Stream E
- Can work in parallel with Stream F

**Stream H (Context Passing)**:
- Can start Week 4 Day 1 (after E completes)
- Can work in parallel with Streams F and G
- Uses phase definitions from Stream E

### Database Migration Coordination

**Migration File**: `003_phase_workflow.py`
- Stream E creates migration file
- Stream E adds: `phase_history` table
- Stream G adds: `phase_gate_artifacts`, `phase_gate_results` tables
- Stream H adds: `context` and `context_summary` fields to `tickets` table
- Stream H optionally adds: `phase_context` table

**Coordination Method**:
1. Stream E creates migration file
2. Streams G and H add their schema changes
3. Final review before applying

### Model Changes Coordination

**Ticket Model** (`omoi_os/models/ticket.py`):
- Stream E: Adds `previous_phase_id` field
- Stream H: Adds `context` and `context_summary` fields

**Coordination**: Sequential merges or feature branches

---

## Dependencies & Parallelization

| Stream | Can Start | Blocks | Parallel With |
|--------|-----------|--------|---------------|
| E: Phase Definitions | ✅ Week 3 Day 1 | None | - |
| F: Task Generation | ⚠️ Week 3 Day 2-3 | E (constants) | G, H (after E) |
| G: Phase Gates | ⚠️ Week 4 Day 1 | E (definitions) | F, H |
| H: Context Passing | ⚠️ Week 4 Day 1 | E (definitions) | F, G |

### Critical Path

```
Week 3:
Day 1-2: Stream E (Phase Definitions) - CRITICAL
Day 2-3: Stream F (Task Generation) - Can start after E Day 1

Week 4:
Day 1-5: Streams G and H can work in parallel
```

---

## Success Metrics

### Code Quality
- Test coverage: >80% for new code
- All tests pass: 33+ existing + new Phase 2 tests
- No linter errors

### Functionality
- ✅ Tickets can transition between all defined phases
- ✅ Invalid transitions rejected
- ✅ Tasks generated automatically per phase
- ✅ Phase gates validate before transitions
- ✅ Context passed between phases
- ✅ Phase history tracked

---

## Next Steps

1. **Assign Agents**: Assign Agents E, F, G, H to Phase 2 streams
2. **Stream E Starts**: Begin phase definitions (critical path)
3. **Streams F, G, H Wait**: Until Stream E defines phase constants
4. **Daily Sync**: Coordinate migration file and model changes
5. **Week 3 Review**: Ensure phase definitions complete before Week 4

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Assistant | Initial Phase 2 planning document |

