# Part 14: Integration Gaps & Known Issues

> Extracted from [ARCHITECTURE.md](../../ARCHITECTURE.md) — see hub doc for full system overview.

> **CRITICAL**: This document covers known integration gaps where features were coded but not properly wired together.
> These must be addressed before production deployment.

## Gap Summary

| Category | Issue | Severity |
|----------|-------|----------|
| **Orphaned Services** | 4 services with getters that are never called | Critical |
| **Event System** | 153 event publishes vs 18 subscribes | Critical |
| **DAG System** | CoordinationService not initialized in orchestrator | Critical |
| **Test Coverage** | 20 integration tests for 100 services | High |
| **TODO Items** | 51 TODO/FIXME comments in codebase | High |

---

## Gap 1: Orphaned Services (Never Called)

These services have singleton getters that are **NEVER called** from production code:

| Service | Getter | File | Issue |
|---------|--------|------|-------|
| **OwnershipValidation** | `get_ownership_validation_service()` | `ownership_validation.py:543` | Only called in unit tests |
| **Synthesis** | `get_synthesis_service()` | `synthesis_service.py:527` | Only called in unit tests |
| **SpecTaskExecution** | `get_spec_task_execution_service()` | `spec_task_execution.py:854` | Only called in unit tests |
| **ConvergenceMerge** | `get_convergence_merge_service()` | `convergence_merge_service.py:676` | NEVER called anywhere |

**Why This Matters:**

- Features were coded but never integrated
- The DAG merge system (`ConvergenceMergeService`) is completely orphaned
- Parallel task coordination (`SynthesisService`) is partially wired but getter unused

**Fix Required:**

```python
# In orchestrator_worker.py init_services():

# 1. Initialize CoordinationService (creates JOIN events)
from omoi_os.services.coordination import CoordinationService
coordination_service = CoordinationService(db=db, queue=queue, event_bus=event_bus)

# 2. Initialize ConvergenceMergeService (handles git merges)
from omoi_os.services.convergence_merge_service import get_convergence_merge_service
convergence_merge = get_convergence_merge_service(db=db, event_bus=event_bus)

# SynthesisService is already initialized but needs CoordinationService to publish events
```

---

## Gap 2: Event System Gaps

**153 event types published** but only **18 subscriptions** exist.

### Events Published Into the Void (No Subscribers)

| Event Type | Published In | Subscriber | Status |
|------------|--------------|------------|--------|
| `APPROVAL_CREATED` | approval.py | None | Lost |
| `APPROVAL_COMPLETED` | approval.py | None | Lost |
| `BUDGET_EXCEEDED` | budget_enforcer.py | None | Lost |
| `BUDGET_WARNING` | budget_enforcer.py | None | Lost |
| `COST_RECORDED` | cost_tracking.py | None | Lost |
| `MEMORY_PATTERN_STORED` | memory.py | None | Lost |
| `QUALITY_CHECK_*` | quality_checker.py | None | Lost |
| `WATCHDOG_*` | watchdog.py | None | Lost |
| `ALERT_*` | alerting.py | None | Lost |
| `COLLABORATION_*` | collaboration.py | None | Lost |
| `GITHUB_*` | github_integration.py | None | Lost |
| `SUBSCRIPTION_*` | subscription_service.py | None | Lost |
| `BILLING_*` | billing_service.py | None | Lost |

### Events With Subscribers (Working)

| Event Type | Subscriber |
|------------|------------|
| `TASK_CREATED` | orchestrator_worker |
| `TASK_COMPLETED` | synthesis_service, spec_task_execution, phase_manager, phase_progression |
| `TASK_FAILED` | spec_task_execution |
| `TASK_STARTED` | phase_manager, phase_progression |
| `TASK_VALIDATION_FAILED` | orchestrator_worker |
| `TASK_VALIDATION_PASSED` | orchestrator_worker |
| `TICKET_CREATED` | orchestrator_worker |
| `SANDBOX_agent.completed` | orchestrator_worker |
| `SANDBOX_agent.failed` | orchestrator_worker |
| `SANDBOX_agent.error` | orchestrator_worker |
| `coordination.join.created` | synthesis_service |
| `synthesis.completed` | convergence_merge_service |
| `PHASE_TRANSITION` | phase_progression |

**Impact**: Most events are published but never consumed — wasted work and no reactive behavior.

---

## Gap 3: DAG System Not Wired

The DAG system has 4 services that should work together but aren't connected:

```
WHAT EXISTS:
┌─────────────────────────────────────────────────────────────────────────┐
│  DependencyGraphService  │  CoordinationService  │  SynthesisService    │
│  - Graph visualization   │  - SYNC, SPLIT, JOIN  │  - Merge results     │
│  - Critical path calc    │  - Creates events     │  - Listens for joins │
│                          │                       │                      │
│  ConvergenceMergeService │  ConflictScorer       │  AgentConflictResolver│
│  - Git branch merging    │  - Dry-run scoring    │  - LLM resolution    │
└─────────────────────────────────────────────────────────────────────────┘

WHAT'S CONNECTED:
┌─────────────────────────────────────────────────────────────────────────┐
│  orchestrator_worker.py                                                  │
│  ├── SynthesisService ✅ (initialized, subscribes to events)            │
│  ├── CoordinationService ❌ (NOT initialized, events not created)        │
│  └── ConvergenceMergeService ❌ (NOT initialized)                        │
│                                                                          │
│  spec_task_execution.py                                                  │
│  └── CoordinationService ✅ (initialized for spec execution only)        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Consequence**:

- Tasks can only have basic `depends_on` dependencies
- No automatic result synthesis for non-spec tasks
- No git branch merge orchestration
- Parallel task coordination doesn't work outside spec flow

---

## Gap 4: Test Coverage Gaps

**20 integration test files** for **100 services** = ~20% coverage

### Services WITH Integration Tests

| Test File | Services Tested |
|-----------|-----------------|
| `test_convergence_merge.py` | ConvergenceMergeService, ConflictScorer |
| `test_coordination_activation.py` | CoordinationService |
| `test_spec_task_execution_*.py` | SpecTaskExecutionService |
| `test_spec_sync_integration.py` | SpecSyncService |
| `test_validation_integration.py` | ValidationOrchestrator |
| `sandbox/*.py` (9 files) | Sandbox-related services |

### Services WITHOUT Integration Tests (Critical)

| Service | Risk Level | Notes |
|---------|------------|-------|
| `MonitoringLoop` | Critical | Orchestrates Guardian + Conductor |
| `IntelligentGuardian` | Critical | Per-agent trajectory analysis |
| `ConductorService` | Critical | System-wide coherence |
| `DiscoveryService` | Critical | Workflow branching |
| `MemoryService` | High | Pattern learning |
| `TaskContextBuilder` | High | Context assembly |
| `PhaseProgressionService` | High | Phase transitions |
| `OwnershipValidationService` | High | File ownership |
| `AlertService` | Medium | Alerting |
| `WatchdogService` | Medium | Stuck detection |

---

## Gap 5: TODO/FIXME Items (51 Found)

### Critical TODOs

| File | Line | TODO |
|------|------|------|
| `alerting.py` | 337 | `TODO: Implement actual email sending` |
| `alerting.py` | 346 | `TODO: Implement actual Slack webhook POST` |
| `alerting.py` | 355 | `TODO: Implement actual HTTP webhook POST` |
| `agent_registry.py` | 460 | `TODO: Implement version compatibility matrix` |
| `agent_registry.py` | 484 | `TODO: Implement resource availability check` |
| `restart_orchestrator.py` | 180 | `TODO: Implement cooldown tracking` |
| `restart_orchestrator.py` | 184 | `TODO: Implement restart attempt tracking` |
| `phase_progression_service.py` | 636 | `TODO: Check .omoi_os/specs/ directory` |
| `phase_progression_service.py` | 717 | `TODO: Integrate with parse_specs.py` |
| `billing.py` | 842-927 | `TODO: Add proper admin authentication check` (3 places) |

### Medium Priority TODOs

| File | TODO |
|------|------|
| `memory.py:703` | Make extract_pattern async |
| `tickets.py:491` | Make embedding service async |
| `ticket_search_service.py:17` | Integrate with Qdrant |
| `auth.py:199` | Track logout in audit log |
| `auth.py:284` | Send email with reset link |
| `github.py:156` | Get webhook secret from project settings |
| `github.py:206` | Implement sync logic |

---

## Gap 6: API Routes Without Initialization

Some API routes import services that may not be initialized at startup:

| Route | Service Used | Initialization |
|-------|--------------|----------------|
| `/api/v1/graph/*` | DependencyGraphService | Created per-request |
| `/api/v1/specs/execute` | SpecTaskExecutionService | Created per-request |
| `/api/v1/memory/*` | MemoryService | Created per-request |

**Note**: Per-request initialization may cause performance issues under load.

---

## Recommended Fix Priority

### Phase 1: Critical

1. Wire CoordinationService into orchestrator_worker.py
2. Wire ConvergenceMergeService into orchestrator_worker.py
3. Add subscribers for critical events (BUDGET_*, ALERT_*)
4. Fix admin auth TODOs in billing routes

### Phase 2: High

1. Add integration tests for MonitoringLoop, Guardian, Conductor
2. Add integration tests for DiscoveryService
3. Implement alerting TODOs (email, Slack, webhooks)
4. Implement restart_orchestrator TODOs

### Phase 3: Medium

1. Add event subscribers for remaining orphaned events
2. Add integration tests for remaining untested services
3. Implement remaining TODO items
4. Performance test per-request service initialization

---

## Exact Code Changes for Integration Fixes

### Fix 1: Wire CoordinationService into Orchestrator Worker

**File:** `backend/omoi_os/workers/orchestrator_worker.py`
**Location:** `init_services()` function, after SynthesisService initialization

```python
    # CoordinationService (creates coordination patterns: SYNC, SPLIT, JOIN, MERGE)
    # This service publishes coordination.join.created events that SynthesisService listens for
    from omoi_os.services.coordination import CoordinationService
    coordination_service = CoordinationService(
        db=db,
        queue=queue,
        event_bus=event_bus,
    )
    logger.info(
        "service_initialized",
        service="coordination_service",
        capabilities=["sync", "split", "join", "merge"],
    )
```

### Fix 2: Wire ConvergenceMergeService into Orchestrator Worker

**File:** `backend/omoi_os/workers/orchestrator_worker.py`
**Location:** `init_services()` function, after CoordinationService

```python
    # ConvergenceMergeService (handles git merging at DAG convergence points)
    from omoi_os.services.convergence_merge_service import (
        get_convergence_merge_service,
        ConvergenceMergeConfig,
    )
    from omoi_os.services.agent_conflict_resolver import AgentConflictResolver

    conflict_resolver = AgentConflictResolver(llm_service=get_llm_service())

    convergence_merge_service = get_convergence_merge_service(
        db=db,
        event_bus=event_bus,
        config=ConvergenceMergeConfig(
            max_conflicts_auto_resolve=10,
            enable_auto_push=False,
        ),
        conflict_resolver=conflict_resolver,
    )
    convergence_merge_service.subscribe_to_events()
    logger.info(
        "service_initialized",
        service="convergence_merge_service",
        capabilities=["branch_merge", "conflict_scoring", "llm_resolution"],
    )
```

### Fix 3: Wire OwnershipValidationService into Orchestrator Worker

**File:** `backend/omoi_os/workers/orchestrator_worker.py`
**Location:** `init_services()` function, before DaytonaSpawner is used

```python
    from omoi_os.services.ownership_validation import (
        get_ownership_validation_service,
    )
    ownership_service = get_ownership_validation_service(
        db=db,
        strict_mode=False,
    )
    logger.info(
        "service_initialized",
        service="ownership_validation",
        capabilities=["file_ownership", "conflict_detection"],
    )
```

---

## Integration Checklist for Future Agents

> **Copy this checklist when making changes to OmoiOS services.**

### Before Adding a New Service

- [ ] Determine which process needs it (API, Orchestrator, or both)
- [ ] Check if a singleton getter exists (e.g., `get_*_service()`)
- [ ] If singleton exists, check if it's actually called anywhere
- [ ] Plan where to initialize (see [Service Initialization Map](../../ARCHITECTURE.md#service-initialization-map-critical-reference))

### When Initializing a Service

- [ ] Add import at top of file
- [ ] Initialize in correct order (dependencies first)
- [ ] If service publishes events, verify subscribers exist
- [ ] If service subscribes to events, call `.subscribe_to_events()`
- [ ] Add logger.info for initialization tracking
- [ ] Update this document if adding to core initialization

### When Adding Event Publishing

- [ ] Check if any service subscribes to this event type
- [ ] If no subscribers exist, document in Gap 2 above
- [ ] Consider adding a subscriber for the event
- [ ] Use consistent event naming (ENTITY_ACTION format)

### When Adding Event Subscribing

- [ ] Verify the event is actually published somewhere
- [ ] Call `event_bus.subscribe()` AFTER event_bus is initialized
- [ ] Test that events are received (use Redis CLI to publish test events)

### Testing Integration

```bash
# Test event flow
redis-cli PUBLISH events.TASK_COMPLETED '{"event_type":"TASK_COMPLETED","entity_type":"task","entity_id":"test-123","payload":{}}'

# Check service initialization
grep -r "service_initialized" backend/omoi_os/workers/ | wc -l

# Check event subscriptions
grep -r "event_bus.subscribe" backend/omoi_os/ | wc -l
```

## Quick Reference Cards

### Card 1: Where to Initialize Services

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SERVICE INITIALIZATION LOCATIONS                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  API Routes need it?  ──────────→  api/main.py:lifespan()           │
│                                                                      │
│  Background worker needs it?  ──→  workers/orchestrator_worker.py   │
│                                    init_services()                   │
│                                                                      │
│  Both need it?  ────────────────→  Initialize in BOTH places        │
│                                    (they're separate processes!)     │
│                                                                      │
│  Per-request? (bad pattern) ────→  Review if should be singleton    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Card 2: Event Flow Verification

```
┌─────────────────────────────────────────────────────────────────────┐
│                      EVENT FLOW CHECKLIST                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. PUBLISHER                                                        │
│     - Where is event_bus.publish() called?                           │
│     - File: _________________ Line: _______                          │
│                                                                      │
│  2. SUBSCRIBER                                                       │
│     - Where is event_bus.subscribe() called?                         │
│     - File: _________________ Line: _______                          │
│     - Handler function: _________________                            │
│                                                                      │
│  3. REDIS CHANNEL                                                    │
│     - Channel name: events.{EVENT_TYPE}                              │
│     - Test: redis-cli SUBSCRIBE events.EVENT_TYPE                    │
│                                                                      │
│  4. VERIFICATION                                                     │
│     - [ ] Publisher initializes after event_bus                      │
│     - [ ] Subscriber calls subscribe() in initialization             │
│     - [ ] Handler function handles SystemEvent format                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Card 3: DAG System Integration

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DAG SYSTEM FLOW                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    coordination.join.created                   │
│  │CoordinationService│ ─────────────────────────────────┐            │
│  │  join_tasks()    │                                   │            │
│  │  split_task()    │                                   ▼            │
│  └──────────────────┘                         ┌──────────────────┐   │
│                                               │ SynthesisService │   │
│                                               │ _handle_join_*() │   │
│  ┌──────────────────┐    TASK_COMPLETED       │ tracks pending   │   │
│  │  TaskQueueService │ ──────────────────────→│ joins, merges    │   │
│  │  update_status() │                         │ results when     │   │
│  └──────────────────┘                         │ ready            │   │
│                                               └────────┬─────────┘   │
│                                                        │             │
│                              coordination.synthesis.completed        │
│                                                        │             │
│                                                        ▼             │
│                                         ┌────────────────────────┐   │
│                                         │ConvergenceMergeService │   │
│                                         │ merge_at_convergence() │   │
│                                         │ (git branch merging)   │   │
│                                         └────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```
