# Async SQLAlchemy Test Migration Guide

## Scope of Test Changes

### Current State
- **533 test functions** across **47 test files**
- **741 database operations** in tests (session usage, queries, commits)
- **Only 43 async test functions** (mostly in `test_intelligent_monitoring.py`)
- **All fixtures are synchronous** in `conftest.py`

### What Needs to Change
- **~490 test functions** need to become async (533 - 43 already async)
- **All test fixtures** in `conftest.py` need async conversion
- **All mock patterns** need to support async context managers
- **All database operations** in tests need `await`

---

## Test Migration Patterns

### 1. Test Fixtures (`conftest.py`)

#### ❌ BEFORE (Synchronous)
```python
@pytest.fixture(scope="function")
def db_service(test_database_url: str) -> Generator[DatabaseService, None, None]:
    """Create a fresh database service for each test."""
    db = DatabaseService(test_database_url)
    db.create_tables()  # Sync
    try:
        yield db
    finally:
        db.drop_tables()  # Sync

@pytest.fixture
def sample_ticket(db_service: DatabaseService) -> Ticket:
    """Create a sample ticket for testing."""
    with db_service.get_session() as session:  # Sync context manager
        ticket = Ticket(...)
        session.add(ticket)
        session.commit()  # Sync
        session.refresh(ticket)  # Sync
        session.expunge(ticket)
        return ticket
```

#### ✅ AFTER (Asynchronous)
```python
import pytest
from typing import AsyncGenerator

@pytest.fixture(scope="function")
async def db_service(test_database_url: str) -> AsyncGenerator[DatabaseService, None]:
    """Create a fresh database service for each test."""
    db = DatabaseService(test_database_url)
    await db.create_tables()  # Async
    try:
        yield db
    finally:
        await db.drop_tables()  # Async

@pytest.fixture
async def sample_ticket(db_service: DatabaseService) -> Ticket:
    """Create a sample ticket for testing."""
    async with db_service.get_session() as session:  # Async context manager
        ticket = Ticket(...)
        session.add(ticket)
        await session.commit()  # Async
        await session.refresh(ticket)  # Async
        session.expunge(ticket)
        return ticket
```

**Key Changes:**
- `Generator` → `AsyncGenerator`
- `def` → `async def`
- `with` → `async with`
- `session.commit()` → `await session.commit()`
- `session.refresh()` → `await session.refresh()`

---

### 2. Simple Test Functions

#### ❌ BEFORE (Synchronous)
```python
def test_ticket_crud(db_service: DatabaseService):
    """Test Ticket model CRUD operations."""
    # Create
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            description="Test description",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id

    # Read
    with db_service.get_session() as session:
        retrieved = session.get(Ticket, ticket_id)  # Sync
        assert retrieved is not None
        assert retrieved.title == "Test Ticket"
```

#### ✅ AFTER (Asynchronous)
```python
import pytest

@pytest.mark.asyncio
async def test_ticket_crud(db_service: DatabaseService):
    """Test Ticket model CRUD operations."""
    # Create
    async with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            description="Test description",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        await session.commit()  # Async
        ticket_id = ticket.id

    # Read
    async with db_service.get_session() as session:
        retrieved = await session.get(Ticket, ticket_id)  # Async
        assert retrieved is not None
        assert retrieved.title == "Test Ticket"
```

**Key Changes:**
- Add `@pytest.mark.asyncio` decorator
- `def test_` → `async def test_`
- `with` → `async with`
- `session.get()` → `await session.get()`
- `session.commit()` → `await session.commit()`

---

### 3. Query Pattern Changes

#### ❌ BEFORE (SQLAlchemy 1.x + Sync)
```python
def test_get_next_task_priority_order(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test get_next_task returns highest priority task first."""
    task_high = task_queue_service.enqueue_task(...)
    
    with db_service.get_session() as session:
        tasks = session.query(Task).filter(
            Task.status == "pending",
            Task.phase_id == "PHASE_REQUIREMENTS"
        ).all()
        assert len(tasks) == 3
```

#### ✅ AFTER (SQLAlchemy 2.0 + Async)
```python
import pytest
from sqlalchemy import select

@pytest.mark.asyncio
async def test_get_next_task_priority_order(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test get_next_task returns highest priority task first."""
    task_high = await task_queue_service.enqueue_task(...)  # Service method now async
    
    async with db_service.get_session() as session:
        result = await session.execute(
            select(Task).where(
                Task.status == "pending",
                Task.phase_id == "PHASE_REQUIREMENTS"
            )
        )
        tasks = result.scalars().all()  # Get list from result
        assert len(tasks) == 3
```

**Key Changes:**
- `session.query(Model)` → `session.execute(select(Model))`
- `.filter()` → `.where()`
- `.all()` → `.scalars().all()` or `.scalar_one_or_none()`
- `await` on `session.execute()`
- Service method calls need `await` too

---

### 4. Relationship Loading (Lazy Loading Issues)

#### ❌ BEFORE (Sync with Lazy Loading)
```python
def test_ticket_task_relationship(db_service: DatabaseService):
    """Test Ticket-Task relationship."""
    with db_service.get_session() as session:
        ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
        # Lazy loading works in sync
        assert len(ticket.tasks) == 2  # This triggers lazy load
```

#### ✅ AFTER (Async with Eager Loading)
```python
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

@pytest.mark.asyncio
async def test_ticket_task_relationship(db_service: DatabaseService):
    """Test Ticket-Task relationship."""
    async with db_service.get_session() as session:
        result = await session.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.tasks))  # Must eager load!
        )
        ticket = result.scalar_one_or_none()
        # Eager loading required - lazy loading doesn't work in async
        assert len(ticket.tasks) == 2
```

**Key Changes:**
- Must use `selectinload()` or `joinedload()` for relationships
- Lazy loading **doesn't work** in async SQLAlchemy
- Need to explicitly load relationships

---

### 5. Mock Patterns for Async

#### ❌ BEFORE (Sync Mock)
```python
def test_emit_heartbeat_success():
    """Test successful heartbeat emission."""
    mock_db = Mock(spec=DatabaseService)
    mock_session = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_session)
    mock_context.__exit__ = Mock(return_value=None)
    mock_db.get_session.return_value = mock_context
    
    mock_session.query.return_value.filter.return_value.first.return_value = sample_agent
    
    health_service = AgentHealthService(mock_db)
    result = health_service.emit_heartbeat("test-agent-123")  # Sync
```

#### ✅ AFTER (Async Mock)
```python
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_emit_heartbeat_success():
    """Test successful heartbeat emission."""
    mock_db = Mock(spec=DatabaseService)
    mock_session = AsyncMock()  # AsyncMock for async session
    mock_context = AsyncMock()
    
    # Async context manager pattern
    async def async_enter():
        return mock_session
    async def async_exit(exc_type, exc_val, exc_tb):
        return False
    
    mock_context.__aenter__ = async_enter
    mock_context.__aexit__ = async_exit
    mock_db.get_session.return_value = mock_context
    
    # Async query pattern
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=sample_agent)
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    health_service = AgentHealthService(mock_db)
    result = await health_service.emit_heartbeat("test-agent-123")  # Async
```

**Key Changes:**
- `Mock()` → `AsyncMock()` for async methods
- `__enter__`/`__exit__` → `__aenter__`/`__aexit__` for async context managers
- `session.query()` → `session.execute(select())` with async mock
- Service calls need `await`

---

### 6. Service Method Calls in Tests

#### ❌ BEFORE (Sync Service)
```python
def test_enqueue_task(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test enqueueing a task."""
    task = task_queue_service.enqueue_task(  # Sync method
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="analyze_requirements",
        description="Analyze requirements",
        priority="HIGH",
    )
    assert task is not None
```

#### ✅ AFTER (Async Service)
```python
import pytest

@pytest.mark.asyncio
async def test_enqueue_task(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test enqueueing a task."""
    task = await task_queue_service.enqueue_task(  # Async method
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="analyze_requirements",
        description="Analyze requirements",
        priority="HIGH",
    )
    assert task is not None
```

**Key Changes:**
- All service method calls need `await`
- Service methods become `async def`

---

### 7. Complex Test with Multiple Operations

#### ❌ BEFORE (Sync)
```python
def test_task_dependencies_complete(db_service: DatabaseService):
    """Test checking if task dependencies are complete."""
    with db_service.get_session() as session:
        # Create parent task
        parent = Task(...)
        session.add(parent)
        session.commit()
        parent_id = parent.id
        
        # Create child task with dependency
        child = Task(..., dependencies={"depends_on": [str(parent_id)]})
        session.add(child)
        session.commit()
        child_id = child.id
    
    # Check dependencies
    with db_service.get_session() as session:
        child = session.query(Task).filter(Task.id == child_id).first()
        parent = session.query(Task).filter(Task.id == parent_id).first()
        
        # Complete parent
        parent.status = "completed"
        session.commit()
        
        # Check if child is now available
        queue_service = TaskQueueService(db_service)
        available = queue_service._check_dependencies_complete(session, child)
        assert available is True
```

#### ✅ AFTER (Async)
```python
import pytest
from sqlalchemy import select

@pytest.mark.asyncio
async def test_task_dependencies_complete(db_service: DatabaseService):
    """Test checking if task dependencies are complete."""
    async with db_service.get_session() as session:
        # Create parent task
        parent = Task(...)
        session.add(parent)
        await session.commit()  # Async
        parent_id = parent.id
        
        # Create child task with dependency
        child = Task(..., dependencies={"depends_on": [str(parent_id)]})
        session.add(child)
        await session.commit()  # Async
        child_id = child.id
    
    # Check dependencies
    async with db_service.get_session() as session:
        result = await session.execute(
            select(Task).where(Task.id == child_id)
        )
        child = result.scalar_one_or_none()
        
        result = await session.execute(
            select(Task).where(Task.id == parent_id)
        )
        parent = result.scalar_one_or_none()
        
        # Complete parent
        parent.status = "completed"
        await session.commit()  # Async
        
        # Check if child is now available
        queue_service = TaskQueueService(db_service)
        available = await queue_service._check_dependencies_complete(session, child)  # Async
        assert available is True
```

---

## Migration Checklist Per Test File

For each test file, you need to:

### 1. Update Imports
```python
# Add these imports
import pytest
from typing import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from unittest.mock import AsyncMock
```

### 2. Update Test Functions
- [ ] Add `@pytest.mark.asyncio` decorator to each test
- [ ] Change `def test_` → `async def test_`
- [ ] Change `with db.get_session()` → `async with db.get_session()`
- [ ] Change `session.query()` → `await session.execute(select())`
- [ ] Change `session.get()` → `await session.get()`
- [ ] Change `session.commit()` → `await session.commit()`
- [ ] Change `session.refresh()` → `await session.refresh()`
- [ ] Change `session.rollback()` → `await session.rollback()`
- [ ] Change `.all()` → `.scalars().all()`
- [ ] Change `.first()` → `.scalar_one_or_none()`
- [ ] Change `.one()` → `.scalar_one()`
- [ ] Add `await` to all service method calls

### 3. Update Fixtures
- [ ] Change `Generator` → `AsyncGenerator`
- [ ] Change `def fixture` → `async def fixture`
- [ ] Update all database operations in fixtures

### 4. Update Mocks
- [ ] Change `Mock()` → `AsyncMock()` for async methods
- [ ] Update context manager mocks to use `__aenter__`/`__aexit__`
- [ ] Update query mocks to use `execute(select())` pattern

### 5. Fix Relationship Loading
- [ ] Add `selectinload()` or `joinedload()` for all relationships
- [ ] Remove any lazy loading assumptions

---

## Example: Complete Test File Migration

### ❌ BEFORE: `tests/test_01_database.py`
```python
def test_ticket_crud(db_service: DatabaseService):
    with db_service.get_session() as session:
        ticket = Ticket(...)
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id

    with db_service.get_session() as session:
        retrieved = session.get(Ticket, ticket_id)
        assert retrieved is not None
```

### ✅ AFTER: `tests/test_01_database.py`
```python
import pytest
from sqlalchemy import select

@pytest.mark.asyncio
async def test_ticket_crud(db_service: DatabaseService):
    async with db_service.get_session() as session:
        ticket = Ticket(...)
        session.add(ticket)
        await session.commit()
        ticket_id = ticket.id

    async with db_service.get_session() as session:
        retrieved = await session.get(Ticket, ticket_id)
        assert retrieved is not None
```

---

## Statistics

### Files Requiring Changes
- **47 test files** total
- **~44 test files** need full conversion (excluding 3 that are already async)
- **1 conftest.py** needs complete rewrite

### Operations Per File
- Average **15-20 test functions** per file
- Average **15-30 database operations** per file
- Some files have **50+ operations** (e.g., `test_validation_system.py`)

### Estimated Effort
- **~490 test functions** to convert
- **~741 database operations** to update
- **~2-3 weeks** for test migration alone
- **High risk** - tests are critical for validation

---

## Common Pitfalls

### 1. Forgetting `@pytest.mark.asyncio`
```python
# ❌ WRONG - will fail silently or with confusing errors
async def test_something(db_service):
    async with db_service.get_session() as session:
        ...

# ✅ CORRECT
@pytest.mark.asyncio
async def test_something(db_service):
    async with db_service.get_session() as session:
        ...
```

### 2. Lazy Loading in Async
```python
# ❌ WRONG - will raise error
async with session:
    ticket = await session.get(Ticket, id)
    tasks = ticket.tasks  # ERROR: Lazy loading doesn't work!

# ✅ CORRECT
async with session:
    result = await session.execute(
        select(Ticket)
        .where(Ticket.id == id)
        .options(selectinload(Ticket.tasks))
    )
    ticket = result.scalar_one_or_none()
    tasks = ticket.tasks  # Works!
```

### 3. Forgetting `await` on Service Calls
```python
# ❌ WRONG
task = task_queue_service.enqueue_task(...)  # Missing await

# ✅ CORRECT
task = await task_queue_service.enqueue_task(...)
```

### 4. Wrong Result Access Pattern
```python
# ❌ WRONG
result = await session.execute(select(Task))
tasks = result.all()  # ERROR: Result has no .all()

# ✅ CORRECT
result = await session.execute(select(Task))
tasks = result.scalars().all()  # Get scalars first
```

---

## Migration Strategy

### Phase 1: Update `conftest.py` (Week 1)
- Convert all fixtures to async
- Test with one simple test file first

### Phase 2: Core Tests (Week 2)
- `test_01_database.py` - foundation tests
- `test_02_task_queue.py` - service tests
- `test_03_event_bus.py` - simpler tests first

### Phase 3: Complex Tests (Week 3)
- Tests with relationships
- Tests with complex queries
- Integration tests

### Phase 4: Mock-Heavy Tests (Week 3-4)
- Tests with extensive mocking
- Update all mock patterns
- Verify async mocks work correctly

### Phase 5: Validation (Week 4)
- Run full test suite
- Fix any remaining issues
- Performance testing

---

## Conclusion

**Yes, you need to change a LOT of tests:**
- **~490 test functions** need async conversion
- **~741 database operations** need updating
- **All fixtures** need async conversion
- **All mocks** need async patterns

**The changes are systematic but extensive:**
- Add `@pytest.mark.asyncio` to every test
- Change `def` → `async def`
- Change `with` → `async with`
- Change `session.query()` → `await session.execute(select())`
- Add `await` to all database operations
- Add `await` to all service method calls

**Estimated effort: 2-3 weeks** for test migration alone, in addition to the 8-10 weeks for code migration.
