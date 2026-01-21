# Figma Make Prompt 9: Development Status Notifications

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. I need you to build a comprehensive notification system for displaying real-time app development status updates.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. Users need to be notified of development progress, agent activity, phase completions, errors, and important milestones as specs execute through the pipeline.

**COMPONENT FRAMEWORK:**
Shadcn UI (https://ui.shadcn.com) with **Tailwind CSS v4**. Build on the foundation from Prompt 1.

**NOTIFICATION TYPES:**

1. **Phase Transition Notifications**
   - Spec moved from one phase to another (explore → requirements → design → tasks → sync → complete)
   - Show: Phase icon, spec title, from/to phases, timestamp
   - Color coding: Blue (in progress), Green (completed), Yellow (warning), Red (failed)
   - Example: "🔄 Design Phase Complete → Moving to Tasks | Feature: User Authentication | 2m ago"

2. **Agent Activity Notifications**
   - Agent started working on task
   - Agent completed task (success/failure)
   - Agent requesting human intervention
   - Agent heartbeat timeout (stale)
   - Show: Agent icon/avatar, action type, task name, status badge
   - Example: "🤖 Agent-42 completed 'Create login API endpoint' ✓ | +156 -23 lines"

3. **Spec Status Notifications**
   - Spec created
   - Spec execution started
   - Spec completed (all phases done)
   - Spec failed (with error summary)
   - PR created for spec
   - Show: Spec title, status change, progress percentage, linked tickets count
   - Example: "✅ Spec Complete: 'Dark Mode Toggle' | PR #234 ready for review"

4. **Error & Warning Notifications**
   - Build failures
   - Test failures
   - Dependency issues
   - Rate limiting/resource constraints
   - Guardian interventions (agent drift detected)
   - Show: Error type, affected component, severity badge, action button
   - Example: "⚠️ Guardian Intervention | Agent-17 diverged from spec requirements | View Details"

5. **Milestone Notifications**
   - Requirements approved
   - Design approved
   - All tests passing
   - PR merged
   - Deployment successful
   - Show: Milestone type, celebratory styling (subtle), relevant metrics
   - Example: "🎉 Milestone: All 12 acceptance criteria met for 'Payment Integration'"

**NOTIFICATION COMPONENTS:**

1. **Toast Notifications** (Ephemeral, bottom-right)
   - Auto-dismiss after 5s (configurable)
   - Manual dismiss button
   - Stack up to 3 visible, queue remaining
   - Variants: info, success, warning, error
   - Compact layout: icon + message + dismiss (max 400px width)
   - Subtle entrance animation (slide up + fade in)

2. **Notification Center** (Persistent, dropdown from header bell icon)
   - Bell icon with unread count badge (red dot or number)
   - Dropdown panel (400px width, max 500px height)
   - Tabs: All | Specs | Agents | Errors
   - Each notification: icon, title, description, timestamp, read/unread indicator
   - Mark all as read button
   - Click to navigate to relevant page
   - Empty state: "No notifications yet"

3. **Inline Status Banners** (Page-level alerts)
   - Full-width, dismissible
   - Used for: ongoing executions, system-wide announcements, degraded service
   - Sticky to top of content area (below header)
   - Variants: info (blue), warning (amber), error (red), success (green)
   - Include action button when applicable
   - Example: "⚡ 3 specs currently executing | View Dashboard →"

4. **Activity Feed Item** (For timeline views)
   - Timestamp (relative: "2m ago", "1h ago", "Yesterday")
   - Event type icon (phase, agent, error, milestone)
   - Title (bold) + Description (muted)
   - Optional: expandable details section
   - Optional: line change indicators (+X -Y)
   - Connecting line between items for timeline effect

**DATA STRUCTURE:**

```typescript
interface Notification {
  id: string
  type: 'phase_transition' | 'agent_activity' | 'spec_status' | 'error' | 'milestone'
  severity: 'info' | 'success' | 'warning' | 'error'
  title: string
  description: string
  timestamp: Date
  read: boolean
  specId?: string
  agentId?: string
  taskId?: string
  metadata?: {
    fromPhase?: string
    toPhase?: string
    linesAdded?: number
    linesRemoved?: number
    errorCode?: string
    prNumber?: number
    [key: string]: any
  }
  actions?: Array<{
    label: string
    href?: string
    onClick?: () => void
    variant: 'default' | 'outline' | 'ghost'
  }>
}
```

**VISUAL DESIGN:**

**Icons by Type:**
- Phase: RotateCw (transition), CheckCircle (complete), Circle (pending)
- Agent: Bot, Cpu, Loader2 (working)
- Spec: FileText, FolderGit2, GitPullRequest
- Error: AlertCircle, AlertTriangle, XCircle
- Milestone: Trophy, Flag, Sparkles

**Color Mapping:**
- Info: Border-left blue (#0366D6), icon blue
- Success: Border-left green (#22863A), icon green
- Warning: Border-left amber (#B08800), icon amber
- Error: Border-left red (#CB2431), icon red

**Animation:**
- Toast enter: translateY(100%) → translateY(0), opacity 0 → 1, duration 200ms
- Toast exit: translateY(0) → translateY(100%), opacity 1 → 0, duration 150ms
- Badge pulse: subtle scale animation on new notification
- Read transition: background fade from accent/5 to transparent

**RESPONSIVE BEHAVIOR:**

- Mobile (< 640px): Toast full-width, notification center as full-screen modal
- Tablet (640-1024px): Toast bottom-center, notification center as side panel
- Desktop (> 1024px): Toast bottom-right, notification center as dropdown

**ACCESSIBILITY:**

- Toast: role="alert", aria-live="polite" (info/success), aria-live="assertive" (error)
- Notification center: role="region", aria-label="Notifications"
- Unread badge: aria-label="X unread notifications"
- Keyboard: Escape to dismiss toasts, Tab through notification items
- Screen reader: Announce new notifications with context

**BUILD THESE COMPONENTS:**

1. `Toast` - Shadcn toast with custom variants and auto-dismiss
2. `ToastContainer` - Manages toast stack positioning
3. `NotificationBell` - Header icon with badge
4. `NotificationCenter` - Dropdown panel with tabs and list
5. `NotificationItem` - Individual notification row
6. `StatusBanner` - Full-width inline alert
7. `ActivityFeedItem` - Timeline-style notification
8. `NotificationProvider` - Context for managing notification state

**EXAMPLE STATES TO SHOW:**

1. Empty notification center
2. Notification center with mixed types (5+ notifications)
3. Toast stack with 3 notifications (success, warning, info)
4. Status banner showing active execution
5. Activity feed showing spec progression through phases
6. Error notification with "View Details" action
7. Milestone celebration notification

**INTEGRATION HOOKS:**

```typescript
// Usage pattern
const { toast, notifications, markAsRead, clearAll } = useNotifications()

// Trigger toast
toast({
  type: 'success',
  title: 'Phase Complete',
  description: 'Design phase finished, moving to tasks',
  duration: 5000,
})

// Subscribe to real-time updates
useEffect(() => {
  const unsubscribe = subscribeToNotifications((notification) => {
    toast(notification)
  })
  return unsubscribe
}, [])
```

Build the complete notification system with all components, proper TypeScript types, and example usage showing various notification scenarios.
