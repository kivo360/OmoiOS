# 6 Key Interactions

**Part of**: [User Journey Documentation](./README.md)

---
## Key User Interactions

### Primary Flow: Sandbox Interaction

The main user interaction pattern centers on creating and monitoring sandboxes:

**1. Create Sandbox (Command Center)**
```
/command page:
┌──────────────────────────────────────────────┐
│ What do you want to build?                   │
│                                              │
│ [Large text input area]                      │
│                                              │
│ User types: "Add payment processing with     │
│ Stripe integration including webhooks"       │
│                                              │
│                           [Submit Button] →  │
└──────────────────────────────────────────────┘
```

**2. Wait for Sandbox Spawn**
- Submit creates a ticket via API
- System shows loading state while orchestrator processes
- WebSocket listens for `SANDBOX_SPAWNED` event
- Fallback polling every 3s if WebSocket misses event

**3. Auto-redirect to Sandbox Detail**
- Once `sandbox_id` received, redirect to `/sandbox/:sandboxId`
- TasksPanel highlights the new sandbox as "Running"

**4. Monitor Agent in Real-Time**

Events render beautifully via the `EventRenderer` component with specialized cards:

```
/sandbox/:sandboxId page:
┌──────────────────────────────────────────────┐
│ [Events] [Details]                           │
├──────────────────────────────────────────────┤
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ 🤔 Thinking                              │ │
│ │ "Analyzing Stripe integration patterns"  │ │
│ └──────────────────────────────────────────┘ │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ $ Terminal                               │ │
│ │ $ pnpm add stripe                        │ │
│ │ + stripe@14.0.0                          │ │
│ └──────────────────────────────────────────┘ │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ + Created  📜 payment.ts         +45     │ │
│ │ ─────────────────────────────────────────│ │
│ │  1 │ import Stripe from 'stripe';       │ │
│ │  2 │                                     │ │
│ │  3 │ export const stripe = new Stripe(  │ │
│ │  4 │   process.env.STRIPE_SECRET_KEY!   │ │
│ │  5 │ );                                  │ │
│ └──────────────────────────────────────────┘ │
│                                              │
└──────────────────────────────────────────────┘
```

**Event Card Types:**
- **MessageCard**: Agent messages with Markdown, thinking indicator
- **FileWriteCard**: Cursor-style diffs with syntax highlighting, language icons
- **BashCard**: Terminal with `$` prompt, stdout/stderr, exit codes
- **GlobCard**: Tree-style file listings
- **GrepCard**: Search results grouped by directory
- **TodoCard**: Task progress with status icons

**5. Interact with Agent**
```
┌──────────────────────────────────────────────┐
│ [Message input]                              │
│ "Make sure to use webhook signature          │
│ verification for security"            [Send] │
└──────────────────────────────────────────────┘
```
- Messages sent to running agent as context
- Agent incorporates feedback into its work

**6. Navigate Between Sandboxes**
- TasksPanel shows all sandboxes grouped by status
- Click any sandbox to view its detail page
- Current sandbox highlighted in panel

---

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
- **Sandbox events**: Agent thinking, tool use, file edits stream in real-time
- **TasksPanel**: Sandbox status changes (Running → Completed/Failed)
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

### Monitoring System Access
Users can monitor system health at any time:
- **Header Indicator**: 🛡️ Guardian status icon shows monitoring state (🟢 active, 🟡 paused, 🔴 issue)
- **System Health Dashboard**: Access via sidebar "Health" or header indicator click
- **Real-time Alignment Scores**: View all agents' trajectory alignment in real-time
- **Intervention History**: Review past interventions with success/failure rates
- **Pattern Learning Insights**: See how the system is learning and adapting
- **Configure Thresholds**: Settings → Monitoring to adjust intervention thresholds

### Monitoring Notifications
Real-time alerts pushed via WebSocket:
- **Alignment Drop**: Agent alignment falls below threshold (e.g., < 70%)
- **Intervention Sent**: Guardian sends steering message to agent
- **Stuck Detection**: Agent appears stuck (same error 5+ times)
- **Idle Detection**: Agent finished but hasn't updated status
- **Constraint Violation**: Agent breaks rules from earlier in conversation
- **Coherence Issue**: Conductor detects duplicate work or agent conflict

### Monitoring Quick Actions
From any monitoring view:
- **Send Manual Intervention**: Override Guardian with custom steering message
- **Pause Monitoring**: Temporarily pause Guardian analysis for specific agent
- **Adjust Threshold**: Quick-adjust alignment threshold for current workflow
- **View Trajectory**: Drill into full agent trajectory analysis
- **Export Logs**: Download monitoring logs for debugging

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
