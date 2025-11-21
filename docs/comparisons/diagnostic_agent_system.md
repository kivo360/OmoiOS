# Diagnostic Agent System Comparison: Hephaestus vs OmoiOS

**Created**: 2025-01-30  
**Status**: Verified Analysis  
**Purpose**: Compare Hephaestus Diagnostic Agent System with OmoiOS's existing implementation (verified against actual codebase)

---

## Executive Summary

After **verifying against the actual codebase**, OmoiOS has **~75% feature parity** with Hephaestus. The core detection logic exists, but several **integration points are missing** and the **task spawning mechanism is incomplete**.

**Key Finding**: OmoiOS's `spawn_diagnostic_agent()` **only creates a DiagnosticRun record** but **doesn't actually spawn recovery tasks**. The DiscoveryService has `spawn_diagnostic_recovery()` but it's **not called** in the diagnostic flow.

---

## Feature-by-Feature Comparison (Verified)

### 1. Stuck Workflow Detection ✅ **IMPLEMENTED**

| Feature | Hephaestus | OmoiOS | Status |
|---------|-----------|--------|--------|
| Active workflow check | ✅ | ✅ | ✅ Same |
| Tasks exist check | ✅ | ✅ | ✅ Same |
| All tasks finished | ✅ | ✅ | ✅ Same |
| No validated result | ✅ | ✅ | ✅ Same |
| Cooldown check | ✅ | ✅ | ✅ Same |
| Stuck time check | ✅ | ✅ | ✅ Same |

**OmoiOS Implementation** (`omoi_os/services/diagnostic.py:57-169`):
- ✅ All 6 conditions checked correctly
- ✅ Cooldown tracking via `_last_diagnostic` dict
- ✅ Stuck time calculated from last task completion

**Status**: ✅ **FULLY IMPLEMENTED**

---

### 2. Context Gathering ⚠️ **PARTIALLY IMPLEMENTED**

| Context Type | Hephaestus | OmoiOS | Status | Notes |
|--------------|-----------|--------|--------|-------|
| Workflow goal | ✅ From `result_criteria` | ✅ From config or ticket | ✅ Same | |
| Phase definitions | ✅ All phases | ⚠️ Current phase only | ⚠️ Partial | Only includes `current_phase` |
| Recent agents (15) | ✅ Last 15 agents | ✅ Last 15 tasks | ✅ Same | Different model but equivalent |
| Conductor analyses | ✅ Last 5 analyses | ❌ Not included | ❌ Missing | ConductorService exists but not queried |
| Submitted results | ✅ All submissions | ❌ Not included | ❌ Missing | WorkflowResult model exists but not queried |
| Validation feedback | ✅ Rejection reasons | ❌ Not included | ❌ Missing | WorkflowResult has `validation_feedback` but not queried |

**OmoiOS Implementation** (`omoi_os/services/diagnostic.py:263-347`):
```python
def build_diagnostic_context(...) -> dict:
    # ✅ Includes: workflow_goal, recent_tasks, task_distribution
    # ❌ Missing: Conductor analyses (ConductorService exists!)
    # ❌ Missing: WorkflowResult submissions (WorkflowResult model exists!)
    # ❌ Missing: Validation feedback (WorkflowResult.validation_feedback exists!)
```

**Gap**: Infrastructure exists but **not integrated**:
- ✅ `ConductorService` exists (`omoi_os/services/conductor.py`)
- ✅ `conductor_analyses` table exists (migration `003_intelligent_monitoring_enhancements.py`)
- ✅ `WorkflowResult` model exists (`omoi_os/models/workflow_result.py`)
- ✅ `ResultSubmissionService.list_workflow_results()` exists
- ❌ **Not queried** in `build_diagnostic_context()`

**Status**: ⚠️ **INFRASTRUCTURE EXISTS BUT NOT INTEGRATED**

---

### 3. Diagnostic Agent Creation ❌ **INCOMPLETE**

| Aspect | Hephaestus | OmoiOS | Status | Notes |
|--------|-----------|--------|--------|-------|
| Creates diagnostic task | ✅ Yes | ❌ No | ❌ Missing | Only creates DiagnosticRun record |
| Creates diagnostic agent | ✅ Yes | ❌ No | ❌ Missing | No agent execution |
| Agent type | ✅ `'diagnostic'` | ❌ N/A | ❌ Missing | No diagnostic agent type |
| Phase assignment | ✅ `phase_id=None` | ❌ N/A | ❌ Missing | No task created |
| Agent execution | ✅ Agent runs diagnostic | ❌ No execution | ❌ Missing | No agent spawned |
| Recovery task spawning | ✅ Agent creates tasks | ⚠️ DiscoveryService exists | ⚠️ Partial | `spawn_diagnostic_recovery()` exists but **not called** |

**Hephaestus Model**:
```
1. Create DiagnosticRun record
2. Create diagnostic task
3. Create diagnostic agent (agent_type='diagnostic')
4. Agent executes diagnostic process (4 steps)
5. Agent creates 1-5 recovery tasks via create_task MCP tool
6. Agent marks diagnostic task as done
```

**OmoiOS Model** (`omoi_os/services/diagnostic.py:171-223`):
```python
def spawn_diagnostic_agent(...) -> DiagnosticRun:
    # 1. Create DiagnosticRun record ✅
    # 2. Update cooldown tracking ✅
    # 3. Publish event ✅
    # ❌ DOES NOT CREATE TASK
    # ❌ DOES NOT SPAWN AGENT
    # ❌ DOES NOT CALL spawn_diagnostic_recovery()
    return diagnostic_run  # Just returns record, no actual spawning!
```

**Critical Gap**: `spawn_diagnostic_agent()` **only creates a record** but doesn't spawn anything!

**DiscoveryService has the method** (`omoi_os/services/discovery.py:320-363`):
```python
def spawn_diagnostic_recovery(...) -> Task:
    # ✅ This method exists and spawns recovery tasks!
    # ❌ But it's NEVER CALLED in diagnostic flow
```

**Status**: ❌ **INCOMPLETE - Task spawning not implemented**

---

### 4. Diagnostic Process ❌ **NOT EXECUTED**

| Step | Hephaestus | OmoiOS | Status | Notes |
|------|-----------|--------|--------|-------|
| Step 1: Understand Goal | ✅ Agent reads `result_criteria` | ✅ Context includes goal | ✅ Same | |
| Step 2: Analyze State | ✅ Agent reviews accomplishments | ✅ Context includes tasks | ✅ Same | |
| Step 3: Identify Gap | ✅ Agent diagnoses gap | ⚠️ `generate_hypotheses()` exists | ⚠️ Not used | Method exists but **not called** |
| Step 4: Create Tasks | ✅ Agent uses `create_task` MCP | ⚠️ DiscoveryService exists | ⚠️ Not called | `spawn_diagnostic_recovery()` exists but **not called** |

**OmoiOS Implementation** (`omoi_os/services/diagnostic.py:225-261`):
```python
async def generate_hypotheses(...) -> DiagnosticAnalysis:
    # ✅ This method exists!
    # ✅ Uses LLM to generate structured hypotheses
    # ✅ Returns DiagnosticAnalysis with hypotheses and recommendations
    # ❌ BUT IT'S NEVER CALLED in diagnostic flow!
```

**Status**: ❌ **METHODS EXIST BUT NOT USED**

---

### 5. Configuration ⚠️ **INFRASTRUCTURE EXISTS BUT NOT USED**

| Config | Hephaestus | OmoiOS | Status | Notes |
|--------|-----------|--------|--------|-------|
| YAML config | ✅ `hephaestus_config.yaml` | ✅ `config/base.yaml` exists | ⚠️ Not used | Config system exists but diagnostic settings not added |
| Environment vars | ✅ `DIAGNOSTIC_AGENT_ENABLED` | ✅ Env var system exists | ⚠️ Not used | `OmoiBaseSettings` pattern exists |
| SDK config | ✅ `HephaestusConfig` | ❌ N/A | ❌ Missing | |
| Cooldown | ✅ Configurable | ⚠️ Hardcoded (60s) | ⚠️ Partial | Passed as parameter but not from config |
| Stuck time | ✅ Configurable | ⚠️ Hardcoded (60s) | ⚠️ Partial | Passed as parameter but not from config |
| Max agents | ✅ Configurable (15) | ✅ Configurable (15) | ✅ Same | |
| Max analyses | ✅ Configurable (5) | ⚠️ Parameter exists but unused | ⚠️ Partial | `max_analyses` parameter exists but not used |
| Max tasks | ✅ Configurable (5) | ❌ No limit | ❌ Missing | No limit in DiscoveryService |

**OmoiOS Configuration System** (`omoi_os/config.py`):
- ✅ Comprehensive YAML + env var system exists
- ✅ `OmoiBaseSettings` pattern for all settings
- ✅ `MonitoringSettings` class exists (lines 334-350)
- ❌ **No `DiagnosticSettings` class**
- ❌ Diagnostic values hardcoded in `omoi_os/api/main.py:219-222`

**Status**: ⚠️ **CONFIG SYSTEM EXISTS BUT DIAGNOSTIC SETTINGS NOT ADDED**

---

### 6. Database Schema ✅ **SIMILAR**

| Field | Hephaestus | OmoiOS | Status |
|-------|-----------|--------|--------|
| All fields | ✅ | ✅ | ✅ Nearly identical |

**Status**: ✅ **FULLY IMPLEMENTED** (OmoiOS uses JSONB instead of JSON - PostgreSQL enhancement)

---

### 7. Monitoring Integration ✅ **IMPLEMENTED**

| Aspect | Hephaestus | OmoiOS | Status |
|--------|-----------|--------|--------|
| Monitoring loop | ✅ Every 60s | ✅ Every 60s | ✅ Same |
| Auto-trigger | ✅ Yes | ✅ Yes | ✅ Same |
| Background task | ✅ Yes | ✅ Yes | ✅ Same |

**OmoiOS Implementation** (`omoi_os/api/main.py:207-256`):
- ✅ Background loop runs every 60 seconds
- ✅ Calls `find_stuck_workflows()`
- ✅ Calls `spawn_diagnostic_agent()` (but doesn't actually spawn)

**Status**: ✅ **IMPLEMENTED** (but spawning incomplete)

---

## Critical Gaps (Verified)

### 🔴 **Critical Missing**

1. **Task Spawning Not Implemented**
   - ❌ `spawn_diagnostic_agent()` only creates DiagnosticRun record
   - ❌ Doesn't call `DiscoveryService.spawn_diagnostic_recovery()`
   - ❌ No recovery tasks actually created
   - **Impact**: Diagnostics detect stuck workflows but don't fix them

2. **Hypothesis Generation Not Used**
   - ❌ `generate_hypotheses()` exists but never called
   - ❌ No LLM analysis performed
   - **Impact**: No intelligent diagnosis, just detection

### 🟡 **High Priority Missing**

3. **Conductor Integration Missing**
   - ✅ ConductorService exists
   - ✅ `conductor_analyses` table exists
   - ❌ Not queried in `build_diagnostic_context()`
   - **Impact**: Missing system coherence context

4. **Result Submission Tracking Missing**
   - ✅ WorkflowResult model exists
   - ✅ `ResultSubmissionService.list_workflow_results()` exists
   - ❌ Not queried in `build_diagnostic_context()`
   - **Impact**: Can't analyze why results were rejected

5. **Configuration Not Added**
   - ✅ Configuration system exists (`omoi_os/config.py`)
   - ✅ `MonitoringSettings` pattern exists
   - ❌ No `DiagnosticSettings` class
   - ❌ Values hardcoded
   - **Impact**: Not configurable

### 🟢 **Medium Priority Missing**

6. **Max Tasks Limit**
   - ❌ No limit on recovery tasks
   - **Impact**: Could create too many tasks

7. **All Phase Definitions**
   - ⚠️ Only includes current phase
   - **Impact**: Limited phase context

---

## What Actually Exists (Verified)

### ✅ **Fully Implemented**

1. **Stuck Detection Logic** - All 6 conditions checked correctly
2. **Database Schema** - DiagnosticRun model matches Hephaestus
3. **Monitoring Loop** - Background task runs every 60s
4. **Cooldown Tracking** - Prevents duplicate diagnostics
5. **Context Building** - Basic context (tasks, goal, distribution)

### ✅ **Infrastructure Exists (Not Integrated)**

1. **ConductorService** - System coherence analysis exists
2. **WorkflowResult Model** - Result tracking exists
3. **ResultSubmissionService** - Result querying exists
4. **Hypothesis Generation** - `generate_hypotheses()` method exists
5. **Recovery Task Spawning** - `spawn_diagnostic_recovery()` method exists
6. **Configuration System** - YAML + env var system exists

---

## Recommendations

### Option A: Complete Current Implementation ⭐ **RECOMMENDED**

**Changes Required**:
1. ✅ **Fix task spawning**: Call `DiscoveryService.spawn_diagnostic_recovery()` in `spawn_diagnostic_agent()`
2. ✅ **Use hypothesis generation**: Call `generate_hypotheses()` and use results
3. ✅ **Add Conductor integration**: Query `conductor_analyses` table in `build_diagnostic_context()`
4. ✅ **Add result tracking**: Query `WorkflowResult` in `build_diagnostic_context()`
5. ✅ **Add configuration**: Create `DiagnosticSettings` class
6. ✅ **Add max tasks limit**: Add limit parameter to `spawn_diagnostic_recovery()`

**Pros**: Uses existing infrastructure, minimal changes  
**Cons**: Still different from Hephaestus agent execution model

### Option B: Adopt Hephaestus Model (More Complete)

**Changes Required**:
1. Add `'diagnostic'` agent type
2. Create diagnostic agent execution logic
3. Implement 4-step diagnostic process
4. Add all integrations (Conductor, results, config)
5. Agent uses MCP tools to create tasks

**Pros**: Matches Hephaestus exactly  
**Cons**: More complex, requires new agent type

---

## Conclusion

OmoiOS has **~75% feature parity** with Hephaestus, but the **critical task spawning mechanism is incomplete**. The infrastructure exists (ConductorService, WorkflowResult, hypothesis generation, recovery spawning) but **isn't integrated**.

**Recommendation**: **Option A** - Complete the current implementation by:
1. Actually calling `spawn_diagnostic_recovery()` 
2. Using `generate_hypotheses()` for analysis
3. Integrating Conductor and WorkflowResult queries
4. Adding configuration

This will bring OmoiOS to **~95% feature parity** while maintaining its architectural advantages (DiscoveryService integration).

---

## Related Documents

- [Hephaestus Adoption Analysis](./hephaestus_adoption_analysis.md) - Phase system comparison
- [Diagnostic System README](../diagnostic/README.md) - OmoiOS diagnostic documentation
- [Discovery Service](../implementation/workflows/hephaestus_workflow_enhancements.md) - Discovery/branching system
