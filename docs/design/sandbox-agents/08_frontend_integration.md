# Frontend Integration for Sandbox Agents

**Created**: 2025-12-12  
**Status**: Planning Document  
**Priority**: Optional (Phase 5 enhancement)

---

## Overview

This document outlines the frontend components needed to provide users with visibility and control over sandbox agents.

---

## User Stories

### Core Stories (MVP)

1. **As a user, I want to see real-time progress** of my agent working on a task
2. **As a user, I want to send messages** to the agent while it's working
3. **As a user, I want to see when the agent needs my input** (blocking on review)
4. **As a user, I want to see the final results** including files changed and PR link

### Extended Stories (Full Integration)

5. **As a user, I want to see the agent's thought process** (tool calls, reasoning)
6. **As a user, I want to pause/resume/cancel** an agent mid-task
7. **As a user, I want historical logs** of what the agent did
8. **As a user, I want to see Guardian interventions** and their impact

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FRONTEND COMPONENT HIERARCHY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        SandboxDashboard                              │   │
│  │  ├─ SandboxList (all active sandboxes for user)                     │   │
│  │  └─ SandboxDetailView (selected sandbox)                            │   │
│  │       ├─ TaskHeader (task title, status, progress bar)              │   │
│  │       ├─ AgentActivityFeed (real-time events)                       │   │
│  │       ├─ MessagePanel (user ↔ agent chat)                           │   │
│  │       ├─ FileChangePreview (diff viewer)                            │   │
│  │       └─ ActionButtons (pause, resume, cancel, approve PR)          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Data Flow:                                                                 │
│  ├─ WebSocket: Real-time events (agent.*, SANDBOX_*)                       │
│  ├─ REST API: Initial data load, user actions                              │
│  └─ State: React Query or Zustand for cache/state                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## UI Components Specification

### 1. SandboxList

**Purpose**: Show all active sandboxes for the current user

**Data Source**: `GET /api/v1/sandboxes?user_id={user_id}&status=active`

```tsx
interface SandboxListItem {
  sandbox_id: string;
  task_id: string;
  task_title: string;
  status: "creating" | "running" | "completing" | "completed" | "failed";
  progress_percent: number;
  started_at: string;
  last_event_at: string;
}

function SandboxList({ sandboxes }: { sandboxes: SandboxListItem[] }) {
  return (
    <div className="sandbox-list">
      {sandboxes.map((sandbox) => (
        <SandboxListCard
          key={sandbox.sandbox_id}
          sandbox={sandbox}
          onClick={() => selectSandbox(sandbox.sandbox_id)}
        />
      ))}
    </div>
  );
}
```

**Visual Design**:
- Card layout with status indicator (colored dot)
- Progress bar showing completion percentage
- Last activity timestamp (relative: "2 min ago")
- Click to open detail view

---

### 2. TaskHeader

**Purpose**: Display task information and high-level status

```tsx
interface TaskHeaderProps {
  task: {
    id: string;
    title: string;
    description: string;
    status: string;
    progress_percent: number;
    branch_name: string;
    pr_url?: string;
  };
  sandbox: {
    id: string;
    status: string;
    uptime_seconds: number;
  };
}

function TaskHeader({ task, sandbox }: TaskHeaderProps) {
  return (
    <div className="task-header">
      <div className="task-info">
        <h2>{task.title}</h2>
        <p className="description">{task.description}</p>
        <div className="meta">
          <Badge variant={getStatusVariant(task.status)}>{task.status}</Badge>
          <span className="branch">Branch: {task.branch_name}</span>
          {task.pr_url && <a href={task.pr_url}>View PR →</a>}
        </div>
      </div>
      <ProgressRing percent={task.progress_percent} />
    </div>
  );
}
```

---

### 3. AgentActivityFeed

**Purpose**: Real-time stream of agent events

**Data Source**: WebSocket subscription to `entity_types=sandbox&entity_ids={sandbox_id}`

```tsx
interface AgentEvent {
  id: string;
  timestamp: string;
  event_type: string; // "agent.thinking", "agent.tool_use", "agent.error", etc.
  data: {
    tool?: string;
    file_path?: string;
    thought?: string;
    error?: string;
    [key: string]: any;
  };
}

function AgentActivityFeed({ sandboxId }: { sandboxId: string }) {
  const events = useWebSocketEvents(sandboxId);
  
  return (
    <div className="activity-feed">
      <h3>Agent Activity</h3>
      <div className="event-list">
        {events.map((event) => (
          <EventCard key={event.id} event={event} />
        ))}
      </div>
    </div>
  );
}

function EventCard({ event }: { event: AgentEvent }) {
  // Different rendering based on event_type
  switch (event.event_type) {
    case "agent.thinking":
      return <ThinkingBubble thought={event.data.thought} />;
    case "agent.tool_use":
      return <ToolUseCard tool={event.data.tool} args={event.data} />;
    case "agent.file_modified":
      return <FileModifiedCard path={event.data.file_path} />;
    case "agent.error":
      return <ErrorCard error={event.data.error} />;
    default:
      return <GenericEventCard event={event} />;
  }
}
```

**Event Type Rendering**:

| Event Type | Visual | Content |
|------------|--------|---------|
| `agent.thinking` | 💭 Thought bubble | Truncated reasoning |
| `agent.tool_use` | 🔧 Tool card | Tool name + params |
| `agent.file_modified` | 📄 File card | Path + diff preview |
| `agent.error` | ❌ Error banner | Error message |
| `guardian.intervention` | 🛡️ Guardian card | Steering message |
| `user.message` | 💬 User bubble | User's message |

---

### 4. MessagePanel

**Purpose**: Allow users to send messages to the agent

**API**: `POST /api/v1/sandboxes/{sandbox_id}/messages`

```tsx
function MessagePanel({ sandboxId }: { sandboxId: string }) {
  const [message, setMessage] = useState("");
  const { mutate: sendMessage, isLoading } = useSendMessage(sandboxId);
  
  const handleSend = () => {
    if (!message.trim()) return;
    
    sendMessage({
      content: message,
      message_type: "user_message",
    });
    setMessage("");
  };
  
  return (
    <div className="message-panel">
      <h3>Send Message to Agent</h3>
      <p className="hint">
        The agent will see your message before its next action.
      </p>
      <div className="input-row">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Give the agent guidance or additional context..."
          maxLength={5000}
        />
        <Button 
          onClick={handleSend} 
          disabled={isLoading || !message.trim()}
        >
          {isLoading ? "Sending..." : "Send"}
        </Button>
      </div>
    </div>
  );
}
```

---

### 5. FileChangePreview

**Purpose**: Show files changed by the agent with diff view

**Data Source**: From task results or real-time events

```tsx
interface FileChange {
  path: string;
  action: "created" | "modified" | "deleted";
  lines_added: number;
  lines_removed: number;
  diff?: string; // Unified diff format
}

function FileChangePreview({ files }: { files: FileChange[] }) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  
  return (
    <div className="file-changes">
      <h3>Files Changed ({files.length})</h3>
      <div className="file-list">
        {files.map((file) => (
          <div 
            key={file.path}
            className={`file-item ${file.action}`}
            onClick={() => setSelectedFile(file.path)}
          >
            <FileIcon action={file.action} />
            <span className="path">{file.path}</span>
            <span className="stats">
              <span className="additions">+{file.lines_added}</span>
              <span className="deletions">-{file.lines_removed}</span>
            </span>
          </div>
        ))}
      </div>
      
      {selectedFile && (
        <DiffViewer
          file={files.find((f) => f.path === selectedFile)!}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </div>
  );
}
```

---

### 6. ActionButtons

**Purpose**: Allow user control over sandbox/task

```tsx
interface ActionButtonsProps {
  sandboxId: string;
  taskId: string;
  status: string;
  prUrl?: string;
}

function ActionButtons({ sandboxId, taskId, status, prUrl }: ActionButtonsProps) {
  const { mutate: pauseSandbox } = usePauseSandbox();
  const { mutate: resumeSandbox } = useResumeSandbox();
  const { mutate: cancelTask } = useCancelTask();
  const { mutate: approvePR } = useApprovePR();
  
  return (
    <div className="action-buttons">
      {status === "running" && (
        <>
          <Button variant="secondary" onClick={() => pauseSandbox(sandboxId)}>
            ⏸️ Pause
          </Button>
          <Button variant="danger" onClick={() => cancelTask(taskId)}>
            ❌ Cancel
          </Button>
        </>
      )}
      
      {status === "paused" && (
        <Button variant="primary" onClick={() => resumeSandbox(sandboxId)}>
          ▶️ Resume
        </Button>
      )}
      
      {status === "completed" && prUrl && (
        <Button variant="success" onClick={() => approvePR(prUrl)}>
          ✅ Approve & Merge PR
        </Button>
      )}
      
      {status === "awaiting_review" && (
        <Button variant="primary" onClick={() => navigateToReview(taskId)}>
          👀 Review Required
        </Button>
      )}
    </div>
  );
}
```

---

## WebSocket Integration

### Connection Setup

```tsx
// hooks/useWebSocketEvents.ts

import { useEffect, useState, useCallback } from "react";

export function useWebSocketEvents(sandboxId: string) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  
  useEffect(() => {
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/api/v1/ws/events?entity_types=sandbox&entity_ids=${sandboxId}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      setConnectionStatus("connected");
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Skip ping messages
      if (data.type === "ping") return;
      
      // Add to events list (newest first)
      setEvents((prev) => [data, ...prev].slice(0, 100)); // Keep last 100
    };
    
    ws.onclose = () => {
      setConnectionStatus("disconnected");
    };
    
    ws.onerror = () => {
      setConnectionStatus("disconnected");
    };
    
    return () => ws.close();
  }, [sandboxId]);
  
  return { events, connectionStatus };
}
```

### Event Filtering

```tsx
// Filter events by type for different UI sections
function useFilteredEvents(sandboxId: string) {
  const { events, connectionStatus } = useWebSocketEvents(sandboxId);
  
  const toolEvents = events.filter((e) => e.event_type === "agent.tool_use");
  const thinkingEvents = events.filter((e) => e.event_type === "agent.thinking");
  const fileEvents = events.filter((e) => e.event_type.includes("file"));
  const interventions = events.filter((e) => e.event_type.includes("intervention"));
  
  return {
    allEvents: events,
    toolEvents,
    thinkingEvents,
    fileEvents,
    interventions,
    connectionStatus,
  };
}
```

---

## State Management

### Recommended: React Query + Zustand

```tsx
// stores/sandboxStore.ts

import { create } from "zustand";

interface SandboxState {
  activeSandboxId: string | null;
  setActiveSandbox: (id: string | null) => void;
  
  expandedEventIds: Set<string>;
  toggleEventExpanded: (id: string) => void;
  
  messageInput: string;
  setMessageInput: (value: string) => void;
}

export const useSandboxStore = create<SandboxState>((set) => ({
  activeSandboxId: null,
  setActiveSandbox: (id) => set({ activeSandboxId: id }),
  
  expandedEventIds: new Set(),
  toggleEventExpanded: (id) =>
    set((state) => {
      const newSet = new Set(state.expandedEventIds);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return { expandedEventIds: newSet };
    }),
  
  messageInput: "",
  setMessageInput: (value) => set({ messageInput: value }),
}));
```

### React Query for API Data

```tsx
// queries/sandboxQueries.ts

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export function useSandboxList(userId: string) {
  return useQuery({
    queryKey: ["sandboxes", userId],
    queryFn: () => fetchSandboxes(userId),
    refetchInterval: 10000, // Refresh every 10s
  });
}

export function useSandboxDetails(sandboxId: string) {
  return useQuery({
    queryKey: ["sandbox", sandboxId],
    queryFn: () => fetchSandboxDetails(sandboxId),
    enabled: !!sandboxId,
  });
}

export function useSendMessage(sandboxId: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (message: { content: string; message_type: string }) =>
      postMessage(sandboxId, message),
    onSuccess: () => {
      // Optionally invalidate queries or show toast
      queryClient.invalidateQueries({ queryKey: ["sandbox", sandboxId] });
    },
  });
}
```

---

## API Endpoints Needed

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/sandboxes` | GET | List user's sandboxes | ⬜ New |
| `/api/v1/sandboxes/{id}` | GET | Get sandbox details | ⬜ New |
| `/api/v1/sandboxes/{id}/events` | GET | Get event history | ⬜ New |
| `/api/v1/sandboxes/{id}/messages` | POST | Send message to agent | ✅ Exists |
| `/api/v1/sandboxes/{id}/pause` | POST | Pause sandbox | ⬜ New |
| `/api/v1/sandboxes/{id}/resume` | POST | Resume sandbox | ⬜ New |
| `/api/v1/sandboxes/{id}/cancel` | POST | Cancel/terminate | ⬜ New |
| `/api/v1/ws/events` | WS | Real-time events | ✅ Exists |

---

## Implementation Phases

### Phase 5A: Basic Visibility (4-6 hours)

| Task | Priority | Complexity |
|------|----------|------------|
| Create SandboxList component | High | Low |
| Create TaskHeader component | High | Low |
| Implement WebSocket hook | High | Medium |
| Create basic AgentActivityFeed | High | Medium |

### Phase 5B: User Interaction (4-6 hours)

| Task | Priority | Complexity |
|------|----------|------------|
| Create MessagePanel | High | Low |
| Create ActionButtons | Medium | Low |
| Implement pause/resume/cancel | Medium | Medium |
| Add toast notifications | Low | Low |

### Phase 5C: Enhanced Display (4-6 hours)

| Task | Priority | Complexity |
|------|----------|------------|
| FileChangePreview with diff | Medium | Medium |
| Expand/collapse event details | Low | Low |
| Guardian intervention badges | Low | Low |
| Historical event pagination | Low | Medium |

---

## Wireframe Mockup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏠 Dashboard  │  📋 Tasks  │  🤖 Agents  │  ⚙️ Settings                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────┐  ┌────────────────────────────────────────────┐  │
│  │ Active Sandboxes (3) │  │  Task: Implement dark mode toggle          │  │
│  │                      │  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68%        │  │
│  │ ● Dark Mode Toggle   │  │  Branch: feature/TICKET-456-dark-mode      │  │
│  │   ████████░░ 68%     │  │  Status: 🔵 In Progress                    │  │
│  │                      │  │                                            │  │
│  │ ○ Fix Login Bug      │  │  ┌──────────────────────────────────────┐  │  │
│  │   ███░░░░░░░ 30%     │  │  │ Agent Activity                       │  │  │
│  │                      │  │  │                                      │  │  │
│  │ ○ Add Tests          │  │  │ 💭 Analyzing component structure...  │  │  │
│  │   ░░░░░░░░░░ 5%      │  │  │                                      │  │  │
│  │                      │  │  │ 🔧 Tool: read_file                   │  │  │
│  └──────────────────────┘  │  │    Path: src/components/Settings.tsx │  │  │
│                            │  │                                      │  │  │
│                            │  │ 📄 Modified: src/hooks/useTheme.ts   │  │  │
│                            │  │    +12 lines, -3 lines               │  │  │
│                            │  │                                      │  │  │
│                            │  │ 💭 Implementing toggle component...  │  │  │
│                            │  └──────────────────────────────────────┘  │  │
│                            │                                            │  │
│                            │  ┌──────────────────────────────────────┐  │  │
│                            │  │ Send Message to Agent                │  │  │
│                            │  │                                      │  │  │
│                            │  │ [Also add a loading spinner...    ]  │  │  │
│                            │  │                              [Send]  │  │  │
│                            │  └──────────────────────────────────────┘  │  │
│                            │                                            │  │
│                            │  [⏸️ Pause] [❌ Cancel]                     │  │
│                            └────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Component Tests

```tsx
// __tests__/components/AgentActivityFeed.test.tsx

import { render, screen } from "@testing-library/react";
import { AgentActivityFeed } from "@/components/sandbox/AgentActivityFeed";

describe("AgentActivityFeed", () => {
  it("renders thinking events with thought bubble", () => {
    const events = [
      { id: "1", event_type: "agent.thinking", data: { thought: "Analyzing..." } },
    ];
    
    render(<AgentActivityFeed events={events} />);
    
    expect(screen.getByText("Analyzing...")).toBeInTheDocument();
    expect(screen.getByTestId("thought-bubble")).toBeInTheDocument();
  });
  
  it("renders tool use events with tool card", () => {
    const events = [
      { id: "1", event_type: "agent.tool_use", data: { tool: "write_file", path: "/test.ts" } },
    ];
    
    render(<AgentActivityFeed events={events} />);
    
    expect(screen.getByText("write_file")).toBeInTheDocument();
  });
});
```

### Integration Tests

```tsx
// __tests__/integration/SandboxDashboard.test.tsx

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SandboxDashboard } from "@/pages/sandbox/[id]";

describe("SandboxDashboard Integration", () => {
  it("sends message and shows confirmation", async () => {
    render(<SandboxDashboard sandboxId="test-123" />);
    
    const input = screen.getByPlaceholderText(/guidance/i);
    await userEvent.type(input, "Focus on the API first");
    
    const sendButton = screen.getByRole("button", { name: /send/i });
    await userEvent.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText(/message sent/i)).toBeInTheDocument();
    });
  });
});
```

---

## Related Documents

- [Architecture](./01_architecture.md) - System design
- [Communication Patterns](./04_communication_patterns.md) - API specs
- [Implementation Checklist](./06_implementation_checklist.md) - Phase 5 details
