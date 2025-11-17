# Phase 5 Parallel Implementation Plan — Advanced Features

**Created**: 2025-11-17  
**Status**: READY TO START  
**Timeline**: Weeks 9-12 (4 weeks, but can parallelize to 2-3 weeks)  
**Prerequisite**: Phase 3 complete ✅ (Phase 4 optional, independent)

---

## Executive Summary

Phase 5 adds production-ready advanced features:
1. **Guardian Agent** — Emergency intervention and resource reallocation
2. **Memory & Learning** — Pattern recognition from past task executions
3. **Cost Tracking** — LLM API cost monitoring and budgeting
4. **Quality Gates** — Advanced validation and quality metrics

**Parallelization Potential:** ⭐⭐⭐⭐⭐ (90% independent)

---

## Dependency Analysis

```
Phase 3 (✅ COMPLETE)
  │
  ├─→ Guardian Agent (Week 9) ────────────┐ [INDEPENDENT]
  ├─→ Memory System (Week 10) ────────────┤ [INDEPENDENT]
  ├─→ Cost Tracking (Week 11) ────────────┤ [INDEPENDENT]
  └─→ Quality Gates (Week 12) ───────────→│ [Needs Memory patterns]
                                           │
                                           └─→ Phase 6
```

**Critical Path:** Memory → Quality Gates (1-week dependency)  
**Fully Parallel:** Guardian, Memory, Cost Tracking can all start Day 1

---

## Squad Assignments (4 Milestones as Squads)

### 🔴 **Guardian Squad** (Week 9 — Can Start: Day 1)

**Dependencies:** Phase 3 Registry APIs ✅  
**Blocks:** None (independent)  
**Complexity:** ⭐⭐⭐⭐ (Medium-High)

**Scope:**
- Emergency intervention system for critical failures
- Resource reallocation (steal capacity from low-priority work)
- Authority hierarchy (Guardian > Watchdog > Worker)
- Intervention policies (YAML configs)
- Audit trail for all guardian actions

**Deliverables:**
```
Files to Create:
  • omoi_os/models/guardian_action.py (intervention audit log)
  • omoi_os/services/guardian.py (intervention logic)
  • omoi_os/config/guardian_policies/*.yaml (3 policy examples)
  • omoi_os/api/routes/guardian.py (manual intervention API)
  • tests/test_guardian.py (15 tests)
  • tests/test_guardian_policies.py (8 tests)
  • docs/guardian/README.md

Migration 006_guardian:
  • guardian_actions table (id, action_type, target_entity, authority_level, 
    reason, initiated_by, approved_by, executed_at, reverted_at, audit_log JSONB)

Integration Points:
  • Uses AgentRegistryService to find/reassign agents
  • Publishes guardian.intervention.* events
  • Can cancel running tasks via TaskQueueService
  • Integrates with Phase 4 Watchdog (if available) for escalation
```

**Key Features:**
- Emergency task cancellation
- Agent capacity reallocation
- Priority queue override
- Automatic rollback after crisis
- Authority validation (only Guardian can override)

**Test Scenarios:**
- Critical task stuck → Guardian reallocates resources
- Agent failure → Guardian spawns replacement
- Queue overflow → Guardian pauses low-priority work
- Authority validation → Non-guardian actions rejected

**Estimated Effort:** 6-8 hours

---

### 🧠 **Memory Squad** (Week 10 — Can Start: Day 1, Independent)

**Dependencies:** None (pure addition)  
**Blocks:** Quality Gates squad (provides patterns)  
**Complexity:** ⭐⭐⭐⭐⭐ (High — ML/embedding work)

**Scope:**
- Pattern recognition from completed tasks
- Success/failure pattern storage
- Context retrieval for similar tasks
- Embedding-based similarity search (pgvector already installed!)
- Learning from execution history

**Deliverables:**
```
Files to Create:
  • omoi_os/models/task_memory.py (memory record with embeddings)
  • omoi_os/models/learned_pattern.py (pattern templates)
  • omoi_os/services/memory.py (storage, retrieval, pattern extraction)
  • omoi_os/services/embedding.py (text → vector via OpenAI/local model)
  • omoi_os/api/routes/memory.py (search similar tasks, view patterns)
  • tests/test_memory.py (12 tests)
  • tests/test_pattern_learning.py (10 tests)
  • tests/test_similarity_search.py (8 tests)
  • docs/memory/README.md

Migration 006_memory_learning:
  • task_memories table (id, task_id, execution_summary, context_embedding vector(1536),
    success, error_patterns JSONB, learned_at, reused_count)
  • learned_patterns table (id, pattern_type, task_type_pattern, success_indicators JSONB,
    failure_indicators JSONB, embedding vector(1536), confidence_score, usage_count)
  • Vector similarity indexes (ivfflat or hnsw)

Integration Points:
  • Reads completed tasks from TaskQueueService
  • Provides context suggestions to new tasks
  • Embeddings via OpenAI API or local sentence-transformers
  • Similarity search returns top-K similar past tasks
```

**Key Features:**
- Automatic pattern extraction from task results
- Embedding-based similarity search (`pgvector`)
- Success/failure indicator learning
- Context suggestion for new tasks
- Pattern confidence scoring

**Embedding Options:**
1. **OpenAI** (`text-embedding-3-small`) — High quality, API cost
2. **Local** (`sentence-transformers/all-MiniLM-L6-v2`) — Free, lower quality
3. **Hybrid** — OpenAI for production, local for dev/test

**Test Scenarios:**
- Execute 10 similar tasks → Pattern emerges
- New task arrives → Memory suggests context from past success
- Failure pattern detected → Warning issued
- Embedding similarity search → Returns top-5 similar tasks

**Estimated Effort:** 8-10 hours (embedding integration adds complexity)

---

### 💰 **Cost Tracking Squad** (Week 11 — Can Start: Day 1, Independent)

**Dependencies:** None (reads existing events)  
**Blocks:** None  
**Complexity:** ⭐⭐⭐ (Medium)

**Scope:**
- LLM API cost tracking (OpenAI, Anthropic, etc.)
- Budget enforcement and alerts
- Cost attribution (per ticket, per agent, per phase)
- Cost forecasting based on historical usage
- Cost optimization recommendations

**Deliverables:**
```
Files to Create:
  • omoi_os/models/cost_record.py (LLM API call costs)
  • omoi_os/models/budget.py (budget limits and alerts)
  • omoi_os/services/cost_tracking.py (cost calculation, attribution)
  • omoi_os/services/budget_enforcer.py (budget limit checks)
  • omoi_os/api/routes/costs.py (cost reports, budgets)
  • omoi_os/config/cost_models.yaml (pricing for different LLM providers)
  • tests/test_cost_tracking.py (10 tests)
  • tests/test_budget_enforcement.py (8 tests)
  • docs/cost_tracking/README.md

Migration 007_cost_tracking:
  • cost_records table (id, task_id, agent_id, provider, model, 
    prompt_tokens, completion_tokens, total_cost, recorded_at)
  • budgets table (id, scope_type (ticket/agent/phase), scope_id, 
    limit_amount, spent_amount, period_start, period_end, alert_threshold)

Integration Points:
  • Hooks into AgentExecutor to capture OpenHands conversation stats
  • Subscribes to TASK_COMPLETED events to extract cost data
  • Publishes cost.budget.exceeded events
  • Provides cost dashboard via API
```

**Key Features:**
- Real-time cost tracking per API call
- Budget limits (per ticket, agent, phase, or global)
- Cost attribution and reporting
- Budget alerts before overrun
- Cost forecasting (based on queue depth + avg cost)

**LLM Provider Support:**
- OpenAI (GPT-4, GPT-3.5, embeddings)
- Anthropic (Claude Sonnet, Opus, Haiku)
- Configurable via `cost_models.yaml`

**Test Scenarios:**
- Task completes → Cost record created
- Budget 80% consumed → Warning alert
- Budget exceeded → Task queue paused
- Cost report → Shows breakdown by phase/agent

**Estimated Effort:** 5-6 hours

---

### ✅ **Quality Gates Squad** (Week 12 — Can Start: Week 10 Day 3)

**Dependencies:** Memory patterns (2-day delay from Memory Squad)  
**Blocks:** None  
**Complexity:** ⭐⭐⭐⭐ (Medium-High)

**Scope:**
- Advanced quality validation beyond phase gates
- Code quality metrics (test coverage, lint scores, complexity)
- Learning-based quality prediction
- Quality trend analysis
- Automated quality improvement suggestions

**Deliverables:**
```
Files to Create:
  • omoi_os/models/quality_metric.py (quality measurements)
  • omoi_os/models/quality_gate.py (advanced gate definitions)
  • omoi_os/services/quality_checker.py (quality validation logic)
  • omoi_os/services/quality_predictor.py (uses Memory patterns)
  • omoi_os/api/routes/quality.py (quality reports, gates)
  • omoi_os/config/quality_gates/*.yaml (gate definitions)
  • tests/test_quality_checker.py (12 tests)
  • tests/test_quality_predictor.py (10 tests)
  • docs/quality/README.md

Migration 008_quality_gates:
  • quality_metrics table (id, task_id, metric_type, metric_name, 
    value, threshold, passed, measured_at)
  • advanced_quality_gates table (id, phase_id, gate_type, requirements JSONB,
    predictor_model, enabled)

Integration Points:
  • Consumes Memory patterns to predict quality
  • Extends Phase 2 PhaseGateService
  • Analyzes task results for quality signals
  • Publishes quality.gate.failed events
```

**Key Features:**
- Code coverage requirements
- Lint score thresholds
- Cyclomatic complexity limits
- Test pass rate requirements
- ML-based quality prediction (uses Memory patterns)

**Quality Metrics:**
- Test coverage percentage
- Linting error count
- Code complexity score
- Documentation completeness
- Security scan results

**Test Scenarios:**
- Task completes with low coverage → Quality gate fails
- Similar past tasks had issues → Predictor warns
- Quality trend declining → Alert triggered
- All gates pass → Phase transition allowed

**Estimated Effort:** 6-8 hours

---

## Parallelization Strategy

### **Optimal Parallel Execution**

**Week 9-10 (Fully Parallel):**
```
Day 1-5: Guardian Squad + Memory Squad + Cost Squad (3 parallel agents)
  → No dependencies between them
  → Each uses Phase 3 foundation
  → Can merge independently
```

**Week 11 (Sequential):**
```
Day 1-3: Quality Gates Squad (waits for Memory patterns)
  → Consumes Memory Squad outputs
  → Extends Phase 2 gates
```

**Timeline Compression:**
- Sequential: 4 weeks
- Parallel: 1.5-2 weeks (60% time savings!)

---

## Shared Contracts (Define First)

### 1. Guardian Authority Levels
```python
# omoi_os/models/authority.py
class AuthorityLevel(int, Enum):
    WORKER = 1
    WATCHDOG = 2
    MONITOR = 3
    GUARDIAN = 4
    SYSTEM = 5
```

### 2. Memory Pattern Schema
```python
# omoi_os/services/memory.py
@dataclass
class TaskPattern:
    pattern_id: str
    task_type_pattern: str  # Regex or template
    success_indicators: List[str]
    failure_indicators: List[str]
    recommended_context: dict
    confidence_score: float
    usage_count: int
```

### 3. Cost Model Schema
```yaml
# omoi_os/config/cost_models.yaml
providers:
  openai:
    gpt-4-turbo:
      prompt_token_cost: 0.00001
      completion_token_cost: 0.00003
    gpt-3.5-turbo:
      prompt_token_cost: 0.0000005
      completion_token_cost: 0.0000015
  anthropic:
    claude-sonnet-4.5:
      prompt_token_cost: 0.000003
      completion_token_cost: 0.000015
```

### 4. Quality Gate Schema
```python
# Extended from Phase 2 PhaseGateService
{
    "gate_type": "quality",
    "requirements": {
        "min_test_coverage": 80,
        "max_lint_errors": 0,
        "max_complexity": 10,
        "predicted_quality_score": 0.7
    }
}
```

---

## Migration Strategy

### Migration 006: Guardian & Memory
**Parent:** `005_monitoring_observability`

Tables:
- `guardian_actions`
- `task_memories` (with vector column)
- `learned_patterns` (with vector column)

**Vector Index:**
```sql
CREATE INDEX idx_task_memories_embedding 
ON task_memories USING ivfflat (context_embedding vector_cosine_ops);
```

### Migration 007: Cost Tracking
**Parent:** `006_guardian_memory`

Tables:
- `cost_records`
- `budgets`

### Migration 008: Quality Gates
**Parent:** `007_cost_tracking`

Tables:
- `quality_metrics`
- `advanced_quality_gates`

**Alternative (Parallel Migrations):**
Could use branch labels and merge migration if squads truly parallel.

---

## Test Strategy

### Guardian Tests (23 tests)
```
test_guardian.py:
  • test_emergency_intervention
  • test_resource_reallocation
  • test_authority_validation
  • test_task_cancellation_by_guardian
  • test_agent_replacement
  • test_priority_override
  • test_intervention_audit_trail
  • test_automatic_rollback
  
test_guardian_policies.py:
  • test_policy_loading
  • test_policy_evaluation
  • test_escalation_chain
  • test_policy_validation
  
test_guardian_integration.py:
  • test_watchdog_escalation (if Phase 4 done)
  • test_registry_integration
  • test_event_publishing
```

### Memory Tests (30 tests)
```
test_memory.py:
  • test_store_task_execution
  • test_retrieve_similar_tasks
  • test_embedding_generation
  • test_similarity_threshold
  
test_pattern_learning.py:
  • test_extract_success_pattern
  • test_extract_failure_pattern
  • test_pattern_confidence_scoring
  • test_pattern_reuse_increment
  
test_similarity_search.py:
  • test_vector_search_accuracy
  • test_top_k_retrieval
  • test_similarity_ranking
  • test_hybrid_search (text + vector)
```

### Cost Tests (18 tests)
```
test_cost_tracking.py:
  • test_record_llm_cost
  • test_cost_attribution
  • test_cost_aggregation
  • test_provider_pricing
  
test_budget_enforcement.py:
  • test_budget_limit_check
  • test_budget_alert_threshold
  • test_budget_exceeded_event
  • test_budget_period_rollover
```

### Quality Tests (22 tests)
```
test_quality_checker.py:
  • test_coverage_requirement
  • test_lint_score_requirement
  • test_complexity_check
  • test_quality_aggregation
  
test_quality_predictor.py:
  • test_predict_from_patterns
  • test_quality_confidence
  • test_recommendation_generation
```

**Total New Tests:** ~93 tests

---

## Implementation Order (Recommended)

### **Parallel Track A: Guardian + Cost** (Week 9)
Both are independent, can run simultaneously:
- Guardian: 6-8 hours
- Cost: 5-6 hours
- **Wall-clock:** 1 week if parallel, 2 weeks if sequential

### **Parallel Track B: Memory** (Week 10)
Needs focus due to embedding complexity:
- Memory: 8-10 hours
- **Blocks:** Quality Gates (provides patterns)

### **Sequential Track C: Quality Gates** (Week 11-12)
Waits for Memory patterns:
- Quality: 6-8 hours
- **Can start:** Week 10 Day 3 (after Memory patterns defined)

**Optimal Strategy:**
```
Week 9:  Start Guardian + Cost in parallel (2 agents/contexts)
Week 10: Start Memory while Guardian/Cost finish
Week 11: Start Quality Gates (uses Memory outputs)
Week 12: Integration testing all 4 features
```

**Compressed Timeline:** 2.5-3 weeks instead of 4

---

## Code Estimates

### Guardian Squad
- **Production Code:** ~400 lines
- **Test Code:** ~600 lines
- **Config Files:** ~200 lines
- **Total:** ~1,200 lines

### Memory Squad
- **Production Code:** ~600 lines (embedding complexity)
- **Test Code:** ~800 lines
- **Config Files:** ~100 lines
- **Total:** ~1,500 lines

### Cost Tracking Squad
- **Production Code:** ~350 lines
- **Test Code:** ~450 lines
- **Config Files:** ~150 lines (pricing models)
- **Total:** ~950 lines

### Quality Gates Squad
- **Production Code:** ~450 lines
- **Test Code:** ~550 lines
- **Config Files:** ~200 lines
- **Total:** ~1,200 lines

**Phase 5 Total:** ~4,850 lines (~5K lines of code)

---

## Tech Stack Decisions

### Embeddings (Memory Squad)
**Recommended:** Hybrid approach
- **Development:** `sentence-transformers/all-MiniLM-L6-v2` (local, free)
- **Production:** OpenAI `text-embedding-3-small` (better quality)
- **Configuration:** Environment variable `EMBEDDING_PROVIDER`

**Dependencies to add:**
```toml
sentence-transformers = ">=3.0.0"  # Local embeddings
openai = ">=1.0.0"  # OpenAI API (for embeddings + cost tracking)
anthropic = ">=0.34.0"  # Anthropic API (for cost tracking)
numpy = ">=1.24.0"  # Vector operations
```

### Vector Search
- **Already have:** `pgvector>=0.3.3` ✅
- **Index type:** IVFFlat (good for <1M vectors) or HNSW (better accuracy)
- **Distance metric:** Cosine similarity

### Cost Tracking
**Data Sources:**
1. OpenHands `conversation.conversation_stats.get_combined_metrics()` ← Already available!
2. Parse OpenAI/Anthropic response headers
3. Manual cost records via API

---

## API Endpoints

### Guardian APIs (`/api/v1/guardian`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/intervention/cancel-task` | Emergency task cancellation |
| POST | `/intervention/reallocate` | Reallocate agent resources |
| POST | `/intervention/override-priority` | Boost task priority |
| GET | `/actions` | List guardian actions (audit trail) |
| POST | `/actions/{id}/revert` | Revert an intervention |

### Memory APIs (`/api/v1/memory`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/search` | Search similar past tasks |
| GET | `/patterns` | List learned patterns |
| GET | `/tasks/{id}/context` | Get suggested context for task |
| POST | `/patterns/{id}/feedback` | Provide pattern feedback |

### Cost APIs (`/api/v1/costs`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/records` | List cost records |
| GET | `/summary` | Cost summary (by ticket/agent/phase) |
| GET | `/budgets` | List budgets |
| POST | `/budgets` | Create budget limit |
| GET | `/forecast` | Cost forecast based on queue |

### Quality APIs (`/api/v1/quality`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/metrics/{task_id}` | Get quality metrics for task |
| POST | `/predict` | Predict quality for planned task |
| GET | `/gates/{phase_id}` | Get quality gate requirements |
| POST | `/gates` | Create/update quality gate |

---

## Event Types (New)

### Guardian Events
- `guardian.intervention.started`
- `guardian.intervention.completed`
- `guardian.intervention.reverted`
- `guardian.resource.reallocated`

### Memory Events
- `memory.pattern.learned`
- `memory.pattern.matched`
- `memory.context.suggested`

### Cost Events
- `cost.budget.warning` (80% threshold)
- `cost.budget.exceeded`
- `cost.forecast.high`

### Quality Events
- `quality.gate.evaluated`
- `quality.prediction.low`
- `quality.trend.declining`

---

## Integration with Phase 4 (Optional)

If Phase 4 Monitoring is complete:
- Guardian receives escalations from Watchdog
- Cost tracking feeds into Monitor dashboards
- Quality metrics appear in anomaly detection
- Memory patterns improve Watchdog remediation

If Phase 4 not done yet:
- All Phase 5 features work independently
- Can integrate retroactively

---

## Squad Kickoff Prompts

### **Guardian Squad Prompt:**
```
Implement Phase 5 Guardian Agent (Emergency Intervention System).

Context:
- Phase 3 complete: AgentRegistryService, TaskQueueService, EventBus available
- Phase 4 optional: If Watchdog exists, receive escalations from it

Deliverables:
1. Create guardian_action.py model with audit trail
2. Implement GuardianService with:
   - emergency_cancel_task(task_id, reason)
   - reallocate_agent_capacity(from_agent, to_agent, capacity)
   - override_task_priority(task_id, new_priority, authority)
3. Add guardian policy YAML configs (3 examples)
4. Create /api/v1/guardian routes
5. Write 23 tests covering intervention, authority, rollback

Follow TDD. Use session.expunge() pattern. Publish events for all actions.
Target: 1,200 lines total, 100% test pass rate.
```

### **Memory Squad Prompt:**
```
Implement Phase 5 Memory & Learning System (Pattern Recognition).

Context:
- Phase 3 complete: TaskQueueService provides completed task history
- pgvector installed: Use for similarity search

Deliverables:
1. Create task_memory.py, learned_pattern.py models with vector columns
2. Implement MemoryService with:
   - store_execution(task_id, summary, embedding)
   - search_similar(task_description, top_k=5)
   - extract_pattern(similar_tasks) → LearnedPattern
3. Implement EmbeddingService (OpenAI API + local fallback)
4. Create /api/v1/memory routes
5. Write 30 tests including vector search accuracy

Use sentence-transformers for local dev, OpenAI for production.
Create migration 006 with vector indexes (ivfflat).
Target: 1,500 lines, 90%+ coverage.
```

### **Cost Tracking Squad Prompt:**
```
Implement Phase 5 Cost Tracking & Budget Enforcement.

Context:
- OpenHands conversation_stats already tracks token counts
- Need to convert tokens → USD costs

Deliverables:
1. Create cost_record.py, budget.py models
2. Implement CostTrackingService:
   - record_llm_cost(task_id, provider, tokens, model)
   - check_budget(scope_type, scope_id) → remaining
   - forecast_costs(pending_tasks) → estimated_total
3. Create cost_models.yaml with provider pricing
4. Hook into TASK_COMPLETED events to extract costs
5. Create /api/v1/costs routes
6. Write 18 tests for tracking, budgets, forecasting

Publish cost.budget.exceeded events when limits hit.
Target: 950 lines, 95%+ coverage.
```

### **Quality Gates Squad Prompt:**
```
Implement Phase 5 Advanced Quality Gates (ML-Based Validation).

Context:
- Phase 2 PhaseGateService exists (basic gates)
- Memory Squad provides learned patterns (wait for Week 10 Day 3)

Deliverables:
1. Create quality_metric.py, quality_gate.py models
2. Implement QualityCheckerService:
   - check_code_quality(task_result) → QualityMetrics
   - evaluate_gate(task_id, gate_requirements) → pass/fail
3. Implement QualityPredictorService (uses Memory patterns):
   - predict_quality(task_description, similar_patterns) → score
4. Create quality gate YAML configs
5. Create /api/v1/quality routes
6. Write 22 tests for checking, prediction, gates

Extend PhaseGateService, don't replace it.
Target: 1,200 lines, 90%+ coverage.
```

---

## File Ownership Matrix

| Squad | Models | Services | API Routes | Tests | Config |
|-------|--------|----------|------------|-------|--------|
| Guardian | guardian_action.py | guardian.py | guardian.py | test_guardian*.py | guardian_policies/*.yaml |
| Memory | task_memory.py, learned_pattern.py | memory.py, embedding.py | memory.py | test_memory*.py | - |
| Cost | cost_record.py, budget.py | cost_tracking.py, budget_enforcer.py | costs.py | test_cost*.py | cost_models.yaml |
| Quality | quality_metric.py, quality_gate.py | quality_checker.py, quality_predictor.py | quality.py | test_quality*.py | quality_gates/*.yaml |

**No file conflicts** — all squads own distinct files!

---

## Success Criteria

### Phase 5 Complete When:
- [ ] All 4 milestones implemented
- [ ] 93+ new tests passing
- [ ] Zero linting errors
- [ ] Migrations 006, 007, 008 applied
- [ ] Integration tests pass
  - Guardian can cancel tasks
  - Memory suggests context for new tasks
  - Cost tracking records all LLM calls
  - Quality gates extend phase gates
- [ ] Documentation complete (4 squad READMEs)

**Expected Total:**
- ~260 tests (171 Phase 3 + 93 Phase 5)
- ~7,000 lines of code total
- 4 new migrations
- Full production feature set

---

## Risk Assessment

### Low Risk ✅
- **Guardian:** Uses existing Phase 3 APIs, clean isolation
- **Cost Tracking:** Reads existing conversation stats, simple calculations

### Medium Risk ⚠️
- **Memory:** Embedding generation can be slow, need caching
- **Quality:** ML prediction quality depends on training data volume

### Mitigation
- Memory: Start with local embeddings, optimize later
- Quality: Graceful fallback to rule-based if insufficient patterns
- All: Comprehensive unit tests before integration

---

## Quick Start Commands (For Parallel Context)

### Guardian Squad
```bash
# Create models, services, tests following prompt above
# Migration will be 006_guardian (if going first)
uv run pytest tests/test_guardian.py -v
```

### Memory Squad
```bash
# Install embedding dependencies first
uv add sentence-transformers openai
# Implement memory service with vector search
uv run pytest tests/test_memory.py -v
```

### Cost Squad
```bash
# Add provider SDKs
uv add openai anthropic
# Implement cost tracking + budgets
uv run pytest tests/test_cost_tracking.py -v
```

### Quality Squad
```bash
# Wait for Memory patterns (Week 10 Day 3)
# Extend PhaseGateService
uv run pytest tests/test_quality_checker.py -v
```

---

## Handoff Checklist (Between Squads)

### Memory → Quality (Critical)
- [ ] Memory Squad: Export `TaskPattern` dataclass
- [ ] Memory Squad: Provide `search_patterns(task_type)` API
- [ ] Quality Squad: Import pattern schema
- [ ] Contract test: Quality can retrieve patterns

### Guardian → Watchdog (Optional, if Phase 4 done)
- [ ] Guardian: Accept escalations via `escalate(alert_id)` method
- [ ] Watchdog: Call Guardian when remediation fails
- [ ] Contract test: Escalation flow works

### Cost → Monitor (Optional, if Phase 4 done)
- [ ] Cost: Export cost metrics in Monitor-compatible format
- [ ] Monitor: Display cost in dashboard
- [ ] Contract test: Cost metrics visible

---

## Merge Strategy

### Option A: Sequential Merges (Safer)
```
Week 9:  Merge Guardian → main
Week 10: Merge Cost → main
Week 11: Merge Memory → main
Week 12: Merge Quality → main
```

### Option B: Feature Branches (Parallel)
```
main
  ├── feature/guardian (Week 9-10)
  ├── feature/memory (Week 10-11)
  ├── feature/cost (Week 9-10)
  └── feature/quality (Week 11-12)
      ↓
    integration/phase5 (Week 12)
      ↓
    main (after integration tests pass)
```

**Recommended:** Option B for true parallelism

---

## TLDR — Phase 5 Parallel Execution

**START IMMEDIATELY (3 parallel contexts):**
1. **Context 1:** Guardian Squad (6-8 hours)
2. **Context 2:** Memory Squad (8-10 hours)
3. **Context 3:** Cost Tracking Squad (5-6 hours)

**START WEEK 10 DAY 3 (1 context):**
4. **Context 4:** Quality Gates Squad (6-8 hours, waits for Memory)

**TOTAL DURATION:** 2-3 weeks wall-clock (vs. 4 weeks sequential)

**READY TO START:** ✅ YES — All prerequisites met from Phase 3

---

**Use this document to spawn parallel Phase 5 agents while I complete Phase 4!** 🚀

