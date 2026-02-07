# Part 3: The Discovery System

> Extracted from [ARCHITECTURE.md](../../ARCHITECTURE.md) — see hub doc for full system overview.

## Purpose

Enable adaptive workflow branching when agents discover new requirements during execution.

## Location

```
backend/omoi_os/services/
├── discovery.py           # Core discovery recording + branching
├── discovery_analyzer.py  # LLM-powered pattern analysis
```

## Hephaestus Pattern

**Key Insight**: Discovery-based branching **bypasses** `PhaseModel.allowed_transitions`. A Phase 3 validation agent can spawn Phase 1 investigation tasks.

```
Normal Transition:      PHASE_IMPLEMENTATION → PHASE_TESTING → PHASE_DEPLOYMENT

Discovery Branch:       PHASE_TESTING → (discovery) → PHASE_IMPLEMENTATION
                        ↑                              ↓
                        └──────────────────────────────┘
                              (can spawn ANY phase)
```

## Discovery Types

| Type | Trigger | Priority Boost |
|------|---------|----------------|
| `BUG_FOUND` | Agent finds bug during validation | Yes |
| `BLOCKER_IDENTIFIED` | Blocking dependency discovered | Yes |
| `MISSING_DEPENDENCY` | Required component missing | Yes |
| `OPTIMIZATION_OPPORTUNITY` | Performance improvement found | No |
| `DIAGNOSTIC_NO_RESULT` | Stuck workflow recovery | Yes |

## Discovery Flow

```python
# Agent discovers a bug during validation
discovery, spawned_task = discovery_service.record_discovery_and_branch(
    session=session,
    source_task_id="task-123",
    discovery_type=DiscoveryType.BUG_FOUND,
    description="Authentication fails for expired tokens",
    spawn_phase_id="PHASE_IMPLEMENTATION",  # Goes BACK to implementation
    spawn_description="Fix token expiration handling",
    priority_boost=True,  # MEDIUM → HIGH
)
# New task created and linked to discovery for traceability
```

## DiscoveryAnalyzerService

LLM-powered analysis of discovery patterns:

| Method | Purpose |
|--------|---------|
| `analyze_patterns()` | Find recurring patterns across discoveries |
| `predict_blockers()` | Predict likely blockers based on history |
| `recommend_agent()` | Suggest best agent type for a discovery |
| `summarize_workflow_health()` | Comprehensive health metrics |

**Example Output:**

```python
PatternAnalysisResult(
    patterns=[
        DiscoveryPattern(
            pattern_type="recurring_bug",
            description="Token handling issues",
            severity="high",
            affected_components=["AuthService", "TokenValidator"],
            suggested_action="Add comprehensive token tests",
            confidence=0.85
        )
    ],
    health_score=0.72,
    hotspots=["AuthService"],
    recommendations=["Add token expiration tests before deployment"]
)
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/discovery.py` | Core discovery + branching (~519 lines) |
| `backend/omoi_os/services/discovery_analyzer.py` | LLM pattern analysis (~515 lines) |
