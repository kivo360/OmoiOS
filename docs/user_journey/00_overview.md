# Overview

**Part of**: [User Journey Documentation](./README.md)

---
## Overview

OmoiOS follows a **spec-driven autonomous engineering workflow** where users describe what they want built, and the system automatically plans, executes, and monitors the work. Users provide strategic oversight at approval gates rather than micromanaging every step.

---

## Dashboard Layout

### Main Dashboard Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Logo | Projects | Search | Notifications | Profile  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐  ┌──────────────────────────────────────┐   │
│  │ Sidebar │  │  Main Content Area                    │   │
│  │         │  │                                       │   │
│  │ • Home  │  │  ┌────────────────────────────────┐ │   │
│  │ • Board │  │  │ Overview Section                │ │   │
│  │ • Graph │  │  │ • Total Specs: 5                │ │   │
│  │ • Specs │  │  │ • Active Agents: 3              │ │   │
│  │ • Stats │  │  │ • Tickets in Progress: 12        │ │   │
│  │ • Agents│  │  │ • Recent Commits: 8              │ │   │
│  │ • Cost  │  │  └────────────────────────────────┘ │   │
│  │ • Audit │  │                                       │   │
│  │         │  │  ┌────────────────────────────────┐ │   │
│  │         │  │  │ Active Specs Grid               │ │   │
│  │         │  │  │                                │ │   │
│  │         │  │  │ ┌──────────┐  ┌──────────┐   │ │   │
│  │         │  │  │ │ Spec 1    │  │ Spec 2    │   │ │   │
│  │         │  │  │ │ Progress: │  │ Progress: │   │ │   │
│  │         │  │  │ │ ████░░ 60%│  │ ██████ 80%│   │ │   │
│  │         │  │  │ └──────────┘  └──────────┘   │ │   │
│  │         │  │  └────────────────────────────────┘ │   │
│  │         │  │                                       │   │
│  │         │  │  ┌────────────────────────────────┐ │   │
│  │         │  │  │ Quick Actions                   │ │   │
│  │         │  │  │ [+ New Spec] [+ New Project]   │ │   │
│  │         │  │  └────────────────────────────────┘ │   │
│  └─────────┘  └──────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Right Sidebar (Collapsible)                        │  │
│  │  Recent Activity Feed                                │  │
│  │  • Spec "Auth System" requirements approved          │  │
│  │  • Agent worker-1 completed task "Setup JWT"        │  │
│  │  • Discovery: Bug found in login flow               │  │
│  │  • Guardian intervention sent to worker-2            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Dashboard Sections:**
- **Overview Section**: Key metrics (total specs, active agents, tickets in progress, recent commits)
- **Active Specs Grid**: Cards showing all active specs with progress bars
- **Quick Actions**: Buttons for common actions (+ New Spec, + New Project)
- **Recent Activity Sidebar**: Chronological feed of recent events (collapsible)

**Managing Multiple Specs:**
- Dashboard shows grid view of all active specs
- Each spec card displays:
  - Spec name and description
  - Progress bar (0-100%)
  - Status badge (Draft, Requirements, Design, Tasks, Executing, Completed)
  - Last updated timestamp
  - Quick actions ([View] [Edit] [Export])
- Filter options: All | Active | Completed | Draft
- Search bar to find specs by name

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
