# 6a Guardian & Monitoring System

**Part of**: [User Journey Documentation](./README.md)

---

## Overview

OmoiOS includes a sophisticated **self-healing monitoring system** that operates continuously in the background. This system ensures agents stay on track, detect and recover from issues automatically, and learn patterns over time to improve effectiveness.

The monitoring system is a **core differentiator** of OmoiOS—users can trust the system to autonomously manage agent execution while only requiring strategic oversight at approval gates.

---

## Core Components

### 1. Guardian Agent
The Guardian monitors individual agent trajectories every 60 seconds:

- **Trajectory Analysis**: Builds understanding from entire conversation history
- **Alignment Scoring**: Calculates 0.0-1.0 alignment with task goals
- **Constraint Tracking**: Persists constraints throughout the session (even from 20+ minutes ago)
- **Steering Interventions**: Sends targeted messages to keep agents on track

### 2. Conductor Service
The Conductor performs system-wide coherence analysis:

- **Duplicate Work Detection**: Prevents multiple agents from working on same task
- **Conflict Resolution**: Detects and resolves agent conflicts
- **Resource Optimization**: Ensures efficient agent coordination
- **Coherence Scoring**: Measures overall system alignment

### 3. Adaptive Monitoring Loop
The monitoring loop learns and adapts over time:

- **Pattern Discovery**: Extracts reusable patterns from successful workflows
- **Failure Learning**: Identifies and avoids patterns that lead to failures
- **Threshold Adjustment**: Optimizes intervention thresholds based on outcomes
- **Cross-Project Learning**: Shares patterns across organization projects

---

## User Interface Elements

### Header Indicator
```
┌─────────────────────────────────────────────────────────────┐
│  Logo | Projects | 🛡️ Guardian | Search | Notifications     │
│                     ↑                                        │
│                     └── Click to open System Health          │
└─────────────────────────────────────────────────────────────┘

Indicator States:
- 🟢 Active: Monitoring running normally
- 🟡 Paused: Monitoring temporarily paused
- 🔴 Issue: Monitoring system needs attention
- 🔵 Learning: Adaptive loop updating patterns
```

### Sidebar Navigation
```
┌─────────┐
│ Sidebar │
│         │
│ • Home  │
│ • Board │
│ • Graph │
│ • Specs │
│ • Stats │
│ • Agents│
│ • Cost  │
│ • Audit │
│ • Health│ ← NEW: System Health Dashboard
└─────────┘
```

---

## System Health Dashboard

### Main View
```
┌─────────────────────────────────────────────────────────────┐
│  System Health                              [Refresh] [⚙️]  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Status Cards:                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Guardian │  │ Conductor│  │ Agents   │  │ Overall  │   │
│  │ 🟢 Active│  │ 🟢 Active│  │ 5/5 OK   │  │ 94%      │   │
│  │ 12s ago  │  │ 45s ago  │  │ 0 stuck  │  │ Health   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  Tabs: [Overview] [Trajectories] [Interventions] [Insights] │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Overview Tab
Shows real-time monitoring metrics:

- **Monitoring Loop Status**: Last cycle time, cycle interval, agents monitored
- **Aggregate Metrics**: Average alignment score, interventions today, pattern matches
- **Quick Actions**: Pause monitoring, send manual intervention, export logs

### Trajectories Tab
Shows all active agent trajectory analyses:

```
┌──────────────────────────────────────────────────────────────┐
│  Active Trajectory Analyses                                   │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ worker-1                                                 │ │
│  │ ├─ Alignment: 85% ████████████████░░░░ ✅ On Track      │ │
│  │ ├─ Task: "Implement JWT authentication"                  │ │
│  │ ├─ Last Check: 5 seconds ago                            │ │
│  │ ├─ Active Constraints: 2                                 │ │
│  │ │   • "Use Node.js crypto module, no external libraries"│ │
│  │ │   • "All endpoints must return JSON responses"        │ │
│  │ ├─ Mandatory Steps Completed: 3/4                        │ │
│  │ └─ [View Full Trajectory] [Send Intervention]            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ worker-2                                                 │ │
│  │ ├─ Alignment: 72% ██████████████░░░░░░ ⚠️ Drifting      │ │
│  │ ├─ Task: "Add OAuth2 configuration"                      │ │
│  │ ├─ Last Check: 8 seconds ago                            │ │
│  │ ├─ Drift Reason: Scope creep detected                    │ │
│  │ ├─ Intervention Pending: Auto-sending in 15s            │ │
│  │ └─ [View Full Trajectory] [Send Intervention Now]        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Interventions Tab
Shows intervention history and effectiveness:

```
┌──────────────────────────────────────────────────────────────┐
│  Intervention History                        [Export] [Filter]│
│                                                               │
│  Summary: 46/50 successful (92%)                             │
│  Average Recovery Time: 2.3 minutes                          │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Today, 11:45 AM                                         │ │
│  │ Agent: worker-2 | Type: Refocus                          │ │
│  │ Message: "Focus on core authentication flow first"       │ │
│  │ Result: ✅ Success | Recovery: 2.1 min                   │ │
│  │ Alignment: 45% → 82%                                     │ │
│  │ [View Details]                                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Today, 10:30 AM                                         │ │
│  │ Agent: worker-1 | Type: Prioritize                       │ │
│  │ Message: "Complete tests before moving on"               │ │
│  │ Result: ✅ Success | Recovery: 1.5 min                   │ │
│  │ Alignment: 68% → 91%                                     │ │
│  │ [View Details]                                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Insights Tab
Shows pattern learning and adaptive behavior:

```
┌──────────────────────────────────────────────────────────────┐
│  Monitoring Insights                                          │
│                                                               │
│  Pattern Learning:                                            │
│  • Successful patterns stored: 12                            │
│  • Failure patterns avoided: 3                               │
│  • Adaptive thresholds last updated: 2h ago                  │
│                                                               │
│  Common Drift Patterns:                                       │
│  • Scope creep: 34%                                          │
│  • Test skipping: 28%                                         │
│  • Constraint violations: 22%                                 │
│  • Idle after completion: 16%                                 │
│                                                               │
│  Cross-Project Learning:                                      │
│  • Patterns shared from other projects: 8                    │
│  • Patterns contributed: 4                                    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Intervention Types

The Guardian can send different types of steering interventions:

| Type | Description | When Used |
|------|-------------|-----------|
| **Prioritize** | Focus on specific area | Agent working on less important tasks |
| **Refocus** | Change direction | Agent drifting from main objective |
| **Stop** | Halt current work | Agent violating critical constraints |
| **Add Constraint** | Add new requirement | New limitation discovered |
| **Inject Tool Call** | Force specific action | Agent missing mandatory step |
| **Status Reminder** | Request status update | Agent idle after completion |

### Intervention Message Format
```
[GUARDIAN INTERVENTION]

You appear to be {drift_reason}.

Suggested action: {specific_guidance}

Original constraint (from {time_ago}): "{constraint_text}"

Please acknowledge and adjust your approach.
```

---

## Alignment Score Breakdown

The alignment score (0.0-1.0) is calculated from multiple factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Task Progress** | 30% | Progress toward task completion |
| **Constraint Compliance** | 25% | Adherence to all active constraints |
| **Mandatory Steps** | 20% | Completion of required phase steps |
| **Direction Alignment** | 15% | Working toward correct objectives |
| **Activity Status** | 10% | Active work, not idle or stuck |

### Visual Indicators
- 🟢 **85-100%**: On Track - Agent aligned with goals
- 🟡 **70-84%**: Attention Needed - Minor drift detected
- 🟠 **50-69%**: Drifting - Intervention likely needed
- 🔴 **0-49%**: Critical - Immediate intervention required

---

## Configuring the Monitoring System

### Settings → Monitoring

```
┌─────────────────────────────────────────────────────────────┐
│  Monitoring Configuration                                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Guardian Settings:                                         │
│  ├─ Monitoring Cycle Interval: [60] seconds                │
│  ├─ Alignment Threshold: [70]%                              │
│  ├─ Auto-Intervention: [✓] Enabled                         │
│  └─ Intervention Delay: [0] seconds after threshold breach │
│                                                              │
│  Conductor Settings:                                        │
│  ├─ Coherence Check Interval: [120] seconds                │
│  ├─ Duplicate Detection: [✓] Enabled                       │
│  └─ Conflict Resolution: [Auto] / Manual                   │
│                                                              │
│  Notification Preferences:                                  │
│  ├─ [✓] Alignment drops below threshold                    │
│  ├─ [✓] Intervention sent                                  │
│  ├─ [✓] Agent stuck detected                               │
│  ├─ [ ] Every monitoring cycle completed                   │
│  └─ [✓] Critical issues only                               │
│                                                              │
│  Pattern Learning:                                          │
│  ├─ [✓] Enable adaptive threshold adjustment               │
│  ├─ [✓] Share patterns across projects                     │
│  └─ Pattern retention: [30] days                           │
│                                                              │
│  [Save Changes] [Reset to Defaults]                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Real-Time Notifications

Monitoring events are pushed via WebSocket:

| Event | Description | User Action |
|-------|-------------|-------------|
| `MONITORING_CYCLE_COMPLETE` | Guardian completed analysis cycle | None (informational) |
| `ALIGNMENT_DROP` | Agent alignment below threshold | Review agent status |
| `STEERING_ISSUED` | Guardian sent intervention | Review intervention |
| `INTERVENTION_SUCCESS` | Agent recovered after intervention | None (success) |
| `INTERVENTION_FAILED` | Agent didn't recover | Consider manual intervention |
| `STUCK_DETECTED` | Agent appears stuck | Review and intervene |
| `IDLE_DETECTED` | Agent finished but no status update | Send status reminder |
| `CONSTRAINT_VIOLATION` | Agent broke a constraint | Review and correct |
| `COHERENCE_ISSUE` | Conductor detected conflict | Review agent assignments |
| `PATTERN_LEARNED` | New pattern stored | None (informational) |

---

## How the Adaptive Loop Works

```
┌─────────────────────────────────────────────────────────────┐
│                    ADAPTIVE MONITORING LOOP                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. OBSERVE                                                  │
│     └─ Collect agent trajectories, actions, outcomes        │
│                                                              │
│  2. ANALYZE                                                  │
│     └─ Calculate alignment scores, detect drift patterns    │
│                                                              │
│  3. INTERVENE (if needed)                                    │
│     └─ Send targeted steering based on detected issue       │
│                                                              │
│  4. MEASURE                                                  │
│     └─ Track intervention success/failure, recovery time    │
│                                                              │
│  5. LEARN                                                    │
│     ├─ Successful interventions → Store as patterns         │
│     ├─ Failed interventions → Mark as anti-patterns         │
│     └─ Adjust thresholds based on outcomes                  │
│                                                              │
│  6. SHARE                                                    │
│     └─ Propagate patterns across projects (org-wide)        │
│                                                              │
│  ↻ Repeat every 60 seconds                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Benefits

| Benefit | Description |
|---------|-------------|
| **Self-Healing** | System automatically detects and fixes stuck agents |
| **Reduced Oversight** | Users monitor at approval gates, not every step |
| **Continuous Improvement** | System learns from every workflow |
| **Constraint Persistence** | Constraints remembered throughout entire session |
| **Proactive Detection** | Issues caught before they become problems |
| **Organizational Learning** | Patterns shared across all projects |

---

## Common User Journeys

### Journey 1: Checking System Health
```
User logs in → Sees 🛡️ Guardian indicator in header (🟢 Active)
   ↓
Clicks indicator → Opens System Health Dashboard
   ↓
Views Overview tab → Sees 5 agents monitored, avg alignment 78%
   ↓
Notices worker-2 at 72% (⚠️ Drifting) → Clicks to view trajectory
   ↓
Reviews drift reason → Decides to let Guardian auto-intervene
   ↓
Continues with other work → Guardian handles intervention automatically
```

### Journey 2: Reviewing Interventions
```
User receives notification → "Intervention sent to worker-1"
   ↓
Clicks notification → Opens Interventions tab
   ↓
Views intervention details → "Focus on tests first"
   ↓
Sees result → ✅ Success, alignment recovered to 85%
   ↓
Reviews recovery time → 1.5 minutes
   ↓
No action needed → System handled it automatically
```

### Journey 3: Configuring Thresholds
```
User notices too many interventions → Opens Settings → Monitoring
   ↓
Reviews current threshold → 70%
   ↓
Adjusts to 65% → Reduces intervention frequency
   ↓
Enables "Critical issues only" notifications
   ↓
Saves changes → System applies new configuration
```

---

## Related Documentation

- [03_execution_monitoring.md](./03_execution_monitoring.md) - Execution phase monitoring details
- [05_optimization.md](./05_optimization.md) - Monitoring insights and optimization
- [06_key_interactions.md](./06_key_interactions.md) - Monitoring interactions and notifications
- [11_cost_memory_management.md](./11_cost_memory_management.md) - Cost budgets, Memory patterns, and Alert management
- [Product Vision](../product_vision.md) - Adaptive Monitoring Loop architecture

---

**Next**: See [README.md](./README.md) for complete documentation index.

