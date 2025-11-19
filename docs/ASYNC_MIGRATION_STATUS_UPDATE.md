# Async SQLAlchemy Migration Status Update

## Initial Assessment (from Migration Plan)

### Scope
- **Total Files to Modify**: ~87 files
- **Service Files**: 38 files
- **Test Files**: 30+ files
- **API Routes**: 10+ files
- **Infrastructure**: 5 files

### Database Operations
- **Total Session Usages**: 537+ instances of `get_session()`
- **Query Operations**: 483+ instances of `session.query()`, `session.get()`, etc.
- **Background Loops**: 6+ async background loops calling sync database code

### Estimated Effort
- **Time**: 6-8 weeks for full migration
- **Risk Level**: High (large codebase, many touchpoints)

---

## Current State Analysis (2024)

### Actual Scope - **INCREASED**

#### Service Files: **61 files** (up from 38 - **+60% increase**)
New services added since initial assessment:
- `intelligent_guardian.py`
- `conductor.py`
- `monitoring_loop.py`
- `agent_output_collector.py`
- `trajectory_context.py`
- `ace_engine.py`, `ace_curator.py`, `ace_reflector.py`, `ace_executor.py`
- `validation_orchestrator.py`, `validation_agent.py`
- `mcp_registry.py`, `mcp_circuit_breaker.py`, `mcp_authorization.py`, `mcp_integration.py`, `mcp_retry.py`
- `quality_checker.py`, `quality_predictor.py`
- `budget_enforcer.py`
- `restart_orchestrator.py`
- `orchestrator_coordination.py`
- `context_summarizer.py`
- `template_service.py`
- `pattern_loader.py`
- `phase_loader.py`
- `validation_helpers.py`
- And more...

#### API Routes: **24 route files** (up from 10+ - **+140% increase**)
- `agents.py`, `alerts.py`, `auth.py`, `board.py`, `collaboration.py`
- `commits.py`, `costs.py`, `diagnostic.py`, `events.py`, `github.py`
- `graph.py`, `guardian.py`, `mcp.py`, `memory.py`, `monitor.py`
- `phases.py`, `projects.py`, `quality.py`, `results.py`, `tasks.py`
- `tickets.py`, `validation.py`, `watchdog.py`

### Database Operations - **ACTUAL COUNTS**

#### Session Usage
- **586 instances** of `get_session()` across **106 files** (up from 537+)
- **236 instances** of `session.query()` across **62 files** (down from 483+, but still significant)

#### SQLAlchemy 2.0 Migration Status
- **Only 13 instances** of `session.execute(select(...))` across **5 files**
- **16 files** import `select` from SQLAlchemy (partial migration)
- **Most code still uses** `session.query()` pattern (SQLAlchemy 1.x style)

### Test Files Status
- **43 async test functions** (mostly in `test_intelligent_monitoring.py`)
- **Most tests still synchronous** - using sync `db_service` fixture
- Test fixtures in `conftest.py` are **still synchronous**

### Current Architecture State

#### ✅ Already Async (Good News)
- **14 service files** have some async methods (90 async/await usages)
- FastAPI routes are already `async def` (just need session updates)
- Background loops in `api/main.py` are already async functions
- `monitoring_loop.py` is fully async

#### ❌ Still Synchronous (Needs Work)
- **DatabaseService** - completely synchronous
- **Base model** - no `AsyncAttrs` mixin
- **Worker** (`omoi_os/worker.py`) - uses threading, not async
- **Most service methods** - all synchronous
- **Test fixtures** - all synchronous
- **Alembic migrations** - synchronous

---

## What Has Changed Since Initial Plan

### 1. **Codebase Growth** ⚠️
- **Service files increased by 60%** (38 → 61)
- **API routes increased by 140%** (10+ → 24)
- **More database operations** to migrate (586 vs 537)
- **Migration scope is larger** than originally estimated

### 2. **Partial SQLAlchemy 2.0 Adoption** ✅
- Some services already use `select()` pattern (16 files)
- But most still use `session.query()` (236 instances)
- **Migration will require both**:
  - Converting sync → async
  - Converting `session.query()` → `session.execute(select())`

### 3. **New Async Patterns Introduced** ✅
- `monitoring_loop.py` is fully async
- Some services have async methods (LLM calls, HTTP requests)
- But they still use **sync database sessions** inside async functions

### 4. **Worker Architecture** ⚠️
- Worker still uses **threading** (`ThreadPoolExecutor`)
- This is a **bigger challenge** than initially thought
- May require complete worker rewrite to async/await

---

## New Considerations for Migration

### 1. **Hybrid Async/Sync Patterns** 🔴 CRITICAL
Many services now have **async methods that call sync database code**:
```python
async def some_async_method(self):
    # This is async but uses sync database!
    with self.db.get_session() as session:  # BLOCKS!
        session.query(...)
```

**Impact**: These will need careful refactoring to avoid blocking the event loop.

### 2. **Monitoring Loop Already Async** ✅
- `monitoring_loop.py` is already async
- But it calls sync database methods
- This creates **async functions blocking on sync DB calls**
- Needs immediate attention

### 3. **Worker Threading Challenge** 🔴 CRITICAL
- Worker uses `ThreadPoolExecutor` and threading
- Async database won't work well in threads
- **Options**:
  a. Convert entire worker to async (major refactor)
  b. Use `asyncio.run()` in worker threads (not recommended)
  c. Keep worker sync, use sync DB for worker only (hybrid approach)

### 4. **Test Infrastructure** ⚠️
- Only 43 async tests out of many more
- `conftest.py` fixtures are sync
- Need to convert **all test fixtures** to async
- Need `@pytest.mark.asyncio` on all test functions
- This is a **large undertaking**

### 5. **SQLAlchemy 2.0 Query Migration** ⚠️
- 236 instances of `session.query()` need conversion
- Must convert to `session.execute(select())` **before** async migration
- Or do both simultaneously (more complex)

### 6. **New Service Dependencies** ⚠️
New services have complex interdependencies:
- `IntelligentGuardian` → `TrajectoryContext` → `AgentOutputCollector` → DB
- `ConductorService` → `IntelligentGuardian` → DB
- `MonitoringLoop` → `ConductorService` → `IntelligentGuardian` → DB

**Impact**: Need to migrate in dependency order, or all at once.

### 7. **MCP Integration Services** ⚠️
New MCP-related services (`mcp_registry.py`, `mcp_integration.py`, etc.):
- Some have async methods for HTTP calls
- But still use sync database
- Need careful migration

### 8. **Alembic Async Support** ⚠️
- Current Alembic config is fully synchronous
- Alembic 2.0+ has better async support
- May need to upgrade Alembic version
- Or keep migrations sync (common pattern)

### 9. **Connection Pooling** ⚠️
- Async engines use different pooling
- May need to tune `pool_size`, `max_overflow` for async
- Connection string format is fine (`postgresql+psycopg://` works)

### 10. **Lazy Loading Issues** ⚠️
- Async SQLAlchemy doesn't support lazy loading
- Need to use `selectinload()` or `joinedload()` for relationships
- Current code may have lazy loading that will break

---

## Updated Migration Estimates

### Revised Scope
- **Service Files**: 61 files (up from 38)
- **API Routes**: 24 files (up from 10+)
- **Test Files**: 30+ files (unchanged, but all need async conversion)
- **Total Files**: **~115+ files** (up from 87)

### Revised Effort
- **Time**: **8-10 weeks** (up from 6-8 weeks)
- **Risk Level**: **Very High** (larger codebase, more complex patterns)
- **Complexity**: **Higher** (hybrid async/sync patterns, worker threading)

### Critical Path Items
1. **Worker threading** - biggest architectural challenge
2. **Monitoring loop** - already async but blocks on sync DB
3. **Test infrastructure** - all fixtures need async conversion
4. **SQLAlchemy 2.0 query migration** - 236 instances to convert

---

## Recommendations

### 1. **Phased Approach** (Recommended)
**Phase 1: Foundation** (Week 1-2)
- Update dependencies (`greenlet`)
- Convert `DatabaseService` to async
- Update `Base` model with `AsyncAttrs`
- Create async test fixtures

**Phase 2: Core Services** (Week 3-4)
- Convert `TaskQueueService` (most used)
- Convert `AgentRegistryService`
- Convert monitoring-related services (`IntelligentGuardian`, `ConductorService`)
- Update background loops in `api/main.py`

**Phase 3: Remaining Services** (Week 5-7)
- Convert remaining 50+ service files
- Update all API routes
- Convert test files

**Phase 4: Worker & Edge Cases** (Week 8-9)
- Convert worker to async (or hybrid approach)
- Fix lazy loading issues
- Performance tuning

**Phase 5: Testing & Validation** (Week 10)
- Full test suite
- Performance testing
- Documentation

### 2. **Alternative: Hybrid Approach**
- Keep worker sync with sync database
- Make API and background loops async
- Use sync database for worker, async for API
- **Pros**: Lower risk, faster migration
- **Cons**: Two database connection pools, more complexity

### 3. **SQLAlchemy 2.0 First**
- Convert all `session.query()` → `session.execute(select())` first
- Then convert to async
- **Pros**: Smaller incremental changes
- **Cons**: Two migration phases

---

## Conclusion

The migration scope has **significantly increased** since the initial plan:
- **61 service files** (vs 38 originally)
- **24 API routes** (vs 10+ originally)
- **~115+ total files** (vs 87 originally)
- **More complex patterns** (hybrid async/sync)

**Key Challenges**:
1. Worker threading architecture
2. Hybrid async/sync patterns in new services
3. Test infrastructure conversion
4. SQLAlchemy 2.0 query migration

**Estimated Effort**: **8-10 weeks** (up from 6-8 weeks)

The migration is still **technically feasible** but **more complex** than initially estimated. A phased approach with careful dependency management is strongly recommended.
