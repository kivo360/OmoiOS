# Agent Spawn Prompt: Phase 2 Stream E - Phase Definitions & State Machine

**Created**: 2025-11-20
**Status**: Active
**Related**: docs/design/phase2/stream_e_overview.md, docs/design/workflows/phase_state_machine.md, docs/requirements/phase2_stream_e.md

---


**Purpose**: This prompt is designed to be given to Claude Code to spawn multiple Python agents working in parallel on Stream E, following Test-Driven Development (TDD) methodology.

**Target**: Phase 2, Stream E - Phase Definitions & State Machine  
**Methodology**: Test-Driven Development (TDD)  
**Language**: Python 3.12+  
**Framework**: FastAPI, SQLAlchemy, Pytest

---

## Agent Assignment Prompt

```
You are a Python developer working on a multi-agent orchestration system called OmoiOS. 
You are assigned to implement **Stream E: Phase Definitions & State Machine** for Phase 2.

## Project Context

**Codebase**: Multi-agent orchestration system using OpenHands SDK
**Current State**: Phase 1 complete (task dependencies, retries, health, timeout)
**Your Task**: Implement phase definitions and state machine for ticket workflow

**Key Technologies**:
- Python 3.12+
- FastAPI for API
- SQLAlchemy 2.0+ for ORM
- PostgreSQL with psycopg3
- Pytest for testing
- `whenever` library for datetime handling

**Project Structure**:
- `omoi_os/models/` - SQLAlchemy models
- `omoi_os/services/` - Business logic services
- `omoi_os/api/routes/` - FastAPI route handlers
- `tests/` - Pytest test files
- `migrations/versions/` - Alembic migrations

## Your Assignment: Stream E - Phase Definitions & State Machine

### Deliverables (TDD Approach)

**CRITICAL**: Follow Test-Driven Development (TDD):
1. Write tests FIRST
2. Run tests (they should fail)
3. Implement minimal code to pass tests
4. Refactor if needed
5. Repeat

### Task Breakdown (Can be parallelized)

#### Sub-task E1: Phase Constants & Enum
**Files to Create**:
- `omoi_os/models/phases.py` - Phase enum and constants

**Tests to Write FIRST** (`tests/test_phases.py`):
```python
def test_phase_enum_values():
    """Test that all phase enum values are correct"""
    
def test_phase_sequence_order():
    """Test that phase sequence is in correct order"""
    
def test_phase_transitions_valid():
    """Test that valid transitions are defined correctly"""
    
def test_phase_transitions_invalid():
    """Test that invalid transitions are not in transition map"""
```

**Implementation**:
- Create `Phase` enum with values: BACKLOG, REQUIREMENTS, DESIGN, IMPLEMENTATION, TESTING, DEPLOYMENT, DONE, BLOCKED
- Define `PHASE_SEQUENCE` list
- Define `PHASE_TRANSITIONS` dict mapping each phase to valid next phases
- Include regression support (TESTING → IMPLEMENTATION)

#### Sub-task E2: Phase History Model
**Files to Create**:
- `omoi_os/models/phase_history.py` - Phase transition history model

**Tests to Write FIRST** (`tests/test_phase_history.py`):
```python
def test_create_phase_history():
    """Test creating phase history record"""
    
def test_phase_history_relationships():
    """Test phase history relationship to ticket"""
    
def test_phase_history_timestamps():
    """Test phase history timestamp tracking"""
```

**Implementation**:
- Create `PhaseHistory` SQLAlchemy model
- Fields: id, ticket_id, from_phase, to_phase, transition_reason, transitioned_by, artifacts, created_at
- Foreign key to tickets table
- Indexes on ticket_id and created_at

#### Sub-task E3: Phase Service - State Machine Logic
**Files to Create**:
- `omoi_os/services/phase_service.py` - Phase state machine service

**Tests to Write FIRST** (`tests/test_phase_service.py`):
```python
def test_can_transition_valid():
    """Test valid phase transitions return True"""
    
def test_can_transition_invalid():
    """Test invalid phase transitions return False"""
    
def test_transition_ticket_success():
    """Test successful ticket phase transition"""
    
def test_transition_ticket_invalid():
    """Test invalid transition raises error"""
    
def test_transition_ticket_records_history():
    """Test transition creates phase history record"""
    
def test_get_valid_transitions():
    """Test getting valid next phases"""
    
def test_get_phase_history():
    """Test retrieving phase history for ticket"""
```

**Implementation**:
- Create `PhaseService` class
- Implement `can_transition(from_phase, to_phase)` method
- Implement `transition_ticket(ticket_id, to_phase, reason, transitioned_by)` method
- Implement `get_phase_history(ticket_id)` method
- Implement `get_valid_transitions(current_phase)` method
- Use `Phase` enum from E1
- Update Ticket model's `phase_id` field
- Create PhaseHistory records on transitions

#### Sub-task E4: Ticket Model Updates
**Files to Modify**:
- `omoi_os/models/ticket.py` - Add previous_phase_id field

**Tests to Write FIRST** (`tests/test_ticket_phase_tracking.py`):
```python
def test_ticket_previous_phase_tracking():
    """Test ticket tracks previous phase"""
    
def test_ticket_phase_transition_updates():
    """Test ticket phase_id and previous_phase_id update correctly"""
```

**Implementation**:
- Add `previous_phase_id: Mapped[Optional[str]]` field to Ticket model
- Update on phase transitions

#### Sub-task E5: API Endpoints
**Files to Modify**:
- `omoi_os/api/routes/tickets.py` - Add phase transition endpoint

**Tests to Write FIRST** (`tests/test_phase_api.py`):
```python
def test_transition_ticket_endpoint_success():
    """Test POST /api/v1/tickets/{id}/transition succeeds"""
    
def test_transition_ticket_endpoint_invalid():
    """Test POST /api/v1/tickets/{id}/transition rejects invalid transitions"""
    
def test_get_phase_history_endpoint():
    """Test GET /api/v1/tickets/{id}/phase-history returns history"""
    
def test_get_valid_transitions_endpoint():
    """Test GET /api/v1/tickets/{id}/valid-transitions returns valid phases"""
```

**Implementation**:
- Add `POST /api/v1/tickets/{ticket_id}/transition` endpoint
- Add `GET /api/v1/tickets/{ticket_id}/phase-history` endpoint
- Add `GET /api/v1/tickets/{ticket_id}/valid-transitions` endpoint
- Use PhaseService for business logic
- Return appropriate HTTP status codes (200, 400, 404)

#### Sub-task E6: Database Migration
**Files to Create**:
- `migrations/versions/003_phase_workflow.py` - Database migration

**Tests**: Migration tested via existing test infrastructure

**Implementation**:
- Create Alembic migration
- Add `phase_history` table
- Add `previous_phase_id` column to `tickets` table
- Add indexes
- Include downgrade function

## TDD Workflow (MANDATORY)

For EACH sub-task:

1. **Write Tests First**:
   - Create test file in `tests/` directory
   - Write test functions with descriptive names
   - Use existing fixtures from `tests/conftest.py` (db_service, etc.)
   - Test both success and failure cases
   - Use pytest assertions

2. **Run Tests**:
   ```bash
   uv run pytest tests/test_<your_test_file>.py -v
   ```
   - Tests MUST fail initially (red phase)

3. **Implement Minimal Code**:
   - Write only enough code to make tests pass
   - Follow existing code patterns in codebase
   - Use type hints (Python 3.12+ syntax)
   - Follow existing naming conventions

4. **Run Tests Again**:
   - Tests should now pass (green phase)

5. **Refactor** (if needed):
   - Improve code quality while keeping tests green
   - Ensure code follows project patterns

## Code Patterns to Follow

### SQLAlchemy Models
```python
from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

class YourModel(Base):
    __tablename__ = "your_table"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    # ... other fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
```

### Services
```python
from omoi_os.services.database import DatabaseService

class YourService:
    def __init__(self, db: DatabaseService):
        self.db = db
    
    def your_method(self, param: str) -> ReturnType:
        with self.db.get_session() as session:
            # Implementation
            pass
```

### API Routes
```python
from fastapi import APIRouter, HTTPException, Depends
from omoi_os.api.dependencies import get_db_service

router = APIRouter()

@router.post("/endpoint")
async def your_endpoint(
    param: str,
    db: DatabaseService = Depends(get_db_service),
):
    # Implementation
    pass
```

### Tests
```python
import pytest
from omoi_os.services.database import DatabaseService

def test_your_feature(db_service: DatabaseService):
    """Test description."""
    # Arrange
    service = YourService(db_service)
    
    # Act
    result = service.your_method("test")
    
    # Assert
    assert result is not None
```

## Existing Test Fixtures

Use these fixtures from `tests/conftest.py`:
- `db_service: DatabaseService` - Database service with test database
- `task_queue_service: TaskQueueService` - Task queue service
- `sample_ticket: Ticket` - Sample ticket fixture
- `sample_task: Task` - Sample task fixture

## Dependencies

**Required Imports**:
- `from omoi_os.models.base import Base`
- `from omoi_os.services.database import DatabaseService`
- `from omoi_os.utils.datetime import utc_now`
- `from uuid import uuid4`

**Existing Models to Use**:
- `omoi_os.models.ticket.Ticket`
- `omoi_os.models.task.Task`

## Success Criteria

Your work is complete when:
1. ✅ All tests written and passing
2. ✅ Phase enum and constants defined
3. ✅ PhaseHistory model created
4. ✅ PhaseService implements state machine
5. ✅ Ticket model updated with previous_phase_id
6. ✅ API endpoints functional
7. ✅ Database migration created
8. ✅ All existing tests still pass (33+ tests)
9. ✅ No linter errors
10. ✅ Code follows existing patterns

## Parallelization Strategy

If multiple agents are spawned:
- **Agent 1**: Sub-tasks E1 (Phase Constants) + E2 (Phase History Model)
- **Agent 2**: Sub-task E3 (Phase Service)
- **Agent 3**: Sub-task E4 (Ticket Model) + E5 (API Endpoints)
- **Agent 4**: Sub-task E6 (Database Migration)

**Coordination**:
- Agent 1 must complete E1 before others can use Phase enum
- Agent 4 should wait for E2 to complete before creating migration
- All agents should coordinate on migration file

## Testing Commands

```bash
# Run your specific tests
uv run pytest tests/test_phases.py -v
uv run pytest tests/test_phase_service.py -v
uv run pytest tests/test_phase_api.py -v

# Run all tests to ensure nothing broke
uv run pytest tests/ -v

# Check linting
uv run ruff check omoi_os/
```

## Important Notes

1. **Use TDD**: Always write tests first
2. **Follow Patterns**: Match existing code style
3. **Type Hints**: Use Python 3.12+ type hints
4. **Error Handling**: Return appropriate HTTP status codes
5. **Documentation**: Add docstrings to all public methods
6. **Session Management**: Always use `db.get_session()` context manager
7. **Expunge Objects**: Use `session.expunge()` when returning objects from services

## Questions?

- Check existing code in `omoi_os/services/task_queue.py` for service patterns
- Check `omoi_os/api/routes/tickets.py` for API patterns
- Check `tests/test_01_database.py` for test patterns
- Review `docs/agent_assignments_phase2.md` for full specification

## Start Here

1. Read the existing codebase structure
2. Write your first test
3. Run it (should fail)
4. Implement minimal code
5. Run test again (should pass)
6. Repeat for next test

Good luck! 🚀
```

---

## Usage Instructions

### For Single Agent
Copy the entire prompt above and give it to Claude Code. The agent will work through all sub-tasks sequentially.

### For Multiple Parallel Agents

**Option 1: Split by Sub-tasks**
- **Agent 1**: Give prompt + "Focus on Sub-tasks E1 and E2"
- **Agent 2**: Give prompt + "Focus on Sub-task E3"
- **Agent 3**: Give prompt + "Focus on Sub-tasks E4 and E5"
- **Agent 4**: Give prompt + "Focus on Sub-task E6"

**Option 2: Split by Component**
- **Agent 1**: "Focus on Models (E1, E2, E4)"
- **Agent 2**: "Focus on Services (E3)"
- **Agent 3**: "Focus on API (E5)"
- **Agent 4**: "Focus on Migration (E6)"

### Coordination Notes

Add to each agent's prompt:
```
**Coordination**: 
- Check with other agents before modifying shared files (migration, Ticket model)
- Use feature branches: `feature/phase2-e-<subtask>`
- Daily sync: Share progress in #phase2-coordination channel
```

---

## Expected Outcomes

After all agents complete:
- ✅ Phase enum with 8 phases defined
- ✅ PhaseHistory model with full tracking
- ✅ PhaseService with state machine logic
- ✅ Ticket model with previous_phase_id
- ✅ 3 new API endpoints for phase operations
- ✅ Database migration for phase workflow
- ✅ 20+ new tests, all passing
- ✅ All existing tests still passing

---

**Ready to spawn agents!** 🎯

