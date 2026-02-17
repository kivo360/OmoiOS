# 1 Additional Flows

**Part of**: [User Journey Documentation](./README.md)

---
## Additional Flows & Edge Cases

### Error Handling & Failure Recovery

#### Agent Failure Scenarios

**Task Execution Failure:**
```
Agent fails to complete task:
   ↓
1. System detects failure (timeout, exception, test failure)
   ↓
2. Automatic retry logic:
   - Exponential backoff (1s, 2s, 4s, 8s + jitter)
   - Maximum retry attempts (configurable)
   - Error classification (retryable vs permanent)
   ↓
3. If retryable:
   - Agent retries with updated context
   - Guardian may provide intervention
   ↓
4. If permanent failure:
   - Task marked as failed
   - Discovery created (type: "bug" or "clarification_needed")
   - User notified
   - Option to spawn new task or update requirements
```

**Agent Stuck Detection:**
```
Agent stops responding:
   ↓
1. Heartbeat timeout (90s without heartbeat)
   ↓
2. System marks agent as "stuck"
   ↓
3. Guardian analyzes trajectory:
   - Checks alignment score
   - Reviews recent actions
   - Determines intervention needed
   ↓
4. Guardian sends intervention:
   - "[GUARDIAN INTERVENTION] Please provide status update"
   ↓
5. If no response:
   - Agent marked as failed
   - Task reassigned to new agent
   - Original agent's work preserved
```

**Spec Generation Failure:**
```
AI fails to generate spec:
   ↓
1. User sees error message:
   - "Unable to generate spec. Please try again or provide more details."
   ↓
2. Options:
   - Retry with same input
   - Provide more context
   - Use manual spec creation
   ↓
3. System logs error for analysis
   ↓
4. User can contact support if persistent
```

### Notification & Alert Flows

#### Notification Types

**In-App Notifications:**
```
Notification Center (Bell Icon):
   ↓
Shows unread notifications:
- Phase transition approval pending
- PR ready for review
- Agent stuck/failed
- Discovery made
- Budget threshold exceeded
- WIP limit violation
   ↓
Click notification → Navigate to relevant page
   ↓
Mark as read / Dismiss
```

**Email Notifications:**
```
User configures email preferences:
   ↓
Receives emails for:
- Critical: Agent failures, budget exceeded
- Important: Phase approvals, PR reviews
- Informational: Task completions, discoveries
   ↓
Email contains:
- Summary of event
- Direct link to relevant page
- Action buttons (Approve/Reject)
```

**Slack/Webhook Integration:**
```
Configure webhook in settings:
   ↓
System sends webhook events:
- Ticket created/completed
- Agent status changes
- Discovery events
- Approval requests
   ↓
Slack channel receives updates:
- Rich formatted messages
- Links back to dashboard
- Quick action buttons
```

**Cost & Budget Alerts:**
```
System monitors cost thresholds:
   ↓
Budget warning triggered (e.g., 80% utilization):
   - Alert created (severity: warning)
   - In-app notification shown
   - Email sent (if configured)
   ↓
User views alert:
   - Click notification or Cost → Budgets
   - See current spend vs limit
   - Options: [Increase Limit] [View Records]
   ↓
If hard limit exceeded:
   - Agents automatically paused
   - Alert severity: critical
   - User must take action to resume
```

**Memory & Pattern Alerts:**
```
Pattern learning events:
   ↓
New pattern extracted:
   - Alert created (severity: info)
   - Shows pattern name and confidence
   - Links to pattern details
   ↓
Pattern confidence declining:
   - Alert created (severity: warning)
   - Suggests pattern review
   - Links to affected tasks
```

> 💡 **For detailed cost and memory flows**, see [11_cost_memory_management.md](./11_cost_memory_management.md).

### Settings & Configuration

#### User Settings Flow

**Profile Settings:**
```
Navigate to /settings/profile:
   ↓
Configure:
- Display name
- Email preferences
- Timezone
- Language
- Theme (light/dark)
   ↓
Save changes → Applied immediately
```

**Notification Preferences:**
```
Navigate to /settings/notifications:
   ↓
Configure per notification type:
- In-app: ✓ Enabled
- Email: ✓ Enabled
- Slack: ✓ Enabled
   ↓
Set frequency:
- Real-time
- Daily digest
- Weekly summary
   ↓
Save preferences
```

**Integration Settings:**
```
Navigate to /settings/integrations:
   ↓
GitHub Integration:
- Connected repositories
- Webhook status
- Permissions granted
- [Reconnect] [Disconnect]
   ↓
Slack Integration:
- Workspace connection
- Channel selection
- Event subscriptions
- [Connect] [Disconnect]
```

#### Project Settings Flow

**Project Configuration:**
```
Navigate to /projects/:id/settings:
   ↓
General Tab:
- Project name, description
- Default phase
- Status (active/archived)
   ↓
GitHub Tab:
- Repository connection
- Branch selection
- Webhook configuration
   ↓
Phases Tab:
- Phase definitions
- Done criteria
- Expected outputs
   ↓
Board Tab:
- WIP limits per phase
- Column configuration
- Auto-transition rules
   ↓
Notifications Tab:
- Project-specific alerts
- Team member preferences
```

### Multi-User Collaboration

#### Team Workflows

**Role-Based Access:**
```
User Roles:
- Admin: Full control (settings, agents, projects)
- Manager: Approve/reject, monitor, intervene
- Viewer: Read-only access
   ↓
Permissions enforced:
- Can only approve if Manager+
- Can only spawn agents if Admin
- Can only modify settings if Admin
```

**Collaborative Review:**
```
Multiple users review same PR:
   ↓
1. User A reviews → Requests changes
   ↓
2. User B reviews → Approves
   ↓
3. System shows:
   - Both reviews visible
   - Approval status: "1 approve, 1 request changes"
   - Requires all approvers to approve
   ↓
4. User A updates review → Approves
   ↓
5. PR can be merged
```

**Comments & Collaboration:**
```
Agent/User adds comment to ticket:
   ↓
1. Opens ticket detail → Comments tab
   ↓
2. Types comment in rich text editor:
   - "@worker-2 please review this approach"
   - Attaches file if needed
   - Selects comment type (general, status_change, resolution)
   ↓
3. Posts comment:
   - Comment saved to database
   - WebSocket: COMMENT_ADDED event broadcast
   ↓
4. Real-time updates:
   - All users viewing ticket see comment instantly
   - @worker-2 receives notification (in-app + email)
   - Comment appears in activity timeline
   ↓
5. @worker-2 receives notification:
   - Clicks link → Goes to ticket
   - Sees comment highlighted
   - Can reply inline or take action
   ↓
6. Agent replies via MCP tool:
   - add_ticket_comment() called
   - WebSocket: COMMENT_ADDED event
   - User sees agent reply in real-time
```

**Ticket Search Before Creation:**
```
Agent needs to create ticket:
   ↓
1. Before creating, searches for existing tickets:
   - Opens search modal (Cmd+K or Search button)
   - Types: "authentication JWT login"
   - Selects hybrid search (70% semantic + 30% keyword)
   ↓
2. Reviews search results:
   - System shows similar tickets
   - Agent checks if duplicate exists
   ↓
3a. If similar ticket found:
   - References existing ticket instead
   - Links current task to existing ticket
   ↓
3b. If no similar ticket:
   - Proceeds to create new ticket
   - Uses create_ticket MCP tool
   ↓
4. New ticket appears on board:
   - WebSocket: TICKET_CREATED event
   - Board updates in real-time
   - Ticket visible to all users immediately
```

**Ticket Creation with Blocking Relationships:**
```
Agent creates ticket with dependencies:
   ↓
1. Opens Create Ticket modal:
   - Fills title: "Build Authentication System"
   - Adds description
   - Selects ticket type: "component"
   - Sets priority: "HIGH"
   ↓
2. Sets blocking relationships:
   - Searches for blocking tickets
   - Selects: "Setup Database Schema" (blocker)
   - System shows dependency graph preview
   ↓
3. Creates ticket:
   - Ticket created with blocked_by_ticket_ids
   - Ticket status: "blocked" (overlay)
   - WebSocket: TICKET_CREATED + TICKET_BLOCKED events
   ↓
4. Real-time updates:
   - Ticket appears on board with blocked indicator
   - Dependency graph updates automatically
   - When blocker resolves → Auto-unblock via WebSocket
```

**Status Transitions with Agent Updates:**
```
Agent moves ticket through workflow:
   ↓
1. Agent completes implementation:
   - Calls change_ticket_status() MCP tool
   - New status: "building-done"
   - Comment: "Implementation complete. 8 test cases added."
   ↓
2. System validates transition:
   - Checks valid state machine transition
   - Validates phase gate criteria
   ↓
3. Status updated:
   - Ticket status changed in database
   - WebSocket: TICKET_UPDATED event broadcast
   ↓
4. Real-time board updates:
   - Ticket moves to new column automatically
   - All users see movement instantly
   - Activity timeline shows status change
   ↓
5. User manually transitions:
   - Opens ticket → Clicks "Move Ticket"
   - Selects new status: "testing"
   - Adds reason: "Ready for test phase"
   - Confirms transition
   ↓
6. System updates:
   - Status changed
   - WebSocket: TICKET_UPDATED event
   - Board reflects change immediately
```

**Blocking Management & Auto-Unblocking:**
```
Ticket blocked by dependencies:
   ↓
1. Ticket "Build Auth" blocked by "Setup DB":
   - Shows blocked indicator on board
   - Dependency graph shows blocking relationship
   ↓
2. Agent working on blocker:
   - Completes "Setup DB" ticket
   - Resolves ticket via resolve_ticket() MCP tool
   ↓
3. System detects blocker resolution:
   - Checks all tickets blocked by resolved ticket
   - Finds "Build Auth" ticket
   ↓
4. Auto-unblocking:
   - Updates blocked_by_ticket_ids (removes resolved blocker)
   - Sets is_blocked = false
   - WebSocket: TICKET_UNBLOCKED event broadcast
   ↓
5. Real-time updates:
   - "Build Auth" ticket unblocked indicator removed
   - Ticket becomes available for agents
   - Dependency graph updates (edge turns green)
   - Activity timeline shows unblock event
   ↓
6. Agent picks up unblocked ticket:
   - Sees ticket available in board
   - Starts working on it
   - WebSocket: TASK_ASSIGNED event
```

**Board Configuration:**
```
User configures board structure:
   ↓
1. Opens Project Settings → Board tab
   ↓
2. Configures columns:
   - Edits column names, colors
   - Sets WIP limits per column
   - Maps columns to phases
   - Reorders columns (drag-and-drop)
   ↓
3. Configures ticket types:
   - Adds/removes ticket types
   - Sets default ticket type
   ↓
4. Saves configuration:
   - Board config saved to database
   - WebSocket: BOARD_CONFIG_UPDATED event
   ↓
5. Real-time board updates:
   - All users see new board structure
   - Columns reorganized
   - WIP limits enforced
   - Ticket types available in creation form
```

### Organization Management Sub-Pages

#### Creating an Organization (/organizations/new)

```
User clicks [+ Create Organization] from /organizations:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Organizations                                     │
│                                                              │
│  Create Organization                                         │
│  Set up a new organization to collaborate with your team     │
│                                                              │
│  Organization Name: [Acme Inc_________]                      │
│                                                              │
│  URL Slug: omoios.dev/ [acme-inc________]                   │
│  Only lowercase letters, numbers, and hyphens                │
│                                                              │
│  Description (optional):                                     │
│  [Tell us about your organization...                ]        │
│                                                              │
│                          [Cancel] [Create Organization]      │
└─────────────────────────────────────────────────────────────┘
   ↓
On submit:
├── Creates organization via API
├── Checks localStorage for "pending_plan" (from /pricing signup)
│   ├── If pending plan (pro/team):
│   │   → Creates Stripe checkout session → Redirects to Stripe
│   └── If no pending plan:
│       → Navigates to /organizations/:id
└── Name auto-generates slug (lowercase, hyphens for spaces)
```

#### Managing Organization Members (/organizations/[id]/members)

```
User navigates to /organizations/:id/members:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Organization                                      │
│  Members                                     [+ Add Member] │
│  Manage team members and their permissions                   │
│                                                              │
│  [Search members...]                                         │
│                                                              │
│  Team Members (5 members)                                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Member         │ Role             │ Joined    │ Actions ││
│  ├─────────────────────────────────────────────────────────┤│
│  │ 👤 a1b2c3... │ 👑 Owner (amber) │ Jan 15    │   [⋮]  ││
│  │    User       │                  │           │         ││
│  │ 🤖 d4e5f6... │ 🛡 Admin (blue)  │ Jan 20    │   [⋮]  ││
│  │    Agent      │                  │           │         ││
│  │ 👤 g7h8i9... │ 🛡 Member (gray) │ Feb 1     │   [⋮]  ││
│  │    User       │                  │           │         ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  Available Roles                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ 👑 Owner     │ │ 🛡 Admin     │ │ 🛡 Member    │        │
│  │ [System]     │ │ [System]     │ │ [System]     │        │
│  │ Full control │ │ manage, edit │ │ read, create │        │
│  │ +3 perms     │ │ +2 perms     │ │              │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘

Actions (via [⋮] dropdown):
- Change to [role] → Updates member role via API
- Remove Member → Destructive confirmation dialog
  "They will lose access to all projects and resources"
  [Cancel] [Remove]

Add Member dialog:
- User ID field
- Role selector (populated from organization's role list)
- [Cancel] [Add Member]

Search: Filters by role name, user ID, or agent ID
Member types: User (person icon) or Agent (bot icon)
```

#### Organization Settings (/organizations/[id]/settings)

```
User navigates to /organizations/:id/settings:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Organization                                      │
│  Organization Settings                                       │
│  Manage your organization's profile and preferences          │
│                                                              │
│  General                                                     │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ [Avatar]  [Change Logo]                                 ││
│  │ Name: [Acme Inc______]  Slug: acme-inc (read-only)     ││
│  │ Description: [Tell us about...]                         ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  Member Settings                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Allow member invites         [toggle on]                ││
│  │ Require approval             [toggle off]               ││
│  │ Note: Stored locally. Backend support coming soon.      ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  Usage Summary                                               │
│  ┌──────────────┐ ┌──────────────┐                          │
│  │ Members: 5   │ │ Projects: 12 │                          │
│  └──────────────┘ └──────────────┘                          │
│                                                              │
│                                        [Save Changes]        │
│                                                              │
│  ⚠ Danger Zone                                               │
│  Delete Organization — permanent         [🗑 Delete]         │
│  Confirmation: "This will permanently delete Acme Inc..."   │
└─────────────────────────────────────────────────────────────┘

Key behaviors:
- Slug is read-only after creation
- Member settings stored in localStorage (backend pending)
- Delete requires confirmation AlertDialog
- On delete → redirect to /organizations
```

### Agent Spawning & Workspaces

#### Spawning an Agent (/agents/spawn)

> **Note**: The `/agents` page is no longer in the primary sidebar (replaced by `/sandboxes`). Agent spawn is accessible via direct URL or deep links from project pages.

```
User navigates to /agents/spawn (via direct URL or ?projectId= link):
   ↓
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Agents                                            │
│                                                              │
│  🤖 Spawn New Agent                                         │
│  Create a new AI agent to work on your project               │
│                                                              │
│  Project (Optional):                                         │
│  [Select a project (optional)       ▼]                      │
│  ← Pre-populated if ?projectId= in URL                      │
│                                                              │
│  Agent Type:                                                 │
│  [Worker (General purpose)          ▼]                      │
│  Options: Worker, Specialist, Coordinator, Reviewer          │
│                                                              │
│  Starting Phase:                                             │
│  [PHASE_IMPLEMENTATION              ▼]                      │
│  ← Lists all phases from PHASES config                       │
│                                                              │
│  Capabilities:                                               │
│  [code_generation, testing, debugging]                       │
│  Comma-separated list                                        │
│                                                              │
│  Capacity:                                                   │
│  [3] (1-10 concurrent tasks)                                │
│                                                              │
│                            [Cancel] [Register Agent]         │
└─────────────────────────────────────────────────────────────┘
   ↓
On submit:
- POST /agents/register with agent_type, phase_id, capabilities, capacity, tags
- Tags include project:${projectId} if project selected
- On success → navigate to /agents/:agentId
```

#### Agent Workspace (/agents/[agentId]/workspace)

```
User opens workspace from agent detail page or /workspaces list:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Agent                                             │
│  🗂 Workspace                     [feature/jwt-auth]        │
│  IMPLEMENTATION                                              │
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Total Commits│ │ Lines Changed│ │ Merge        │        │
│  │     8        │ │ +342  -56    │ │ Conflicts: 0 │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                              │
│  Tabs: [Commits] [Merge Conflicts] [Settings]               │
│                                                              │
│  Commit History:                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ● "Implement JWT middleware"              [View]        ││
│  │   a1b2c3d  3 hours ago  4 files  +120 -8               ││
│  ├─────────────────────────────────────────────────────────┤│
│  │ ● "Add refresh token rotation"            [View]        ││
│  │   e4f5g6h  2 hours ago  2 files  +85 -12               ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  Merge Conflicts: ✓ No merge conflicts                      │
│                                                              │
│  Settings:                                                   │
│  │ Workspace Path:   /workspaces/{agentId}                  │
│  │ Git Branch:       feature/jwt-auth                       │
│  │ Workspace Type:   Docker Container                       │
│  │ Parent Agent:     None (root)                            │
│  │ Retention Policy: 7 days after completion                │
│  │ Created:          3 hours ago                            │
└─────────────────────────────────────────────────────────────┘

Commit [View] dialog:
- Shows file list with path, status badge (added/modified/deleted), +/- counts
- Scrollable for large commits
```

#### Workspaces List (/workspaces)

```
User navigates to /workspaces:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Workspaces                                                  │
│  Isolated agent workspaces with repo context                 │
│                                                              │
│  [Search agent, project, or repo]  [Filter status ▼]        │
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ auth-system  │ │ payment-gw   │ │ analytics    │        │
│  │ github/auth  │ │ github/pay   │ │ github/analy │        │
│  │ [Active ●]   │ │ [Active ●]   │ │ [Degraded ⚠] │        │
│  │ worker-1     │ │ worker-2     │ │ worker-5     │        │
│  │ Sync: 3m ago │ │ Sync: 8m ago │ │ Sync: 15m    │        │
│  │ [Open] [Agent]│ │ [Open] [Agent]│ │ [Open] [Agent]│       │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘

Note: This page currently uses hardcoded mock data (not API-connected).
Filter by: All, Active, Degraded, Idle
Search by: agent name, project name, or repo URL
[Open workspace] → /agents/:agent/workspace
[Agent] → /agents/:agent
```

### Keyboard Shortcuts & Accessibility

#### Keyboard Navigation

**Global Shortcuts:**
```
Cmd+K (Mac) / Ctrl+K (Windows):
   - Opens command palette
   - Quick navigation/search
   ↓
Cmd+/ (Mac) / Ctrl+/ (Windows):
   - Shows keyboard shortcuts help
   ↓
Esc:
   - Closes modals
   - Exits fullscreen views
   ↓
Arrow Keys:
   - Navigate lists
   - Move between tickets in board
```

**Board Shortcuts:**
```
j/k: Navigate up/down tickets
h/l: Navigate left/right columns
Enter: Open selected ticket
Space: Toggle ticket selection
```

**Spec Workspace Shortcuts:**
```
Tab: Switch between Requirements/Design/Tasks/Execution
Cmd+S: Save spec changes
Cmd+E: Export spec
Cmd+/: Show formatting help
```

#### Accessibility Features

**Screen Reader Support:**
```
- ARIA labels on all interactive elements
- Semantic HTML structure
- Keyboard navigation support
- Screen reader announcements for:
  - Real-time updates
  - Status changes
  - Error messages
```

**Visual Accessibility:**
```
- High contrast mode option
- Color-blind friendly color schemes
- Resizable text
- Focus indicators
- Reduced motion option
```

### Mobile & Responsive Design

#### Mobile Experience

**Responsive Layout:**
```
Mobile (< 768px):
- Collapsible sidebar (hamburger menu)
- Stacked columns on Kanban board
- Simplified ticket cards
- Touch-optimized controls
   ↓
Tablet (768px - 1024px):
- Sidebar can be toggled
- Board shows 2-3 columns
- Full ticket details available
   ↓
Desktop (> 1024px):
- Full sidebar visible
- All columns visible
- Multi-panel layouts
```

**Mobile-Specific Features:**
```
- Swipe gestures:
  - Swipe right: Open ticket
  - Swipe left: Quick actions
- Pull to refresh:
  - Refresh board data
  - Sync latest updates
- Touch targets:
  - Minimum 44x44px
  - Adequate spacing
```

### Troubleshooting & Support

#### Common Issues & Solutions

**WebSocket Connection Lost:**
```
Issue: Real-time updates stop working
   ↓
System detects disconnection:
   - Shows "Reconnecting..." indicator
   - Attempts automatic reconnection
   ↓
If reconnection fails:
   - Shows "Connection lost" banner
   - Manual refresh button
   - Falls back to polling
```

**Agent Not Picking Up Tasks:**
```
Issue: Tasks stuck in queue
   ↓
Check:
1. Agent status (active/idle/stuck)
2. Agent phase assignment matches task phase
3. Task dependencies satisfied
4. WIP limits not exceeded
   ↓
Solutions:
- Spawn new agent
- Manually assign task
- Check agent logs
- Contact support
```

**Spec Generation Slow:**
```
Issue: Spec takes > 5 minutes to generate
   ↓
Possible causes:
- Large codebase analysis
- Complex requirements
- LLM API rate limiting
   ↓
User sees:
- Progress indicator
- Estimated time remaining
- Option to cancel
   ↓
If timeout:
- Saves partial spec
- Allows manual completion
- Option to retry
```

### Export & Import Flows

#### Exporting Data

**Spec Export:**
```
Navigate to spec → Click "Export":
   ↓
Options:
- Markdown (.md)
- YAML (.yaml)
- PDF (.pdf)
   ↓
Select format → Download
   ↓
File contains:
- All requirements
- Design documents
- Task breakdown
- Version history (optional)
```

**Audit Trail Export:**
```
Navigate to ticket → Audit tab → Export:
   ↓
Options:
- PDF report
- CSV data
- JSON format
   ↓
Contains:
- Complete history
- All events
- Timestamps
- User actions
```

**Project Export:**
```
Navigate to project settings → Export:
   ↓
Exports:
- All tickets
- All tasks
- All specs
- Agent history
- Commit history
   ↓
Use cases:
- Backup
- Migration
- Compliance
```

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
