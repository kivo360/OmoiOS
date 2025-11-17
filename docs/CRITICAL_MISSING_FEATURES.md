# Critical Missing Features — What We Must Build Next

**TL;DR:** We're missing the **self-healing brain** that makes workflows autonomous.

---

## The #1 Most Critical Missing Piece

### 🚨 **Diagnostic Agent System**

**Why it's critical:**
Without it, workflows can get **silently stuck** and never recover.

**Real-world scenario:**
```
1. User creates ticket: "Build login system"
2. Agents create 15 tasks across 3 phases
3. All 15 tasks complete successfully ✅
4. Agents think they're done ✅
5. But... no one called submit_result() ❌
6. Workflow status = "stuck" forever
7. No one notices 😱
```

**With Diagnostic Agent:**
```
1-5. Same as above
6. System detects: "All tasks done but no validated result"
7. Waits 60s cooldown + 60s stuck time
8. Spawns Diagnostic Agent
9. Diagnostic analyzes: "Missing result submission"
10. Creates new task: "Submit final result with evidence"
11. Workflow resumes and completes ✅
```

**This is THE killer feature for autonomous workflows.**

---

## The Top 5 Critical Gaps (Priority Order)

### 1. 🚨 Diagnostic Agent System (P0 — BLOCKER)

**What it is:** Workflow self-healing system  
**Impact:** **HIGH** — Without it, workflows silently fail  
**Complexity:** ⭐⭐⭐⭐⭐  
**Estimated Effort:** 15-18 hours

**Key Missing Components:**
- `DiagnosticRun` model
- `StuckWorkflowDetector` service
- `DiagnosticService` with agent spawning
- `EvidenceCollector` for context gathering
- `HypothesisGenerator` for root cause analysis
- Monitoring loop integration
- Cooldown + stuck time tracking

**Why you MUST build this:**
It's the difference between:
- ❌ "Workflow stopped and I don't know why"
- ✅ "Workflow auto-recovered from missing result submission"

---

### 2. 📊 WorkflowResult Tracking (P0 — BLOCKER for Diagnostic)

**What it is:** Track final result submissions and validation  
**Impact:** **HIGH** — Diagnostic needs this to detect "no result" condition  
**Complexity:** ⭐⭐⭐  
**Estimated Effort:** 5-6 hours

**Key Missing Components:**
- `WorkflowResult` model (result_submissions table)
- `ResultSubmissionService`
- API endpoints for submit/validate/list
- Auto-termination logic (on_result_found: stop_all)
- Version tracking for multiple submissions

**Why you MUST build this:**
Without it, the system can't differentiate between:
- ❌ "Workflow is done (but no result submitted)"
- ✅ "Workflow has validated result ✓"

---

### 3. 🔄 Automatic Restart Orchestration (P1 — HIGH)

**What it is:** Auto-restart failed/unresponsive agents  
**Impact:** **MEDIUM-HIGH** — Improves reliability  
**Complexity:** ⭐⭐⭐⭐  
**Estimated Effort:** 8-10 hours

**Key Missing Components:**
- `RestartOrchestrator` service
- Escalation ladder (1→2→3 missed heartbeats)
- Graceful shutdown logic
- Task reassignment on restart
- Cooldown manager
- Max restart attempts (3/hour)

**Why you should build this:**
Current behavior:
- ❌ Agent dies → tasks stuck forever → manual intervention needed

With restart orchestration:
- ✅ Agent dies → auto-restart → tasks reassigned → workflow continues

---

### 4. 🎯 Enhanced Validation Orchestration (P1 — HIGH)

**What it is:** Full validation lifecycle with iterations  
**Impact:** **MEDIUM** — Improves code quality  
**Complexity:** ⭐⭐⭐⭐  
**Estimated Effort:** 12-15 hours

**Key Missing Components:**
- `ValidationReview` model with iterations
- `ValidationOrchestrator` service
- Validator agent spawning
- Feedback delivery to workers
- Repeated failure tracking
- Auto-spawn diagnostic on failures

**Why you should build this:**
Current: Basic phase gates (one-shot validation)  
Enhanced: Iterative review → feedback → fix → re-review cycle

---

### 5. 📈 Evidence Collection Infrastructure (P2 — MEDIUM)

**What it is:** Centralized log/metric/trace aggregation  
**Impact:** **MEDIUM** — Enables diagnosis  
**Complexity:** ⭐⭐⭐⭐⭐  
**Estimated Effort:** 10-12 hours

**Key Missing Components:**
- Centralized logging system
- Metrics store (Prometheus integration)
- Distributed tracing
- `EvidenceCollector` service
- Time-windowed queries

**Why you should build this:**
Diagnostic agents need **evidence** to diagnose failures.  
Without logs/metrics/traces, diagnosis is just guessing.

---

## What About The Rest?

### Not Critical (Can Wait)

**Anomaly Detection Service** (P2)
- We have basic monitoring
- Can add ML-based anomaly detection later
- Not blocking any workflows

**Escalation Service** (P2)
- Guardian handles manual escalation
- SEV mapping + notification nice-to-have
- Can build when needed

**Quarantine Protocol** (P3)
- Production hardening feature
- Not needed for development
- Build for production deployment

---

## Implementation Strategy

### Phase 6: "Workflow Intelligence" (4 weeks)

**Week 1: WorkflowResult System**
- Build result_submissions table
- Implement ResultSubmissionService
- Add API endpoints
- Write tests (12 tests)
- **Output:** Workflows can submit and validate results

**Week 2-3: Diagnostic Agent System**
- Build DiagnosticRun model
- Implement StuckWorkflowDetector
- Build DiagnosticService
- Add monitoring loop integration
- Write tests (20 tests)
- **Output:** Stuck workflows auto-recover

**Week 4: Enhanced Validation**
- Build ValidationReview model
- Implement ValidationOrchestrator
- Add validator agent spawning
- Integrate with Diagnostic
- Write tests (15 tests)
- **Output:** Full validation lifecycle

**Phase 6 Total:** ~35-40 hours (4 weeks)

---

### Phase 7: "Production Hardening" (6-8 weeks)

**Milestones:**
1. Automatic restart orchestration (2 weeks)
2. Evidence collection infrastructure (2 weeks)
3. Anomaly detection with ML (2 weeks)
4. Escalation + quarantine (1-2 weeks)

**Phase 7 Total:** ~50-60 hours (6-8 weeks)

---

## Quick Decision Matrix

| Question | Answer |
|----------|--------|
| Should we finish Phase 5 first? | **YES** — Cost + Quality squads in progress |
| Is Diagnostic Agent critical? | **YES** — Core autonomy feature |
| Should we build it in Phase 5? | **NO** — Too large, would delay other squads |
| When should we build it? | **Phase 6** — Right after Phase 5 |
| Can we ship without it? | **For dev/testing: YES. For production: NO.** |
| What's the minimum viable diagnostic? | WorkflowResult tracking + basic stuck detection |

---

## Minimum Viable Diagnostic (If We Must)

If you **absolutely need** diagnostic capabilities in Phase 5, here's the **bare minimum**:

**3-hour implementation:**

```python
# Add to existing MonitorService
class MonitorService:
    def check_stuck_workflows(self) -> List[str]:
        """Detect workflows with all tasks done but no result."""
        with self.db.get_session() as session:
            # Find tickets with all tasks completed
            stuck_tickets = session.query(Ticket).filter(
                Ticket.status != "done"
            ).all()
            
            stuck = []
            for ticket in stuck_tickets:
                # Check all tasks are done
                pending = session.query(Task).filter(
                    Task.ticket_id == ticket.id,
                    Task.status.in_(["pending", "running", "assigned"])
                ).count()
                
                if pending == 0:
                    # Check if stuck for >5 minutes
                    last_task = session.query(Task).filter(
                        Task.ticket_id == ticket.id
                    ).order_by(Task.completed_at.desc()).first()
                    
                    if last_task and last_task.completed_at:
                        time_stuck = (utc_now() - last_task.completed_at).total_seconds()
                        if time_stuck > 300:  # 5 minutes
                            stuck.append(ticket.id)
            
            return stuck

# Add to API
@router.get("/api/v1/monitoring/stuck-workflows")
def get_stuck_workflows():
    """List workflows that appear stuck."""
    monitor = get_monitor_service()
    return {"stuck_workflow_ids": monitor.check_stuck_workflows()}

# Add to monitoring loop (in main.py)
async def monitoring_loop():
    while True:
        stuck = monitor.check_stuck_workflows()
        if stuck:
            for workflow_id in stuck:
                event_bus.publish(SystemEvent(
                    event_type="workflow.stuck.detected",
                    entity_type="ticket",
                    entity_id=workflow_id,
                    payload={"stuck_duration_seconds": 300}
                ))
        await asyncio.sleep(60)  # Check every minute
```

**Pros:** Quick to implement, provides visibility  
**Cons:** No auto-recovery, no diagnostics, just detection

---

## Recommendation

### For Phase 5 (This Week)

✅ **FINISH PLANNED WORK:**
- Guardian Squad ✅ DONE
- Memory Squad ✅ DONE
- Cost Squad (Context 3)
- Quality Squad (Context 4)

🚫 **DO NOT ADD:**
- Diagnostic Agent (too large)
- Full fault tolerance (way too large)
- Enhanced validation (can wait)

---

### For Phase 6 (Next Month)

✅ **BUILD WORKFLOW INTELLIGENCE:**

**Milestone 1: Result Tracking** (Week 1)
- WorkflowResult model
- Result submission API
- Validation workflow
- 12 tests

**Milestone 2: Diagnostic System** (Weeks 2-3)
- DiagnosticRun model
- StuckWorkflowDetector
- DiagnosticService
- Evidence collector (basic)
- 20 tests

**Milestone 3: Enhanced Validation** (Week 4)
- ValidationReview model
- Validation orchestrator
- Feedback transport
- 15 tests

**Phase 6 Total:** 35-40 hours

---

### For Phase 7+ (Later)

✅ **PRODUCTION HARDENING:**
- Full fault tolerance
- Advanced evidence collection
- ML-based anomaly detection
- Escalation + quarantine
- ~50-60 hours

---

## Final Answer to Your Question

### "How far off is our diagnostic system from the original design?"

**Answer:** **100% gap** — We have **0% of the diagnostic system** implemented.

### "Are we missing anything extremely important?"

**Answer:** **YES** — The diagnostic agent is **the core autonomy feature**. Without it:
- Workflows can silently fail
- No auto-recovery from stuck states
- Requires manual intervention
- Defeats the purpose of "autonomous multi-agent orchestration"

**BUT** — We're not behind schedule. The diagnostic system was **never in Phase 5 scope**. It's a **Phase 6 feature** based on the comprehensive design docs.

---

## What You Should Do Right Now

1. ✅ **Finish Phase 5** — Don't add scope
2. 📋 **Plan Phase 6** — Use gap analysis to guide design
3. 🎯 **Prioritize** — Diagnostic Agent → WorkflowResult → Enhanced Validation
4. 🚀 **Build incrementally** — Foundation first, intelligence later

**You're doing great!** The Phase 3-5 foundation is solid. Keep going! 💪

