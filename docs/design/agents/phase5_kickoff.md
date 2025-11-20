# 🚀 Phase 5 Ready to Start — Use This in Parallel Tab

**Created**: 2025-11-20
**Status**: Active
**Purpose**: Provide a quick reference and coordination plan for parallel development of Phase 5 agent squads, including ownership, contracts, and success metrics.
**Related**: docs/PHASE5_PARALLEL_PLAN.md

---


**Comprehensive Plan:** See `docs/PHASE5_PARALLEL_PLAN.md`

## Quick Reference for Parallel Execution

### **3 Agents Can Start NOW (Day 1):**

1. **Guardian Agent Context:**
   - Implement emergency intervention system
   - 23 tests, ~1,200 lines
   - Uses: Phase 3 Registry + TaskQueue APIs
   - Prompt in PHASE5_PARALLEL_PLAN.md line 265

2. **Memory Agent Context:**
   - Implement pattern learning + embeddings
   - 30 tests, ~1,500 lines
   - Dependencies: `uv add sentence-transformers openai`
   - Prompt in PHASE5_PARALLEL_PLAN.md line 280

3. **Cost Tracking Agent Context:**
   - Implement LLM cost tracking + budgets
   - 18 tests, ~950 lines
   - Hooks: OpenHands conversation_stats
   - Prompt in PHASE5_PARALLEL_PLAN.md line 298

### **1 Agent Starts Later (Day 3):**

4. **Quality Gates Agent Context:**
   - Wait for Memory patterns to stabilize
   - 22 tests, ~1,200 lines
   - Extends: Phase 2 PhaseGateService
   - Prompt in PHASE5_PARALLEL_PLAN.md line 312

---

## File Ownership (Zero Conflicts)

✅ **Guardian:** guardian_action.py, guardian.py, test_guardian*.py
✅ **Memory:** task_memory.py, learned_pattern.py, memory.py, test_memory*.py  
✅ **Cost:** cost_record.py, budget.py, cost_tracking.py, test_cost*.py
✅ **Quality:** quality_metric.py, quality_checker.py, test_quality*.py

**No overlap** — safe for parallel development!

---

## Integration Contracts

### Memory Squad Exports (for Quality)
```python
# omoi_os/services/memory.py
@dataclass
class TaskPattern:
    pattern_id: str
    task_type_pattern: str
    success_indicators: List[str]
    failure_indicators: List[str]
    confidence_score: float

def search_patterns(task_type: str, limit: int = 5) -> List[TaskPattern]:
    """Quality Squad calls this to get patterns for prediction."""
    pass
```

### All Squads Use (From Phase 3)
- `DatabaseService` — DB access
- `EventBusService` — Event publishing
- `AgentRegistryService` — Agent lookup
- `TaskQueueService` — Task operations

---

## Success Metrics

**Phase 5 Complete:**
- 93 new tests passing (total: 264 tests)
- Guardian can override any operation
- Memory suggests context for 80%+ similar tasks
- Cost tracking captures all LLM spend
- Quality gates predict issues before execution

**Timeline:**
- Parallel: 2-3 weeks
- Sequential: 4 weeks
- Savings: 40-50%

---

**Copy the prompts from PHASE5_PARALLEL_PLAN.md and start 3 contexts now!** 🎯
