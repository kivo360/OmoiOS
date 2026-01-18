# Product Requirements Document: Spec E2E After Import Fix

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-2026-001 |
| Title | Spec E2E After Import Fix |
| Version | 1.0 |
| Status | Draft |
| Created | 2026-01-18 |
| Author | AI Spec Agent |

---

## 1. Executive Summary

### 1.1 Purpose

This PRD defines requirements for validating and fixing the end-to-end (E2E) spec-driven workflow after correcting billing import issues in the OmoiOS platform. The fix ensures that cost tracking services are properly imported and integrated with the spec execution pipeline, enabling accurate budget enforcement during autonomous agent operations.

### 1.2 Background

OmoiOS is a spec-driven autonomous engineering platform that orchestrates AI agents through phase-based workflows. A critical component is the billing/cost tracking system that monitors LLM API usage and enforces budget constraints. Recent issues identified that billing imports were incorrectly configured, potentially causing:
- Cost tracking failures during spec execution
- Budget enforcement gaps
- Inaccurate cost forecasting for pending tasks

### 1.3 Scope

This feature applies to the **existing OmoiOS codebase** and focuses on:
- Validating correct import paths for billing/cost tracking modules
- End-to-end testing of the spec workflow with proper cost tracking
- Ensuring budget enforcement operates correctly throughout spec phases

---

## 2. Objectives

### 2.1 Primary Objectives

1. **Validate Billing Import Correctness**: Ensure all modules correctly import `CostTrackingService` and related cost models
2. **E2E Spec Workflow Validation**: Confirm the complete spec lifecycle (draft → requirements → design → executing → completed) functions with proper cost tracking
3. **Budget Enforcement Integration**: Verify that budget limits are enforced at each phase transition

### 2.2 Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Import Error Rate | 0% | Static analysis + test suite |
| E2E Test Pass Rate | 100% | Playwright/Pytest test results |
| Cost Tracking Coverage | 100% of LLM calls | Cost record audit |
| Budget Enforcement Accuracy | 100% | Budget vs actual comparison |

---

## 3. Functional Requirements

### 3.1 Billing Import Validation

#### REQ-BILL-001: CostTrackingService Import Verification
**WHEN** any module requires cost tracking functionality
**THE SYSTEM SHALL** import `CostTrackingService` from `omoi_os.services.cost_tracking` without errors

**Acceptance Criteria:**
- [ ] All import statements resolve correctly at runtime
- [ ] No circular import issues exist
- [ ] Static type checking passes (mypy/pyright)

#### REQ-BILL-002: Cost Record Model Availability
**WHEN** recording LLM costs
**THE SYSTEM SHALL** successfully create `CostRecord` instances from `omoi_os.models.cost_record`

**Acceptance Criteria:**
- [ ] CostRecord model imports without errors
- [ ] Database migrations include cost_records table
- [ ] Foreign key relationships (task_id, agent_id) resolve correctly

#### REQ-BILL-003: Cost Models Configuration Loading
**WHEN** `CostTrackingService` initializes
**THE SYSTEM SHALL** load pricing configuration from `omoi_os/config/cost_models.yaml`

**Acceptance Criteria:**
- [ ] YAML configuration file exists and is valid
- [ ] Provider pricing data loads for OpenAI, Anthropic, and defaults
- [ ] Missing providers fall back to default pricing gracefully

### 3.2 E2E Spec Workflow Integration

#### REQ-E2E-001: Spec Creation with Cost Context
**WHEN** a user creates a new specification
**THE SYSTEM SHALL** initialize cost tracking context for the spec's project

**Acceptance Criteria:**
- [ ] New specs have access to project-level cost summaries
- [ ] Cost forecasting is available based on pending tasks

#### REQ-E2E-002: Requirements Phase Cost Tracking
**WHEN** an agent processes requirements during the Requirements phase
**THE SYSTEM SHALL** record all LLM API costs with correct task attribution

**Acceptance Criteria:**
- [ ] Cost records include `task_id` linking to the spec task
- [ ] Provider and model information is captured accurately
- [ ] Token counts (prompt + completion) are recorded

#### REQ-E2E-003: Design Phase Cost Tracking
**WHEN** an agent generates design artifacts
**THE SYSTEM SHALL** record costs and update running totals for the spec

**Acceptance Criteria:**
- [ ] Design phase tasks have associated cost records
- [ ] Running cost total is available via API
- [ ] Cost breakdown by phase is queryable

#### REQ-E2E-004: Execution Phase Budget Enforcement
**WHEN** the spec transitions to executing phase
**THE SYSTEM SHALL** enforce budget limits before spawning agent tasks

**Acceptance Criteria:**
- [ ] Budget check occurs before task assignment
- [ ] Tasks are blocked if budget would be exceeded
- [ ] Warning events are published at 80% budget threshold

#### REQ-E2E-005: Spec Completion Cost Summary
**WHEN** a specification reaches completed status
**THE SYSTEM SHALL** generate a final cost summary with breakdown by phase

**Acceptance Criteria:**
- [ ] Total cost for the spec is calculated accurately
- [ ] Per-phase breakdown is available
- [ ] Agent-level attribution is preserved

### 3.3 Event Integration

#### REQ-EVT-001: Cost Event Publishing
**WHEN** a cost record is created
**THE SYSTEM SHALL** publish a `cost.recorded` event to the EventBus

**Acceptance Criteria:**
- [ ] Event includes task_id, agent_id, provider, model, total_cost
- [ ] Events are received by subscribed listeners
- [ ] No events are lost during high-throughput execution

#### REQ-EVT-002: Budget Alert Events
**WHEN** costs approach or exceed budget thresholds
**THE SYSTEM SHALL** publish appropriate alert events

**Acceptance Criteria:**
- [ ] `budget.warning` event at 80% threshold
- [ ] `budget.exceeded` event when limit is reached
- [ ] Events include scope (project/ticket/spec level)

---

## 4. Non-Functional Requirements

### 4.1 Performance

#### NFR-PERF-001: Cost Recording Latency
Cost recording operations SHALL complete in < 50ms to avoid impacting agent response times.

#### NFR-PERF-002: Query Performance
Cost summary queries SHALL return results in < 200ms for typical scope sizes (< 10,000 records).

### 4.2 Reliability

#### NFR-REL-001: Cost Recording Durability
All cost records SHALL be persisted to the database before returning success to the caller.

#### NFR-REL-002: Import Resilience
Import failures SHALL be caught at application startup with clear error messages indicating the missing module.

### 4.3 Maintainability

#### NFR-MAIN-001: Test Coverage
The billing/cost tracking module SHALL maintain > 90% unit test coverage.

#### NFR-MAIN-002: Import Graph Clarity
Import dependencies SHALL be documented and follow a clear hierarchy to prevent circular imports.

### 4.4 Security

#### NFR-SEC-001: Cost Data Access Control
Cost records SHALL only be accessible to users with project membership or admin roles.

#### NFR-SEC-002: Budget Override Protection
Budget limits SHALL only be modifiable by project owners or organization admins.

---

## 5. Technical Design Considerations

### 5.1 Affected Components

| Component | Location | Impact |
|-----------|----------|--------|
| CostTrackingService | `backend/omoi_os/services/cost_tracking.py` | Primary service for cost operations |
| CostRecord Model | `backend/omoi_os/models/cost_record.py` | Database model for cost persistence |
| Cost API Routes | `backend/omoi_os/api/routes/costs.py` | REST endpoints for cost queries |
| Spec Service | `backend/omoi_os/services/spec_service.py` | Integration point for spec workflows |
| EventBusService | `backend/omoi_os/services/event_bus.py` | Event publishing for cost notifications |

### 5.2 Database Schema

The cost tracking system uses the following schema elements:

```sql
-- cost_records table
CREATE TABLE cost_records (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR REFERENCES tasks(id),
    agent_id VARCHAR REFERENCES agents(id),
    provider VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    prompt_cost FLOAT NOT NULL,
    completion_cost FLOAT NOT NULL,
    total_cost FLOAT NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### 5.3 Import Structure

Correct import hierarchy:

```
omoi_os/
├── models/
│   ├── cost_record.py      # CostRecord model
│   └── task.py             # Task model (dependency)
├── services/
│   ├── cost_tracking.py    # CostTrackingService
│   ├── database.py         # DatabaseService (dependency)
│   └── event_bus.py        # EventBusService (dependency)
└── config/
    └── cost_models.yaml    # Pricing configuration
```

---

## 6. Testing Requirements

### 6.1 Unit Tests

| Test Case | Description | Location |
|-----------|-------------|----------|
| test_cost_calculation | Verify cost math for different providers | `tests/unit/services/test_cost_tracking.py` |
| test_cost_record_creation | Verify CostRecord persistence | `tests/unit/services/test_cost_tracking.py` |
| test_cost_summary_aggregation | Verify aggregation logic | `tests/unit/services/test_cost_tracking.py` |
| test_import_resolution | Verify all imports resolve | `tests/unit/test_imports.py` |

### 6.2 Integration Tests

| Test Case | Description |
|-----------|-------------|
| test_spec_workflow_with_costs | Full spec lifecycle with cost tracking enabled |
| test_budget_enforcement | Budget limit blocking behavior |
| test_cost_event_publishing | Event bus integration |

### 6.3 E2E Tests

| Test Case | Description |
|-----------|-------------|
| test_e2e_spec_creation_to_completion | Complete spec workflow with real LLM calls (mocked) |
| test_e2e_cost_api_queries | Frontend-to-backend cost query flow |
| test_e2e_budget_alerts | User notification flow for budget events |

---

## 7. Dependencies and Assumptions

### 7.1 Dependencies

| Dependency | Type | Description |
|------------|------|-------------|
| PostgreSQL | Infrastructure | Database for cost record persistence |
| Redis | Infrastructure | Event bus message broker |
| SQLAlchemy 2.0+ | Library | ORM for database operations |
| PyYAML | Library | Configuration file parsing |
| pytest 8.0+ | Dev Dependency | Test framework |
| Playwright | Dev Dependency | E2E testing framework |

### 7.2 Assumptions

1. **Database Migrations Applied**: The `cost_records` table exists in the database
2. **Event Bus Operational**: Redis is available for event publishing
3. **Cost Models Configured**: `cost_models.yaml` contains valid pricing data
4. **Authentication Active**: Users are authenticated when querying costs

### 7.3 Constraints

1. **Backward Compatibility**: Existing cost records must remain queryable
2. **No Breaking API Changes**: Existing cost API endpoints maintain their contracts
3. **Migration Safety**: Database migrations must be reversible

---

## 8. Rollout Plan

### 8.1 Phase 1: Import Fix Validation
- Verify all import statements
- Run static type checking
- Execute existing unit tests

### 8.2 Phase 2: Integration Testing
- Run integration test suite
- Validate cost recording in staging environment
- Verify event publishing

### 8.3 Phase 3: E2E Validation
- Execute full E2E test suite
- Perform manual spec workflow testing
- Validate budget enforcement behavior

### 8.4 Phase 4: Production Deployment
- Deploy to production with feature flag
- Monitor cost recording metrics
- Enable for all users after validation

---

## 9. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import regression | Low | High | Add import verification to CI pipeline |
| Cost data loss | Low | High | Database transactions with rollback |
| Budget enforcement bypass | Medium | Medium | Multiple enforcement checkpoints |
| Performance degradation | Low | Medium | Async cost recording option |

---

## 10. Acceptance Criteria Summary

The feature is considered complete when:

1. [ ] All billing module imports resolve without errors
2. [ ] Unit test suite passes with > 90% coverage on cost tracking
3. [ ] Integration tests validate spec workflow with cost tracking
4. [ ] E2E tests confirm full lifecycle functionality
5. [ ] Budget enforcement blocks tasks when limits exceeded
6. [ ] Cost events publish correctly to EventBus
7. [ ] Cost API returns accurate summaries and breakdowns
8. [ ] No performance regression in spec execution (< 5% slowdown)

---

## 11. Related Documents

- [Ticket Workflow Requirements](./workflows/ticket_workflow.md)
- [Monitoring Architecture](./monitoring/monitoring_architecture.md)
- [Agent Lifecycle Requirements](./agents/agent_lifecycle.md)
- [Backend Development Guide](../../backend/CLAUDE.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-18 | AI Spec Agent | Initial PRD creation |
