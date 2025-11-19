# Async SQLAlchemy Migration Plan

## Executive Summary

This document outlines what it would take to migrate **100% of SQLAlchemy code to async** using SQLAlchemy 2.0+ with `psycopg` 3+ (which supports async operations). Based on codebase analysis, this is a **major refactoring effort** affecting approximately **87 files** with **537+ database session usages** across **38 service files**.

## Current State Analysis

### Current Stack
- **SQLAlchemy**: 2.0.0+ (preferably latest 2.x - supports async operations natively)
- **Database Driver**: `psycopg[binary,pool]>=3.2.0` (psycopg 3+ supports async operations natively, no driver change needed)
- **Connection String**: `postgresql+psycopg://...` (can remain the same format with `create_async_engine()`)
- **Session Pattern**: Synchronous `Session` with context manager `get_session()`
- **Usage Pattern**: `with db.get_session() as session:` throughout codebase

**Note**: SQLAlchemy 2.0+ removed `session.query()` entirely. The migration will require converting all `session.query()` calls to `session.execute(select(...))` patterns, which is a SQLAlchemy 2.0 requirement regardless of sync/async.

### Key Statistics
- **Service Files**: 38 files with database operations
- **Total Session Usages**: 537+ instances of `get_session()` or `with db.get_session()`
- **Session Operations**: 483+ instances of `session.query()`, `session.get()`, `session.execute()`, etc.
- **API Routes**: Multiple FastAPI routes using sync database calls
- **Background Loops**: 6+ async background loops calling sync database code
- **Test Files**: 30+ test files using sync database patterns

## Required Changes

### 1. Dependency Updates

**pyproject.toml**:
```toml
# Keep existing (psycopg 3+ supports async):
"psycopg[binary,pool]>=3.2.0,<4",

# Add (required for async SQLAlchemy):
"greenlet>=3.0.0",  # Required for async SQLAlchemy operations
```

**Note**: No driver change needed! `psycopg` 3+ supports async operations natively. The connection string can remain `postgresql+psycopg://` when used with `create_async_engine()`.

### 2. Core Database Service Refactor

**File**: `omoi_os/services/database.py`

**Current** (Synchronous):
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

class DatabaseService:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, ...)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
```

**Required** (Asynchronous):
```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncAttrs
)
from contextlib import asynccontextmanager
from typing import AsyncIterator

class DatabaseService:
    def __init__(self, connection_string: str):
        # psycopg 3+ works with async - connection string can stay the same
        # SQLAlchemy's create_async_engine handles psycopg async automatically
        self.engine = create_async_engine(
            connection_string,  # postgresql+psycopg://... works fine
            echo=False,
            pool_pre_ping=True,  # Recommended for async connections
        )
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False  # Important: prevents lazy loading issues
        )
    
    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def create_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
```

### 3. Base Model Updates

**File**: `omoi_os/models/base.py`

**Required Change**:
```python
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models with async support."""
    pass
```

### 4. Query Pattern Changes

**Current Pattern** (Synchronous):
```python
with db.get_session() as session:
    task = session.query(Task).filter(Task.id == task_id).first()
    session.add(new_task)
    session.commit()
```

**Required Pattern** (Asynchronous):
```python
async with db.get_session() as session:
    # Option 1: Using select() (SQLAlchemy 2.0 style - recommended)
    from sqlalchemy import select
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    # Option 2: Using session.get() (simpler for primary key lookups)
    task = await session.get(Task, task_id)
    
    # Adding/committing
    session.add(new_task)
    await session.commit()
```

**Key Changes**:
- `session.query()` → `session.execute(select(...))` or `await session.get()`
- `session.commit()` → `await session.commit()`
- `session.rollback()` → `await session.rollback()`
- `session.refresh()` → `await session.refresh()`
- `session.expunge()` → `await session.expunge()` (no await needed)
- `session.flush()` → `await session.flush()`
- `session.delete()` → `await session.delete()` (if using async pattern)
- `session.merge()` → `await session.merge()`

### 5. Service Method Signatures

**All service methods** that use database sessions must become `async`:

**Current**:
```python
class TaskQueueService:
    def enqueue_task(self, ticket_id: str, ...) -> Task:
        with self.db.get_session() as session:
            # ...
```

**Required**:
```python
class TaskQueueService:
    async def enqueue_task(self, ticket_id: str, ...) -> Task:
        async with self.db.get_session() as session:
            # ...
```

### 6. API Route Updates

**File**: `omoi_os/api/routes/tickets.py` (and all other route files)

**Current**:
```python
@router.post("", response_model=TicketResponse)
async def create_ticket(
    ticket_data: TicketCreate,
    db: DatabaseService = Depends(get_db_service),
):
    with db.get_session() as session:
        # ...
```

**Required**:
```python
@router.post("", response_model=TicketResponse)
async def create_ticket(
    ticket_data: TicketCreate,
    db: DatabaseService = Depends(get_db_service),
):
    async with db.get_session() as session:
        # ...
```

**Note**: FastAPI routes are already `async`, so only the session usage needs updating.

### 7. Background Loop Updates

**File**: `omoi_os/api/main.py`

**Current**:
```python
async def orchestrator_loop():
    while True:
        with db.get_session() as session:
            available_agent = session.query(Agent).filter(...).first()
        # ...
```

**Required**:
```python
async def orchestrator_loop():
    while True:
        async with db.get_session() as session:
            result = await session.execute(select(Agent).where(...))
            available_agent = result.scalar_one_or_none()
        # ...
```

### 8. Worker Updates

**File**: `omoi_os/worker.py`

**Current**: Uses sync database calls in threading context.

**Required**: Worker needs to be refactored to use async database calls. This may require:
- Converting worker to async/await pattern
- Using `asyncio.run()` or async event loop in worker threads
- Or using `run_in_executor()` for database operations (not recommended)

### 9. Alembic Migration Updates

**File**: `migrations/env.py`

**Required Changes**:
```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

def run_migrations_online() -> None:
    # Use async engine for migrations with psycopg
    # Connection string can remain postgresql+psycopg://
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),  # postgresql+psycopg:// works
        poolclass=pool.NullPool,
    )
    
    async def run_async_migrations():
        async with connectable.begin() as connection:
            await connection.run_sync(do_run_migrations)
    
    asyncio.run(run_async_migrations())
```

**Note**: Alembic 1.13+ has experimental async support. For production, consider upgrading to `alembic>=2.0.0` when available for full async support. Alternatively, you can keep migrations synchronous (using sync engine) while runtime uses async - this is a common pattern.

### 10. Test Updates

**File**: `tests/conftest.py` and all test files

**Current**:
```python
@pytest.fixture
def db_service(test_database_url: str) -> Generator[DatabaseService, None, None]:
    db = DatabaseService(test_database_url)
    db.create_tables()
    try:
        yield db
    finally:
        db.drop_tables()
```

**Required**:
```python
@pytest.fixture
async def db_service(test_database_url: str) -> AsyncGenerator[DatabaseService, None]:
    db = DatabaseService(test_database_url)
    await db.create_tables()
    try:
        yield db
    finally:
        await db.drop_tables()

# All test functions must be async
@pytest.mark.asyncio
async def test_something(db_service: DatabaseService):
    async with db_service.get_session() as session:
        # ...
```

**Note**: All test files need `@pytest.mark.asyncio` decorator and `async def` functions.

## File-by-File Breakdown

### Core Infrastructure (High Priority)
1. **omoi_os/services/database.py** - Complete rewrite
2. **omoi_os/models/base.py** - Add `AsyncAttrs`
3. **migrations/env.py** - Update for async migrations
4. **omoi_os/ticketing/db.py** - Convert to async (if used)

### Service Layer (38 files, ~483 operations)
All files in `omoi_os/services/` that use `db.get_session()`:
- `task_queue.py` (41 operations)
- `agent_registry.py` (19 operations)
- `memory.py` (16 operations)
- `approval.py` (17 operations)
- `agent_health.py` (18 operations)
- `monitor.py` (19 operations)
- `guardian.py` (22 operations)
- `collaboration.py` (18 operations)
- `resource_lock.py` (16 operations)
- `diagnostic.py` (23 operations)
- `validation_orchestrator.py` (21 operations)
- `result_submission.py` (21 operations)
- ... and 26 more service files

### API Routes (Multiple files)
- `omoi_os/api/routes/tickets.py` (3 usages)
- `omoi_os/api/routes/tasks.py` (4 usages)
- `omoi_os/api/routes/agents.py` (2 usages)
- `omoi_os/api/routes/phases.py` (2 usages)
- `omoi_os/api/routes/costs.py` (1 usage)
- `omoi_os/api/routes/alerts.py` (1 usage)
- `omoi_os/api/routes/watchdog.py` (1 usage)
- ... and more route files

### Background Loops
- `omoi_os/api/main.py` - `orchestrator_loop()`, `heartbeat_monitoring_loop()`, `diagnostic_monitoring_loop()`, `anomaly_monitoring_loop()`, `blocking_detection_loop()`, `approval_timeout_loop()`

### Worker
- `omoi_os/worker.py` - Complete refactor for async

### Tests (30+ files)
- All test files in `tests/` directory
- `tests/conftest.py` - Update fixtures
- All test functions need `@pytest.mark.asyncio`

## Migration Strategy

### Phase 1: Foundation (Week 1)
1. Update dependencies (`greenlet` - psycopg already supports async)
2. Refactor `DatabaseService` to async
3. Update `Base` model with `AsyncAttrs`
4. Update Alembic configuration (or keep sync for migrations)
5. Create async test fixtures

### Phase 2: Core Services (Week 2-3)
1. Start with most-used services:
   - `TaskQueueService`
   - `AgentRegistryService`
   - `DatabaseService` (already done)
2. Convert one service at a time
3. Update tests for each service
4. Verify functionality

### Phase 3: Remaining Services (Week 4-5)
1. Convert remaining 30+ service files
2. Update all API routes
3. Update background loops
4. Update worker

### Phase 4: Testing & Validation (Week 6)
1. Run full test suite
2. Fix any remaining issues
3. Performance testing
4. Documentation updates

## Critical Considerations

### 1. Connection String Format
- **Current**: `postgresql+psycopg://user:pass@host:port/db`
- **Required**: `postgresql+psycopg://user:pass@host:port/db` (same format!)
- **Action**: No connection string changes needed. `psycopg` 3+ works with `create_async_engine()` using the same connection string format.

### 2. Session Expiration
- Async sessions should use `expire_on_commit=False` to avoid lazy loading issues
- Objects accessed outside session context will raise errors

### 3. Lazy Loading
- **Problem**: Async SQLAlchemy doesn't support lazy loading by default
- **Solution**: Use `selectinload()` or `joinedload()` for relationships
- **Example**:
  ```python
  from sqlalchemy.orm import selectinload
  result = await session.execute(
      select(Task).options(selectinload(Task.ticket))
  )
  ```

### 4. Transaction Management
- All `session.commit()` calls must be `await session.commit()`
- All `session.rollback()` calls must be `await session.rollback()`
- Context managers automatically handle this, but manual calls need updating

### 5. Query API Changes (SQLAlchemy 2.0+)
- `session.query(Model)` is **removed** in SQLAlchemy 2.0 (not just deprecated)
- **Must use** `session.execute(select(Model))` instead
- Or `await session.get(Model, id)` for primary key lookups
- This applies to both sync and async sessions in SQLAlchemy 2.0+

### 6. Bulk Operations
- `session.query(Model).update()` needs to be rewritten
- Use `session.execute(update(Model).where(...).values(...))`

### 7. Testing Async Code
- All test functions must be `async def`
- Use `@pytest.mark.asyncio` decorator
- Use `pytest-asyncio>=0.23.0` (already in dependencies)

### 8. Worker Threading
- Worker uses threading, which conflicts with async
- **Options**:
  a. Convert worker to async/await pattern
  b. Use `asyncio.run()` in worker threads (not recommended)
  c. Use `run_in_executor()` for database calls (defeats purpose of async)

### 9. Migration Compatibility
- Alembic async support is experimental in 1.13
- May need to upgrade to Alembic 2.0+ for full async support
- Or use sync migrations with async runtime (not ideal)

### 10. Performance Considerations
- Async can improve I/O-bound operations
- Connection pooling is different in async
- May need to tune `pool_size`, `max_overflow` for async engine

## Potential Issues

### 1. Blocking Operations
- Any sync code calling async database will block
- Need to ensure all callers are async

### 2. Third-Party Libraries
- Some libraries may not support async
- May need wrappers or alternative libraries

### 3. Debugging Complexity
- Async stack traces are more complex
- Need proper async debugging tools

### 4. Migration Risk
- Large codebase means high risk of missing updates
- Need comprehensive test coverage

### 5. Performance Regression
- If not done correctly, async can be slower
- Need proper connection pooling and query optimization

## Testing Requirements

### Unit Tests
- All service methods must be tested with async fixtures
- Mock async sessions where appropriate
- Test error handling and rollbacks

### Integration Tests
- Test full async database workflows
- Test connection pooling
- Test concurrent operations

### E2E Tests
- Test API endpoints with async database
- Test background loops
- Test worker integration

## Estimated Effort

- **Total Files to Modify**: ~87 files
- **Service Files**: 38 files
- **Test Files**: 30+ files
- **API Routes**: 10+ files
- **Infrastructure**: 5 files
- **Estimated Time**: 6-8 weeks for full migration
- **Risk Level**: High (large codebase, many touchpoints)

## Recommendations

1. **Start Small**: Begin with one service (`TaskQueueService`) as proof of concept
2. **Incremental Migration**: Convert services one at a time, test thoroughly
3. **Comprehensive Testing**: Ensure test coverage before and after migration
4. **Performance Monitoring**: Monitor database performance during migration
5. **Documentation**: Update all documentation with async patterns
6. **Code Review**: Careful code review for all async conversions
7. **Consider Hybrid Approach**: Keep some sync code if migration is too risky

## Alternative: Hybrid Approach

If full async migration is too risky, consider:
- Keep core services async
- Use sync database for less critical paths
- Gradually migrate remaining code
- Use `run_in_executor()` for sync code calling async (not ideal)

## Conclusion

Migrating to 100% async SQLAlchemy is a **major undertaking** requiring:
- **6-8 weeks** of development time
- **87+ files** to modify
- **537+ database operations** to convert
- **Comprehensive testing** of all changes
- **High risk** due to codebase size

The benefits include:
- Better concurrency for I/O-bound operations
- Improved scalability
- Modern async/await patterns
- Better integration with FastAPI async routes

However, the migration requires careful planning, incremental execution, and thorough testing to avoid production issues.

