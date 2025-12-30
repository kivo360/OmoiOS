# Overview

**Part of**: [User Journey Documentation](./README.md)

---

## The Core Promise

**Start a feature before bed. Wake up to a PR.**

OmoiOS lets AI run overnight and finish your software for you. You describe what you want built, approve a plan, and go to sleep. While you're away, agents autonomously write code, run tests, fix bugs, and create PRs. You wake up to completed work ready for review.

---

## The Overnight Story

```
9:00 PM - You type: "Add payment processing with Stripe"
        ↓
9:02 PM - OmoiOS generates plan (Requirements → Design → Tasks)
        ↓
9:05 PM - You review & approve plan
        ↓
9:06 PM - You go to bed 😴
        ↓
   [Agents work through the night]
        ├── Agent 1: Building payment API
        ├── Agent 2: Writing tests
        ├── Agent 3: Discovers bug → fixes it
        └── Guardian: Keeps agents on track, sends corrections
        ↓
7:00 AM - You wake up ☀️
        ↓
   ☕ Coffee + PR Review (5 min)
        ↓
   🎉 Feature merged before standup
```

**Your time: 10 minutes | AI work time: 10 hours | Feature: Complete**

---

## How It Works: Interconnected Problem-Solving

OmoiOS workflows are **interconnected problem-solving graphs**, not linear pipelines. The workflow structure emerges from what agents discover as they work.

### Key Workflow Patterns

| Pattern | Description |
|---------|-------------|
| **Ticket Threading** | Tickets move through phases (Requirements → Design → Implementation → Testing) preserving all context—comments, commits, decisions |
| **Discovery Branching** | Agents find bugs, optimizations, or missing requirements → spawn new tasks → workflow branches dynamically |
| **Feedback Loops** | Validation fails → spawns fix task → revalidates → loops until success |
| **Phase Jumping** | Implementation discovers missing requirements → spawns clarification task → adapts to reality |
| **Parallel Execution** | Multiple agents work on different components simultaneously |

### Self-Healing System

**Guardian agents monitor every 60 seconds:**
- Detects when agents drift, get stuck, or violate constraints
- Sends targeted interventions: "Focus on core authentication flow first"
- Alignment scores (0-100%) show agent health at a glance
- Users see interventions happen but rarely need to act

---

## Overview

OmoiOS follows a **spec-driven autonomous engineering workflow** where users describe what they want built, and the system automatically plans, executes, and monitors the work. Users provide strategic oversight at approval gates rather than micromanaging every step.

---

## Dashboard Layout

### Current Implementation

The UI uses a three-column layout with IconRail navigation and route-aware contextual panels.

**Key Components:**
- `frontend/components/layout/IconRail.tsx` - Primary navigation
- `frontend/components/layout/ContextualPanel.tsx` - Route-aware sidebar
- `frontend/components/panels/TasksPanel.tsx` - Sandbox tasks grouped by status

### Main Dashboard Structure

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌──────┐  ┌─────────────────┐  ┌──────────────────────────────────┐  │
│  │Icon  │  │ Contextual      │  │  Main Content Area                │  │
│  │Rail  │  │ Panel           │  │                                   │  │
│  │      │  │                 │  │  Route-specific content:          │  │
│  │ Logo │  │ Route-aware     │  │                                   │  │
│  │      │  │ sidebar that    │  │  /command → Prompt input +        │  │
│  │ ──── │  │ changes based   │  │             loading state         │  │
│  │ Term │  │ on pathname:    │  │                                   │  │
│  │ Proj │  │                 │  │  /sandbox/:id → Event stream +    │  │
│  │ Phas │  │ /command →      │  │                 agent chat        │  │
│  │ Sand │  │   TasksPanel    │  │                                   │  │
│  │ Anal │  │                 │  │  /projects → Project grid         │  │
│  │ Orgs │  │ /sandbox/* →    │  │                                   │  │
│  │      │  │   TasksPanel    │  │  /phases → Workflow phases        │  │
│  │ ──── │  │                 │  │                                   │  │
│  │ Sett │  │ /projects →     │  │  /sandboxes → All sandboxes       │  │
│  │      │  │   ProjectsPanel │  │                                   │  │
│  │      │  │                 │  │  /analytics → Metrics dashboard   │  │
│  │      │  │ /phases →       │  │                                   │  │
│  │      │  │   PhasesPanel   │  │  /organizations → Team mgmt       │  │
│  │      │  │                 │  │                                   │  │
│  └──────┘  └─────────────────┘  └──────────────────────────────────┘  │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### IconRail Navigation

| Icon | Section | Route | Description |
|------|---------|-------|-------------|
| Terminal | Command | `/command` | Primary entry point - describe what to build |
| FolderGit2 | Projects | `/projects` | Project management and selection |
| Workflow | Phases | `/phases` | Workflow phase configuration |
| Box | Sandboxes | `/sandboxes` | List of all sandbox executions |
| BarChart3 | Analytics | `/analytics` | Usage metrics and performance |
| Building2 | Organizations | `/organizations` | Team and org management |
| Settings | Settings | `/settings` | User and system preferences |

### ContextualPanel Mapping

| Route Pattern | Panel | Content |
|---------------|-------|---------|
| `/command` | TasksPanel | Sandboxes grouped by status (Running, Pending, Completed, Failed) |
| `/sandbox/*` | TasksPanel | Same as above, with current sandbox highlighted |
| `/projects` | ProjectsPanel | Project list and quick actions |
| `/phases` | PhasesPanel | Phase configuration |
| `/sandboxes` | TasksPanel | Full sandbox history |

### TasksPanel Structure

The TasksPanel groups sandbox tasks by execution status:

```
┌─────────────────────┐
│ Running             │  ← Currently executing sandboxes
│ ├─ Payment API      │
│ └─ Auth System      │
├─────────────────────┤
│ Pending             │  ← Queued for execution
│ └─ Database Setup   │
├─────────────────────┤
│ Completed           │  ← Successfully finished
│ ├─ User Profile     │
│ └─ API Routes       │
├─────────────────────┤
│ Failed              │  ← Execution errors
│ └─ Image Upload     │
└─────────────────────┘
```

Clicking any task navigates to `/sandbox/:sandboxId` for detailed monitoring.

---


## Key User Interactions

### Command Palette (Cmd+K)
Quick navigation to:
- Create new ticket
- Search tickets/tasks/commits
- Navigate to projects
- Open spec workspace
- View agent status
- Access settings

### Real-Time Updates
All views update automatically via WebSocket:
- Kanban board: Tickets move as agents work
- Dependency graph: Nodes update as tasks complete
- Activity timeline: New events appear instantly
- Agent status: Heartbeats update every 30s

### Intervention Tools
Users can intervene at any time:
- Pause/resume workflows
- Add constraints: "Make sure to use port 8020"
- Prioritize: "Focus on tests first"
- Refocus: "Switch to authentication flow"
- Stop: "Halt current work"

### Spec Management
Users can:
- View/edit specs in multi-tab workspace
- Switch between multiple specs
- Export specs to Markdown/YAML
- Version control specs
- Link specs to tickets

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
