# Diagnostic Agent System — Gap Analysis

**Date:** 2025-11-17  
**Analyzed By:** Context 1 (Guardian Squad)  
**Status:** SIGNIFICANT GAPS IDENTIFIED

---

## Executive Summary

After comparing our current implementation against the comprehensive design documents in `docs/design/` and `docs/requirements/`, we are **missing the entire Diagnostic Agent System**.

### Current Implementation State

**✅ What We Have (Phase 3-5):**
- Guardian Agent emergency intervention (Phase 5) ✅
- Memory & pattern learning system (Phase 5) ✅  
- Cost tracking & budgets (Phase 5) ✅
- Basic monitoring (MonitorAnomaly, Alert models) 🟡
- Phase gates with validation results 🟡
- Task queue with dependency management ✅
- Agent registry with health monitoring ✅
- Event bus for pub/sub ✅

**❌ What We're Missing (Critical):**
1. **Diagnostic Agent System** — Workflow doctor for stuck/failed workflows
2. **DiagnosisReport** model and persistence
3. **diagnostic_runs** tracking table
4. **Stuck workflow detection** logic
5. **Evidence collection** from logs/metrics/traces
6. **Hypothesis generation** for root cause analysis
7. **Automatic diagnostic task creation** (1-5 recovery tasks)
8. **WorkflowResult** validation tracking
9. **Cooldown + stuck time** threshold enforcement
10. **Full fault tolerance system** (restart, anomaly, escalation, quarantine)

---

## Gap Analysis by Component

### SECTION 1 — Core Diagnostic System ❌ NOT IMPLEMENTED

**Design Specification (from diagnosis_agent.md):**

The Diagnostic Agent is a "workflow doctor" that:
- Detects workflows where all tasks are complete but no validated result exists
- Waits for cooldown (60s) + stuck time (60s) thresholds
- Gathers rich context (recent agents, tasks, conductor logs, validation feedback)
- Analyzes goal vs. reality gap
- Creates 1-5 new tasks to resume workflow
- Tracks interventions in `diagnostic_runs` table

**Current Status:** ❌ **NOT IMPLEMENTED**

**What We Have:**
- None of this exists in our codebase

**What We Need:**

```python
# Missing Model
class DiagnosticRun(Base):
    __tablename__ = "diagnostic_runs"
    
    id: Mapped[str]
    workflow_id: Mapped[str]  # ticket_id in our system
    diagnostic_agent_id: Mapped[Optional[str]]
    diagnostic_task_id: Mapped[Optional[str]]
    triggered_at: Mapped[datetime]
    total_tasks_at_trigger: Mapped[int]
    done_tasks_at_trigger: Mapped[int]
    failed_tasks_at_trigger: Mapped[int]
    time_since_last_task_seconds: Mapped[int]
    tasks_created_count: Mapped[int]
    tasks_created_ids: Mapped[Optional[dict]]  # JSONB
    completed_at: Mapped[Optional[datetime]]
    status: Mapped[str]  # created, running, completed, failed
    workflow_goal: Mapped[Optional[str]]
    phases_analyzed: Mapped[Optional[dict]]  # JSONB
    agents_reviewed: Mapped[Optional[dict]]  # JSONB
    diagnosis: Mapped[Optional[str]]

# Missing Service
class DiagnosticService:
    def detect_stuck_workflows(self) -> List[str]:
        """Find workflows that are stuck."""
        pass
    
    def should_trigger_diagnostic(self, ticket_id: str) -> bool:
        """Check if diagnostic should trigger based on thresholds."""
        pass
    
    def spawn_diagnostic_agent(self, ticket_id: str) -> DiagnosticRun:
        """Spawn diagnostic agent with rich context."""
        pass
    
    def build_diagnostic_context(self, ticket_id: str) -> dict:
        """Gather context for diagnostic agent."""
        pass
```

**Estimated Effort:** 10-12 hours (large scope)

---

### SECTION 2 — Evidence Collection ❌ NOT IMPLEMENTED

**Design Specification (from diagnosis_agent.md):**

Evidence Collector pulls data from multiple sources:
- Recent logs within time window
- Metrics (Prometheus/similar)
- Distributed traces
- Validation feedback
- Anomaly/quarantine context from monitoring
- Prior related incidents from Memory System

**Current Status:** ❌ **NOT IMPLEMENTED**

**What We Have:**
- Memory System can search similar tasks ✅
- MonitorAnomaly model exists 🟡 (but no collector service)
- No centralized log/metric/trace collection

**What We Need:**

```python
class EvidenceCollector:
    def collect_evidence(
        self,
        subject_type: str,  # "task" or "ticket"
        subject_id: str,
        window_minutes: int = 60,
    ) -> EvidenceBundle:
        """Collect all evidence for diagnosis."""
        return EvidenceBundle(
            logs=self._collect_logs(subject_id, window_minutes),
            metrics=self._collect_metrics(subject_id, window_minutes),
            traces=self._collect_traces(subject_id, window_minutes),
            validation_feedback=self._get_validation_feedback(subject_id),
            anomalies=self._get_related_anomalies(subject_id),
            memory_matches=self._search_memory(subject_id),
        )
```

**Dependencies:**
- Centralized logging (currently missing)
- Metrics store integration (currently missing)
- Distributed tracing (currently missing)

**Estimated Effort:** 8-10 hours

---

### SECTION 3 — Hypothesis Generation ❌ NOT IMPLEMENTED

**Design Specification:**

Hypothesis Generator/Evaluator:
- Generates ranked hypotheses from diagnosis dossier
- Uses LLM or heuristics
- Configurable `max_hypotheses` (default 5)
- Ranks by likelihood score

**Current Status:** ❌ **NOT IMPLEMENTED**

**What We Need:**

```python
class HypothesisGenerator:
    def generate_hypotheses(
        self,
        dossier: DiagnosisDossier,
        max_hypotheses: int = 5,
    ) -> List[Hypothesis]:
        """Generate and rank failure hypotheses."""
        pass

@dataclass
class Hypothesis:
    description: str
    likelihood_score: float  # 0.0-1.0
    supporting_evidence: List[str]
    proposed_tests: List[str]
```

**Estimated Effort:** 6-8 hours

---

### SECTION 4 — Workflow Result Validation ❌ PARTIALLY IMPLEMENTED

**Design Specification (from result_submission.md):**

System should track:
- WorkflowResult submissions
- Result validation status
- Validated vs. non-validated workflows
- Auto-termination on validated result (if configured)

**Current Status:** 🟡 **PARTIAL**

**What We Have:**
- `PhaseGateResult` model ✅ (per-phase validation)
- Phase gate validation service ✅
- Validation agent placeholder ✅

**What We're Missing:**
- **WorkflowResult** model (distinct from phase gates)
- **result_submissions** table (append-only, versioned)
- **Workflow-level validation** (beyond phase validation)
- **Auto-termination** on validated result
- **Result criteria** configuration per workflow

**Gap:**

```python
# Missing Model
class WorkflowResult(Base):
    __tablename__ = "workflow_results"
    
    submission_id: Mapped[str]  # PK
    workflow_id: Mapped[str]  # ticket_id
    agent_id: Mapped[str]
    markdown_file_path: Mapped[str]
    created_at: Mapped[datetime]
    
    # Validation metadata
    validated_at: Mapped[Optional[datetime]]
    passed: Mapped[Optional[bool]]
    feedback: Mapped[Optional[str]]
    evidence_index: Mapped[Optional[dict]]  # JSONB
    
    # Versioning
    version: Mapped[int]
    result_criteria_snapshot: Mapped[str]
    status: Mapped[str]  # submitted, validated
```

**Estimated Effort:** 5-6 hours

---

### SECTION 5 — Stuck Detection Logic ❌ NOT IMPLEMENTED

**Design Specification (from user's design doc):**

Activation conditions:
1. Workflow exists
2. Has tasks
3. All tasks finished (no pending/assigned/in_progress/under_review/validation_in_progress)
4. No validated result exists
5. Cooldown passed (60s)
6. Stuck time met (60s since last task activity)

**Current Status:** ❌ **NOT IMPLEMENTED**

**What We Have:**
- Task status tracking ✅
- Ticket status tracking ✅

**What We're Missing:**
- Monitoring loop that checks for stuck workflows
- Cooldown tracking between diagnostic interventions
- Last activity timestamp tracking
- Stuck threshold configuration

**Gap:**

```python
class StuckWorkflowDetector:
    def __init__(
        self,
        cooldown_seconds: int = 60,
        stuck_threshold_seconds: int = 60,
    ):
        self.cooldown = cooldown_seconds
        self.stuck_threshold = stuck_threshold_seconds
        self._last_diagnostic = {}  # workflow_id -> timestamp
    
    def find_stuck_workflows(self) -> List[str]:
        """Find workflows meeting all stuck conditions."""
        stuck = []
        
        with db.get_session() as session:
            # Find workflows with all tasks done
            tickets = session.query(Ticket).filter(
                Ticket.status != "done"
            ).all()
            
            for ticket in tickets:
                if self._is_stuck(session, ticket):
                    stuck.append(ticket.id)
        
        return stuck
    
    def _is_stuck(self, session, ticket: Ticket) -> bool:
        """Check if ticket meets stuck criteria."""
        # Check all tasks are finished
        pending_tasks = session.query(Task).filter(
            Task.ticket_id == ticket.id,
            Task.status.in_([
                "pending", "assigned", "running",
                "under_review", "validation_in_progress"
            ])
        ).count()
        
        if pending_tasks > 0:
            return False
        
        # Check no validated result
        validated_result = session.query(WorkflowResult).filter(
            WorkflowResult.workflow_id == ticket.id,
            WorkflowResult.status == "validated",
            WorkflowResult.passed == True
        ).first()
        
        if validated_result:
            return False
        
        # Check cooldown
        if ticket.id in self._last_diagnostic:
            time_since_last = (utc_now() - self._last_diagnostic[ticket.id]).total_seconds()
            if time_since_last < self.cooldown:
                return False
        
        # Check stuck time
        last_task = session.query(Task).filter(
            Task.ticket_id == ticket.id
        ).order_by(Task.completed_at.desc()).first()
        
        if last_task and last_task.completed_at:
            time_since_activity = (utc_now() - last_task.completed_at).total_seconds()
            return time_since_activity >= self.stuck_threshold
        
        return False
```

**Estimated Effort:** 4-5 hours

---

### SECTION 6 — Full Fault Tolerance System ❌ MOSTLY NOT IMPLEMENTED

**Design Specification (from fault_tolerance.md):**

Comprehensive fault tolerance with 5 subsystems:

1. **Heartbeat Detection Layer**
   - Bidirectional heartbeats
   - TTL thresholds (idle: 30s, running: 15s, monitor: 15s)
   - Sequence gap detection
   - Clock tolerance (2s skew)

2. **Automatic Restart Service**
   - Escalation ladder (warn → degraded → unresponsive → restart)
   - Graceful stop (10s) → force terminate
   - Spawn replacement agent
   - Reassign incomplete tasks
   - Cooldown manager (60s)
   - Max attempts tracking (3 per hour)

3. **Anomaly Detection Service**
   - Baseline learning per agent-type/phase
   - Composite anomaly scoring (latency, error rate, resource, queue impact)
   - False positive guard (3 consecutive readings)
   - Threshold: 0.8

4. **Escalation Service**
   - Severity mapping (SEV-1/2/3)
   - Notification matrix
   - Human-in-the-loop for SEV-1 (5min SLA)

5. **Quarantine Service**
   - Agent isolation
   - Forensics collection
   - Clearance validation

**Current Status:** 🟡 **10% IMPLEMENTED**

**What We Have:**
- Basic heartbeat tracking in AgentHealthService ✅ (30s intervals, stale detection 90s)
- MonitorAnomaly model ✅ (but no detection service)
- Alert model ✅ (but no alert generation)

**What We're Missing:**
- 90% of the fault tolerance architecture
- Automatic restart orchestration
- Anomaly detection with baseline learning
- Escalation ladder and severity mapping
- Quarantine protocol
- Integration with diagnostic agent spawning

**Estimated Effort:** 20-25 hours (Phase 6 scope?)

---

### SECTION 7 — Validation System ❌ PARTIALLY IMPLEMENTED

**Design Specification (from validation_system.md):**

Comprehensive validation orchestration:
- Task validation states (under_review, validation_in_progress, needs_work)
- Validator agent spawning
- ValidationReview persistence (iterations tracked)
- Feedback delivery to worker agents
- Memory integration for validation history
- Diagnosis integration on repeated failures
- Git commit creation per validation iteration

**Current Status:** 🟡 **30% IMPLEMENTED**

**What We Have:**
- `PhaseGateResult` model ✅ (stores validation outcomes)
- `ValidationAgent` placeholder class ✅ (minimal)
- Phase gate validation service ✅

**What We're Missing:**
- `ValidationReview` model with iteration tracking
- Validation state machine integration with Task states
- Validator agent spawning logic
- Feedback transport to worker agents
- Repeated failure threshold tracking
- Auto-spawn diagnosis on validation failures
- Git commit creation per review iteration

**Estimated Effort:** 12-15 hours

---

## Critical Missing Pieces (Priority Order)

### Priority 1 — Diagnostic Agent System (Highest Impact)

**What:** Workflow self-healing system  
**Complexity:** ⭐⭐⭐⭐⭐ (Very High)  
**Dependencies:** WorkflowResult tracking, Memory System ✅, Phase Gates ✅  
**Estimated Effort:** 15-18 hours

**Components to Build:**

1. **Models** (3 hours):
   - `DiagnosticRun` — Track diagnostic interventions
   - `WorkflowResult` — Track final result submissions
   - Migration 009_diagnostic_system

2. **Services** (8 hours):
   - `StuckWorkflowDetector` — Find stuck workflows
   - `DiagnosticService` — Spawn diagnostic agents, track runs
   - `EvidenceCollector` — Gather context for diagnosis
   - `HypothesisGenerator` — Root cause analysis

3. **Monitoring Loop** (3 hours):
   - Background task to detect stuck workflows
   - Cooldown tracking
   - Diagnostic agent spawning

4. **Tests** (4 hours):
   - 20+ tests covering detection, spawning, context gathering
   - Integration tests with Memory + Guardian

**Deliverables:**
```
omoi_os/models/diagnostic_run.py
omoi_os/models/workflow_result.py
omoi_os/services/diagnostic.py
omoi_os/services/evidence_collector.py
omoi_os/services/hypothesis_generator.py
migrations/versions/009_diagnostic_system.py
tests/test_diagnostic.py (20+ tests)
docs/diagnostic/README.md
```

---

### Priority 2 — Workflow Result Tracking (Blocks Diagnostic)

**What:** System for tracking final workflow results and validation  
**Complexity:** ⭐⭐⭐ (Medium)  
**Dependencies:** Validation agent, Phase gates ✅  
**Estimated Effort:** 5-6 hours

**Components to Build:**

1. **Model:**
   - `WorkflowResult` (result_submissions table)
   - Append-only, versioned submissions

2. **Service:**
   - `ResultSubmissionService` — Submit, validate, list results
   - Auto-termination logic (on_result_found: stop_all)

3. **API:**
   - `POST /api/v1/results/submit`
   - `POST /api/v1/results/validate`
   - `GET /api/v1/workflows/{id}/results`

**Deliverables:**
```
omoi_os/models/workflow_result.py
omoi_os/services/result_submission.py
omoi_os/api/routes/results.py
tests/test_result_submission.py (12 tests)
```

---

### Priority 3 — Enhanced Validation System (Improves Quality)

**What:** Full validation orchestration with iterations  
**Complexity:** ⭐⭐⭐⭐ (Medium-High)  
**Dependencies:** Validator agents, Memory ✅, Diagnostic ✅ (for escalation)  
**Estimated Effort:** 12-15 hours

**Components to Build:**

1. **Models:**
   - `ValidationReview` — Track review iterations
   - Extend Task with validation states

2. **Services:**
   - `ValidationOrchestrator` — Spawn validators, manage reviews
   - `FeedbackTransport` — Deliver feedback to workers
   - Integration with Diagnosis on failures

3. **Validator Agent:**
   - Upgrade from placeholder to full implementation
   - LLM-based code review logic
   - Memory-assisted validation

**Deliverables:**
```
omoi_os/models/validation_review.py
omoi_os/services/validation_orchestrator.py
omoi_os/services/feedback_transport.py
Enhance: omoi_os/services/validation_agent.py
tests/test_validation_orchestrator.py (15 tests)
```

---

### Priority 4 — Full Fault Tolerance (Production Hardening)

**What:** Complete heartbeat/restart/anomaly/escalation/quarantine system  
**Complexity:** ⭐⭐⭐⭐⭐ (Very High)  
**Dependencies:** Agent registry ✅, Diagnostic ✅, Guardian ✅  
**Estimated Effort:** 20-25 hours (Phase 6+)

**Major Components Missing:**

1. **Heartbeat Detection Layer:**
   - Bidirectional acknowledgments
   - Sequence number gap detection
   - Clock synchronization tolerance

2. **Automatic Restart:**
   - Escalation ladder (1→2→3 missed = restart)
   - Graceful shutdown logic
   - Task reassignment
   - Max restart attempts (3/hour)

3. **Anomaly Detection:**
   - Baseline learning
   - Composite scoring (latency, error, resource, queue)
   - False positive guard (3 consecutive readings)

4. **Escalation:**
   - SEV-1/2/3 mapping
   - Notification matrix
   - Human-in-the-loop SLA enforcement

5. **Quarantine:**
   - Agent isolation
   - Forensics collection
   - Clearance validation

**This is MASSIVE scope** — Likely Phase 6-7 material.

---

## Implementation Roadmap

### Short-Term (Phase 5 Completion)

**Goal:** Complete planned Phase 5 features

**Remaining:**
- ✅ Guardian Squad (Context 1) — DONE
- ✅ Memory Squad (Context 2) — DONE  
- 🔄 Cost Squad (Context 3) — Schema fixed, in progress
- ⏳ Quality Squad (Context 4) — Waiting on Memory patterns

**Do NOT add Diagnostic yet** — It's beyond Phase 5 scope.

---

### Medium-Term (Phase 6 Proposal)

**Goal:** Add workflow self-healing

**Milestones:**

1. **Week 13-14: Workflow Result System**
   - WorkflowResult model + API
   - Result submission flow
   - Auto-termination logic
   - Integration with Memory
   - **Deliverable:** Results can be submitted and validated

2. **Week 15-17: Diagnostic Agent System**
   - DiagnosticRun model
   - StuckWorkflowDetector
   - DiagnosticService
   - Evidence collection (basic)
   - Hypothesis generation (basic)
   - **Deliverable:** Stuck workflows automatically spawn diagnostic agents

3. **Week 18-19: Enhanced Validation**
   - ValidationReview model
   - Validation orchestrator
   - Feedback transport
   - Diagnosis integration on failures
   - **Deliverable:** Full validation lifecycle with auto-recovery

---

### Long-Term (Phase 7+)

**Goal:** Production-grade fault tolerance

**Milestones:**

1. **Heartbeat & Restart System** (3-4 weeks)
   - Full bidirectional heartbeats
   - Automatic restart orchestration
   - Task reassignment
   - Cooldown management

2. **Anomaly Detection** (2-3 weeks)
   - Baseline learning
   - Composite scoring
   - False positive guards
   - Alert generation

3. **Escalation & Quarantine** (2 weeks)
   - Severity mapping
   - Notification matrix
   - Quarantine protocol
   - Forensics collection

**Total Estimated:** 7-9 weeks additional work

---

## Comparison: Design Spec vs. Current State

| System Component | Design Spec | Current | Gap |
|------------------|-------------|---------|-----|
| **Diagnostic Agent** | Full workflow doctor system | None | ❌ 100% |
| **WorkflowResult Tracking** | Versioned, validated results | Phase gates only | ❌ 70% |
| **Stuck Detection** | Cooldown + threshold monitoring | None | ❌ 100% |
| **Evidence Collection** | Multi-source (logs/metrics/traces) | Memory only | ❌ 80% |
| **Hypothesis Generation** | LLM-based root cause analysis | None | ❌ 100% |
| **Fault Tolerance** | 5-subsystem architecture | Basic heartbeats | ❌ 90% |
| **Validation Orchestration** | Full lifecycle with iterations | Basic phase gates | ❌ 60% |
| **Guardian Integration** | Escalation from diagnostic | Guardian exists | 🟡 50% |
| **Memory Integration** | Evidence + hypothesis storage | Search available | ✅ 80% |

**Overall Implementation:** ~25% of full design specification

---

## Recommendations

### For Phase 5 (Current)

✅ **STAY FOCUSED** — Complete the planned 4 squads:
1. Guardian ✅ DONE
2. Memory ✅ DONE  
3. Cost (schema fixed, waiting on Context 3)
4. Quality (waiting on Memory patterns)

**Do NOT** add Diagnostic yet — it's too large for parallel execution.

---

### For Phase 6 (Proposed)

**New Phase: "Workflow Intelligence & Self-Healing"**

**Scope:**
1. WorkflowResult tracking system (5-6 hours)
2. Diagnostic Agent system (15-18 hours)
3. Enhanced validation orchestration (12-15 hours)

**Total Effort:** 32-39 hours (~1 month)

**Parallelization:** Could split into 2-3 parallel squads:
- Squad A: WorkflowResult + basic validation enhancement
- Squad B: Diagnostic system
- Squad C: Evidence collection + hypothesis generation

---

### For Phase 7+ (Future)

**New Phase: "Production Fault Tolerance"**

**Scope:** Full fault tolerance architecture from design docs

**Total Effort:** 50-60 hours (~2-3 months)

---

## Summary: How Far Off Are We?

### Brutal Honesty Assessment

**Current State:**
- We have a **solid foundation** (registry, queue, events, memory, guardian)
- We have **basic monitoring** (anomalies, alerts)
- We have **basic validation** (phase gates)

**Missing:**
- **Diagnostic Agent System** (the "workflow doctor") — **0% implemented**
- **Workflow Result Validation** (beyond phase gates) — **30% implemented**
- **Full Fault Tolerance** (restart, anomaly, quarantine) — **10% implemented**
- **Enhanced Validation** (iterations, feedback) — **30% implemented**

### The Gap in Numbers

**Design Document Scope:** ~150-200 hours of work  
**Current Implementation:** ~40-50 hours delivered  
**Completion Percentage:** ~25-30%

### What's Missing That's CRITICAL

The user's design doc describes a **self-healing workflow system** where:
1. Workflows detect they're stuck
2. Diagnostic agents analyze the gap
3. Recovery tasks are created automatically
4. The workflow resumes without human intervention

**We have NONE of this.**

What we have is:
- The **building blocks** (tasks, agents, events, memory)
- **Emergency intervention** (Guardian can manually intervene)
- **Pattern learning** (Memory learns from past tasks)

But we're missing the **intelligence layer** that:
- Detects problems automatically
- Analyzes root causes
- Generates recovery plans
- Executes fixes autonomously

---

## Action Items

### Immediate (Phase 5)
1. ✅ Finish Guardian Squad (DONE)
2. ✅ Finish Memory Squad (DONE)
3. ⏳ Finish Cost Squad (waiting on Context 3)
4. ⏳ Finish Quality Squad (waiting on Context 4)

### Phase 6 Proposal
1. Create Phase 6 design document
2. Break down Diagnostic System into squads
3. Implement WorkflowResult tracking first (foundation)
4. Build Diagnostic Agent on top of Memory + Guardian
5. Add enhanced validation with iterations

### Phase 7+ 
1. Full fault tolerance implementation
2. Production hardening
3. Advanced anomaly detection with ML
4. Complete observability suite

---

**Bottom Line:**

We're building an **excellent multi-agent orchestration platform**, but we're missing the **self-healing diagnostic layer** that makes workflows truly autonomous. The good news: **our Phase 3-5 foundation is solid** and provides all the primitives needed to build the diagnostic system on top.

**Recommendation:** Finish Phase 5, then propose Phase 6 for Diagnostic + Workflow Intelligence.

