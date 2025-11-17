# Phase 6 Proposal: Workflow Intelligence & Self-Healing

**Phase 6 builds the "brain" on Phase 3-5's "body"**

---

## Executive Summary

Add autonomous workflow recovery and result validation to complete the vision from `docs/design/diagnosis_agent.md`.

**Goal:** Transform from orchestration platform → self-healing autonomous system

**Timeline:** 4 weeks (parallelizable to 2-3 weeks)  
**Effort:** 35-40 hours total  
**Prerequisites:** Phase 5 complete ✅

---

## The Problem (Without Phase 6)

```
Current Behavior:
1. All tasks complete ✅
2. Agents stop working ✅
3. Workflow status = "stuck" ⚠️
4. No one submitted final result ❌
5. System doesn't notice ❌
6. Requires manual intervention 😞

With Phase 6:
1. All tasks complete ✅
2. Agents stop working ✅
3. System detects: "No validated result" ⚠️
4. Diagnostic agent spawns ✅
5. Creates task: "Submit final result" ✅
6. Workflow auto-recovers 🎉
```

---

## Phase 6 Squad Assignments

### Squad A: Result Validation (Week 1 — 5-6 hours)

**Scope:**
- WorkflowResult model (result_submissions table)
- Result submission API (submit, validate, list)
- Auto-termination logic
- Version tracking

**Deliverables:**
```
omoi_os/models/workflow_result.py
omoi_os/services/result_submission.py
omoi_os/api/routes/results.py
migrations/versions/009_result_validation.py
tests/test_result_submission.py (12 tests)
```

**Complexity:** ⭐⭐⭐ (Medium)

---

### Squad B: Diagnostic System (Weeks 2-3 — 15-18 hours)

**Scope:**
- DiagnosticRun model
- Stuck workflow detection
- Diagnostic agent spawning
- Evidence collection (basic)
- Hypothesis generation
- Recovery task creation

**Deliverables:**
```
omoi_os/models/diagnostic_run.py
omoi_os/services/diagnostic.py
omoi_os/services/stuck_detector.py
omoi_os/services/evidence_collector.py
omoi_os/services/hypothesis_generator.py
migrations/versions/010_diagnostic_system.py
tests/test_diagnostic.py (20 tests)
docs/diagnostic/README.md
```

**Complexity:** ⭐⭐⭐⭐⭐ (Very High)

---

### Squad C: Enhanced Validation (Week 4 — 12-15 hours)

**Scope:**
- ValidationReview model with iterations
- Validation orchestrator
- Feedback delivery to workers
- Repeated failure tracking
- Diagnostic integration

**Deliverables:**
```
omoi_os/models/validation_review.py
omoi_os/services/validation_orchestrator.py
omoi_os/services/feedback_transport.py
Enhance: omoi_os/services/validation_agent.py
migrations/versions/011_validation_enhancement.py
tests/test_validation_orchestrator.py (15 tests)
```

**Complexity:** ⭐⭐⭐⭐ (Medium-High)

---

## Dependency Graph

```
Phase 5 (✅ COMPLETE)
  ├─→ WorkflowResult (Week 1) ────────┐ [INDEPENDENT]
  ├─→ Diagnostic System (Weeks 2-3) ──┤ [Needs: WorkflowResult]
  └─→ Enhanced Validation (Week 4) ───┘ [Needs: Diagnostic]
```

**Can parallelize:** Result + Enhanced Validation can start Week 1  
**Blocker:** Diagnostic needs WorkflowResult complete first

---

## Key Features Added

### 1. Stuck Workflow Detection

**Activation Conditions (ALL must be true):**
```python
✓ Workflow exists
✓ Has tasks
✓ All tasks finished (no pending/running/under_review)
✓ No validated result exists
✓ Cooldown passed (60s since last diagnostic)
✓ Stuck time met (60s since last task activity)
```

**Output:** Spawns diagnostic agent

---

### 2. Diagnostic Agent Context

**What the agent receives:**
```
- Workflow goal + result_criteria
- Last 15 agents (who, what, when, outcome)
- Recent tasks (descriptions, results, failures)
- Conductor analyses
- Validation feedback
- Memory patterns (similar past workflows)
```

**What the agent produces:**
```
- Root cause hypothesis (ranked by likelihood)
- 1-5 recovery tasks (with phase assignments)
- Diagnostic report (stored for audit)
```

---

### 3. WorkflowResult Lifecycle

```
Agent submits result
  ↓
System creates ResultSubmission (status: submitted)
  ↓
Validator agent reviews
  ↓
Validator calls validate_result(passed: true/false, feedback)
  ↓
If PASS + on_result_found="stop_all":
  → Terminate all agents
  → Mark workflow complete
  → Store in Memory
  
If FAIL:
  → Deliver feedback to agent
  → Allow re-submission
  → Track iteration count
```

---

### 4. Enhanced Validation with Iterations

```
Task completes
  ↓
Enters "under_review" state
  ↓
Spawn validator agent
  ↓
Validator reviews code
  ↓
If needs work:
  → Create ValidationReview (iteration N)
  → Deliver feedback to worker
  → Worker fixes
  → Re-submit for review (iteration N+1)
  
If repeated failures (3+ iterations):
  → Spawn diagnostic agent
  → Analyze why validation keeps failing
```

---

## Integration with Phase 5

### Guardian Integration

**Diagnostic calls Guardian when:**
- Workflow is critically stuck
- Need emergency resource reallocation
- Need priority override for recovery tasks

```python
# Diagnostic detects critical stuck state
if ticket.priority == "CRITICAL" and stuck_for > 300:
    # Use Guardian to boost recovery task priority
    guardian.override_task_priority(
        task_id=recovery_task.id,
        new_priority="CRITICAL",
        reason="Diagnostic recovery for critical workflow",
        authority=AuthorityLevel.GUARDIAN
    )
```

---

### Memory Integration

**Diagnostic uses Memory for:**
- Finding similar past stuck workflows
- Retrieving recovery patterns
- Storing diagnostic reports for future reference

```python
# Diagnostic queries Memory
similar_failures = memory.search_similar_tasks(
    task_description=ticket.description,
    filters={"success": False},
    top_k=5
)

# Uses patterns to guide hypothesis generation
for past_failure in similar_failures:
    hypotheses.append(Hypothesis(
        description=f"Similar to past failure: {past_failure.error_patterns}",
        likelihood=past_failure.confidence_score,
    ))
```

---

### Cost Integration

**Diagnostic tracks:**
- Cost of diagnostic agent execution
- Cost-benefit of recovery vs. human intervention
- Budget limits for diagnostic spawning

```python
# Before spawning diagnostic
if cost_tracker.get_remaining_budget("diagnostic") < MIN_DIAGNOSTIC_BUDGET:
    # Don't spawn, escalate to human instead
    guardian.create_alert("Diagnostic budget exhausted")
```

---

## Database Schema

### New Tables (Phase 6)

**result_submissions:**
```sql
CREATE TABLE result_submissions (
    submission_id VARCHAR PRIMARY KEY,
    workflow_id VARCHAR NOT NULL,  -- ticket_id
    agent_id VARCHAR NOT NULL,
    markdown_file_path TEXT NOT NULL,
    
    -- Validation
    validated_at TIMESTAMP WITH TIME ZONE,
    passed BOOLEAN,
    feedback TEXT,
    evidence_index JSONB,
    
    -- Versioning
    version INTEGER NOT NULL,
    result_criteria_snapshot TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,  -- submitted, validated
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    UNIQUE(workflow_id, version)
);
```

**diagnostic_runs:**
```sql
CREATE TABLE diagnostic_runs (
    id VARCHAR PRIMARY KEY,
    workflow_id VARCHAR NOT NULL,  -- ticket_id
    diagnostic_agent_id VARCHAR,
    diagnostic_task_id VARCHAR,
    
    -- Trigger context
    triggered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    total_tasks_at_trigger INTEGER NOT NULL,
    done_tasks_at_trigger INTEGER NOT NULL,
    failed_tasks_at_trigger INTEGER NOT NULL,
    time_since_last_task_seconds INTEGER NOT NULL,
    
    -- Recovery
    tasks_created_count INTEGER DEFAULT 0,
    tasks_created_ids JSONB,
    
    -- Analysis
    workflow_goal TEXT,
    phases_analyzed JSONB,
    agents_reviewed JSONB,
    diagnosis TEXT,
    
    -- Lifecycle
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(32) NOT NULL,  -- created, running, completed, failed
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

**validation_reviews:**
```sql
CREATE TABLE validation_reviews (
    id VARCHAR PRIMARY KEY,
    task_id VARCHAR NOT NULL,
    validator_agent_id VARCHAR NOT NULL,
    
    -- Review details
    iteration INTEGER NOT NULL,
    decision VARCHAR(32) NOT NULL,  -- approved, needs_work, rejected
    feedback TEXT NOT NULL,
    review_artifacts JSONB,
    
    -- Timing
    reviewed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Memory integration
    stored_in_memory BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    UNIQUE(task_id, iteration)
);
```

---

## Test Strategy (Phase 6)

### Result Validation Tests (12 tests)
```
test_result_submission.py:
  • test_submit_result
  • test_validate_result_pass
  • test_validate_result_fail
  • test_multiple_submissions_versioning
  • test_auto_termination_on_pass
  • test_result_criteria_snapshot
  • test_list_results_by_workflow
  • test_immutability (no updates allowed)
```

### Diagnostic System Tests (20 tests)
```
test_diagnostic.py:
  • test_detect_stuck_workflow
  • test_cooldown_enforcement
  • test_stuck_threshold
  • test_spawn_diagnostic_agent
  • test_build_diagnostic_context
  • test_create_recovery_tasks
  • test_diagnostic_run_tracking
  • test_hypothesis_generation
  • test_evidence_collection
  • test_integration_with_memory
  • test_integration_with_guardian
```

### Enhanced Validation Tests (15 tests)
```
test_validation_orchestrator.py:
  • test_spawn_validator_agent
  • test_validation_review_iteration
  • test_feedback_delivery
  • test_repeated_failure_detection
  • test_diagnostic_spawn_on_failures
  • test_validation_memory_integration
```

**Phase 6 Total:** 47 new tests

---

## Success Criteria

**Phase 6 Complete When:**

- [ ] All 47 new tests passing
- [ ] WorkflowResult can be submitted and validated
- [ ] Stuck workflows auto-detected (monitoring loop)
- [ ] Diagnostic agents spawn with rich context
- [ ] Recovery tasks created (1-5 per diagnostic)
- [ ] Validation has iteration support
- [ ] Feedback delivered to workers
- [ ] Integration tests pass with Phase 5 features
- [ ] Documentation complete (3 READMEs)

**Expected Total:**
- ~220 tests (171 Phase 3 + 29 Guardian + 29 Memory + ~47 Phase 6)
- ~10,000 lines of code
- 11 migrations
- Full autonomous workflow system

---

## Code Estimates (Phase 6)

### Result Validation Squad
- **Production:** ~400 lines
- **Tests:** ~350 lines
- **Config:** ~50 lines
- **Total:** ~800 lines

### Diagnostic System Squad
- **Production:** ~800 lines (complex logic)
- **Tests:** ~600 lines
- **Config:** ~100 lines
- **Total:** ~1,500 lines

### Enhanced Validation Squad
- **Production:** ~600 lines
- **Tests:** ~450 lines
- **Config:** ~50 lines
- **Total:** ~1,100 lines

**Phase 6 Total:** ~3,400 lines (35% increase from Phase 5)

---

## Risk Assessment

### Low Risk ✅
- **Result Validation:** Straightforward CRUD + validation flow
- **Diagnostic Detection:** Simple threshold checks

### Medium Risk ⚠️
- **Evidence Collection:** Requires integration with external systems (logs/metrics)
- **Diagnostic Agent Context:** Large prompt engineering effort

### High Risk 🔴
- **Hypothesis Generation:** LLM quality varies, needs good prompting
- **Recovery Task Creation:** Agent must understand complex failure modes

### Mitigation
- Start with minimal viable diagnostic (detection + basic evidence)
- Iterate on hypothesis quality based on real failures
- Provide fallback to Guardian for complex cases
- Comprehensive testing of stuck detection logic

---

## Migration Strategy (Phase 6)

**Three migrations:**

1. **009_result_validation** (Parent: 008_guardian)
   - Creates `result_submissions` table
   - Indexes for workflow queries

2. **010_diagnostic_system** (Parent: 009_result_validation)
   - Creates `diagnostic_runs` table
   - Indexes for monitoring queries

3. **011_validation_enhancement** (Parent: 010_diagnostic_system)
   - Creates `validation_reviews` table
   - Indexes for iteration tracking

**Linear chain:** 008→009→010→011

---

## Quick Start (Phase 6 Kickoff)

### Result Validation Squad Prompt

```
Implement Phase 6 Result Validation System.

Context:
- Phase 5 complete: Guardian, Memory, Cost, Quality available
- Phase gates exist but no workflow-level validation

Deliverables:
1. Create WorkflowResult model (result_submissions table)
2. Implement ResultSubmissionService:
   - submit_result(workflow_id, file_path, agent_id)
   - validate_result(submission_id, passed, feedback)
   - list_results(workflow_id)
   - apply_post_validation_action(on_result_found config)
3. Create /api/v1/results routes (3 endpoints)
4. Write 12 tests (submission, validation, versioning, termination)
5. Document in docs/result_validation/README.md

Follow schema conventions (String UUIDs, timezone-aware datetimes).
Target: 800 lines, 100% test pass rate.
```

### Diagnostic System Squad Prompt

```
Implement Phase 6 Diagnostic Agent System (Workflow Self-Healing).

Context:
- Phase 5 complete: Guardian, Memory, Cost, Quality available
- WorkflowResult tracking complete (Squad A)
- Need autonomous stuck workflow recovery

Deliverables:
1. Create DiagnosticRun model (diagnostic_runs table)
2. Implement StuckWorkflowDetector:
   - find_stuck_workflows() → check all conditions
   - Cooldown tracking (60s)
   - Stuck threshold (60s)
3. Implement DiagnosticService:
   - spawn_diagnostic_agent(ticket_id, context)
   - build_diagnostic_context(ticket_id) → rich prompt
   - track_diagnostic_run(run_id, tasks_created)
4. Implement EvidenceCollector (basic):
   - collect_task_history(ticket_id)
   - collect_validation_feedback(ticket_id)
   - search_memory_patterns(ticket_id)
5. Add monitoring loop integration (detect stuck every 60s)
6. Write 20 tests (detection, spawning, evidence, recovery)
7. Document in docs/diagnostic/README.md

Uses Memory for patterns, Guardian for emergency escalation.
Target: 1,500 lines, 90%+ coverage.
```

### Enhanced Validation Squad Prompt

```
Implement Phase 6 Enhanced Validation System.

Context:
- Phase 5 complete: Basic phase gates exist
- Diagnostic system complete (Squad B)
- Need iterative validation with feedback loops

Deliverables:
1. Create ValidationReview model (validation_reviews table)
2. Implement ValidationOrchestrator:
   - spawn_validator(task_id)
   - store_review(task_id, iteration, decision, feedback)
   - deliver_feedback(worker_agent_id, feedback)
   - check_repeated_failures(task_id) → threshold
   - escalate_to_diagnostic(task_id) when threshold exceeded
3. Enhance ValidationAgent (from placeholder):
   - LLM-based code review
   - Memory-assisted validation
   - Structured feedback generation
4. Create /api/v1/validation routes (review, feedback)
5. Write 15 tests (orchestration, iterations, escalation)
6. Document in docs/validation/README.md

Integrates with Diagnostic on repeated failures (3+ iterations).
Target: 1,100 lines, 85%+ coverage.
```

---

## Parallelization Strategy

### Optimal Execution

**Week 1:**
```
Squad A (Result Validation) — 5-6 hours
Squad C (Enhanced Validation) — Can start in parallel (12-15 hours)
  → Both use existing Phase 5 infrastructure
  → No dependencies between them
```

**Week 2-3:**
```
Squad B (Diagnostic System) — 15-18 hours
  → Waits for Squad A (needs WorkflowResult)
  → Squad C can continue in parallel
```

**Week 4:**
```
Integration Testing:
  - Test Result → Diagnostic flow
  - Test Diagnostic → Enhanced Validation flow
  - Test all 3 systems together
  - Merge to main
```

**Timeline Compression:**
- Sequential: 4 weeks
- Parallel: 2.5-3 weeks

---

## Event Types (New)

### Result Validation Events
- `result.submitted`
- `result.validated`
- `workflow.terminated` (on pass + stop_all)

### Diagnostic Events
- `diagnostic.stuck_detected`
- `diagnostic.agent_spawned`
- `diagnostic.tasks_created`
- `diagnostic.completed`

### Validation Events
- `validation.review_submitted`
- `validation.feedback_delivered`
- `validation.repeated_failure`
- `validation.escalated_to_diagnostic`

---

## API Endpoints (New)

### Result Validation (`/api/v1/results`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/submit` | Submit workflow result |
| POST | `/validate` | Validate result (validator-only) |
| GET | `/workflow/{id}` | List results for workflow |

### Diagnostic (`/api/v1/diagnostic`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/runs` | List diagnostic runs |
| GET | `/stuck-workflows` | List currently stuck workflows |
| POST | `/manual-trigger` | Manually trigger diagnostic |
| GET | `/runs/{id}` | Get diagnostic details |

### Enhanced Validation (`/api/v1/validation`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reviews/{task_id}` | Get review history |
| POST | `/feedback/{agent_id}` | Deliver feedback (internal) |
| GET | `/repeated-failures` | List tasks with repeated failures |

---

## Success Metrics

**Phase 6 delivers:**

1. **Autonomy:** Workflows recover from stuck states without human help
2. **Quality:** Iterative validation improves code quality
3. **Reliability:** Result validation ensures actual completion
4. **Intelligence:** Diagnostic learns from Memory patterns
5. **Visibility:** Full audit trail of recovery actions

**Transforms system from:**
- Task orchestrator → Autonomous self-healing workflow engine

---

## Next Steps

1. ✅ **Review this proposal**
2. ✅ **Confirm Phase 5 is complete**
3. 📋 **Create Phase 6 implementation plan**
4. 🚀 **Spawn 2-3 parallel squads**
5. 💪 **Build the intelligence layer**

---

**Ready to build Phase 6?** Use this document as the implementation spec! 🚀

