# Phase 2: Multi-Phase Workflow - Detailed Specification

**Document Purpose**: Detailed technical specification for Phase 2 implementation, including data models, service interfaces, and API contracts.

**Created**: 2025-11-16  
**Status**: Planning  
**Related Documents**:
- [Agent Assignments Phase 2](./agent_assignments_phase2.md)
- [Implementation Roadmap](./implementation_roadmap.md)
- [Ticket Workflow Design](./design/ticket_workflow.md)

---

## Phase Definitions

### Phase Enum

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

# Phase sequence (normal flow)
PHASE_SEQUENCE = [
    Phase.BACKLOG,
    Phase.REQUIREMENTS,
    Phase.DESIGN,
    Phase.IMPLEMENTATION,
    Phase.TESTING,
    Phase.DEPLOYMENT,
    Phase.DONE,
]

# Valid phase transitions
PHASE_TRANSITIONS: dict[Phase, list[Phase]] = {
    Phase.BACKLOG: [Phase.REQUIREMENTS],
    Phase.REQUIREMENTS: [Phase.DESIGN, Phase.BLOCKED],
    Phase.DESIGN: [Phase.IMPLEMENTATION, Phase.BLOCKED],
    Phase.IMPLEMENTATION: [Phase.TESTING, Phase.BLOCKED],
    Phase.TESTING: [Phase.DEPLOYMENT, Phase.IMPLEMENTATION, Phase.BLOCKED],  # Can regress
    Phase.DEPLOYMENT: [Phase.DONE, Phase.BLOCKED],
    Phase.BLOCKED: [Phase.REQUIREMENTS, Phase.DESIGN, Phase.IMPLEMENTATION, Phase.TESTING],  # Can unblock
    Phase.DONE: [],  # Terminal state
}
```

---

## Database Schema

### Phase History Table

```python
# omoi_os/models/phase_history.py
class PhaseHistory(Base):
    """Tracks phase transitions for tickets."""
    
    __tablename__ = "phase_history"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_phase: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_phase: Mapped[str] = mapped_column(String(50), nullable=False)
    transition_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transitioned_by: Mapped[str] = mapped_column(String(255), nullable=False)  # agent_id or "system"
    artifacts: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Artifacts at transition
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
```

### Phase Gate Artifacts Table

```python
# omoi_os/models/phase_gate_artifact.py
class PhaseGateArtifact(Base):
    """Artifacts collected for phase gate validation."""
    
    __tablename__ = "phase_gate_artifacts"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)  # requirements_doc, test_results, etc.
    artifact_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # File path or reference
    artifact_content: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Structured content
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    collected_by: Mapped[str] = mapped_column(String(255), nullable=False)  # agent_id
```

### Phase Gate Results Table

```python
# omoi_os/models/phase_gate_result.py
class PhaseGateResult(Base):
    """Results of phase gate validation."""
    
    __tablename__ = "phase_gate_results"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    gate_status: Mapped[str] = mapped_column(String(50), nullable=False)  # passed, failed, pending
    validation_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Detailed results
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # validation_agent_id
    blocking_reasons: Mapped[Optional[list[str]]] = mapped_column(
        postgresql.ARRAY(Text), nullable=True
    )  # Reasons gate failed
```

### Ticket Model Updates

```python
# omoi_os/models/ticket.py - Additions
previous_phase_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # For rollback tracking
context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Aggregated context
context_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Summarized context
```

---

## Service Interfaces

### PhaseService Interface

```python
# omoi_os/services/phase_service.py
class PhaseService:
    """Manages phase transitions and state machine."""
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
    def can_transition(self, from_phase: str, to_phase: str) -> bool:
        """
        Check if phase transition is valid.
        
        Args:
            from_phase: Current phase
            to_phase: Target phase
            
        Returns:
            True if transition is valid
        """
        
    def transition_ticket(
        self,
        ticket_id: str,
        to_phase: str,
        reason: str,
        transitioned_by: str,
        artifacts: dict | None = None,
    ) -> bool:
        """
        Transition ticket to new phase.
        
        Args:
            ticket_id: Ticket ID
            to_phase: Target phase
            reason: Reason for transition
            transitioned_by: Agent ID or "system"
            artifacts: Optional artifacts at transition time
            
        Returns:
            True if transition successful
        """
        
    def get_phase_history(self, ticket_id: str) -> list[PhaseHistory]:
        """Get phase transition history for ticket."""
        
    def get_valid_transitions(self, current_phase: str) -> list[str]:
        """Get list of valid next phases."""
        
    def get_current_phase(self, ticket_id: str) -> str | None:
        """Get current phase of ticket."""
```

### TaskGeneratorService Interface

```python
# omoi_os/services/task_generator.py
class TaskGeneratorService:
    """Generates phase-specific tasks from templates."""
    
    def __init__(self, db: DatabaseService, queue: TaskQueueService):
        self.db = db
        self.queue = queue
    
    def generate_phase_tasks(self, ticket_id: str, phase_id: str) -> list[Task]:
        """
        Generate all tasks for a phase based on templates.
        
        Args:
            ticket_id: Ticket ID
            phase_id: Phase to generate tasks for
            
        Returns:
            List of generated Task objects
        """
        
    def generate_task_from_template(
        self,
        ticket: Ticket,
        template: dict,
        dependencies: list[str] | None = None,
    ) -> Task:
        """
        Generate single task from template.
        
        Args:
            ticket: Ticket object
            template: Task template dict
            dependencies: Optional list of task IDs this depends on
            
        Returns:
            Created Task object
        """
        
    def get_templates_for_phase(self, phase_id: str) -> list[dict]:
        """Get task templates for a phase."""
```

### PhaseGateService Interface

```python
# omoi_os/services/phase_gate.py
class PhaseGateService:
    """Validates phase gates before transitions."""
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
    def check_gate_requirements(self, ticket_id: str, phase_id: str) -> dict:
        """
        Check if gate requirements are met.
        
        Returns:
            {
                "requirements_met": bool,
                "missing_artifacts": list[str],
                "validation_status": str,
            }
        """
        
    def validate_gate(self, ticket_id: str, phase_id: str) -> PhaseGateResult:
        """
        Run full gate validation.
        
        Returns:
            PhaseGateResult object
        """
        
    def collect_artifacts(self, ticket_id: str, phase_id: str) -> list[PhaseGateArtifact]:
        """Collect artifacts from completed tasks."""
        
    def can_transition(self, ticket_id: str, to_phase: str) -> tuple[bool, list[str]]:
        """
        Check if ticket can transition.
        
        Returns:
            (can_transition: bool, blocking_reasons: list[str])
        """
```

### ContextService Interface

```python
# omoi_os/services/context_service.py
class ContextService:
    """Manages cross-phase context aggregation and summarization."""
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
    def aggregate_phase_context(self, ticket_id: str, phase_id: str) -> dict:
        """
        Aggregate context from completed phase tasks.
        
        Returns:
            Context dict with phase-specific data
        """
        
    def summarize_context(self, context: dict, max_tokens: int = 2000) -> str:
        """
        Summarize context to reduce token usage.
        
        Args:
            context: Full context dict
            max_tokens: Maximum tokens for summary
            
        Returns:
            Summarized context string
        """
        
    def get_context_for_phase(self, ticket_id: str, target_phase: str) -> dict:
        """
        Get aggregated context from all previous phases.
        
        Returns:
            Context dict with all previous phase data
        """
        
    def update_ticket_context(self, ticket_id: str, phase_id: str) -> None:
        """Update ticket's context with new phase data."""
```

---

## API Contracts

### Phase Transition Endpoint

```python
# POST /api/v1/tickets/{ticket_id}/transition
# Request Body:
{
    "to_phase": "PHASE_IMPLEMENTATION",
    "reason": "Requirements phase complete, all artifacts validated"
}

# Response:
{
    "ticket_id": "uuid",
    "previous_phase": "PHASE_REQUIREMENTS",
    "current_phase": "PHASE_IMPLEMENTATION",
    "transitioned_at": "2025-11-16T10:00:00Z",
    "transitioned_by": "agent_id_or_system"
}
```

### Task Generation Endpoint

```python
# POST /api/v1/tickets/{ticket_id}/generate-tasks
# Request Body (optional):
{
    "phase_id": "PHASE_IMPLEMENTATION"  # Defaults to ticket's current phase
}

# Response:
{
    "ticket_id": "uuid",
    "phase_id": "PHASE_IMPLEMENTATION",
    "generated_tasks": [
        {
            "id": "task_uuid",
            "task_type": "implement_feature",
            "description": "Implement feature: Ticket Title",
            "priority": "HIGH",
            "dependencies": []
        }
    ]
}
```

### Phase Gate Validation Endpoint

```python
# POST /api/v1/tickets/{ticket_id}/validate-gate
# Request Body:
{
    "phase_id": "PHASE_IMPLEMENTATION"
}

# Response:
{
    "ticket_id": "uuid",
    "phase_id": "PHASE_IMPLEMENTATION",
    "gate_status": "passed",  # or "failed", "pending"
    "requirements_met": true,
    "missing_artifacts": [],
    "blocking_reasons": [],
    "validation_result": {
        "artifacts_checked": 3,
        "artifacts_passed": 3,
        "tasks_completed": true
    }
}
```

### Context Endpoint

```python
# GET /api/v1/tickets/{ticket_id}/context
# Response:
{
    "ticket_id": "uuid",
    "full_context": {
        "requirements_phase": {...},
        "design_phase": {...},
        "implementation_phase": {...}
    },
    "summary": "Summarized context for next phase...",
    "last_updated": "2025-11-16T10:00:00Z"
}
```

---

## Implementation Order

### Week 3: Foundation

**Day 1-2: Stream E (Phase Definitions)**
1. Create phase constants enum
2. Implement state machine logic
3. Create phase history model
4. Add phase transition endpoint
5. Write tests

**Day 2-3: Stream F (Task Generation)**
1. Create task templates
2. Implement task generator service
3. Add task generation endpoint
4. Integrate with ticket creation
5. Write tests

### Week 4: Validation & Context

**Day 1-3: Stream G (Phase Gates)**
1. Create gate artifact models
2. Implement gate validation service
3. Create validation agent
4. Add gate validation endpoints
5. Write tests

**Day 1-3: Stream H (Context Passing)**
1. Add context fields to ticket model
2. Implement context service
3. Implement context summarization
4. Add context endpoints
5. Write tests

**Day 4-5: Integration**
1. End-to-end testing
2. Integration with Phase 1 features
3. Performance testing
4. Documentation

---

## Testing Strategy

### Unit Tests
- Phase state machine transitions
- Task template generation
- Gate validation logic
- Context aggregation and summarization

### Integration Tests
- Ticket phase transition flow
- Task generation on phase entry
- Gate validation before transition
- Context passing between phases

### End-to-End Tests
- Complete workflow: ticket creation → phase transitions → completion
- Regression flow: testing → implementation (fix) → testing
- Blocked ticket flow: block → unblock → continue

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Assistant | Initial Phase 2 detailed specification |

