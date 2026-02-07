# Part 4: The Readjustment System

> Extracted from [ARCHITECTURE.md](../../ARCHITECTURE.md) — see hub doc for full system overview.

## Purpose

Monitor agent trajectories and system coherence, intervening when agents drift from goals.

## Location

```
backend/omoi_os/services/
├── monitoring_loop.py         # Main orchestrator
├── intelligent_guardian.py    # Per-agent trajectory analysis
├── conductor.py               # System-wide coherence
├── validation_orchestrator.py # Validation agent management
```

## MonitoringLoop Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MonitoringLoop                                  │
│                                                                          │
│  Three background loops:                                                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │  Guardian Loop    │  │  Conductor Loop   │  │  Health Check     │   │
│  │  (60s interval)   │  │  (5min interval)  │  │  (30s interval)   │   │
│  │                   │  │                   │  │                   │   │
│  │  Per-agent        │  │  System-wide      │  │  Alerts for       │   │
│  │  trajectory       │  │  coherence        │  │  critical states  │   │
│  │  analysis         │  │  + duplicates     │  │                   │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘   │
│                                                                          │
│  Metrics tracked:                                                        │
│  - total_cycles, successful_cycles, failed_cycles                       │
│  - total_interventions                                                   │
│  - success_rate                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## IntelligentGuardian (Per-Agent Analysis)

**Analysis Output:**

```python
TrajectoryAnalysis(
    agent_id="agent-123",
    alignment_score=0.85,      # 0.0 - 1.0
    trajectory_aligned=True,   # On track for goal?
    needs_steering=False,      # Requires intervention?
    steering_type=None,        # "redirect", "refocus", "stop"
    steering_recommendation=None,
    trajectory_summary="Agent progressing on auth implementation",
    current_focus="Adding JWT validation",
    conversation_length=45,
    session_duration=timedelta(minutes=23),
)
```

**Steering Intervention Types:**

| Type | When | Action |
|------|------|--------|
| `redirect` | Agent going wrong direction | Inject message with new direction |
| `refocus` | Agent drifting from scope | Remind of original goal |
| `stop` | Agent causing harm | Terminate execution |

## ConductorService (System Coherence)

**Coherence Score Formula:**

```
coherence = base_alignment - trajectory_penalty - steering_penalty + bonuses

Where:
- base_alignment = average alignment across all agents
- trajectory_penalty = (unaligned_agents / total_agents) * 0.2
- steering_penalty = (agents_needing_steering / total_agents) * 0.1
- bonuses = efficiency_bonus + completion_bonus
```

**System Status Classification:**

| Status | Condition |
|--------|-----------|
| `critical` | coherence < 0.3 |
| `warning` | coherence < 0.5 |
| `inefficient` | coherence < 0.7 |
| `optimal` | coherence >= 0.9 |
| `normal` | otherwise |

**Duplicate Detection:**

```python
# LLM compares same-phase agent pairs
for agent_a, agent_b in pairwise(agents_in_phase):
    prompt = f"Are {agent_a.focus} and {agent_b.focus} duplicates?"
    if llm.is_duplicate(agent_a, agent_b):
        recommendations.append(f"Merge {agent_a.id} and {agent_b.id}")
```

## ValidationOrchestrator

**State Machine:**

```
pending → assigned → in_progress → under_review → validation_in_progress → done
                                        ↓                    ↓
                                   needs_work ←──────────────┘
                                        ↓
                              (after 2+ failures)
                                        ↓
                              DiagnosticService auto-spawn
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/monitoring_loop.py` | Main orchestrator (~669 lines) |
| `backend/omoi_os/services/intelligent_guardian.py` | Per-agent analysis (~1122 lines) |
| `backend/omoi_os/services/conductor.py` | System coherence (~919 lines) |
| `backend/omoi_os/services/validation_orchestrator.py` | Validation agent management |

## Related Documentation

- [Monitoring Architecture](../design/monitoring/monitoring_architecture.md) — detailed monitoring design
