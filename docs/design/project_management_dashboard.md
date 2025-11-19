# Project Management Dashboard Design

**Created**: 2025-01-30  
**Status**: Design Document  
**Purpose**: Comprehensive design for Kanban board, dependency graphs, GitHub integration, and project management UI

---

## Executive Summary

This document designs a real-time project management dashboard that integrates:
- **Kanban Board**: Visual workflow management with real-time updates, ticket cards with commit indicators
- **Dependency Graph**: Interactive visualization of task/ticket relationships with blocking indicators
- **GitHub Integration**: Repository management, webhook handling, PR/task sync, commit tracking
- **Commit Diff Viewer**: View code changes linked to tickets, see exactly what each agent modified
- **Audit Trails**: Complete history of all changes, commits, and agent actions
- **Project Management**: Multi-project support with agent/task spawning
- **Statistics Dashboard**: Analytics on tickets, tasks, agents, and code changes
- **Search & Filtering**: Advanced search across tickets, commits, agents, and code changes
- **Real-Time Updates**: WebSocket-powered live synchronization across all views

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React/Next.js)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Kanban      │  │  Dependency  │  │  Project    │       │
│  │  Board       │  │  Graph       │  │  Manager    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                          │                                   │
│                    WebSocket Client                         │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           │ ws://api/v1/ws/events
                           │
┌──────────────────────────▼───────────────────────────────────┐
│              Backend API (FastAPI)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Board API   │  │  Graph API   │  │  GitHub API  │       │
│  │  /board/*    │  │  /graph/*    │  │  /github/*   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                          │                                   │
│              ┌────────────▼────────────┐                     │
│              │  WebSocket Event       │                     │
│              │  Manager               │                     │
│              └────────────┬────────────┘                     │
│                           │                                   │
│              ┌────────────▼────────────┐                     │
│              │  EventBusService        │                     │
│              │  (Redis Pub/Sub)        │                     │
│              └────────────┬────────────┘                     │
└───────────────────────────┼───────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
    ┌─────────▼─────────┐      ┌──────────▼──────────┐
    │  PostgreSQL       │      │  GitHub Webhooks    │
    │  (Tickets/Tasks)  │      │  (External Events)   │
    └───────────────────┘      └─────────────────────┘
```

---

## 1. Frontend Architecture

### 1.1 Technology Stack

**Recommended Stack:**
- **Framework**: Next.js 14+ (React 18+)
- **State Management**: Zustand or React Query for server state
- **WebSocket**: Native WebSocket API or `useWebSocket` hook
- **Graph Visualization**: React Flow or D3.js
- **UI Components**: shadcn/ui or Tailwind UI
- **Real-Time**: WebSocket connection to `/api/v1/ws/events`

### 1.2 Component Structure

```
frontend/
├── components/
│   ├── kanban/
│   │   ├── KanbanBoard.tsx          # Main board container
│   │   ├── KanbanColumn.tsx         # Individual column
│   │   ├── TicketCard.tsx           # Ticket card component
│   │   └── WIPIndicator.tsx         # WIP limit display
│   ├── graph/
│   │   ├── DependencyGraph.tsx     # Main graph container
│   │   ├── GraphNode.tsx            # Task/ticket node
│   │   ├── GraphEdge.tsx            # Dependency edge
│   │   └── GraphControls.tsx       # Zoom/pan controls
│   ├── projects/
│   │   ├── ProjectList.tsx          # Project selector
│   │   ├── ProjectCard.tsx          # Project overview
│   │   └── ProjectSettings.tsx     # Project configuration
│   ├── github/
│   │   ├── GitHubIntegration.tsx    # GitHub connection UI
│   │   ├── RepositoryList.tsx       # Connected repos
│   │   ├── WebhookStatus.tsx        # Webhook health
│   │   ├── CommitDiffViewer.tsx    # Commit diff modal/viewer
│   │   ├── CommitList.tsx           # List of commits for ticket
│   │   └── FileDiffViewer.tsx      # Individual file diff viewer
│   ├── audit/
│   │   ├── AuditTrailViewer.tsx    # Complete audit trail
│   │   ├── ChangeHistory.tsx       # Change history timeline
│   │   └── AgentActivityLog.tsx    # Agent activity log
│   ├── statistics/
│   │   ├── StatisticsDashboard.tsx  # Main stats dashboard
│   │   ├── TicketStats.tsx         # Ticket statistics
│   │   ├── AgentStats.tsx          # Agent performance stats
│   │   └── CommitStats.tsx         # Code change statistics
│   └── shared/
│       ├── EventListener.tsx        # WebSocket wrapper
│       ├── AgentSpawner.tsx         # Spawn agent UI
│       ├── TaskCreator.tsx          # Create task UI
│       └── SearchBar.tsx            # Global search component
├── hooks/
│   ├── useWebSocket.ts              # WebSocket connection hook
│   ├── useBoard.ts                  # Board data hook
│   ├── useGraph.ts                  # Graph data hook
│   └── useProjects.ts               # Project management hook
├── stores/
│   ├── boardStore.ts                # Kanban board state
│   ├── graphStore.ts                # Graph state
│   └── projectStore.ts              # Project state
└── pages/
    ├── index.tsx                    # Dashboard home
    ├── board/[projectId].tsx        # Kanban board view
    ├── graph/[projectId].tsx        # Dependency graph view
    ├── statistics/[projectId].tsx   # Statistics dashboard
    ├── search.tsx                   # Global search results
    ├── commits/[commitSha].tsx       # Commit detail view
    ├── tickets/[ticketId].tsx     # Ticket detail with commits
    └── projects.tsx                  # Project management
```

---

## 2. WebSocket Integration

### 2.1 Event Subscription Strategy

**Frontend subscribes to relevant events:**

```typescript
// Connect to WebSocket with filters
const ws = new WebSocket(
  'ws://localhost:18000/api/v1/ws/events?' +
  'event_types=TICKET_CREATED,TICKET_UPDATED,TASK_ASSIGNED,TASK_COMPLETED,' +
  'TASK_FAILED,AGENT_REGISTERED,AGENT_STATUS_CHANGED&' +
  'entity_types=ticket,task,agent'
);

// Listen for events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.event_type) {
    case 'TICKET_CREATED':
    case 'TICKET_UPDATED':
      updateBoard(data.entity_id, data.payload);
      break;
    case 'TASK_ASSIGNED':
    case 'TASK_COMPLETED':
      updateGraph(data.entity_id, data.payload);
      updateBoard(data.payload.ticket_id, data.payload);
      break;
    case 'AGENT_REGISTERED':
      updateAgentList(data.payload);
      break;
  }
};
```

### 2.2 Real-Time Update Flow

```
Backend Event → Redis Pub/Sub → WebSocket Manager → Frontend
     │
     └─→ Event Types:
         - TICKET_CREATED
         - TICKET_UPDATED
         - TICKET_BLOCKED
         - TASK_ASSIGNED
         - TASK_COMPLETED
         - TASK_FAILED
         - AGENT_REGISTERED
         - AGENT_STATUS_CHANGED
         - PHASE_TRANSITION
```

### 2.3 Optimistic Updates

**Frontend Strategy:**
1. User action → Optimistic UI update
2. Send API request
3. WebSocket event confirms → Final state
4. If error → Rollback optimistic update

---

## 3. Kanban Board Implementation

### 3.1 Current Backend API

**Existing Endpoints:**
- `GET /api/v1/board/view` - Get complete board
- `POST /api/v1/board/move` - Move ticket to column
- `GET /api/v1/board/stats` - Column statistics
- `GET /api/v1/board/wip-violations` - WIP limit checks
- `POST /api/v1/board/auto-transition/{ticket_id}` - Auto-transition

### 3.2 Frontend Integration

**Kanban Board Component:**

```typescript
// hooks/useBoard.ts
export function useBoard(projectId: string) {
  const [board, setBoard] = useState<BoardView | null>(null);
  const ws = useWebSocket();
  
  // Initial load
  useEffect(() => {
    fetch(`/api/v1/board/view?project_id=${projectId}`)
      .then(res => res.json())
      .then(setBoard);
  }, [projectId]);
  
  // Real-time updates via WebSocket
  useEffect(() => {
    const handler = (event: SystemEvent) => {
      if (event.entity_type === 'ticket') {
        // Update ticket in board
        setBoard(prev => updateTicketInBoard(prev, event));
      }
    };
    
    ws.subscribe(['TICKET_CREATED', 'TICKET_UPDATED'], handler);
    return () => ws.unsubscribe(handler);
  }, [ws]);
  
  const moveTicket = async (ticketId: string, columnId: string) => {
    // Optimistic update
    setBoard(prev => moveTicketOptimistic(prev, ticketId, columnId));
    
    // API call
    await fetch('/api/v1/board/move', {
      method: 'POST',
      body: JSON.stringify({ ticket_id: ticketId, target_column_id: columnId })
    });
    
    // WebSocket event will confirm the move
  };
  
  return { board, moveTicket };
}
```

### 3.3 Real-Time Features

**Live Updates:**
- Ticket moves between columns
- WIP limit violations (red highlight)
- New tickets appear
- Status changes (blocked/unblocked)
- Agent assignments
- Commit indicators update (+X/-Y lines changed)
- New commits linked to tickets

### 3.4 Ticket Card Enhancements

**Ticket Card Features:**
- **Commit Indicators**: Show `+X -Y` for commits linked to ticket
- **Component Tags**: Display component/area (e.g., "infrastructure", "security")
- **Phase Badge**: Show current phase (e.g., "phase-2-pending")
- **Priority Badge**: Color-coded priority (CRITICAL, HIGH, MEDIUM, LOW)
- **Click to View**: Opens ticket detail with commit history
- **Quick Actions**: Link commit, view diff, spawn agent

---

## 4. Dependency Graph Implementation

### 4.1 Backend API Design

**New Endpoints Needed:**

```python
# omoi_os/api/routes/graph.py

@router.get("/dependency-graph/{ticket_id}")
async def get_dependency_graph(
    ticket_id: str,
    include_resolved: bool = Query(True),
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """
    Get dependency graph for a ticket.
    
    Returns:
    {
        "nodes": [
            {
                "id": "task-123",
                "type": "task",
                "title": "Implement feature",
                "status": "running",
                "phase_id": "PHASE_IMPLEMENTATION",
                "priority": "HIGH",
                "is_blocked": false,
                "blocks_count": 2
            },
            ...
        ],
        "edges": [
            {
                "from": "task-123",
                "to": "task-456",
                "type": "depends_on",
                "discovery_type": "bug_found"  # optional
            },
            ...
        ],
        "metadata": {
            "total_tasks": 10,
            "blocked_count": 3,
            "resolved_count": 2
        }
    }
    """
    # Implementation: Query tasks, build graph structure
    pass

@router.get("/dependency-graph/project/{project_id}")
async def get_project_graph(
    project_id: str,
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """Get dependency graph for entire project (all tickets)."""
    pass
```

### 4.2 Graph Data Structure

**Node Types:**
- **Ticket Node**: Top-level work item
- **Task Node**: Individual work unit
- **Discovery Node**: Branch point (bug found, optimization, etc.)

**Edge Types:**
- **depends_on**: Task A must complete before Task B
- **blocks**: Task A blocks Task B
- **spawned_from**: Task B spawned from discovery in Task A
- **parent_child**: Sub-task relationship

**Visual Indicators:**
- **Color**: Status (green=done, red=blocked, yellow=running, gray=pending)
- **Size**: Priority (larger = higher priority)
- **Border**: Critical tasks (thick red border)
- **Icon**: Task type (🔨 building, 🧪 testing, etc.)

### 4.3 Frontend Graph Component

```typescript
// components/graph/DependencyGraph.tsx
import ReactFlow, { Node, Edge } from 'react-flow-renderer';

export function DependencyGraph({ ticketId }: { ticketId: string }) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const ws = useWebSocket();
  
  // Load initial graph
  useEffect(() => {
    fetch(`/api/v1/graph/dependency-graph/${ticketId}`)
      .then(res => res.json())
      .then(data => {
        setNodes(transformToFlowNodes(data.nodes));
        setEdges(transformToFlowEdges(data.edges));
      });
  }, [ticketId]);
  
  // Real-time updates
  useEffect(() => {
    const handler = (event: SystemEvent) => {
      if (event.entity_type === 'task') {
        // Update node status
        setNodes(prev => updateNodeStatus(prev, event.entity_id, event.payload));
        
        // Update edges if dependencies changed
        if (event.payload.dependencies_changed) {
          refreshGraph();
        }
      }
    };
    
    ws.subscribe(['TASK_ASSIGNED', 'TASK_COMPLETED', 'TASK_FAILED'], handler);
    return () => ws.unsubscribe(handler);
  }, [ws]);
  
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodeClick={handleNodeClick}
      onEdgeClick={handleEdgeClick}
    />
  );
}
```

### 4.4 Interactive Features

**User Interactions:**
- **Click node**: Show task details sidebar
- **Drag node**: Reposition (layout persists)
- **Hover edge**: Show dependency reason
- **Filter**: Show/hide resolved tasks
- **Layout**: Top-down or left-right
- **Zoom/Pan**: Navigate large graphs

---

## 5. Commit Tracking & Diff Viewing

### 5.1 Commit Data Model

**Existing Model** (`TicketCommit`):
```python
class TicketCommit(Base):
    id: str
    ticket_id: str
    agent_id: str                    # Which agent made this commit
    commit_sha: str                  # Full commit SHA
    commit_message: str
    commit_timestamp: datetime
    files_changed: Optional[int]     # Number of files
    insertions: Optional[int]         # Lines added (+X)
    deletions: Optional[int]          # Lines deleted (-Y)
    files_list: Optional[dict]        # JSONB: {file_path: {additions, deletions, changes}}
    linked_at: datetime
    link_method: str                  # 'manual', 'webhook', 'auto'
```

### 5.2 Commit Diff Viewer UI

**Component**: `CommitDiffViewer.tsx`

**Features:**
- **Commit Header**: SHA, message, author, date, summary (+X -Y files)
- **File List**: Scrollable list of changed files with diff stats
- **File Diff View**: Side-by-side or unified diff view
- **Syntax Highlighting**: Code syntax highlighting for diffs
- **Line-by-Line**: Click to view specific line changes
- **Agent Attribution**: Show which agent made the commit
- **Ticket Link**: Link back to associated ticket
- **Navigation**: Previous/next commit, jump to file

**UI Layout:**
```
┌─────────────────────────────────────────┐
│ Commit Diff: 02979f61095b7d...          │
├─────────────────────────────────────────┤
│ Merge agent 9a781fc3 work into main     │
│ Ido Levi • Oct 30, 2025 12:47           │
│ +2255 -0 • 17 files                      │
├─────────────────────────────────────────┤
│ Files Changed:                           │
│ ┌─────────────────────────────────────┐ │
│ │ backend/core/database.py            │ │
│ │ +35 -0                               │ │
│ ├─────────────────────────────────────┤ │
│ │ backend/main.py                      │ │
│ │ +52 -0                               │ │
│ ├─────────────────────────────────────┤ │
│ │ backend/poetry.lock                  │ │
│ │ +1570 -0                             │ │
│ └─────────────────────────────────────┘ │
│                                          │
│ [View Full Diff] [Download Patch]        │
└─────────────────────────────────────────┘
```

### 5.3 Commit Linking

**Automatic Linking:**
- **Webhook**: GitHub push events automatically link commits
- **PR Merge**: When PR merges, commits linked to associated task
- **Agent Work**: Agent commits include ticket ID in commit message
- **Pattern Matching**: Parse commit messages for ticket references

**Manual Linking:**
- **UI Action**: "Link Commit" button on ticket detail
- **Search**: Search commits by SHA, message, or date
- **Bulk Link**: Link multiple commits at once

### 5.4 Commit API Endpoints

**New Endpoints:**

```python
# omoi_os/api/routes/commits.py

@router.get("/commits/{commit_sha}")
async def get_commit_details(
    commit_sha: str,
    db: DatabaseService = Depends(get_db_service),
    github_service: GitHubIntegrationService = Depends(get_github_service),
) -> Dict[str, Any]:
    """
    Get commit details including diff.
    
    Returns:
    {
        "commit_sha": "02979f61095b7d...",
        "commit_message": "Merge agent work",
        "author": "Ido Levi",
        "date": "2025-10-30T12:47:00Z",
        "summary": {"files": 17, "insertions": 2255, "deletions": 0},
        "files": [
            {
                "path": "backend/core/database.py",
                "additions": 35,
                "deletions": 0,
                "changes": 35,
                "status": "added"
            },
            ...
        ],
        "ticket_id": "ticket-123",  # if linked
        "agent_id": "agent-456",    # if linked
        "diff_url": "https://github.com/owner/repo/commit/02979f6..."
    }
    """
    pass

@router.get("/tickets/{ticket_id}/commits")
async def get_ticket_commits(
    ticket_id: str,
    db: DatabaseService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    """Get all commits linked to a ticket."""
    pass

@router.post("/tickets/{ticket_id}/commits/link")
async def link_commit_to_ticket(
    ticket_id: str,
    request: LinkCommitRequest,
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """Manually link a commit to a ticket."""
    pass

@router.get("/agents/{agent_id}/commits")
async def get_agent_commits(
    agent_id: str,
    db: DatabaseService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    """Get all commits made by an agent."""
    pass

@router.get("/commits/{commit_sha}/diff")
async def get_commit_diff(
    commit_sha: str,
    file_path: Optional[str] = None,
    github_service: GitHubIntegrationService = Depends(get_github_service),
) -> Dict[str, Any]:
    """
    Get commit diff (full or for specific file).
    
    Returns:
    {
        "commit_sha": "...",
        "files": [
            {
                "path": "backend/core/database.py",
                "old_content": "...",
                "new_content": "...",
                "hunks": [
                    {
                        "old_start": 10,
                        "old_lines": 5,
                        "new_start": 10,
                        "new_lines": 7,
                        "lines": [
                            {"type": "context", "content": "..."},
                            {"type": "removed", "content": "-old line"},
                            {"type": "added", "content": "+new line"},
                        ]
                    }
                ]
            }
        ]
    }
    """
    pass
```

### 5.5 Agent-to-Commit Tracking

**Key Feature**: "View exactly which code changes each agent made"

**Implementation:**
- Every commit linked to ticket includes `agent_id`
- Agent commits tracked in `TicketCommit` model
- UI shows agent name/ID on commit cards
- Filter commits by agent
- Agent activity log shows all commits

**UI Components:**
- **Agent Commit List**: All commits by specific agent
- **Agent Stats**: Lines changed, files modified, commits count
- **Timeline View**: Chronological view of agent commits
- **Contribution Graph**: Visual representation of agent contributions

---

## 6. GitHub Integration

### 6.1 GitHub Webhook Handler

**New Backend Service:**

```python
# omoi_os/services/github_integration.py

class GitHubIntegrationService:
    """Manages GitHub repository connections and webhooks."""
    
    def __init__(self, db: DatabaseService, event_bus: EventBusService):
        self.db = db
        self.event_bus = event_bus
        self.github_client = None  # PyGithub client
    
    def connect_repository(
        self,
        repo_owner: str,
        repo_name: str,
        access_token: str,
    ) -> GitHubRepository:
        """Connect a GitHub repository and set up webhooks."""
        # 1. Verify access token
        # 2. Create repository record
        # 3. Register webhook with GitHub
        # 4. Store webhook secret
        pass
    
    def handle_webhook(
        self,
        event_type: str,
        payload: dict,
        signature: str,
    ) -> None:
        """Process incoming GitHub webhook events."""
        # Verify webhook signature
        # Route to appropriate handler:
        # - issues.opened → Create ticket
        # - pull_request.opened → Link to task
        # - pull_request.merged → Mark task complete, link commits
        # - push → Link commits to tickets, update codebase context
        # - commit_comment → Link comment to ticket/task
        pass
    
    def get_commit_diff(
        self,
        repo_owner: str,
        repo_name: str,
        commit_sha: str,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch commit diff from GitHub API."""
        # Use GitHub API to get commit details and diff
        # Return structured diff data
        pass
    
    def link_commit_to_ticket(
        self,
        commit_sha: str,
        ticket_id: str,
        agent_id: Optional[str] = None,
    ) -> TicketCommit:
        """Link a GitHub commit to a ticket."""
        # Fetch commit details from GitHub
        # Create TicketCommit record
        # Publish COMMIT_LINKED event
        pass
    
    def parse_commit_message_for_ticket(
        self,
        commit_message: str,
    ) -> Optional[str]:
        """Extract ticket ID from commit message patterns."""
        # Patterns: "Fix #123", "Closes ticket-456", "TICKET-789"
        pass
```

### 6.2 Webhook Events → System Events

**Event Mapping:**

```python
# GitHub Webhook → System Event

# Issue created
github.issues.opened → {
    event_type: "TICKET_CREATED",
    entity_type: "ticket",
    payload: {
        source: "github",
        github_issue_number: 123,
        github_repo: "owner/repo",
        title: issue.title,
        description: issue.body,
    }
}

# PR merged
github.pull_request.merged → {
    event_type: "TASK_COMPLETED",
    entity_type: "task",
    payload: {
        source: "github",
        github_pr_number: 456,
        commit_sha: pr.merge_commit_sha,
        linked_task_id: task_id,  # From PR description or labels
    }
}

# Push to main
github.push → {
    event_type: "COMMIT_PUSHED",
    entity_type: "commit",
    payload: {
        branch: "main",
        commits: [
            {
                "sha": "02979f61095b7d...",
                "message": "Merge agent 9a781fc3 work into main",
                "author": "Ido Levi",
                "files_changed": 17,
                "insertions": 2255,
                "deletions": 0
            }
        ],
        # Auto-link commits to tickets based on message patterns
        "linked_tickets": ["ticket-123"]
    }
}

# Commit comment
github.commit_comment → {
    event_type: "COMMIT_COMMENTED",
    entity_type: "commit",
    payload: {
        commit_sha: "...",
        comment: "...",
        ticket_id: "..."  # if linked
    }
}
```

### 6.3 GitHub API Integration

**New API Routes:**

```python
# omoi_os/api/routes/github.py

@router.post("/repositories/connect")
async def connect_repository(
    request: ConnectRepositoryRequest,
    github_service: GitHubIntegrationService = Depends(get_github_service),
):
    """Connect a GitHub repository."""
    repo = github_service.connect_repository(
        repo_owner=request.owner,
        repo_name=request.name,
        access_token=request.access_token,
    )
    return {"repository_id": repo.id, "webhook_url": repo.webhook_url}

@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    github_service: GitHubIntegrationService = Depends(get_github_service),
):
    """Receive GitHub webhook events."""
    event_type = request.headers.get("X-GitHub-Event")
    signature = request.headers.get("X-Hub-Signature-256")
    payload = await request.json()
    
    github_service.handle_webhook(event_type, payload, signature)
    return {"status": "processed"}

@router.get("/repositories/{repo_id}/issues")
async def list_github_issues(
    repo_id: str,
    github_service: GitHubIntegrationService = Depends(get_github_service),
):
    """List GitHub issues for a repository."""
    pass

@router.post("/repositories/{repo_id}/create-issue")
async def create_github_issue(
    repo_id: str,
    request: CreateIssueRequest,
    github_service: GitHubIntegrationService = Depends(get_github_service),
):
    """Create a GitHub issue from a ticket."""
    pass
```

### 6.4 Bidirectional Sync

**GitHub → System:**
- Issue created → Ticket created
- PR opened → Task linked
- PR merged → Task completed
- Push → Codebase context updated

**System → GitHub:**
- Ticket created → GitHub issue (optional)
- Task completed → PR comment
- Agent spawn → GitHub issue comment
- Status update → GitHub label update

---

## 7. Audit Trails & History

### 7.1 Complete Audit Trail

**Key Feature**: "Complete audit trails of all modifications"

**Data Sources:**
- `TicketHistory`: All ticket changes (status, fields, etc.)
- `TicketCommit`: All commits linked to tickets
- `AgentStatusTransition`: Agent status changes
- `Task` status changes: Task lifecycle events
- `TaskDiscovery`: Workflow branching decisions

### 7.2 Audit Trail Viewer

**Component**: `AuditTrailViewer.tsx`

**Features:**
- **Timeline View**: Chronological list of all changes
- **Filter by Type**: Commits, status changes, field updates, discoveries
- **Filter by Agent**: See all changes by specific agent
- **Filter by Ticket**: Complete history for a ticket
- **Search**: Search audit trail entries
- **Export**: Export audit trail as CSV/JSON

**Timeline Entry Types:**
```typescript
interface AuditEntry {
  id: string;
  timestamp: string;
  type: 'commit' | 'status_change' | 'field_update' | 'discovery' | 'agent_action';
  agent_id: string;
  agent_name: string;
  ticket_id?: string;
  task_id?: string;
  description: string;
  details: {
    // For commits
    commit_sha?: string;
    files_changed?: number;
    insertions?: number;
    deletions?: number;
    
    // For status changes
    from_status?: string;
    to_status?: string;
    
    // For field updates
    field_name?: string;
    old_value?: string;
    new_value?: string;
    
    // For discoveries
    discovery_type?: string;
    spawned_tasks?: string[];
  };
}
```

### 7.3 Change History API

**New Endpoints:**

```python
# omoi_os/api/routes/audit.py

@router.get("/audit/tickets/{ticket_id}")
async def get_ticket_audit_trail(
    ticket_id: str,
    db: DatabaseService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    """Get complete audit trail for a ticket."""
    # Combine TicketHistory + TicketCommit records
    pass

@router.get("/audit/agents/{agent_id}")
async def get_agent_audit_trail(
    agent_id: str,
    db: DatabaseService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    """Get all actions by an agent."""
    # Commits, task assignments, discoveries, etc.
    pass

@router.get("/audit/projects/{project_id}")
async def get_project_audit_trail(
    project_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: DatabaseService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    """Get audit trail for entire project."""
    pass
```

---

## 8. Statistics Dashboard

### 8.1 Statistics Views

**Component**: `StatisticsDashboard.tsx`

**Key Metrics:**
- **Ticket Statistics**:
  - Total tickets by status
  - Tickets by priority
  - Average time in each phase
  - Blocked tickets count
  - Completion rate
  
- **Agent Statistics**:
  - Active agents count
  - Tasks completed per agent
  - Commits per agent
  - Lines changed per agent
  - Average task completion time
  
- **Code Change Statistics**:
  - Total commits
  - Total lines changed (insertions/deletions)
  - Files changed
  - Commits per ticket
  - Most active files
  
- **Project Health**:
  - WIP violations
  - Dependency blockers
  - Agent health status
  - Cost tracking

### 8.2 Statistics API

**New Endpoints:**

```python
# omoi_os/api/routes/statistics.py

@router.get("/statistics/projects/{project_id}/overview")
async def get_project_statistics(
    project_id: str,
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """Get comprehensive project statistics."""
    pass

@router.get("/statistics/tickets")
async def get_ticket_statistics(
    project_id: Optional[str] = None,
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """Get ticket statistics."""
    pass

@router.get("/statistics/agents")
async def get_agent_statistics(
    project_id: Optional[str] = None,
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """Get agent performance statistics."""
    pass

@router.get("/statistics/commits")
async def get_commit_statistics(
    project_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """Get code change statistics."""
    pass
```

---

## 9. Search & Filtering

### 9.1 Global Search

**Component**: `SearchBar.tsx`

**Search Capabilities:**
- **Tickets**: By title, description, ID, component
- **Tasks**: By description, status, agent
- **Commits**: By SHA, message, author, date
- **Agents**: By name, ID, type
- **Files**: By path, changes in commits

**Search Features:**
- **Full-text search**: Across all ticket/task descriptions
- **Fuzzy matching**: Handle typos
- **Filter by type**: Tickets, tasks, commits, agents
- **Filter by project**: Scope to specific project
- **Recent searches**: Quick access to recent queries
- **Saved searches**: Save common search queries

### 9.2 Advanced Filtering

**Filter Options:**
- **By Status**: All statuses, specific status
- **By Priority**: CRITICAL, HIGH, MEDIUM, LOW
- **By Component**: Infrastructure, security, frontend, etc.
- **By Phase**: Backlog, building, testing, etc.
- **By Agent**: Filter tickets/tasks by assigned agent
- **By Date Range**: Created, updated, completed dates
- **By Commit**: Tickets with/without commits
- **By Blocking**: Blocked tickets, blocking tickets

### 9.3 Search API

**New Endpoints:**

```python
# omoi_os/api/routes/search.py

@router.get("/search")
async def global_search(
    q: str,
    types: Optional[str] = None,  # Comma-separated: ticket,task,commit,agent
    project_id: Optional[str] = None,
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """
    Global search across all entities.
    
    Returns:
    {
        "tickets": [...],
        "tasks": [...],
        "commits": [...],
        "agents": [...],
        "total": 42
    }
    """
    pass

@router.get("/search/tickets")
async def search_tickets(
    q: str,
    filters: Optional[Dict[str, Any]] = None,
    db: DatabaseService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    """Search tickets with filters."""
    pass

@router.get("/search/commits")
async def search_commits(
    q: str,
    agent_id: Optional[str] = None,
    ticket_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: DatabaseService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    """Search commits with filters."""
    pass
```

---

## 10. Project Management

### 10.1 Project Model

**New Database Model:**

```python
# omoi_os/models/project.py

class Project(Base):
    """Project represents a collection of tickets and agents."""
    
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # GitHub integration
    github_owner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    github_repo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    github_webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Project settings
    default_phase_id: Mapped[str] = mapped_column(String(50), nullable=False)
    board_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="project")
    agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="project")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
```

### 10.2 Project API

**New Endpoints:**

```python
# omoi_os/api/routes/projects.py

@router.get("/projects")
async def list_projects(
    db: DatabaseService = Depends(get_db_service),
) -> List[ProjectDTO]:
    """List all projects."""
    pass

@router.post("/projects")
async def create_project(
    request: CreateProjectRequest,
    db: DatabaseService = Depends(get_db_service),
) -> ProjectDTO:
    """Create a new project."""
    pass

@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: DatabaseService = Depends(get_db_service),
) -> ProjectDTO:
    """Get project details."""
    pass

@router.post("/projects/{project_id}/spawn-agent")
async def spawn_agent(
    project_id: str,
    request: SpawnAgentRequest,
    registry: AgentRegistryService = Depends(get_agent_registry_service),
) -> AgentDTO:
    """Spawn a new agent for this project."""
    pass

@router.post("/projects/{project_id}/create-ticket")
async def create_ticket(
    project_id: str,
    request: CreateTicketRequest,
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
) -> TicketDTO:
    """Create a ticket in this project."""
    pass
```

---

## 10.3 AI-Assisted Project Exploration & Definition

### 10.3.1 Overview

**Feature**: AI-powered project discovery and planning workflow that helps users explore, define, and document projects through conversational interaction.

**Workflow:**
1. User initiates project exploration with initial idea (e.g., "I want to create an authentication system with plugins")
2. AI asks clarifying questions to understand requirements
3. AI generates comprehensive requirements document
4. User reviews and approves requirements
5. AI generates design document based on approved requirements
6. User uses documents to create tickets/tasks for implementation

### 10.3.2 Database Models

**New Models:**

```python
# omoi_os/models/project_exploration.py

class ProjectExploration(Base):
    """Tracks AI-assisted project exploration sessions."""
    
    __tablename__ = "project_explorations"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("projects.id"), nullable=True, index=True
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    
    # Exploration state
    initial_idea: Mapped[str] = mapped_column(Text, nullable=False)
    current_stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="exploring"
    )  # exploring, requirements_draft, requirements_review, design_draft, design_review, completed
    
    # Generated documents
    requirements_document_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("project_documents.id"), nullable=True
    )
    design_document_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("project_documents.id"), nullable=True
    )
    
    # Conversation history
    conversation_history: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # Stores full conversation with AI
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectDocument(Base):
    """Stores requirements and design documents generated by AI."""
    
    __tablename__ = "project_documents"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("projects.id"), nullable=True, index=True
    )
    exploration_id: Mapped[str] = mapped_column(
        String, ForeignKey("project_explorations.id"), nullable=False, index=True
    )
    
    # Document metadata
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # requirements, design
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Document content
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown content
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hash
    
    # Approval workflow
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )  # draft, pending_review, approved, rejected, superseded
    approved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    previous_version_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("project_documents.id"), nullable=True
    )  # For versioning
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ExplorationQuestion(Base):
    """Tracks questions asked during exploration."""
    
    __tablename__ = "exploration_questions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    exploration_id: Mapped[str] = mapped_column(
        String, ForeignKey("project_explorations.id"), nullable=False, index=True
    )
    
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # scope, technical, user_experience, security, performance, etc.
    
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # AI metadata
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    follow_up_questions: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
```

### 10.3.3 AI Conversation Interface

**Component**: `ProjectExplorer.tsx`

**Features:**
- Chat-like interface for AI conversation
- Question cards with answer inputs
- Progress indicator showing exploration stage
- Document preview (requirements/design)
- Approval/rejection controls

**UI Layout:**
```
┌─────────────────────────────────────────┐
│ Project Explorer: Authentication System│
├─────────────────────────────────────────┤
│ Stage: Requirements Review (2/5)       │
├─────────────────────────────────────────┤
│                                         │
│ 🤖 AI: "What authentication methods    │
│         should be supported?"          │
│                                         │
│ 👤 You: "OAuth2, JWT, and API keys"    │
│                                         │
│ 🤖 AI: "Should this support multi-      │
│         tenant scenarios?"              │
│                                         │
│ 👤 You: [Answer input...]               │
│                                         │
├─────────────────────────────────────────┤
│ [View Requirements Draft] [Continue]   │
└─────────────────────────────────────────┘
```

### 10.3.4 Question Generation Strategy

**AI Question Categories:**

1. **Scope & Boundaries**
   - What is the primary goal?
   - What is out of scope?
   - Target users/audience?

2. **Technical Requirements**
   - Technology stack preferences?
   - Integration requirements?
   - Performance requirements?
   - Scalability needs?

3. **Security & Compliance**
   - Security requirements?
   - Compliance standards (GDPR, HIPAA, etc.)?
   - Authentication/authorization needs?

4. **User Experience**
   - User interface requirements?
   - Accessibility needs?
   - Mobile support?

5. **Business Logic**
   - Core features?
   - Edge cases?
   - Business rules?

**Question Generation Algorithm:**
```python
class ProjectExplorationService:
    def generate_questions(
        self,
        exploration_id: str,
        conversation_history: List[Dict],
        current_understanding: Dict
    ) -> List[Question]:
        """
        Generate next set of clarifying questions based on:
        - Gaps in current understanding
        - Complexity of the project
        - Industry best practices
        - Similar projects in knowledge base
        """
        # Use LLM to analyze conversation and generate questions
        # Prioritize questions by importance
        # Return top N questions
        pass
```

### 10.3.5 Requirements Document Generation

**Generation Process:**

1. **Analysis Phase**: AI analyzes all Q&A pairs
2. **Structuring Phase**: Organizes information into requirements sections
3. **Drafting Phase**: Generates comprehensive requirements document
4. **Review Phase**: User reviews and provides feedback
5. **Iteration Phase**: AI refines based on feedback
6. **Approval Phase**: User approves final version

**Requirements Document Structure:**
```markdown
# Project Requirements: Authentication System with Plugins

## 1. Overview
- Project goal
- Scope
- Out of scope

## 2. Functional Requirements
- Core features
- User stories
- Use cases

## 3. Non-Functional Requirements
- Performance
- Security
- Scalability
- Reliability

## 4. Technical Requirements
- Technology stack
- Integration points
- API requirements

## 5. User Experience Requirements
- UI/UX needs
- Accessibility
- Mobile support

## 6. Constraints & Assumptions
- Technical constraints
- Business constraints
- Assumptions

## 7. Success Criteria
- Acceptance criteria
- Metrics
- KPIs
```

**API Endpoints:**
```python
@router.post("/projects/explore/start")
async def start_exploration(
    request: StartExplorationRequest,
    llm_service: LLMService = Depends(get_llm_service),
) -> ExplorationDTO:
    """Start new project exploration session."""
    # Create exploration record
    # Generate initial questions
    pass

@router.post("/projects/explore/{exploration_id}/answer")
async def answer_question(
    exploration_id: str,
    request: AnswerQuestionRequest,
    llm_service: LLMService = Depends(get_llm_service),
) -> ExplorationDTO:
    """Answer a question and get next questions."""
    # Store answer
    # Generate follow-up questions
    # Check if ready for requirements generation
    pass

@router.post("/projects/explore/{exploration_id}/generate-requirements")
async def generate_requirements(
    exploration_id: str,
    llm_service: LLMService = Depends(get_llm_service),
) -> ProjectDocumentDTO:
    """Generate requirements document from exploration."""
    # Analyze all Q&A
    # Generate requirements document
    # Create document record
    pass

@router.post("/projects/explore/{exploration_id}/refine-requirements")
async def refine_requirements(
    exploration_id: str,
    request: RefineRequirementsRequest,
    llm_service: LLMService = Depends(get_llm_service),
) -> ProjectDocumentDTO:
    """Refine requirements based on user feedback."""
    # Update requirements document
    # Create new version
    pass
```

### 10.3.6 Design Document Generation

**Generation Trigger:**
- Only after requirements document is approved
- Uses approved requirements as source of truth

**Design Document Structure:**
```markdown
# Design Document: Authentication System with Plugins

## 1. Architecture Overview
- System architecture
- Component diagram
- Technology stack

## 2. Component Design
- Authentication service
- Plugin system
- API design
- Database schema

## 3. Security Design
- Authentication flows
- Authorization model
- Security measures

## 4. Integration Design
- External integrations
- API contracts
- Data flow

## 5. Implementation Plan
- Phases
- Dependencies
- Timeline estimates

## 6. Testing Strategy
- Test approach
- Test cases
- Quality metrics
```

**API Endpoints:**
```python
@router.post("/projects/explore/{exploration_id}/generate-design")
async def generate_design(
    exploration_id: str,
    llm_service: LLMService = Depends(get_llm_service),
) -> ProjectDocumentDTO:
    """Generate design document from approved requirements."""
    # Verify requirements are approved
    # Generate design document
    # Create document record
    pass
```

### 10.3.7 Document Approval Workflow

**Approval States:**
- `draft` - Initial generation
- `pending_review` - Awaiting user review
- `approved` - User approved, ready for next stage
- `rejected` - User rejected, needs revision
- `superseded` - Replaced by newer version

**UI Components:**
- `DocumentViewer.tsx` - View document with syntax highlighting
- `DocumentApproval.tsx` - Approval/rejection controls
- `DocumentFeedback.tsx` - Provide feedback for refinement
- `DocumentVersionHistory.tsx` - View all versions

**API Endpoints:**
```python
@router.post("/documents/{document_id}/approve")
async def approve_document(
    document_id: str,
    user_id: str,
) -> ProjectDocumentDTO:
    """Approve a document."""
    pass

@router.post("/documents/{document_id}/reject")
async def reject_document(
    document_id: str,
    request: RejectDocumentRequest,
) -> ProjectDocumentDTO:
    """Reject a document with feedback."""
    pass

@router.get("/documents/{document_id}/versions")
async def get_document_versions(
    document_id: str,
) -> List[ProjectDocumentDTO]:
    """Get version history for a document."""
    pass
```

### 10.3.8 Integration with Ticket/Task Creation

**Workflow:**
1. After design document approval, user can "Initialize Project"
2. System analyzes design document
3. System creates initial tickets based on design phases
4. System creates tasks for each ticket
5. Project is ready for agent assignment

**UI Component**: `ProjectInitializer.tsx`
- Preview of tickets that will be created
- Option to customize ticket creation
- One-click project initialization

**API Endpoints:**
```python
@router.post("/projects/explore/{exploration_id}/initialize-project")
async def initialize_project(
    exploration_id: str,
    request: InitializeProjectRequest,
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
) -> ProjectDTO:
    """
    Create project and initial tickets from approved design.
    
    Steps:
    1. Create project record
    2. Parse design document for phases/features
    3. Create tickets for each major feature/phase
    4. Create initial tasks for each ticket
    5. Link documents to project
    """
    pass
```

### 10.3.9 Document Storage & Versioning

**Storage:**
- Documents stored in database (`project_documents` table)
- Content stored as Markdown text
- Version history maintained via `previous_version_id`
- Content hashing for change detection

**Features:**
- Full version history
- Diff view between versions
- Export to file (Markdown, PDF)
- Link documents to tickets/tasks

**UI Components:**
- `DocumentDiffViewer.tsx` - Compare document versions
- `DocumentExporter.tsx` - Export document
- `DocumentLinker.tsx` - Link document to tickets

### 10.3.10 Real-Time Updates

**WebSocket Events:**
```typescript
EXPLORATION_STARTED → { exploration_id, initial_idea }
QUESTION_GENERATED → { exploration_id, question_id, question_text }
QUESTION_ANSWERED → { exploration_id, question_id, answer_text }
REQUIREMENTS_GENERATED → { exploration_id, document_id }
REQUIREMENTS_APPROVED → { exploration_id, document_id }
DESIGN_GENERATED → { exploration_id, document_id }
DESIGN_APPROVED → { exploration_id, document_id }
PROJECT_INITIALIZED → { exploration_id, project_id }
```

### 10.3.11 Example User Flow

```
1. User clicks "Explore New Project"
   ↓
2. Enters: "I want to create an authentication system with plugins"
   ↓
3. AI asks: "What authentication methods should be supported?"
   ↓
4. User answers: "OAuth2, JWT, and API keys"
   ↓
5. AI asks: "Should this support multi-tenant scenarios?"
   ↓
6. User answers: "Yes, with tenant isolation"
   ↓
7. [More Q&A rounds...]
   ↓
8. AI: "I have enough information. Generating requirements document..."
   ↓
9. Requirements document appears for review
   ↓
10. User reviews, provides feedback
    ↓
11. AI refines requirements
    ↓
12. User approves requirements
    ↓
13. AI: "Generating design document based on approved requirements..."
    ↓
14. Design document appears for review
    ↓
15. User reviews, provides feedback
    ↓
16. AI refines design
    ↓
17. User approves design
    ↓
18. User clicks "Initialize Project"
    ↓
19. System creates project and initial tickets/tasks
    ↓
20. Project ready for development!
```

### 10.3.12 Implementation Notes

**LLM Integration:**
- Use existing LLM service for conversation
- Maintain conversation context across turns
- Use structured prompts for document generation
- Implement token limits and cost tracking

**Knowledge Base Integration:**
- Reference similar projects from memory system
- Use existing design patterns
- Learn from past project explorations

**Performance Considerations:**
- Cache common questions/answers
- Stream document generation (show progress)
- Background processing for large documents

---

## 11. Agent & Task Spawning UI

### 11.1 Agent Spawner Component

```typescript
// components/shared/AgentSpawner.tsx

export function AgentSpawner({ projectId }: { projectId: string }) {
  const [agentType, setAgentType] = useState('worker');
  const [phaseId, setPhaseId] = useState('PHASE_IMPLEMENTATION');
  const [capabilities, setCapabilities] = useState<string[]>([]);
  
  const spawnAgent = async () => {
    const response = await fetch(`/api/v1/projects/${projectId}/spawn-agent`, {
      method: 'POST',
      body: JSON.stringify({
        agent_type: agentType,
        phase_id: phaseId,
        capabilities: capabilities,
        capacity: 1,
      }),
    });
    
    const agent = await response.json();
    // WebSocket event will update UI automatically
  };
  
  return (
    <form onSubmit={spawnAgent}>
      {/* Agent configuration form */}
    </form>
  );
}
```

### 11.2 Task Creator Component

```typescript
// components/shared/TaskCreator.tsx

export function TaskCreator({ projectId, ticketId }: Props) {
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('MEDIUM');
  const [dependencies, setDependencies] = useState<string[]>([]);
  
  const createTask = async () => {
    await fetch(`/api/v1/tickets/${ticketId}/tasks`, {
      method: 'POST',
      body: JSON.stringify({
        description,
        priority,
        phase_id: 'PHASE_IMPLEMENTATION',
        dependencies: { depends_on: dependencies },
      }),
    });
    // WebSocket event will update board/graph
  };
  
  return (
    <form onSubmit={createTask}>
      {/* Task creation form */}
    </form>
  );
}
```

---

## 12. Data Flow Diagrams

### 12.1 Real-Time Update Flow

```
User Action (Move Ticket)
    │
    ├─→ POST /api/v1/board/move
    │       │
    │       ├─→ BoardService.move_ticket_to_column()
    │       │       │
    │       │       ├─→ Update Ticket.phase_id
    │       │       │
    │       │       └─→ EventBusService.publish(
    │       │               SystemEvent(
    │       │                   event_type="TICKET_UPDATED",
    │       │                   entity_type="ticket",
    │       │                   payload={"new_phase": ...}
    │       │               )
    │       │           )
    │       │
    │       └─→ Return success
    │
    └─→ WebSocket Event Received
            │
            └─→ Frontend updates Kanban board
                (optimistic update confirmed)
```

### 12.2 GitHub Webhook Flow

```
GitHub Event (PR Merged)
    │
    └─→ POST /api/v1/webhooks/github
            │
            ├─→ GitHubIntegrationService.handle_webhook()
            │       │
            │       ├─→ Verify signature
            │       ├─→ Parse payload
            │       ├─→ Find linked task (from PR description/labels)
            │       │
            │       └─→ TaskQueueService.update_task_status(
            │               task_id=linked_task_id,
            │               status="completed",
            │               result={"github_pr": pr_number}
            │           )
            │               │
            │               └─→ EventBusService.publish(
            │                       SystemEvent(
            │                           event_type="TASK_COMPLETED",
            │                           ...
            │                       )
            │                   )
            │
            └─→ WebSocket broadcasts to all connected clients
                    │
                    └─→ Frontend updates:
                        - Kanban board (task moves to done)
                        - Dependency graph (node turns green)
                        - Project stats (completion %)
```

---

## 13. Implementation Phases

### Phase 1: Core Dashboard (Week 1-2)
**Deliverables:**
1. ✅ WebSocket endpoint (already done)
2. Frontend WebSocket client hook
3. Basic Kanban board UI
4. Real-time ticket updates
5. Project list view

**APIs Needed:**
- Existing: `/api/v1/board/*`
- New: `/api/v1/projects/*`

### Phase 2: Dependency Graph (Week 2-3)
**Deliverables:**
1. Graph API endpoints
2. React Flow integration
3. Interactive graph visualization
4. Real-time graph updates
5. Node/edge interactions

**APIs Needed:**
- New: `/api/v1/graph/*`

### Phase 3: GitHub Integration (Week 3-4)
**Deliverables:**
1. GitHub service implementation
2. Webhook handler
3. Repository connection UI
4. Issue/PR sync
5. Bidirectional updates

**APIs Needed:**
- New: `/api/v1/github/*`
- New: `/api/v1/webhooks/github`

### Phase 4: Advanced Features (Week 4-5)
**Deliverables:**
1. Agent spawner UI
2. Task creator UI
3. Project settings
4. Multi-project support
5. Analytics dashboard

---

## 14. WebSocket Event Types

### 14.1 Board Events

```typescript
// Ticket events
TICKET_CREATED → { ticket_id, title, phase_id, status }
TICKET_UPDATED → { ticket_id, changes: { phase_id?, status? } }
TICKET_BLOCKED → { ticket_id, blocked_reason }
TICKET_UNBLOCKED → { ticket_id }

// Board events
BOARD_WIP_VIOLATION → { column_id, current_count, wip_limit }
BOARD_TICKET_MOVED → { ticket_id, from_column, to_column }
```

### 14.2 Graph Events

```typescript
// Task events
TASK_CREATED → { task_id, ticket_id, dependencies }
TASK_ASSIGNED → { task_id, agent_id }
TASK_COMPLETED → { task_id, result }
TASK_FAILED → { task_id, error_message }
TASK_DEPENDENCY_ADDED → { task_id, depends_on_task_id }
```

### 14.3 Agent Events

```typescript
AGENT_REGISTERED → { agent_id, agent_type, phase_id }
AGENT_STATUS_CHANGED → { agent_id, old_status, new_status }
AGENT_HEARTBEAT → { agent_id, health_metrics }
```

### 14.4 GitHub Events

```typescript
GITHUB_ISSUE_CREATED → { issue_number, repo, title }
GITHUB_PR_OPENED → { pr_number, repo, linked_task_id }
GITHUB_PR_MERGED → { pr_number, commit_sha, linked_task_id }
COMMIT_PUSHED → { commit_sha, message, author, files_changed, insertions, deletions }
COMMIT_LINKED → { commit_sha, ticket_id, agent_id }
COMMIT_COMMENTED → { commit_sha, comment, ticket_id }
```

### 14.5 Commit Events

```typescript
COMMIT_LINKED → { commit_sha, ticket_id, agent_id, files_changed, insertions, deletions }
COMMIT_DIFF_VIEWED → { commit_sha, viewer_id }  // Analytics
COMMIT_UNLINKED → { commit_sha, ticket_id }
```

---

## 15. Frontend State Management

### 15.1 Zustand Store Example

```typescript
// stores/boardStore.ts
import create from 'zustand';

interface BoardState {
  columns: Column[];
  tickets: Map<string, Ticket>;
  
  // Actions
  updateTicket: (ticketId: string, updates: Partial<Ticket>) => void;
  moveTicket: (ticketId: string, columnId: string) => void;
  addTicket: (ticket: Ticket) => void;
}

export const useBoardStore = create<BoardState>((set) => ({
  columns: [],
  tickets: new Map(),
  
  updateTicket: (ticketId, updates) => set((state) => ({
    tickets: new Map(state.tickets).set(ticketId, {
      ...state.tickets.get(ticketId)!,
      ...updates,
    }),
  })),
  
  moveTicket: (ticketId, columnId) => {
    // Optimistic update
    set((state) => ({
      tickets: new Map(state.tickets).set(ticketId, {
        ...state.tickets.get(ticketId)!,
        phase_id: getPhaseForColumn(columnId),
      }),
    }));
    
    // API call
    fetch('/api/v1/board/move', {
      method: 'POST',
      body: JSON.stringify({ ticket_id: ticketId, target_column_id: columnId }),
    });
  },
}));
```

### 15.2 WebSocket Hook

```typescript
// hooks/useWebSocket.ts
export function useWebSocket(filters?: EventFilters) {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const listeners = useRef<Map<string, Set<Function>>>(new Map());
  
  useEffect(() => {
    const url = buildWebSocketUrl('/api/v1/ws/events', filters);
    const socket = new WebSocket(url);
    
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const handlers = listeners.current.get(data.event_type) || new Set();
      handlers.forEach(handler => handler(data));
    };
    
    setWs(socket);
    return () => socket.close();
  }, [filters]);
  
  const subscribe = (eventTypes: string[], handler: Function) => {
    eventTypes.forEach(type => {
      if (!listeners.current.has(type)) {
        listeners.current.set(type, new Set());
      }
      listeners.current.get(type)!.add(handler);
    });
    
    return () => {
      eventTypes.forEach(type => {
        listeners.current.get(type)?.delete(handler);
      });
    };
  };
  
  return { ws, connected, subscribe };
}
```

---

## 16. Security Considerations

### 16.1 WebSocket Authentication

**Options:**
1. **Query Parameter Token**: `ws://api/v1/ws/events?token=JWT_TOKEN`
2. **Cookie-based**: Session cookie automatically sent
3. **Subprotocol**: Custom WebSocket subprotocol with auth

**Recommended:**
```typescript
// Frontend: Include JWT in WebSocket URL
const token = localStorage.getItem('auth_token');
const ws = new WebSocket(
  `ws://api/v1/ws/events?token=${token}&event_types=TICKET_UPDATED`
);

// Backend: Validate token in WebSocket endpoint
@router.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    # Validate JWT token
    user = verify_jwt_token(token)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    # Proceed with connection
    await ws_manager.connect(websocket, filters)
```

### 16.2 GitHub Webhook Security

**Webhook Signature Verification:**
```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## 17. Performance Considerations

### 17.1 WebSocket Scalability

**Connection Management:**
- Single Redis listener per server instance
- Connection pooling for multiple clients
- Filter at connection level (reduce message volume)

**Optimization:**
```python
# Only subscribe to events matching client filters
# Use Redis pattern subscriptions efficiently
# Batch events if needed (debounce rapid updates)
```

### 17.2 Graph Rendering

**Large Graph Handling:**
- Virtual rendering (only render visible nodes)
- Lazy loading (load sub-graphs on expand)
- Graph clustering (group related nodes)
- Incremental updates (only update changed nodes)

### 17.3 Board Performance

**Optimizations:**
- Pagination for large boards
- Virtual scrolling for columns
- Debounced updates (batch rapid changes)
- Client-side caching with TTL

---

## 18. Example User Flows

### 18.1 Viewing Commit Diff from Ticket

```
1. User clicks on ticket in Kanban board
   ↓
2. Ticket detail view opens
   ↓
3. User sees "Commits" section with list of commits
   ↓
4. User clicks on commit (e.g., "02979f61095b7d...")
   ↓
5. Commit Diff modal opens
   ↓
6. Shows:
   - Commit message: "Merge agent 9a781fc3 work into main"
   - Author: "Ido Levi"
   - Date: "Oct 30, 2025 12:47"
   - Summary: "+2255 -0 • 17 files"
   - File list with diff stats
   ↓
7. User clicks on file (e.g., "backend/core/database.py")
   ↓
8. File diff viewer shows:
   - Side-by-side diff
   - Syntax highlighting
   - Line-by-line changes
   - Agent attribution
```

### 18.2 Linking Commit to Ticket

```
1. GitHub webhook receives push event
   ↓
2. GitHubIntegrationService.handle_webhook()
   ↓
3. Parse commit message for ticket reference
   ↓
4. Create TicketCommit record
   ↓
5. EventBusService.publish(COMMIT_LINKED)
   ↓
6. WebSocket broadcasts to all clients
   ↓
7. Frontend updates:
   - Ticket card shows commit indicator (+X -Y)
   - Ticket detail shows new commit in list
   - Statistics update commit counts
```

### 18.3 Viewing Agent Activity

```
1. User navigates to Statistics dashboard
   ↓
2. Clicks on "Agent Activity" tab
   ↓
3. Sees list of agents with stats:
   - Commits made
   - Lines changed
   - Tasks completed
   - Files modified
   ↓
4. User clicks on specific agent
   ↓
5. Agent detail view shows:
   - Timeline of all commits
   - List of tasks worked on
   - Code changes summary
   - Performance metrics
```

### 18.4 Creating a Ticket from GitHub Issue

```
1. GitHub issue created
   ↓
2. Webhook → /api/v1/webhooks/github
   ↓
3. GitHubIntegrationService creates Ticket
   ↓
4. EventBusService.publish(TICKET_CREATED)
   ↓
5. WebSocket broadcasts to all clients
   ↓
6. Frontend receives event
   ↓
7. Kanban board shows new ticket in Backlog
   ↓
8. Dependency graph shows new node
```

### 18.5 Spawning an Agent

```
1. User clicks "Spawn Agent" in UI
   ↓
2. POST /api/v1/projects/{id}/spawn-agent
   ↓
3. AgentRegistryService.register_agent()
   ↓
4. Agent created in database
   ↓
5. EventBusService.publish(AGENT_REGISTERED)
   ↓
6. WebSocket broadcasts
   ↓
7. Frontend updates agent list
   ↓
8. Agent appears in "Available Agents" panel
```

### 18.6 Task Completion Updates Graph

```
1. Agent completes task
   ↓
2. POST /api/v1/tasks/{id}/complete
   ↓
3. TaskQueueService.update_task_status(completed)
   ↓
4. Check if dependencies are now satisfied
   ↓
5. EventBusService.publish(TASK_COMPLETED)
   ↓
6. WebSocket broadcasts
   ↓
7. Frontend updates:
   - Graph: Node turns green, blocked tasks become unblocked
   - Board: Ticket may move to next column
   - Stats: Completion percentage updates
```

---

## 19. API Endpoint Summary

### 15.1 Existing Endpoints (Ready to Use)

**Board:**
- `GET /api/v1/board/view`
- `POST /api/v1/board/move`
- `GET /api/v1/board/stats`
- `GET /api/v1/board/wip-violations`

**Tasks:**
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{id}/dependencies`
- `POST /api/v1/tasks/{id}/cancel`

**Tickets:**
- `POST /api/v1/tickets`
- `GET /api/v1/tickets/{id}`

**Agents:**
- `GET /api/v1/agents`
- `POST /api/v1/agents/register`

**WebSocket:**
- `WS /api/v1/ws/events` ✅ (Just implemented!)

### 19.2 New Endpoints Needed

**Graph:**
- `GET /api/v1/graph/dependency-graph/{ticket_id}`
- `GET /api/v1/graph/dependency-graph/project/{project_id}`
- `GET /api/v1/graph/blocked-tasks/{task_id}`

**Commits:**
- `GET /api/v1/commits/{commit_sha}` - Get commit details
- `GET /api/v1/commits/{commit_sha}/diff` - Get commit diff
- `GET /api/v1/tickets/{ticket_id}/commits` - Get ticket commits
- `POST /api/v1/tickets/{ticket_id}/commits/link` - Link commit to ticket
- `GET /api/v1/agents/{agent_id}/commits` - Get agent commits

**Projects:**
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{id}`
- `POST /api/v1/projects/{id}/spawn-agent`
- `POST /api/v1/projects/{id}/create-ticket`

**GitHub:**
- `POST /api/v1/github/repositories/connect`
- `GET /api/v1/github/repositories`
- `POST /api/v1/webhooks/github`
- `GET /api/v1/github/repositories/{id}/issues`
- `POST /api/v1/github/repositories/{id}/create-issue`

**Audit:**
- `GET /api/v1/audit/tickets/{ticket_id}` - Ticket audit trail
- `GET /api/v1/audit/agents/{agent_id}` - Agent audit trail
- `GET /api/v1/audit/projects/{project_id}` - Project audit trail

**Statistics:**
- `GET /api/v1/statistics/projects/{project_id}/overview` - Project stats
- `GET /api/v1/statistics/tickets` - Ticket statistics
- `GET /api/v1/statistics/agents` - Agent statistics
- `GET /api/v1/statistics/commits` - Commit statistics

**Search:**
- `GET /api/v1/search` - Global search
- `GET /api/v1/search/tickets` - Search tickets
- `GET /api/v1/search/commits` - Search commits
- `GET /api/v1/search/agents` - Search agents

---

## 20. Next Steps

### Immediate Actions:
1. **Create Graph API** (`omoi_os/api/routes/graph.py`)
2. **Create Commits API** (`omoi_os/api/routes/commits.py`) - For commit tracking and diffs
3. **Create Projects API** (`omoi_os/api/routes/projects.py`)
4. **Create GitHub Service** (`omoi_os/services/github_integration.py`) - Enhanced with commit diff fetching
5. **Create Audit API** (`omoi_os/api/routes/audit.py`) - For audit trails
6. **Create Statistics API** (`omoi_os/api/routes/statistics.py`) - For analytics
7. **Create Search API** (`omoi_os/api/routes/search.py`) - For global search
8. **Add Project Model** (database migration) - If not exists
9. **Frontend Setup** (Next.js project structure)

### Testing Strategy:
1. Unit tests for graph building logic
2. Integration tests for GitHub webhooks
3. E2E tests for WebSocket event flow
4. Frontend component tests

---

## 21. Feature Summary

### Core Features

1. **Kanban Board** ✅ Backend Ready
   - Visual workflow management
   - Drag-and-drop ticket movement
   - WIP limit enforcement
   - Real-time updates
   - Commit indicators on tickets (+X -Y)
   - Component tags and priority badges

2. **Dependency Graph** 📊 Needs Implementation
   - Interactive task/ticket relationship visualization
   - Blocking indicators
   - Discovery nodes (workflow branching)
   - Real-time status updates

3. **Commit Tracking & Diff Viewing** 📝 Needs Implementation
   - Link commits to tickets automatically
   - View commit diffs with syntax highlighting
   - File-by-file diff viewing
   - Agent attribution for each commit
   - Complete audit trail of code changes
   - "View exactly which code changes each agent made"

4. **GitHub Integration** 🐙 Needs Implementation
   - Repository connection
   - Webhook handling
   - Issue/PR sync
   - Commit auto-linking
   - Bidirectional updates

5. **Audit Trails** 📜 Needs Implementation
   - Complete history of all modifications
   - Timeline view of changes
   - Agent activity logs
   - Change history per ticket
   - Export capabilities

6. **Statistics Dashboard** 📈 Needs Implementation
   - Ticket statistics
   - Agent performance metrics
   - Code change statistics
   - Project health indicators
   - WIP violations
   - Cost tracking

7. **Search & Filtering** 🔍 Needs Implementation
   - Global search across all entities
   - Advanced filtering options
   - Saved searches
   - Full-text search

8. **Project Management** 📁 Needs Implementation
   - Multi-project support
   - Project settings
   - Agent/task spawning UI
   - Project-scoped views

9. **Real-Time Updates** ⚡ ✅ Implemented
   - WebSocket infrastructure ready
   - Event broadcasting
   - Live synchronization

## 22. Comments & Collaboration

### 22.1 Comment System

**Existing Backend**: `TicketComment` model exists with support for:
- Agent-authored comments
- Comment types (general, review, question, etc.)
- Mentions (@agent_id)
- Attachments (file paths)
- Edit tracking

**Frontend Components Needed:**
- `CommentThread.tsx` - Threaded comment display
- `CommentEditor.tsx` - Rich text comment editor
- `MentionAutocomplete.tsx` - @mention autocomplete
- `AttachmentUploader.tsx` - File attachment UI

**API Endpoints:**
```python
# omoi_os/api/routes/comments.py

@router.get("/tickets/{ticket_id}/comments")
async def get_ticket_comments(ticket_id: str) -> List[CommentDTO]:
    """Get all comments for a ticket."""

@router.post("/tickets/{ticket_id}/comments")
async def add_comment(ticket_id: str, request: CreateCommentRequest) -> CommentDTO:
    """Add comment to ticket."""

@router.put("/comments/{comment_id}")
async def edit_comment(comment_id: str, request: EditCommentRequest) -> CommentDTO:
    """Edit existing comment."""

@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str):
    """Delete comment."""
```

**Real-Time Updates:**
- `COMMENT_ADDED` WebSocket event
- `COMMENT_EDITED` WebSocket event
- `COMMENT_DELETED` WebSocket event
- Live typing indicators (optional)

### 22.2 Collaboration Threads

**Existing Backend**: `CollaborationThread` model tracks agent conversations

**UI Features:**
- View collaboration threads on tickets/tasks
- See agent-to-agent handoffs
- Review consultation threads
- Thread status (active, resolved, abandoned)

---

## 23. Notifications & Alerts

### 23.1 Notification System

**Existing Infrastructure**: Alert rules exist in `config/alert_rules/`

**Dashboard Integration:**
- **Notification Center**: Bell icon with unread count
- **Notification Types**:
  - Ticket blocked/unblocked
  - Agent heartbeat missed
  - Task completed/failed
  - Approval pending
  - WIP limit violation
  - Budget threshold exceeded
  - Dependency resolved
- **Notification Channels**: In-app, email, Slack (via webhooks)

**UI Components:**
- `NotificationCenter.tsx` - Dropdown notification list
- `NotificationBadge.tsx` - Unread count indicator
- `NotificationSettings.tsx` - User notification preferences

**API Endpoints:**
```python
@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50
) -> List[NotificationDTO]:
    """Get user notifications."""

@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id: str):
    """Mark notification as read."""

@router.post("/notifications/read-all")
async def mark_all_read():
    """Mark all notifications as read."""
```

### 23.2 Alert Rules Configuration UI

**Component**: `AlertRulesEditor.tsx`
- Visual editor for alert rules (YAML-based)
- Test alert rules
- Enable/disable rules
- View alert history

---

## 24. User Management & Permissions

### 24.1 Authentication

**Current State**: No general user authentication system (only agent-scoped MCP permissions)

**Needed:**
- User login/logout
- JWT token management
- Session management
- Password reset
- OAuth integration (GitHub, Google)

**API Endpoints:**
```python
@router.post("/auth/login")
async def login(credentials: LoginRequest) -> AuthResponse:
    """User login."""

@router.post("/auth/logout")
async def logout():
    """User logout."""

@router.get("/auth/me")
async def get_current_user() -> UserDTO:
    """Get current authenticated user."""
```

### 24.2 Authorization & Permissions

**Permission Model:**
- **Roles**: Admin, Project Manager, Developer, Viewer
- **Permissions**:
  - Create tickets
  - Edit tickets
  - Approve tickets
  - Spawn agents
  - View costs
  - Manage projects
  - Export data

**UI Components:**
- `PermissionGuard.tsx` - Route protection
- `RoleSelector.tsx` - Assign roles to users
- `PermissionMatrix.tsx` - Visual permission editor

---

## 25. Time Tracking & Analytics

### 25.1 Time Tracking

**Existing Backend**: Tasks have `started_at`, `completed_at` timestamps

**Enhancements Needed:**
- Track time spent per phase
- Agent time allocation
- Ticket time-to-completion metrics
- Time estimates vs. actuals

**UI Components:**
- `TimeTracker.tsx` - Manual time entry (for human users)
- `TimeChart.tsx` - Visual time breakdown
- `TimeReport.tsx` - Time analytics report

**API Endpoints:**
```python
@router.get("/tickets/{ticket_id}/time")
async def get_ticket_time(ticket_id: str) -> TimeTrackingDTO:
    """Get time tracking data for ticket."""

@router.get("/agents/{agent_id}/time")
async def get_agent_time(agent_id: str) -> TimeTrackingDTO:
    """Get time tracking data for agent."""
```

### 25.2 Performance Analytics

**Metrics:**
- Average task completion time
- Phase transition times
- Agent productivity metrics
- Ticket velocity
- Cycle time (from creation to completion)

---

## 26. Cost Tracking Dashboard

### 26.1 Cost Visualization

**Existing Backend**: `CostRecord` model tracks LLM API costs

**UI Components:**
- `CostDashboard.tsx` - Main cost overview
- `CostChart.tsx` - Time-series cost visualization
- `CostBreakdown.tsx` - Cost by agent/task/phase
- `BudgetAlerts.tsx` - Budget threshold warnings

**Features:**
- Real-time cost updates
- Cost forecasting
- Budget vs. actual comparisons
- Cost per ticket/task breakdown
- Agent cost efficiency metrics

**API Endpoints:**
```python
@router.get("/costs/projects/{project_id}")
async def get_project_costs(project_id: str) -> CostSummaryDTO:
    """Get cost summary for project."""

@router.get("/costs/agents/{agent_id}")
async def get_agent_costs(agent_id: str) -> CostSummaryDTO:
    """Get cost summary for agent."""

@router.get("/costs/forecast")
async def get_cost_forecast() -> CostForecastDTO:
    """Get cost forecast based on queue depth."""
```

---

## 27. Export & Import

### 27.1 Data Export

**Export Formats:**
- CSV (tickets, tasks, commits)
- JSON (complete project data)
- PDF (reports, audit trails)
- Excel (analytics, statistics)

**Export Options:**
- Export by project
- Export by date range
- Export filtered results
- Scheduled exports

**API Endpoints:**
```python
@router.get("/export/tickets")
async def export_tickets(
    project_id: str,
    format: str = "csv",
    filters: Optional[Dict] = None
) -> StreamingResponse:
    """Export tickets."""

@router.get("/export/audit-trail")
async def export_audit_trail(
    ticket_id: str,
    format: str = "json"
) -> StreamingResponse:
    """Export audit trail."""
```

### 27.2 Data Import

**Import Capabilities:**
- Import tickets from CSV
- Import from GitHub issues
- Import from Jira (future)
- Bulk ticket creation

---

## 28. File Attachments

### 28.1 Attachment System

**Existing Backend**: `TicketComment.attachments` (JSONB field)

**Enhancements Needed:**
- File storage service (S3, local filesystem)
- File upload API
- File preview (images, PDFs, code files)
- File versioning
- Attachment size limits

**UI Components:**
- `FileUploader.tsx` - Drag-and-drop file upload
- `FilePreview.tsx` - File preview modal
- `AttachmentList.tsx` - List of attachments

**API Endpoints:**
```python
@router.post("/tickets/{ticket_id}/attachments")
async def upload_attachment(
    ticket_id: str,
    file: UploadFile
) -> AttachmentDTO:
    """Upload file attachment."""

@router.get("/attachments/{attachment_id}")
async def download_attachment(attachment_id: str):
    """Download attachment."""

@router.delete("/attachments/{attachment_id}")
async def delete_attachment(attachment_id: str):
    """Delete attachment."""
```

---

## 29. Templates & Bulk Operations

### 29.1 Ticket Templates

**Template Types:**
- Ticket creation templates
- Task templates
- Comment templates
- Project templates

**UI Components:**
- `TemplateSelector.tsx` - Choose template
- `TemplateEditor.tsx` - Create/edit templates
- `TemplateLibrary.tsx` - Browse templates

### 29.2 Bulk Operations

**Bulk Actions:**
- Bulk ticket status update
- Bulk assignment
- Bulk priority change
- Bulk delete
- Bulk export

**UI Components:**
- `BulkActionBar.tsx` - Bulk action toolbar
- `BulkActionModal.tsx` - Confirm bulk actions

---

## 30. Mobile Responsiveness

### 30.1 Mobile UI Considerations

**Responsive Design:**
- Mobile-first Kanban board (swipe to move tickets)
- Collapsible sidebar
- Touch-optimized controls
- Mobile navigation
- Offline support (service workers)

**Breakpoints:**
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

---

## 31. Accessibility (A11y)

### 31.1 Accessibility Features

**WCAG 2.1 AA Compliance:**
- Keyboard navigation
- Screen reader support
- ARIA labels
- Color contrast compliance
- Focus indicators
- Alt text for images

**Keyboard Shortcuts:**
- `Ctrl/Cmd + K` - Global search
- `Ctrl/Cmd + N` - New ticket
- `Ctrl/Cmd + /` - Show shortcuts
- `Esc` - Close modals
- Arrow keys - Navigate board

**UI Components:**
- `KeyboardShortcuts.tsx` - Shortcuts help modal
- `SkipToContent.tsx` - Skip navigation link

---

## 32. Dark Mode & Theming

### 32.1 Theme System

**Theme Options:**
- Light mode (default)
- Dark mode
- High contrast mode
- Custom themes

**Implementation:**
- CSS variables for colors
- Theme toggle in header
- Persist theme preference
- System theme detection

**UI Components:**
- `ThemeToggle.tsx` - Theme switcher
- `ThemeProvider.tsx` - Theme context provider

---

## 33. Internationalization (i18n)

### 33.1 Multi-Language Support

**Supported Languages:**
- English (default)
- Spanish
- French
- German
- Japanese
- Chinese

**Implementation:**
- i18next integration
- Language switcher
- RTL support (Arabic, Hebrew)
- Date/time localization
- Number formatting

**UI Components:**
- `LanguageSelector.tsx` - Language dropdown
- `LocaleProvider.tsx` - i18n context

---

## 34. Integration with External Tools

### 34.1 Slack Integration

**Features:**
- Slack notifications for ticket updates
- Slack commands to create tickets
- Slack bot for status queries
- Slack webhook for alerts

**API Endpoints:**
```python
@router.post("/integrations/slack/webhook")
async def slack_webhook(request: SlackWebhookRequest):
    """Handle Slack webhook events."""
```

### 34.2 Jira Integration (Future)

**Features:**
- Sync tickets with Jira issues
- Import Jira projects
- Bidirectional updates
- Jira field mapping

### 34.3 Other Integrations

- **Linear**: Issue sync
- **Notion**: Documentation sync
- **Discord**: Team notifications
- **Email**: Email-to-ticket creation

---

## 35. Transaction Management & Error Handling

### 35.1 Transaction Safety

**Current Issue**: Foreign key violation when creating tasks before ticket commit (see terminal error)

**Solution:**
- Ensure ticket is committed before task creation
- Use database transactions properly
- Add retry logic for transient failures
- Implement proper rollback on errors

**Code Pattern:**
```python
# In create_ticket endpoint
with db.get_session() as session:
    ticket = Ticket(...)
    session.add(ticket)
    session.flush()  # Get ticket.id
    session.commit()  # Commit ticket first
    
    # Now create tasks in separate transaction
    if ApprovalStatus.can_proceed(ticket.approval_status):
        with db.get_session() as task_session:
            queue.enqueue_task(
                ticket_id=ticket.id,  # Ticket now exists
                session=task_session,
                ...
            )
            task_session.commit()
```

### 35.2 Error Handling UI

**Error Display:**
- User-friendly error messages
- Error recovery suggestions
- Retry buttons
- Error logging and reporting

**UI Components:**
- `ErrorBoundary.tsx` - React error boundary
- `ErrorMessage.tsx` - Error display component
- `ErrorToast.tsx` - Toast notifications for errors

---

## 36. Performance Optimization

### 36.1 Frontend Performance

**Optimizations:**
- Code splitting
- Lazy loading
- Virtual scrolling for large lists
- Memoization
- Debounced search
- Optimistic updates

### 36.2 Backend Performance

**Optimizations:**
- Database query optimization
- Caching (Redis)
- Pagination
- GraphQL for flexible queries (optional)
- CDN for static assets

### 36.3 WebSocket Performance

**Optimizations:**
- Event batching
- Connection pooling
- Message compression
- Filter at connection level

---

## 37. Data Retention & Archiving

### 37.1 Archive System

**Archive Policies:**
- Auto-archive completed tickets after X days
- Archive old audit trails
- Archive old commits
- Archive old cost records

**UI Components:**
- `ArchiveView.tsx` - View archived items
- `ArchiveSettings.tsx` - Configure retention policies

**API Endpoints:**
```python
@router.post("/tickets/{ticket_id}/archive")
async def archive_ticket(ticket_id: str):
    """Archive ticket."""

@router.get("/archive/tickets")
async def get_archived_tickets() -> List[TicketDTO]:
    """Get archived tickets."""
```

---

## 38. Backup & Recovery

### 38.1 Backup System

**Backup Features:**
- Automated daily backups
- Manual backup trigger
- Backup verification
- Backup restoration

**UI Components:**
- `BackupStatus.tsx` - Backup status indicator
- `BackupRestore.tsx` - Restore from backup

---

## 39. Testing & Quality Assurance

### 39.1 Testing Strategy

**Test Types:**
- Unit tests (Jest/Vitest)
- Integration tests
- E2E tests (Playwright)
- Visual regression tests
- Performance tests

**Test Coverage:**
- All API endpoints
- Critical user flows
- WebSocket event handling
- Real-time updates

### 39.2 Quality Metrics

**Metrics:**
- Test coverage percentage
- Performance benchmarks
- Error rate
- User satisfaction scores

---

## 40. Documentation & Help

### 40.1 In-App Help

**Help Features:**
- Contextual tooltips
- Help center
- Video tutorials
- Interactive tours
- FAQ section

**UI Components:**
- `HelpCenter.tsx` - Help documentation
- `Tooltip.tsx` - Contextual tooltips
- `Tour.tsx` - Interactive onboarding tour

---

## Conclusion

This design provides a complete blueprint for building a real-time project management dashboard that integrates:
- ✅ **WebSocket real-time updates** (already implemented)
- 📋 **Kanban board** (backend exists, needs frontend with commit indicators)
- 📊 **Dependency graphs** (needs implementation)
- 📝 **Commit tracking & diff viewing** (needs implementation - key feature!)
- 🐙 **GitHub integration** (needs implementation with commit linking)
- 📜 **Audit trails** (needs implementation - complete history tracking)
- 📈 **Statistics dashboard** (needs implementation)
- 🔍 **Search & filtering** (needs implementation)
- 🚀 **Agent/task spawning** (backend exists, needs UI)
- 📁 **Project management** (needs implementation)
- 🤖 **AI-Assisted Project Exploration** (needs implementation - NEW!)
  - Conversational project discovery
  - Requirements document generation
  - Design document generation
  - Approval workflow
  - Project initialization from documents
- 💬 **Comments & collaboration** (backend exists, needs UI)
- 🔔 **Notifications & alerts** (infrastructure exists, needs UI)
- 👥 **User management & permissions** (needs implementation)
- ⏱️ **Time tracking** (partial backend, needs UI)
- 💰 **Cost tracking dashboard** (backend exists, needs UI)
- 📤 **Export & import** (needs implementation)
- 📎 **File attachments** (partial backend, needs UI)
- 📝 **Templates & bulk operations** (needs implementation)
- 📱 **Mobile responsiveness** (needs implementation)
- ♿ **Accessibility** (needs implementation)
- 🌙 **Dark mode & theming** (needs implementation)
- 🌍 **Internationalization** (needs implementation)
- 🔗 **External integrations** (needs implementation)
- 🔄 **Transaction management** (needs fixes)
- ⚡ **Performance optimization** (ongoing)
- 📦 **Data retention & archiving** (needs implementation)
- 💾 **Backup & recovery** (needs implementation)

**Key Differentiator**: The ability to "view exactly which code changes each agent made" with complete audit trails provides unprecedented transparency into AI agent work, enabling full traceability from ticket → task → agent → commit → code changes.

The WebSocket infrastructure we just built is the foundation that enables all real-time features!

