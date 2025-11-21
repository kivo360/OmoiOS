# Diagnostic Agent System Comparison: Hephaestus vs OmoiOS

**Created**: 2025-01-30  
**Status**: Analysis Document  
**Purpose**: Compare Hephaestus Diagnostic Agent System with OmoiOS's existing implementation

---

## Executive Summary

OmoiOS has **~85% feature parity** with Hephaestus's Diagnostic Agent System. The core functionality (stuck detection, diagnostic spawning, context gathering) is implemented, but there are **key differences in agent execution model, configuration, and integration patterns**.

**Key Finding**: OmoiOS's diagnostic system is **more integrated** with the Discovery Service and uses a **different agent execution model** (DiscoveryService spawns recovery tasks directly vs Hephaestus creating diagnostic agents that create tasks).

---

## Feature-by-Feature Comparison

### 1. Stuck Workflow Detection ✅ **SIMILAR**

| Feature | Hephaestus | OmoiOS | Status |
|---------|-----------|--------|--------|
| Active workflow check | ✅ | ✅ | ✅ Same |
| Tasks exist check | ✅ | ✅ | ✅ Same |
| All tasks finished | ✅ | ✅ | ✅ Same |
| No validated result | ✅ | ✅ | ✅ Same |
| Cooldown check | ✅ | ✅ | ✅ Same |
| Stuck time check | ✅ | ✅ | ✅ Same |

**OmoiOS Implementation** (`omoi_os/services/diagnostic.py:57-169`):
```python
def find_stuck_workflows(
    self,
    cooldown_seconds: int = 60,
    stuck_threshold_seconds: int = 60,
) -> List[dict]:
    # Checks ALL 6 conditions:
    # 1. Active workflow exists
    # 2. Tasks exist
    # 3. All tasks finished (no pending/assigned/running/under_review/validation_in_progress)
    # 4. No validated WorkflowResult
    # 5. Cooldown passed
    # 6. Stuck time met
```

**Difference**: OmoiOS checks more task statuses (`under_review`, `validation_in_progress`) than Hephaestus's simpler list (`pending`, `assigned`, `in_progress`).

---

### 2. Context Gathering ⚠️ **PARTIALLY DIFFERENT**

| Context Type | Hephaestus | OmoiOS | Status |
|--------------|-----------|--------|--------|
| Workflow goal | ✅ From `result_criteria` | ✅ From config or ticket | ✅ Same |
| Phase definitions | ✅ All phases | ✅ Current phase only | ⚠️ Partial |
| Recent agents (15) | ✅ Last 15 agents | ✅ Last 15 tasks | ⚠️ Different model |
| Conductor analyses | ✅ Last 5 analyses | ❌ Not included | ❌ Missing |
| Submitted results | ✅ All submissions | ❌ Not included | ❌ Missing |
| Validation feedback | ✅ Rejection reasons | ❌ Not included | ❌ Missing |

**OmoiOS Implementation** (`omoi_os/services/diagnostic.py:263-347`):
```python
def build_diagnostic_context(
    self,
    workflow_id: str,
    max_agents: int = 15,
    max_analyses: int = 5,  # Parameter exists but not used
) -> dict:
    # Gathers:
    # - Workflow goal (from config or ticket)
    # - Recent tasks (last 15)
    # - Task distribution by phase
    # - Task counts (total, done, failed)
    # ❌ Missing: Conductor analyses, submitted results, validation feedback
```

**Gap**: OmoiOS doesn't include:
- Conductor system analyses (system coherence scores, duplicate work detections)
- Submitted WorkflowResult records (even rejected ones)
- Validation feedback explaining rejections

---

### 3. Diagnostic Agent Creation ⚠️ **DIFFERENT MODEL**

| Aspect | Hephaestus | OmoiOS | Status |
|--------|-----------|--------|--------|
| Creates diagnostic task | ✅ Yes | ✅ Yes | ✅ Same |
| Creates diagnostic agent | ✅ Yes | ❌ No | ⚠️ Different |
| Agent type | ✅ `'diagnostic'` | ❌ N/A | ⚠️ Different |
| Phase assignment | ✅ `phase_id=None` | ❌ Uses DiscoveryService | ⚠️ Different |
| Agent execution | ✅ Agent runs diagnostic | ❌ DiscoveryService spawns tasks | ⚠️ Different |

**Hephaestus Model**:
```
1. Create DiagnosticRun record
2. Create diagnostic task
3. Create diagnostic agent (agent_type='diagnostic')
4. Agent executes diagnostic process:
   - Step 1: Understand goal
   - Step 2: Analyze state
   - Step 3: Identify gap
   - Step 4: Create tasks via create_task MCP tool
5. Agent marks diagnostic task as done
```

**OmoiOS Model** (`omoi_os/services/diagnostic.py:171-223`):
```
1. Create DiagnosticRun record
2. Call DiscoveryService.spawn_diagnostic_recovery()
3. DiscoveryService creates recovery task directly
4. No diagnostic agent execution
5. Recovery task picked up by regular agent
```

**Key Difference**: 
- **Hephaestus**: Diagnostic agent is a **specialized agent** that analyzes and creates tasks
- **OmoiOS**: Diagnostic system **spawns recovery tasks** via DiscoveryService, no specialized agent

---

### 4. Diagnostic Process ⚠️ **DIFFERENT**

| Step | Hephaestus | OmoiOS | Status |
|------|-----------|--------|--------|
| Step 1: Understand Goal | ✅ Agent reads `result_criteria` | ✅ Context includes goal | ✅ Same |
| Step 2: Analyze State | ✅ Agent reviews accomplishments | ✅ Context includes tasks | ✅ Same |
| Step 3: Identify Gap | ✅ Agent diagnoses gap | ⚠️ LLM generates hypotheses | ⚠️ Different |
| Step 4: Create Tasks | ✅ Agent uses `create_task` MCP | ✅ DiscoveryService spawns | ⚠️ Different |

**Hephaestus**: Diagnostic agent follows **4-step structured process** with explicit instructions.

**OmoiOS**: Uses **LLM structured output** (`generate_hypotheses()`) to generate hypotheses and recommendations, but **doesn't execute the diagnostic agent** - instead spawns recovery tasks directly.

**OmoiOS Implementation** (`omoi_os/services/diagnostic.py:225-261`):
```python
async def generate_hypotheses(
    self,
    context: dict,
) -> DiagnosticAnalysis:
    # Uses LLM to generate structured hypotheses
    # Returns DiagnosticAnalysis with:
    # - root_cause
    # - hypotheses (ranked by likelihood)
    # - recommendations (with priority)
    # - confidence score
    # ❌ But this is not used in the actual diagnostic flow!
```

**Gap**: OmoiOS has hypothesis generation but **doesn't use it** in the diagnostic spawning flow.

---

### 5. Configuration ⚠️ **DIFFERENT**

| Config | Hephaestus | OmoiOS | Status |
|--------|-----------|--------|--------|
| YAML config | ✅ `hephaestus_config.yaml` | ❌ Hardcoded in code | ❌ Missing |
| Environment vars | ✅ `DIAGNOSTIC_AGENT_ENABLED` | ❌ Not configurable | ❌ Missing |
| SDK config | ✅ `HephaestusConfig` | ❌ N/A | ❌ Missing |
| Cooldown | ✅ Configurable | ✅ Hardcoded (60s) | ⚠️ Partial |
| Stuck time | ✅ Configurable | ✅ Hardcoded (60s) | ⚠️ Partial |
| Max agents | ✅ Configurable (15) | ✅ Configurable (15) | ✅ Same |
| Max analyses | ✅ Configurable (5) | ✅ Parameter exists but unused | ⚠️ Partial |
| Max tasks | ✅ Configurable (5) | ❌ No limit | ⚠️ Different |

**OmoiOS Implementation** (`omoi_os/api/main.py:219-222`):
```python
stuck_workflows = diagnostic_service.find_stuck_workflows(
    cooldown_seconds=60,  # Hardcoded
    stuck_threshold_seconds=60,  # Hardcoded
)
```

**Gap**: OmoiOS has **no configuration system** - all values are hardcoded or passed as parameters.

---

### 6. Database Schema ✅ **SIMILAR**

| Field | Hephaestus | OmoiOS | Status |
|-------|-----------|--------|--------|
| `id` | ✅ TEXT PRIMARY KEY | ✅ String UUID | ✅ Same |
| `workflow_id` | ✅ TEXT FK | ✅ String FK | ✅ Same |
| `diagnostic_agent_id` | ✅ TEXT FK | ✅ Optional String FK | ✅ Same |
| `diagnostic_task_id` | ✅ TEXT FK | ✅ Optional String FK | ✅ Same |
| `triggered_at` | ✅ DATETIME | ✅ DateTime(timezone=True) | ✅ Same |
| `total_tasks_at_trigger` | ✅ INTEGER | ✅ Integer | ✅ Same |
| `done_tasks_at_trigger` | ✅ INTEGER | ✅ Integer | ✅ Same |
| `failed_tasks_at_trigger` | ✅ INTEGER | ✅ Integer | ✅ Same |
| `time_since_last_task_seconds` | ✅ INTEGER | ✅ Integer | ✅ Same |
| `tasks_created_count` | ✅ INTEGER | ✅ Integer | ✅ Same |
| `tasks_created_ids` | ✅ JSON | ✅ JSONB | ✅ Same |
| `workflow_goal` | ✅ TEXT | ✅ Optional Text | ✅ Same |
| `phases_analyzed` | ✅ JSON | ✅ Optional JSONB | ✅ Same |
| `agents_reviewed` | ✅ JSON | ✅ Optional JSONB | ✅ Same |
| `diagnosis` | ✅ TEXT | ✅ Optional Text | ✅ Same |
| `completed_at` | ✅ DATETIME | ✅ Optional DateTime | ✅ Same |
| `status` | ✅ TEXT CHECK | ✅ String(32) | ✅ Same |

**Status**: ✅ **Nearly identical** - OmoiOS uses JSONB instead of JSON (PostgreSQL-specific enhancement).

---

### 7. Agent Type Support ⚠️ **DIFFERENT**

| Aspect | Hephaestus | OmoiOS | Status |
|--------|-----------|--------|--------|
| Agent type enum | ✅ Includes `'diagnostic'` | ❌ No diagnostic type | ❌ Missing |
| Specialized agent | ✅ Yes | ❌ No | ❌ Missing |
| Agent execution | ✅ Diagnostic agent runs | ❌ DiscoveryService spawns | ⚠️ Different |

**Hephaestus**: Diagnostic agents are **first-class agent types** with specialized execution.

**OmoiOS**: No diagnostic agent type - uses **DiscoveryService** to spawn recovery tasks directly.

---

### 8. Monitoring Integration ✅ **SIMILAR**

| Aspect | Hephaestus | OmoiOS | Status |
|--------|-----------|--------|--------|
| Monitoring loop | ✅ Every 60s | ✅ Every 60s | ✅ Same |
| Auto-trigger | ✅ Yes | ✅ Yes | ✅ Same |
| Background task | ✅ Yes | ✅ Yes | ✅ Same |

**OmoiOS Implementation** (`omoi_os/api/main.py:207-256`):
```python
async def diagnostic_monitoring_loop():
    """Check for stuck workflows every 60 seconds and spawn diagnostic agents."""
    while True:
        stuck_workflows = diagnostic_service.find_stuck_workflows(...)
        for workflow_info in stuck_workflows:
            diagnostic_run = diagnostic_service.spawn_diagnostic_agent(...)
        await asyncio.sleep(60)
```

**Status**: ✅ **Same pattern** - background monitoring loop checks every 60 seconds.

---

### 9. Integration with Other Systems ⚠️ **DIFFERENT**

| System | Hephaestus | OmoiOS | Status |
|--------|-----------|--------|--------|
| Guardian | ✅ Complementary | ✅ Complementary | ✅ Same |
| Conductor | ✅ Shares analyses | ❌ Not integrated | ❌ Missing |
| Validation | ✅ Considers feedback | ⚠️ Partial integration | ⚠️ Partial |
| Phase System | ✅ Phase-aware | ✅ Phase-aware | ✅ Same |
| Discovery Service | ❌ N/A | ✅ Uses DiscoveryService | ⚠️ Different |

**OmoiOS**: Uses **DiscoveryService** to spawn recovery tasks, which is more integrated with the discovery/branching system.

**Hephaestus**: Diagnostic agents are **independent** and use MCP tools directly.

---

## Key Architectural Differences

### 1. **Agent Execution Model**

**Hephaestus**:
- Creates **specialized diagnostic agent** (`agent_type='diagnostic'`)
- Agent executes **4-step diagnostic process**
- Agent uses **MCP tools** (`create_task`) to create recovery tasks
- Agent marks diagnostic task as done

**OmoiOS**:
- **No specialized agent** - uses DiscoveryService
- DiscoveryService **spawns recovery task directly**
- Recovery task picked up by **regular agent**
- More integrated with discovery/branching system

### 2. **Diagnostic Process**

**Hephaestus**:
- **Structured 4-step process**:
  1. Understand goal
  2. Analyze state
  3. Identify gap
  4. Create tasks
- Agent follows explicit instructions
- Agent creates 1-5 tasks via MCP

**OmoiOS**:
- **LLM hypothesis generation** (`generate_hypotheses()`)
- But **not used** in actual flow
- DiscoveryService spawns recovery task directly
- No structured diagnostic process execution

### 3. **Context Gathering**

**Hephaestus**:
- Includes **Conductor analyses** (system coherence, duplicates)
- Includes **submitted results** (even rejected)
- Includes **validation feedback**

**OmoiOS**:
- **Missing** Conductor analyses
- **Missing** submitted results
- **Missing** validation feedback
- Focuses on **task history** only

---

## Missing Features in OmoiOS

### 🔴 Critical Missing

1. **Conductor Integration**
   - ❌ No Conductor analyses in context
   - ❌ No system coherence scores
   - ❌ No duplicate work detection

2. **Result Submission Tracking**
   - ❌ No submitted WorkflowResult records in context
   - ❌ No validation feedback in context
   - ❌ Can't analyze why results were rejected

3. **Configuration System**
   - ❌ No YAML configuration
   - ❌ No environment variables
   - ❌ Hardcoded values

### 🟡 High Priority Missing

4. **Diagnostic Agent Execution**
   - ❌ No specialized diagnostic agent type
   - ❌ No 4-step diagnostic process execution
   - ❌ Hypothesis generation not used

5. **Max Tasks Limit**
   - ❌ No limit on tasks diagnostic can create
   - ⚠️ Could create too many tasks

### 🟢 Medium Priority Missing

6. **All Phase Definitions**
   - ⚠️ Only includes current phase, not all phases
   - ⚠️ Can't see full workflow structure

---

## OmoiOS Advantages

### ✅ **Better Integration**

1. **DiscoveryService Integration**
   - Uses existing discovery/branching system
   - Recovery tasks tracked as discoveries
   - More consistent with workflow branching patterns

2. **Unified Task Model**
   - Recovery tasks are regular tasks
   - No special handling needed
   - Simpler architecture

### ✅ **More Flexible**

1. **No Agent Type Constraint**
   - Doesn't require new agent type
   - Uses existing agent infrastructure
   - Easier to maintain

---

## Recommendations

### Option A: Adopt Hephaestus Model (More Complete)

**Changes Required**:
1. Add `'diagnostic'` to agent type enum
2. Create diagnostic agent execution logic
3. Implement 4-step diagnostic process
4. Add Conductor integration to context
5. Add result submission tracking
6. Add configuration system

**Pros**: More complete, follows Hephaestus pattern exactly  
**Cons**: More complex, requires new agent type

### Option B: Enhance Current Model (Hybrid Approach) ⭐ **RECOMMENDED**

**Changes Required**:
1. ✅ **Add Conductor integration** to `build_diagnostic_context()`
2. ✅ **Add result submission tracking** to context
3. ✅ **Use `generate_hypotheses()`** in diagnostic flow
4. ✅ **Add configuration system** (YAML + env vars)
5. ✅ **Add max tasks limit** to DiscoveryService spawn
6. ⚠️ **Keep DiscoveryService model** (simpler, more integrated)

**Pros**: Enhances existing system, maintains integration benefits  
**Cons**: Still different from Hephaestus model

### Option C: Keep Current Model (Minimal Changes)

**Changes Required**:
1. Add configuration system only
2. Document differences

**Pros**: Minimal changes  
**Cons**: Missing important context (Conductor, results)

---

## Conclusion

OmoiOS's diagnostic system is **functionally similar** to Hephaestus but uses a **different architectural model**:

- **Hephaestus**: Specialized diagnostic agent executes 4-step process
- **OmoiOS**: DiscoveryService spawns recovery tasks directly

**Recommendation**: **Option B (Hybrid Approach)** - Enhance current model with:
1. Conductor integration
2. Result submission tracking
3. Use hypothesis generation
4. Add configuration system
5. Keep DiscoveryService integration (it's better integrated)

This maintains OmoiOS's architectural advantages while adding missing context and configurability.

---

## Related Documents

- [Hephaestus Adoption Analysis](./hephaestus_adoption_analysis.md) - Phase system comparison
- [Diagnostic System README](../diagnostic/README.md) - OmoiOS diagnostic documentation
- [Discovery Service](../implementation/workflows/hephaestus_workflow_enhancements.md) - Discovery/branching system
