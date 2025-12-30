# Command Page Workflow Modes Design

**Created**: 2025-12-30
**Status**: Draft
**Purpose**: Design document for adding workflow mode selection to the Command Center page

---

## Overview

The Command Center (`/command`) is the primary entry point for authenticated users. Currently it supports a single workflow: describe → create ticket → spawn sandbox. This document outlines the design for supporting multiple workflow modes from the command page.

---

## Workflow Modes

### Mode 1: Quick Implementation (Default)

**Purpose**: Fast path for simple tasks - directly spawn an agent to implement.

**User Flow**:
```
1. User types prompt: "Add a login button to the header"
   ↓
2. System creates ticket (PHASE_IMPLEMENTATION)
   ↓
3. Orchestrator spawns sandbox
   ↓
4. Redirect to /sandbox/:id for real-time monitoring
   ↓
5. Agent implements and creates PR
```

**Best For**:
- Small bug fixes
- Simple features
- Quick experiments
- Tasks that don't need extensive planning

**Requirements**: Project must be selected

---

### Mode 2: Spec-Driven Development

**Purpose**: Structured workflow for complex features requiring planning and approval gates.

**User Flow**:
```
1. User types prompt: "Add payment processing with Stripe"
   ↓
2. System analyzes codebase and generates:
   - Requirements (EARS-style WHEN/SHALL patterns)
   - Design (architecture, data models, APIs)
   - Tasks (discrete units with dependencies)
   ↓
3. User reviews/edits in Spec Workspace
   ↓
4. User approves Requirements → Design → Plan
   ↓
5. System creates tickets for each task
   ↓
6. Orchestrator assigns to agents
   ↓
7. Parallel execution with Guardian monitoring
   ↓
8. PRs created, user reviews and merges
```

**Best For**:
- New features
- Complex integrations
- Multi-component changes
- Production-critical work

**Requirements**: Project must be selected

---

## UI Design (Dropdown Approach)

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│                    What would you like to do?                    │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │                                                          │   │
│   │  Describe what you want to build...                      │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│   [⚡ Quick ▼]  [Project selector]        [Model] [Submit →]     │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │ ℹ️ Agent will immediately start implementing             │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Dropdown Options

```
┌─────────────────────────────────┐
│ ⚡ Quick                    ✓   │  ← Default
├─────────────────────────────────┤
│ 📋 Spec-Driven                  │
└─────────────────────────────────┘
```

Each option shows:
- Icon (visual distinction)
- Mode name
- Checkmark for selected

### Behavior by Mode

| Mode | Placeholder | Helper Text | Submit Label |
|------|-------------|-------------|--------------|
| Quick | "Describe what you want to build..." | "Agent will immediately start implementing" | "Launch →" |
| Spec-Driven | "Describe the feature to plan..." | "We'll generate requirements & design for approval" | "Create Spec →" |

---

## Mode-Specific UI Elements

### Quick Mode
```
Placeholder: "Describe what you want to build..."
Helper text: "An agent will immediately start implementing your request"
Submit button: "Launch →"
```

### Spec-Driven Mode
```
Placeholder: "Describe the feature you want to plan..."
Helper text: "We'll generate requirements, design, and tasks for your review"
Submit button: "Create Spec →"
```

---

## Data Flow & API Parameters

### Parameter Differences by Mode

| Parameter | Quick | Spec-Driven |
|-----------|-------|-------------|
| `workflow_mode` | `"quick"` | `"spec_driven"` |
| `phase_id` | `"PHASE_IMPLEMENTATION"` | `"PHASE_REQUIREMENTS"` |
| `auto_spawn_sandbox` | `true` | `false` |
| `generate_spec` | `false` | `true` |

### Quick Mode (Current Implementation)
```typescript
// Uses existing ticket creation flow
POST /api/tickets
{
  title: prompt.slice(0, 100),
  description: prompt,
  phase_id: "PHASE_IMPLEMENTATION",
  priority: "MEDIUM",
  workflow_mode: "quick",        // NEW: identifies mode
  auto_spawn_sandbox: true       // NEW: tells orchestrator to spawn immediately
}

// Response: ticket created, orchestrator spawns sandbox
// Frontend: waits for SANDBOX_SPAWNED event, redirects to /sandbox/:id
```

### Spec-Driven Mode (New)
```typescript
// Creates a spec with auto-generated requirements/design/tasks
POST /api/tickets
{
  title: prompt.slice(0, 100),
  description: prompt,
  phase_id: "PHASE_REQUIREMENTS",  // Starts in requirements phase
  priority: "MEDIUM",
  workflow_mode: "spec_driven",    // Triggers spec generation
  generate_spec: true,             // Auto-generate requirements & design
  auto_spawn_sandbox: false        // Don't spawn until user approves
}

// Response: ticket created with spec_id
{
  id: "ticket-123",
  spec_id: "spec-456",             // Generated spec attached
  status: "pending_approval"
}

// Frontend: redirects to /specs/:spec_id for review & approval
```

### Unified Submit Handler

```typescript
const handleSubmit = async (prompt: string) => {
  const basePayload = {
    title: prompt.slice(0, 100) + (prompt.length > 100 ? "..." : ""),
    description: prompt,
    priority: "MEDIUM",
    project_id: selectedProject?.id,
  }

  let payload: CreateTicketPayload

  switch (selectedMode) {
    case "quick":
      payload = {
        ...basePayload,
        phase_id: "PHASE_IMPLEMENTATION",
        workflow_mode: "quick",
        auto_spawn_sandbox: true,
      }
      // Wait for sandbox, redirect to /sandbox/:id
      break

    case "spec_driven":
      payload = {
        ...basePayload,
        phase_id: "PHASE_REQUIREMENTS",
        workflow_mode: "spec_driven",
        generate_spec: true,
        auto_spawn_sandbox: false,
      }
      // Redirect to /specs/:spec_id
      break
  }

  const result = await createTicketMutation.mutateAsync(payload)
  // Handle redirect based on mode...
}
```

---

## Navigation After Submit

| Mode | Destination | Purpose |
|------|-------------|---------|
| Quick | `/sandbox/:id` | Real-time agent monitoring |
| Spec-Driven | `/specs/:id` | Spec workspace for review/approval |

---

## State Machine

```
                    ┌─────────────────┐
                    │  Command Page   │
                    │  (Mode Select)  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
        ┌─────────┐                  ┌───────────┐
        │  Quick  │                  │ Spec-Drv  │
        │  Mode   │                  │   Mode    │
        └────┬────┘                  └─────┬─────┘
             │                             │
             ▼                             ▼
       ┌───────────┐                ┌───────────┐
       │  Sandbox  │                │   Spec    │
       │  Detail   │                │ Workspace │
       └───────────┘                └─────┬─────┘
                                          │
                                 (After approvals)
                                          │
                                          ▼
                                   ┌───────────┐
                                   │ Sandboxes │
                                   │ (Parallel)│
                                   └───────────┘
```

---

## Implementation Phases

### Phase 1: UI Foundation
- Add mode selector dropdown to command page
- Update prompt placeholders based on mode
- Add mode-specific helper text
- Track selected mode in state

### Phase 2: Quick Mode Polish
- Ensure current flow works as "Quick Mode"
- Add mode indicator to created tickets
- Update sandbox detail to show mode

### Phase 3: Spec-Driven Mode
- Create spec generation API endpoint
- Build Spec Workspace page (`/specs/:id`)
- Add approval gate UI
- Connect to task creation on approval

---

## Open Questions

1. **Mode Persistence**: Should we remember the user's last-used mode?
2. **Mode Suggestions**: Should we suggest modes based on prompt analysis?
3. **Hybrid Flows**: Can users switch modes mid-flow (e.g., quick → spec-driven)?
4. **Keyboard Shortcuts**: Should modes have keyboard shortcuts (e.g., Cmd+1, Cmd+2, Cmd+3)?

---

## Related Documentation

- [Command Center Design](../figma_prompts/prompt_4a_command_center.md)
- [Feature Planning User Journey](../user_journey/02_feature_planning.md)
- [Execution Monitoring](../user_journey/03_execution_monitoring.md)
- [MCP Spec Workflow Server](./mcp_spec_workflow_server.md)

---

**Next Steps**:
1. Review and approve design
2. Implement Phase 1 (UI Foundation)
3. Iterate based on feedback
