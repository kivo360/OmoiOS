# Claude Code Agent Prompt: Phase 2 Streams F, G, H

**Purpose**: This document provides comprehensive instructions for Claude Code agents to implement Phase 2 Streams F, G, and H in parallel.

**Methodology**: Test-Driven Development (TDD) - Write tests FIRST, then implement  
**Language**: Python 3.12+  
**Framework**: FastAPI, SQLAlchemy 2.0+, Pytest

---

## 🎯 Agent Assignment Instructions

You are a Python developer implementing **Phase 2** of the OmoiOS multi-agent orchestration system. You will be assigned to ONE of the following streams:

- **Stream F**: Phase-Specific Task Generation
- **Stream G**: Phase Gates & Validation  
- **Stream H**: Cross-Phase Context Passing

**CRITICAL**: Follow Test-Driven Development (TDD) methodology:
1. ✅ Write tests FIRST (they will fail - this is expected)
2. ✅ Run tests to confirm they fail
3. ✅ Implement minimal code to make tests pass
4. ✅ Refactor if needed
5. ✅ Repeat for each feature

---

## 📋 Project Context

**Codebase**: Multi-agent orchestration system using OpenHands SDK  
**Current State**: 
- Phase 1 complete (task dependencies, retries, health monitoring, timeouts)
- Stream E complete (phase definitions, state machine, phase history)

**Key Technologies**:
- Python 3.12+ with type hints
- FastAPI for REST API
- SQLAlchemy 2.0+ (using `Mapped` annotations)
- PostgreSQL with psycopg3 (`postgresql+psycopg://`)
- Pytest for testing
- `whenever` library for datetime (use `utc_now()` not `datetime.utcnow()`)
- UV package manager

**Project Structure**:
```
omoi_os/
├── models/          # SQLAlchemy models
├── services/        # Business logic services
├── api/
│   └── routes/     # FastAPI route handlers
├── utils/          # Utility functions
tests/               # Pytest test files
migrations/versions/ # Alembic migrations
```

**Existing Patterns to Follow**:
- Services use `DatabaseService` with `get_session()` context manager
- Models use `Base` from `omoi_os.models.base`
- Use `utc_now()` from `omoi_os.utils.datetime`
- Always `session.expunge()` objects before returning from services
- API routes use `Depends(get_db_service)` for dependency injection

---

## 🔧 STREAM F: Phase-Specific Task Generation

### Your Assignment

Implement automatic task generation when tickets enter phases. Tasks should be generated from phase-specific templates.

### Files to Create

1. **`omoi_os/services/task_generator.py`** - Task generation service
2. **`omoi_os/services/task_templates.py`** - Phase-specific task templates
3. **`tests/test_task_generation.py`** - Comprehensive tests

### Files to Modify

1. **`omoi_os/api/routes/tickets.py`** - Add task generation endpoint
2. **`migrations/versions/003_phase_workflow.py`** - Add task_templates table (optional)

### Database Changes (Optional)

If implementing configurable templates:

```sql
CREATE TABLE task_templates (
    id UUID PRIMARY KEY,
    phase_id VARCHAR(50) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    template_description TEXT NOT NULL,
    default_priority VARCHAR(20) DEFAULT 'MEDIUM',
    required_capabilities JSONB,
    dependencies_template JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_task_templates_phase ON task_templates(phase_id);
```

### Phase Task Templates

**Required Templates** (implement in `task_templates.py`):

```python
# omoi_os/services/task_templates.py
from omoi_os.models.phases import Phase

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

### Service Interface to Implement

```python
# omoi_os/services/task_generator.py
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService

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
        # Implementation:
        # 1. Get ticket from database
        # 2. Get templates for phase_id
        # 3. For each template, call generate_task_from_template()
        # 4. Return list of created tasks
        
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
        # Implementation:
        # 1. Format description_template with ticket.title
        # 2. Call queue.enqueue_task() with template values
        # 3. Return created Task
        
    def get_templates_for_phase(self, phase_id: str) -> list[dict]:
        """Get task templates for a phase."""
        # Return templates from PHASE_TASK_TEMPLATES
```

### Tests to Write FIRST

```python
# tests/test_task_generation.py
import pytest
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.models.phases import Phase
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.task_generator import TaskGeneratorService

def test_get_templates_for_phase():
    """Test getting templates for a phase."""
    generator = TaskGeneratorService(None, None)  # Will need proper setup
    templates = generator.get_templates_for_phase(Phase.REQUIREMENTS)
    assert len(templates) > 0
    assert all("task_type" in t for t in templates)

def test_generate_task_from_template(db_service: DatabaseService, task_queue_service: TaskQueueService):
    """Test generating a single task from template."""
    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Feature",
            description="Test",
            phase_id=Phase.REQUIREMENTS,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
    
    # Generate task
    generator = TaskGeneratorService(db_service, task_queue_service)
    template = {
        "task_type": "analyze_requirements",
        "description_template": "Analyze: {ticket_title}",
        "priority": "HIGH",
    }
    task = generator.generate_task_from_template(ticket, template)
    
    assert task is not None
    assert task.ticket_id == ticket.id
    assert "Test Feature" in task.description
    assert task.priority == "HIGH"

def test_generate_phase_tasks(db_service: DatabaseService, task_queue_service: TaskQueueService):
    """Test generating all tasks for a phase."""
    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Feature",
            phase_id=Phase.REQUIREMENTS,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        ticket_id = ticket.id
        session.expunge(ticket)
    
    # Generate tasks
    generator = TaskGeneratorService(db_service, task_queue_service)
    tasks = generator.generate_phase_tasks(ticket_id, Phase.REQUIREMENTS)
    
    assert len(tasks) >= 2  # Should generate at least 2 tasks for REQUIREMENTS
    assert all(task.ticket_id == ticket_id for task in tasks)
    assert all(task.phase_id == Phase.REQUIREMENTS for task in tasks)

def test_template_variable_substitution(db_service: DatabaseService, task_queue_service: TaskQueueService):
    """Test that template variables are substituted correctly."""
    # Create ticket with specific title
    with db_service.get_session() as session:
        ticket = Ticket(
            title="My Special Feature",
            phase_id=Phase.IMPLEMENTATION,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
    
    generator = TaskGeneratorService(db_service, task_queue_service)
    template = {
        "task_type": "implement_feature",
        "description_template": "Implement: {ticket_title}",
        "priority": "HIGH",
    }
    task = generator.generate_task_from_template(ticket, template)
    
    assert "My Special Feature" in task.description
```

### API Endpoint to Add

```python
# omoi_os/api/routes/tickets.py - Add this endpoint

@router.post("/{ticket_id}/generate-tasks", response_model=List[dict])
async def generate_tasks_for_ticket(
    ticket_id: UUID,
    phase_id: str | None = None,  # Optional, defaults to ticket's current phase
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Generate tasks for a ticket's phase.
    
    Args:
        ticket_id: Ticket ID
        phase_id: Optional phase ID (defaults to ticket's current phase)
        db: Database service
        queue: Task queue service
        
    Returns:
        List of generated tasks
    """
    from omoi_os.services.task_generator import TaskGeneratorService
    
    generator = TaskGeneratorService(db, queue)
    
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        target_phase = phase_id or ticket.phase_id
        tasks = generator.generate_phase_tasks(ticket_id, target_phase)
        
        return [
            {
                "id": task.id,
                "task_type": task.task_type,
                "description": task.description,
                "priority": task.priority,
                "phase_id": task.phase_id,
            }
            for task in tasks
        ]
```

### Success Criteria

- ✅ All tests written and passing
- ✅ TaskGeneratorService implements all methods
- ✅ Templates defined for all phases (REQUIREMENTS, DESIGN, IMPLEMENTATION, TESTING, DEPLOYMENT)
- ✅ Template variable substitution works ({ticket_title})
- ✅ API endpoint functional
- ✅ All existing tests still pass
- ✅ No linter errors

---

## 🚪 STREAM G: Phase Gates & Validation

### Your Assignment

Implement phase gate validation that checks required artifacts and validates phase completion before allowing transitions.

### Files to Create

1. **`omoi_os/services/phase_gate.py`** - Phase gate validation service
2. **`omoi_os/services/validation_agent.py`** - Validation agent (separate from worker)
3. **`omoi_os/models/phase_gate_artifact.py`** - Artifact tracking model
4. **`omoi_os/models/phase_gate_result.py`** - Gate validation result model
5. **`tests/test_phase_gates.py`** - Comprehensive tests

### Files to Modify

1. **`omoi_os/api/routes/phases.py`** - Create new routes file for phase operations
2. **`migrations/versions/003_phase_workflow.py`** - Add gate tables

### Database Changes

**Add to migration file** (coordinate with Stream E):

```python
# migrations/versions/003_phase_workflow.py - Add these to upgrade()

# Phase gate artifacts table
op.create_table(
    'phase_gate_artifacts',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('ticket_id', sa.String(), nullable=False),
    sa.Column('phase_id', sa.String(length=50), nullable=False),
    sa.Column('artifact_type', sa.String(length=100), nullable=False),
    sa.Column('artifact_path', sa.Text(), nullable=True),
    sa.Column('artifact_content', postgresql.JSONB(), nullable=True),
    sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('collected_by', sa.String(length=255), nullable=False),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
)
op.create_index('idx_gate_artifacts_ticket_phase', 'phase_gate_artifacts', ['ticket_id', 'phase_id'])

# Phase gate results table
op.create_table(
    'phase_gate_results',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('ticket_id', sa.String(), nullable=False),
    sa.Column('phase_id', sa.String(length=50), nullable=False),
    sa.Column('gate_status', sa.String(length=50), nullable=False),
    sa.Column('validation_result', postgresql.JSONB(), nullable=True),
    sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('validated_by', sa.String(length=255), nullable=True),
    sa.Column('blocking_reasons', postgresql.ARRAY(sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
)
op.create_index('idx_gate_results_ticket_phase', 'phase_gate_results', ['ticket_id', 'phase_id'])
```

### Models to Create

```python
# omoi_os/models/phase_gate_artifact.py
from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class PhaseGateArtifact(Base):
    """Artifacts collected for phase gate validation."""
    
    __tablename__ = "phase_gate_artifacts"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifact_content: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    collected_by: Mapped[str] = mapped_column(String(255), nullable=False)
```

```python
# omoi_os/models/phase_gate_result.py
from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy import Text
from datetime import datetime

class PhaseGateResult(Base):
    """Results of phase gate validation."""
    
    __tablename__ = "phase_gate_results"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    gate_status: Mapped[str] = mapped_column(String(50), nullable=False)  # passed, failed, pending
    validation_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    blocking_reasons: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
```

### Phase Gate Requirements

```python
# omoi_os/services/phase_gate.py
from omoi_os.models.phases import Phase

PHASE_GATE_REQUIREMENTS = {
    Phase.REQUIREMENTS: {
        "required_artifacts": ["requirements_document"],
        "required_tasks_completed": True,
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

### Service Interface to Implement

```python
# omoi_os/services/phase_gate.py
from omoi_os.models.phase_gate_artifact import PhaseGateArtifact
from omoi_os.models.phase_gate_result import PhaseGateResult
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService

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
        # Implementation:
        # 1. Get gate requirements for phase_id
        # 2. Check if all required artifacts exist
        # 3. Check if all phase tasks are completed
        # 4. Return status dict
        
    def validate_gate(self, ticket_id: str, phase_id: str) -> PhaseGateResult:
        """
        Run full gate validation.
        
        Returns:
            PhaseGateResult object
        """
        # Implementation:
        # 1. Check gate requirements
        # 2. Validate artifacts against criteria
        # 3. Create PhaseGateResult record
        # 4. Return result
        
    def collect_artifacts(self, ticket_id: str, phase_id: str) -> list[PhaseGateArtifact]:
        """Collect artifacts from completed tasks."""
        # Implementation:
        # 1. Query completed tasks for phase
        # 2. Extract artifacts from task results
        # 3. Create PhaseGateArtifact records
        # 4. Return list
        
    def can_transition(self, ticket_id: str, to_phase: str) -> tuple[bool, list[str]]:
        """
        Check if ticket can transition.
        
        Returns:
            (can_transition: bool, blocking_reasons: list[str])
        """
        # Implementation:
        # 1. Get current phase
        # 2. Validate gate for current phase
        # 3. Return (True, []) if passed, (False, reasons) if failed
```

### Validation Agent (Optional - Can be Simplified)

```python
# omoi_os/services/validation_agent.py
from omoi_os.services.agent_executor import AgentExecutor

class ValidationAgent:
    """Validation agent for phase gate reviews."""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
    
    def validate_phase_completion(self, ticket_id: str, phase_id: str, artifacts: list[dict]) -> dict:
        """
        Use OpenHands agent to validate phase completion.
        
        Returns:
            {
                "passed": bool,
                "feedback": str,
                "blocking_reasons": list[str],
            }
        """
        # Implementation:
        # 1. Create AgentExecutor with validation prompt
        # 2. Pass artifacts to agent
        # 3. Get validation result
        # 4. Return structured result
```

### Tests to Write FIRST

```python
# tests/test_phase_gates.py
import pytest
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.models.phases import Phase
from omoi_os.models.phase_gate_artifact import PhaseGateArtifact
from omoi_os.models.phase_gate_result import PhaseGateResult
from omoi_os.services.database import DatabaseService
from omoi_os.services.phase_gate import PhaseGateService

def test_check_gate_requirements_met(db_service: DatabaseService):
    """Test checking gate requirements when all met."""
    # Create ticket and tasks
    # Add required artifacts
    # Check requirements
    # Assert requirements_met is True

def test_check_gate_requirements_missing(db_service: DatabaseService):
    """Test checking gate requirements when artifacts missing."""
    # Create ticket
    # Don't add required artifacts
    # Check requirements
    # Assert requirements_met is False
    # Assert missing_artifacts list is populated

def test_collect_artifacts(db_service: DatabaseService):
    """Test collecting artifacts from completed tasks."""
    # Create ticket with completed tasks
    # Tasks should have result dicts with artifacts
    # Collect artifacts
    # Assert artifacts are created

def test_validate_gate_passed(db_service: DatabaseService):
    """Test gate validation when all criteria met."""
    # Setup ticket with all requirements
    # Validate gate
    # Assert gate_status is "passed"

def test_validate_gate_failed(db_service: DatabaseService):
    """Test gate validation when criteria not met."""
    # Setup ticket missing requirements
    # Validate gate
    # Assert gate_status is "failed"
    # Assert blocking_reasons populated

def test_can_transition_when_gate_passed(db_service: DatabaseService):
    """Test can_transition returns True when gate passed."""
    # Setup ticket with passed gate
    # Check can_transition
    # Assert True

def test_can_transition_when_gate_failed(db_service: DatabaseService):
    """Test can_transition returns False when gate failed."""
    # Setup ticket with failed gate
    # Check can_transition
    # Assert False and blocking reasons
```

### API Endpoints to Create

```python
# omoi_os/api/routes/phases.py - Create new file
from fastapi import APIRouter, HTTPException, Depends
from omoi_os.api.dependencies import get_db_service
from omoi_os.services.phase_gate import PhaseGateService

router = APIRouter()

@router.post("/tickets/{ticket_id}/validate-gate")
async def validate_gate(
    ticket_id: str,
    phase_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Validate phase gate for ticket."""
    gate_service = PhaseGateService(db)
    result = gate_service.validate_gate(ticket_id, phase_id)
    return {
        "gate_status": result.gate_status,
        "requirements_met": result.gate_status == "passed",
        "blocking_reasons": result.blocking_reasons or [],
    }

@router.get("/tickets/{ticket_id}/gate-status")
async def get_gate_status(
    ticket_id: str,
    phase_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Get current gate status."""
    gate_service = PhaseGateService(db)
    requirements = gate_service.check_gate_requirements(ticket_id, phase_id)
    return requirements

@router.post("/tickets/{ticket_id}/artifacts")
async def add_artifact(
    ticket_id: str,
    artifact_type: str,
    artifact_path: str | None = None,
    artifact_content: dict | None = None,
    db: DatabaseService = Depends(get_db_service),
):
    """Add artifact for phase gate."""
    # Implementation
```

### Success Criteria

- ✅ All tests written and passing
- ✅ PhaseGateService implements all methods
- ✅ Gate requirements defined for all phases
- ✅ Artifact collection works
- ✅ Gate validation works
- ✅ API endpoints functional
- ✅ All existing tests still pass
- ✅ No linter errors

---

## 📚 STREAM H: Cross-Phase Context Passing

### Your Assignment

Implement context aggregation from completed phases and summarization for passing to next phases.

### Files to Create

1. **`omoi_os/services/context_service.py`** - Context aggregation service
2. **`omoi_os/services/context_summarizer.py`** - Context summarization logic
3. **`tests/test_context_passing.py`** - Comprehensive tests

### Files to Modify

1. **`omoi_os/models/ticket.py`** - Add context fields
2. **`migrations/versions/003_phase_workflow.py`** - Add context columns

### Database Changes

**Add to migration file**:

```python
# migrations/versions/003_phase_workflow.py - Add to upgrade()

# Add context fields to tickets table
op.add_column('tickets', sa.Column('context', postgresql.JSONB(), nullable=True))
op.add_column('tickets', sa.Column('context_summary', sa.Text(), nullable=True))

# Optional: Phase context table for detailed tracking
op.create_table(
    'phase_context',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('ticket_id', sa.String(), nullable=False),
    sa.Column('phase_id', sa.String(length=50), nullable=False),
    sa.Column('context_data', postgresql.JSONB(), nullable=False),
    sa.Column('context_summary', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
)
op.create_index('idx_phase_context_ticket', 'phase_context', ['ticket_id'])
```

### Ticket Model Updates

```python
# omoi_os/models/ticket.py - Add these fields
context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Aggregated context
context_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Summarized context
```

### Service Interface to Implement

```python
# omoi_os/services/context_service.py
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.context_summarizer import ContextSummarizer

class ContextService:
    """Manages cross-phase context aggregation and summarization."""
    
    def __init__(self, db: DatabaseService):
        self.db = db
        self.summarizer = ContextSummarizer()
    
    def aggregate_phase_context(self, ticket_id: str, phase_id: str) -> dict:
        """
        Aggregate context from completed phase tasks.
        
        Returns:
            Context dict with phase-specific data
        """
        # Implementation:
        # 1. Get all completed tasks for phase
        # 2. Extract context from task results
        # 3. Aggregate into phase context dict
        # 4. Return context
        
    def summarize_context(self, context: dict, max_tokens: int = 2000) -> str:
        """
        Summarize context to reduce token usage.
        
        Args:
            context: Full context dict
            max_tokens: Maximum tokens for summary
            
        Returns:
            Summarized context string
        """
        # Implementation:
        # 1. Use ContextSummarizer to summarize
        # 2. Return summary string
        
    def get_context_for_phase(self, ticket_id: str, target_phase: str) -> dict:
        """
        Get aggregated context from all previous phases.
        
        Returns:
            Context dict with all previous phase data
        """
        # Implementation:
        # 1. Get ticket
        # 2. Get context from all phases before target_phase
        # 3. Aggregate into single dict
        # 4. Return context
        
    def update_ticket_context(self, ticket_id: str, phase_id: str) -> None:
        """Update ticket's context with new phase data."""
        # Implementation:
        # 1. Aggregate phase context
        # 2. Get existing ticket context
        # 3. Merge new phase context
        # 4. Summarize
        # 5. Update ticket.context and ticket.context_summary
```

### Context Summarizer

```python
# omoi_os/services/context_summarizer.py
class ContextSummarizer:
    """Summarizes context to reduce token usage."""
    
    def summarize_structured(self, context: dict) -> str:
        """
        Summarize structured context (key decisions, artifacts).
        
        Returns:
            Summarized string
        """
        # Implementation:
        # 1. Extract key points from context
        # 2. Format as summary string
        # 3. Return summary
        
    def extract_key_points(self, context: dict) -> list[str]:
        """Extract key points from context."""
        # Implementation:
        # 1. Extract important information
        # 2. Return list of key points
```

### Tests to Write FIRST

```python
# tests/test_context_passing.py
import pytest
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.models.phases import Phase
from omoi_os.services.database import DatabaseService
from omoi_os.services.context_service import ContextService

def test_aggregate_phase_context(db_service: DatabaseService):
    """Test aggregating context from phase tasks."""
    # Create ticket with completed tasks
    # Tasks have result dicts with context
    # Aggregate context
    # Assert context contains phase data

def test_summarize_context():
    """Test context summarization."""
    context = {"key": "value", "decisions": ["decision1"]}
    summarizer = ContextSummarizer()
    summary = summarizer.summarize_structured(context)
    assert len(summary) > 0
    assert "decision1" in summary

def test_get_context_for_phase(db_service: DatabaseService):
    """Test getting context from previous phases."""
    # Create ticket that has gone through multiple phases
    # Get context for current phase
    # Assert context includes previous phases

def test_update_ticket_context(db_service: DatabaseService):
    """Test updating ticket context."""
    # Create ticket
    # Update context for phase
    # Assert ticket.context is updated
    # Assert ticket.context_summary is updated
```

### API Endpoints to Add

```python
# omoi_os/api/routes/tickets.py - Add these endpoints

@router.get("/{ticket_id}/context")
async def get_ticket_context(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
):
    """Get full aggregated context for ticket."""
    from omoi_os.services.context_service import ContextService
    
    service = ContextService(db)
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return {
            "ticket_id": ticket_id,
            "full_context": ticket.context or {},
            "summary": ticket.context_summary,
        }

@router.post("/{ticket_id}/update-context")
async def update_ticket_context(
    ticket_id: UUID,
    phase_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Update ticket context from phase completion."""
    from omoi_os.services.context_service import ContextService
    
    service = ContextService(db)
    service.update_ticket_context(ticket_id, phase_id)
    return {"status": "updated"}
```

### Success Criteria

- ✅ All tests written and passing
- ✅ ContextService implements all methods
- ✅ Context aggregation works from task results
- ✅ Context summarization works
- ✅ Context passed between phases
- ✅ Ticket model updated with context fields
- ✅ API endpoints functional
- ✅ All existing tests still pass
- ✅ No linter errors

---

## 🧪 Testing Standards

### Test File Structure

```python
"""Test description for this test file."""

import pytest
from omoi_os.services.database import DatabaseService
# ... other imports

def test_feature_name(db_service: DatabaseService):
    """Test description."""
    # Arrange
    service = YourService(db_service)
    
    # Act
    result = service.your_method("param")
    
    # Assert
    assert result is not None
```

### Test Naming

- Use descriptive names: `test_<what>_<condition>_<expected_result>`
- Examples:
  - `test_generate_phase_tasks_creates_all_templates`
  - `test_validate_gate_fails_when_artifacts_missing`
  - `test_aggregate_context_includes_all_phases`

### Test Coverage

- Test success cases
- Test failure cases
- Test edge cases (empty lists, None values, etc.)
- Test error handling
- Test relationships between models

### Running Tests

```bash
# Run your specific test file
uv run pytest tests/test_your_file.py -v

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=omoi_os --cov-report=term-missing
```

---

## 📝 Code Standards

### Type Hints

Always use type hints:

```python
def your_method(self, param: str) -> dict:
    """Method description."""
    return {}
```

### Docstrings

Use Google-style docstrings:

```python
def your_method(self, param: str) -> dict:
    """
    Method description.
    
    Args:
        param: Parameter description
        
    Returns:
        Return value description
    """
```

### Error Handling

Return appropriate HTTP status codes:

```python
if not ticket:
    raise HTTPException(status_code=404, detail="Ticket not found")
```

### Session Management

Always use context manager:

```python
with self.db.get_session() as session:
    # Your code
    session.commit()
```

### Object Expunging

Expunge objects before returning from services:

```python
session.expunge(task)
return task
```

---

## ✅ Final Checklist

Before considering your work complete:

- [ ] All tests written and passing
- [ ] Code follows existing patterns
- [ ] Type hints on all methods
- [ ] Docstrings on all public methods
- [ ] No linter errors (`uv run ruff check omoi_os/`)
- [ ] All existing tests still pass (`uv run pytest tests/ -v`)
- [ ] Database migration created (if needed)
- [ ] API endpoints tested manually
- [ ] Code reviewed against examples in codebase

---

## 🚀 Getting Started

1. **Read the codebase**: Understand existing patterns
2. **Write first test**: Start with simplest test case
3. **Run test**: Confirm it fails (red)
4. **Implement minimal code**: Make test pass (green)
5. **Refactor**: Improve code quality
6. **Repeat**: Add next test case

**Good luck!** 🎯

