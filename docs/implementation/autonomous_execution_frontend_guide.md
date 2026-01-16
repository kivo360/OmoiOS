# Autonomous Execution Frontend Implementation Guide

**Created**: 2025-01-15
**Status**: Ready for Implementation
**Purpose**: Step-by-step guide for implementing the autonomous execution toggle in the frontend

---

## Overview

This guide provides detailed implementation steps for adding the autonomous execution toggle to the frontend Kanban board. The toggle replaces the "Start Processing" button behavior when enabled.

---

## Prerequisites

Ensure the backend migration has been run:
```bash
cd backend && uv run alembic upgrade head
```

---

## Step 1: Update API Types

**File:** `frontend/lib/api/types.ts`

Add the new field to the Project interface and ProjectUpdate type:

```typescript
// Add to Project interface
export interface Project {
  id: string
  name: string
  description: string | null
  github_owner: string | null
  github_repo: string | null
  github_connected: boolean
  default_phase_id: string
  status: "active" | "paused" | "archived" | "completed"
  settings: Record<string, unknown> | null
  autonomous_execution_enabled: boolean  // ADD THIS
  created_at: string
  updated_at: string
}

// Add to ProjectUpdate type
export interface ProjectUpdate {
  name?: string
  description?: string
  default_phase_id?: string
  status?: "active" | "paused" | "archived" | "completed"
  github_owner?: string
  github_repo?: string
  github_connected?: boolean
  settings?: Record<string, unknown>
  autonomous_execution_enabled?: boolean  // ADD THIS
}
```

---

## Step 2: Add API Function

**File:** `frontend/lib/api/projects.ts`

Add a dedicated function for toggling autonomous mode:

```typescript
/**
 * Toggle autonomous execution mode for a project
 */
export async function toggleAutonomousExecution(
  projectId: string,
  enabled: boolean
): Promise<Project> {
  return apiRequest<Project>(`/api/v1/projects/${projectId}`, {
    method: "PATCH",
    body: { autonomous_execution_enabled: enabled },
  })
}
```

---

## Step 3: Add React Query Hook

**File:** `frontend/hooks/useProjects.ts`

Add a mutation hook for the toggle:

```typescript
import { toggleAutonomousExecution } from "@/lib/api/projects"

/**
 * Hook to toggle autonomous execution mode for a project
 */
export function useToggleAutonomousExecution() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ projectId, enabled }: { projectId: string; enabled: boolean }) =>
      toggleAutonomousExecution(projectId, enabled),
    onSuccess: (updatedProject) => {
      // Update the specific project in cache
      queryClient.setQueryData(
        projectKeys.detail(updatedProject.id),
        updatedProject
      )
      // Invalidate lists to refresh sidebar
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}
```

---

## Step 4: Update Board Page Component

**File:** `frontend/app/(app)/board/[projectId]/page.tsx`

### 4a. Import the hook

```typescript
import { useToggleAutonomousExecution } from "@/hooks/useProjects"
```

### 4b. Add the mutation hook in the component

```typescript
export default function BoardPage({ params }: { params: { projectId: string } }) {
  // ... existing code ...

  // Add the autonomous toggle mutation
  const toggleAutonomous = useToggleAutonomousExecution()

  // ... rest of component ...
}
```

### 4c. Add handler function (around line 608, after handleStartProcessing)

```typescript
/**
 * Toggle autonomous execution mode for the project
 */
const handleToggleAutonomous = async (enabled: boolean) => {
  try {
    await toggleAutonomous.mutateAsync({
      projectId: params.projectId,
      enabled
    })

    if (enabled) {
      toast.success("Autonomous mode enabled", {
        description: "Tasks will be automatically spawned when unblocked.",
      })
    } else {
      toast.info("Autonomous mode disabled", {
        description: "Use 'Start Processing' to manually spawn tasks.",
      })
    }
  } catch (error) {
    toast.error("Failed to toggle autonomous mode")
  }
}
```

### 4d. Replace the "Start Processing" button (around line 749-772)

Replace the existing button with conditional rendering:

```tsx
{/* Autonomous Mode Toggle / Start Processing Button */}
{project?.autonomous_execution_enabled ? (
  <Button
    variant="outline"
    onClick={() => handleToggleAutonomous(false)}
    disabled={toggleAutonomous.isPending}
    className="border-green-500 text-green-600 hover:bg-green-50"
  >
    {toggleAutonomous.isPending ? (
      <>
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Updating...
      </>
    ) : (
      <>
        <Pause className="mr-2 h-4 w-4" />
        Autonomous: ON
        {runningTasksCount > 0 && (
          <Badge
            variant="secondary"
            className="ml-2 bg-green-100 text-green-800 animate-pulse"
          >
            {runningTasksCount} running
          </Badge>
        )}
      </>
    )}
  </Button>
) : (
  <div className="flex items-center gap-2">
    <Button
      variant="default"
      onClick={handleStartProcessing}
      disabled={batchSpawn.isPending || processableTickets.length === 0}
      className="bg-green-600 hover:bg-green-700"
    >
      {batchSpawn.isPending ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Starting...
        </>
      ) : (
        <>
          <Play className="mr-2 h-4 w-4" />
          Start Processing
          {processableTickets.length > 0 && (
            <Badge variant="secondary" className="ml-2 bg-green-800">
              {processableTickets.length}
            </Badge>
          )}
        </>
      )}
    </Button>

    {/* Quick enable autonomous button */}
    <Button
      variant="ghost"
      size="icon"
      onClick={() => handleToggleAutonomous(true)}
      disabled={toggleAutonomous.isPending}
      title="Enable autonomous mode"
      className="text-muted-foreground hover:text-green-600"
    >
      <Zap className="h-4 w-4" />
    </Button>
  </div>
)}
```

### 4e. Add necessary imports

```typescript
import { Pause, Zap } from "lucide-react"  // Add to existing lucide imports
```

### 4f. Track running tasks count

Add this after the existing state variables:

```typescript
// Count running tasks across all tickets
const runningTasksCount = useMemo(() => {
  return allTickets.reduce((count, ticket) => {
    const ticketTasks = tasks.get(ticket.id) || []
    return count + ticketTasks.filter(t => t.status === "running").length
  }, 0)
}, [allTickets, tasks])
```

---

## Step 5: Update Project Settings Page

**File:** `frontend/app/(app)/projects/[id]/settings/page.tsx`

Add the autonomous toggle in the "Agent Defaults" section:

```tsx
{/* Add after the "Max Concurrent Agents" setting */}
<div className="flex items-center justify-between">
  <div className="space-y-0.5">
    <Label htmlFor="autonomous-mode">Autonomous Execution</Label>
    <p className="text-sm text-muted-foreground">
      Automatically spawn tasks when they become unblocked (all dependencies completed)
    </p>
  </div>
  <Switch
    id="autonomous-mode"
    checked={project.autonomous_execution_enabled}
    onCheckedChange={(checked) => {
      handleToggleAutonomous(checked)
    }}
  />
</div>
```

---

## Step 6: Add WebSocket Event Handler

**File:** `frontend/hooks/useBoardEvents.ts`

Add handling for autonomous mode change events:

```typescript
// In the event handler switch statement, add:
case "AUTONOMOUS_MODE_CHANGED":
  // Invalidate project data to get fresh autonomous_execution_enabled value
  queryClient.invalidateQueries({
    queryKey: projectKeys.detail(event.entity_id)
  })

  // Show toast notification
  const enabled = event.payload?.enabled
  if (enabled) {
    toast.info("Autonomous mode enabled", {
      description: "Project will auto-spawn tasks when unblocked."
    })
  } else {
    toast.info("Autonomous mode disabled")
  }
  break
```

---

## Step 7: Visual States

### Button States Reference

| State | Visual | Behavior |
|-------|--------|----------|
| Autonomous OFF, no tasks | Green "Start Processing" button | Click to batch spawn |
| Autonomous OFF, tasks ready | Green button + badge count | Click to batch spawn |
| Autonomous ON, idle | Outlined green "Autonomous: ON" | Click to disable |
| Autonomous ON, running | Outlined + pulsing badge | Shows running count |
| Transitioning | Loader spinner | Disabled during API call |

### Color Reference

```css
/* Autonomous ON */
.border-green-500    /* Border */
.text-green-600      /* Text */
.bg-green-100        /* Badge background */
.text-green-800      /* Badge text */

/* Autonomous OFF / Start Processing */
.bg-green-600        /* Button background */
.bg-green-700        /* Hover */
.bg-green-800        /* Badge */
```

---

## Step 8: Testing Checklist

- [ ] Toggle button appears on Kanban board
- [ ] Clicking toggle updates backend
- [ ] Toast notifications appear
- [ ] Badge shows running task count when autonomous
- [ ] "Start Processing" works when autonomous disabled
- [ ] Settings page toggle syncs with board toggle
- [ ] WebSocket events update UI across tabs

---

## Rollback Plan

If issues arise, the feature can be disabled by:

1. Setting all projects' `autonomous_execution_enabled` to false:
   ```sql
   UPDATE projects SET autonomous_execution_enabled = false;
   ```

2. Reverting frontend changes (toggle always hidden, "Start Processing" always shown)

---

## Related Files

- `frontend/app/(app)/board/[projectId]/page.tsx` - Main board component
- `frontend/lib/api/types.ts` - TypeScript types
- `frontend/lib/api/projects.ts` - API functions
- `frontend/hooks/useProjects.ts` - React Query hooks
- `frontend/hooks/useBoardEvents.ts` - WebSocket event handling
- `frontend/app/(app)/projects/[id]/settings/page.tsx` - Settings page
