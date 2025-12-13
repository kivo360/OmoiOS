# Frontend Integration for Sandbox Agents

**Created**: 2025-12-12  
**Status**: Addendum to Existing UI Docs  
**Priority**: Optional (Phase 5 enhancement)

---

## Overview

This document describes **sandbox-specific additions** to the existing frontend. It is NOT a standalone UI spec—the comprehensive UI documentation already exists:

### Existing UI Documentation (Reference These First!)

| Document | Location | Covers |
|----------|----------|--------|
| **Agent Management** | [`page_flows/03_agents_workspaces.md`](../../page_flows/03_agents_workspaces.md) | Agent list, detail view, trajectory, interventions |
| **Command Center** | [`page_flows/10_command_center.md`](../../page_flows/10_command_center.md) | Primary landing, agent spawning, Guardian indicator |
| **Monitoring System** | [`page_flows/10a_monitoring_system.md`](../../page_flows/10a_monitoring_system.md) | System health, trajectory analysis, intervention management |
| **Execution Monitoring** | [`user_journey/03_execution_monitoring.md`](../../user_journey/03_execution_monitoring.md) | User journey for monitoring agents |

---

## What Already Exists (No Changes Needed)

These features are **already designed** in the existing docs:

| Feature | Location | Status |
|---------|----------|--------|
| Agent list with status indicators | `03_agents_workspaces.md` | ✅ Designed |
| Agent detail view with tabs | `03_agents_workspaces.md` | ✅ Designed |
| Real-time activity feed | `10_command_center.md` | ✅ Designed |
| Trajectory timeline | `10a_monitoring_system.md` | ✅ Designed |
| Send intervention UI | `10a_monitoring_system.md` | ✅ Designed |
| Guardian status indicator | `10_command_center.md` | ✅ Designed |
| WebSocket event integration | `10a_monitoring_system.md` | ✅ Designed |
| Agent spawning modal | `03_agents_workspaces.md` | ✅ Designed |

---

## Sandbox-Specific Additions

The following are **new UI elements** specific to sandbox agents that need to be added:

### 1. Sandbox Lifecycle Badge

**Where**: Agent list cards and detail view header

**Current Design** (from `03_agents_workspaces.md`):
```
│ Agent: worker-1                                │
│ Status: 🟢 Active                               │
│ Phase: IMPLEMENTATION                          │
```

**Sandbox Addition**:
```
│ Agent: worker-1                                │
│ Status: 🟢 Active                               │
│ Phase: IMPLEMENTATION                          │
│ Sandbox: ☁️ Daytona • Running                  │  ← NEW
│ Branch: feature/TICKET-123-auth               │  ← NEW
```

**Sandbox Lifecycle States**:
| State | Badge | Color |
|-------|-------|-------|
| PENDING | `⏳ Pending` | Gray |
| CREATING | `🔄 Creating` | Blue |
| RUNNING | `☁️ Running` | Green |
| COMPLETING | `📦 Creating PR` | Yellow |
| COMPLETED | `✅ Completed` | Green |
| FAILED | `❌ Failed` | Red |

---

### 2. Branch & PR Section

**Where**: Agent detail view → New "Git" tab (after existing tabs)

```
┌──────────────────────────────────────────────────────┐
│  Tabs: [Overview] [Trajectory] [Tasks] [Logs] [Git]  │
│                                               ^^^^^   │
│                                               NEW     │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Git Tab                                             │
│                                                      │
│  Repository: kivo360/auth-system                    │
│  Branch: feature/TICKET-123-oauth-setup             │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  Commits (3)                                   │ │
│  │                                                │ │
│  │  abc1234 feat: add OAuth2 configuration       │ │
│  │          5 files changed, +127 -12            │ │
│  │          12 minutes ago                        │ │
│  │                                                │ │
│  │  def5678 refactor: extract auth service       │ │
│  │          3 files changed, +45 -8              │ │
│  │          8 minutes ago                         │ │
│  │                                                │ │
│  │  ghi9012 fix: handle token expiration         │ │
│  │          2 files changed, +18 -3              │ │
│  │          2 minutes ago                         │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  Pull Request:                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  PR #42: [TICKET-123] Implement OAuth setup   │ │
│  │  Status: 🟢 Ready for review                  │ │
│  │  Base: main ← feature/TICKET-123-oauth-setup  │ │
│  │                                                │ │
│  │  [View on GitHub] [Approve & Merge]           │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  Merge Conflicts: None ✅                           │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

### 3. Sandbox Resource Indicator

**Where**: Agent detail view header (alongside existing heartbeat)

**Current Design**:
```
│ Heartbeat: 5s ago ✓                            │
```

**Sandbox Addition**:
```
│ Heartbeat: 5s ago ✓                            │
│ Sandbox: ☁️ us-east-1 • 2.1 GB memory          │  ← NEW
│ Uptime: 23m 15s                                │  ← NEW
```

---

### 4. Clone Status During Spawn

**Where**: Spawn agent modal → Processing step

**Enhancement** to existing spawn flow in `10_command_center.md`:

```
┌──────────────────────────────────────────────────────┐
│  Processing...                                       │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ 1. Creating project (if needed)...  ✓         │ │
│  │ 2. Spawning sandbox environment...   ✓         │ │  ← NEW
│  │ 3. Cloning repository...             ⟳         │ │  ← NEW
│  │    kivo360/auth-system (124 MB)               │ │
│  │    ████████████░░░░░░░░ 60%                   │ │
│  │ 4. Creating branch...                ⏳         │ │  ← NEW
│  │ 5. Starting agent...                 ⏳         │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

### 5. User Message Panel (Sandbox-Specific)

**Where**: Agent detail view → Bottom of page (like existing intervention modal but for users)

The existing intervention UI in `10a_monitoring_system.md` is for **Guardian-initiated** interventions. For sandbox agents, we need a simpler **user message** panel:

```
┌──────────────────────────────────────────────────────┐
│  Send Message to Agent                               │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ Also add input validation for the email field │ │
│  │ and make sure to handle empty strings.        │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  ℹ️ Message will be delivered before next action    │
│                                                      │
│  [Send Message]                                      │
└──────────────────────────────────────────────────────┘
```

**API**: Uses existing `POST /api/v1/sandboxes/{id}/messages` endpoint.

**Difference from Guardian Intervention**:
- User messages use `[USER MESSAGE]` prefix
- No intervention type selection (always "guidance")
- Simpler UI without alignment tracking

---

## New API Endpoints Needed

These endpoints are **in addition to** existing APIs documented in `10a_monitoring_system.md`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/sandboxes/{id}` | GET | Get sandbox details (lifecycle, branch, PR) |
| `/api/v1/sandboxes/{id}/git/commits` | GET | Get commits from sandbox branch |
| `/api/v1/sandboxes/{id}/git/pr` | GET | Get PR status if created |
| `/api/v1/sandboxes/{id}/git/pr/merge` | POST | Merge PR (user action) |

**Note**: Core sandbox message/event APIs are already defined in:
- [`04_communication_patterns.md`](./04_communication_patterns.md)
- [`05_http_api_migration.md`](./05_http_api_migration.md)

---

## WebSocket Event Additions

Add these events to the existing event types in `10a_monitoring_system.md`:

| Event Type | Entity Type | Description |
|------------|-------------|-------------|
| `SANDBOX_CREATED` | sandbox | Sandbox environment created |
| `SANDBOX_CLONE_STARTED` | sandbox | Git clone began |
| `SANDBOX_CLONE_COMPLETED` | sandbox | Git clone finished |
| `SANDBOX_BRANCH_CREATED` | sandbox | Feature branch created |
| `SANDBOX_PR_CREATED` | sandbox | Pull request created |
| `SANDBOX_PR_MERGED` | sandbox | Pull request merged |
| `SANDBOX_TERMINATED` | sandbox | Sandbox shut down |

---

## Integration Points with Existing UI

### Agent List (`/agents`)

**Modification**: Add sandbox indicator to agent cards

```tsx
// In existing AgentCard component
{agent.sandbox_id && (
  <div className="sandbox-badge">
    <CloudIcon /> {agent.sandbox_status}
  </div>
)}
```

### Agent Detail View (`/agents/:agentId`)

**Modification**: Add Git tab if agent has `sandbox_id`

```tsx
// In existing agent detail page
const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'trajectory', label: 'Trajectory' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'logs', label: 'Logs' },
  // Conditionally add Git tab for sandbox agents
  ...(agent.sandbox_id ? [{ id: 'git', label: 'Git' }] : []),
];
```

### Command Center (`/`)

**Modification**: Spawn flow shows clone progress for sandbox agents

```tsx
// In existing spawn processing component
{spawnConfig.useSandbox && (
  <>
    <ProcessStep status={cloneStatus}>
      Cloning repository... {cloneProgress}%
    </ProcessStep>
    <ProcessStep status={branchStatus}>
      Creating branch: {branchName}
    </ProcessStep>
  </>
)}
```

---

## Implementation Priority

Since the core agent UI already exists, sandbox-specific additions are **lower priority**:

| Feature | Priority | Effort | Depends On |
|---------|----------|--------|------------|
| Sandbox lifecycle badge | Medium | 2h | Backend API |
| Clone progress in spawn | Medium | 3h | Spawn flow exists |
| Git tab with commits/PR | Low | 4h | Branch workflow (Phase 5) |
| User message panel | Low | 2h | Message API exists |

**Total Sandbox-Specific UI Effort**: ~11 hours

---

## Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SANDBOX UI: BUILD ON EXISTING UI                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EXISTING UI (No changes needed):                                           │
│  ├─ Agent list page             → 03_agents_workspaces.md                   │
│  ├─ Agent detail with tabs      → 03_agents_workspaces.md                   │
│  ├─ Trajectory & interventions  → 10a_monitoring_system.md                  │
│  ├─ Real-time WebSocket events  → 10a_monitoring_system.md                  │
│  └─ Command center & spawn      → 10_command_center.md                      │
│                                                                             │
│  SANDBOX ADDITIONS (This document):                                         │
│  ├─ Sandbox lifecycle badge     → Agent cards & detail header               │
│  ├─ Git tab with branch/PR      → New tab in agent detail                   │
│  ├─ Clone progress during spawn → Enhancement to spawn modal                │
│  └─ User message panel          → Simple UI for sending messages            │
│                                                                             │
│  KEY INSIGHT: Most UI already exists! Sandbox agents are just               │
│  "agents with extra context" - reuse existing components.                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documents

- [Architecture](./01_architecture.md) - System design
- [Communication Patterns](./04_communication_patterns.md) - API specs with security
- [Implementation Checklist](./06_implementation_checklist.md) - Phase 5 details
- [Agent Management (Existing)](../../page_flows/03_agents_workspaces.md) - Core agent UI
- [Monitoring System (Existing)](../../page_flows/10a_monitoring_system.md) - Health & interventions
