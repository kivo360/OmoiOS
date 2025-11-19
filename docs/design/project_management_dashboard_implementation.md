# Project Management Dashboard - Implementation Details

**Created**: 2025-01-30  
**Status**: Technical Implementation Document  
**Purpose**: Code examples, database models, service implementations, and technical details

**Related Documents:**
- [Main Design Document](./project_management_dashboard.md) - UI/UX design and user flows
- [API Specifications](./project_management_dashboard_api.md) - Complete API endpoint specifications

---

## Table of Contents

1. [Frontend Component Structure](#1-frontend-component-structure)
2. [Frontend Code Examples](#2-frontend-code-examples)
3. [Database Models](#3-database-models)
4. [Service Implementations](#4-service-implementations)
5. [Security Implementation](#5-security-implementation)
6. [Performance Optimization](#6-performance-optimization)
7. [Transaction Management](#7-transaction-management)
8. [Error Handling](#8-error-handling)

---

## 1. Frontend Component Structure

See [Main Design Document - Frontend Architecture](./project_management_dashboard.md#1-frontend-architecture) for complete component structure.

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

## 2. Frontend Code Examples

### 2.1 Kanban Board Hook

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

### 2.2 Dependency Graph Component

```typescript
// components/graph/DependencyGraph.tsx
import ReactFlow, { Node, Edge } from 'react-flow-renderer';

export function DependencyGraph({ ticketId }: { ticketId: string }) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const ws = useWebSocket();
  
  // Load initial graph
  useEffect(() => {
    fetch(`/api/v1/graph/dependency-graph/ticket/${ticketId}`)
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

### 2.3 WebSocket Hook

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

### 2.4 Zustand Store Example

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

### 2.5 Agent Spawner Component

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

### 2.6 Task Creator Component

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

## 3. Database Models

### 3.1 Project Model

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

### 3.2 TicketCommit Model

**Existing Model** (`omoi_os/models/ticket_commit.py`):

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

### 3.3 Project Exploration Models

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
        String, ForeignKey("requirements.id"), nullable=True
    )
    design_document_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("designs.id"), nullable=True
    )
    
    # Conversation history
    conversation_history: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # Stores full conversation with AI
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Requirements(Base):
    """Stores requirements documents generated by AI."""
    
    __tablename__ = "requirements"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("projects.id"), nullable=True, index=True
    )
    exploration_id: Mapped[str] = mapped_column(
        String, ForeignKey("project_explorations.id"), nullable=False, index=True
    )
    
    # Document metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Storage configuration
    storage_location: Mapped[str] = mapped_column(
        String(20), nullable=False, default="database", index=True
    )  # "database" or "s3"
    content_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Size in bytes
    
    # Document content (when stored in database)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Markdown content
    
    # S3 storage (when storage_location = "s3")
    s3_bucket: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Full S3 object key
    s3_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # Pre-signed URL (temporary)
    s3_region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Content hash for integrity verification
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hash
    
    # Requirements-specific metadata
    total_requirements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requirements_by_category: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # e.g., {"functional": 15, "non-functional": 8, "security": 5}
    
    # Approval workflow
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )  # draft, pending_review, approved, rejected, superseded
    approved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    previous_version_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("requirements.id"), nullable=True
    )  # For versioning
    individual_requirements: Mapped[list["IndividualRequirement"]] = relationship(
        "IndividualRequirement", back_populates="requirements_document"
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class IndividualRequirement(Base):
    """Stores individual requirements extracted from requirements document."""
    
    __tablename__ = "individual_requirements"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    requirements_id: Mapped[str] = mapped_column(
        String, ForeignKey("requirements.id"), nullable=False, index=True
    )
    
    # Requirement identification
    requirement_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # e.g., "REQ-001"
    requirement_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Requirement content
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ears_format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # EARS notation
    
    # Requirement metadata
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # functional, non-functional, security, performance, etc.
    priority: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )  # CRITICAL, HIGH, MEDIUM, LOW
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Which question/answer led to this
    
    # Relationships
    requirements_document: Mapped["Requirements"] = relationship(
        "Requirements", back_populates="individual_requirements"
    )
    linked_tasks: Mapped[list["Task"]] = relationship(
        "Task", secondary="requirement_task_links", back_populates="requirements"
    )
    properties: Mapped[list["SpecProperty"]] = relationship(
        "SpecProperty", back_populates="requirement"
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Designs(Base):
    """Stores design documents generated by AI."""
    
    __tablename__ = "designs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("projects.id"), nullable=True, index=True
    )
    exploration_id: Mapped[str] = mapped_column(
        String, ForeignKey("project_explorations.id"), nullable=False, index=True
    )
    requirements_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("requirements.id"), nullable=True, index=True
    )  # Design is based on approved requirements
    
    # Document metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Storage configuration (same as Requirements)
    storage_location: Mapped[str] = mapped_column(
        String(20), nullable=False, default="database", index=True
    )
    content_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    s3_bucket: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    s3_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    s3_region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Design-specific metadata
    sections: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    components_designed: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    diagrams_included: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    
    # Approval workflow (same as Requirements)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    previous_version_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("designs.id"), nullable=True
    )
    based_on_requirements: Mapped[Optional["Requirements"]] = relationship(
        "Requirements", foreign_keys=[requirements_id]
    )
    
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

---

## 4. Service Implementations

### 4.1 GitHub Integration Service

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

### 4.2 Document Storage Service

```python
# omoi_os/services/document_storage.py

class DocumentStorageService:
    """Abstracts document storage operations."""
    
    async def store_document(
        self,
        document_id: str,
        content: str,
        storage_location: str = "database",
        s3_bucket: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store document content.
        
        Returns:
        {
            "storage_location": "database" | "s3",
            "content_size": 12345,
            "content_hash": "sha256...",
            "s3_bucket": "bucket-name" (if S3),
            "s3_key": "path/to/file" (if S3),
        }
        """
        if storage_location == "database":
            return await self._store_in_database(document_id, content)
        elif storage_location == "s3":
            return await self._store_in_s3(document_id, content, s3_bucket)
        else:
            raise ValueError(f"Unknown storage location: {storage_location}")
    
    async def retrieve_document(
        self,
        document_id: str,
        storage_location: str,
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
    ) -> str:
        """Retrieve document content."""
        if storage_location == "database":
            return await self._retrieve_from_database(document_id)
        elif storage_location == "s3":
            return await self._retrieve_from_s3(s3_bucket, s3_key)
        else:
            raise ValueError(f"Unknown storage location: {storage_location}")
    
    async def generate_presigned_url(
        self,
        s3_bucket: str,
        s3_key: str,
        expiration: int = 3600,
    ) -> str:
        """Generate pre-signed URL for S3 object access."""
        pass


# Automatic storage selection based on size
def determine_storage_location(content: str, config: Dict) -> str:
    """
    Determine where to store document based on size and configuration.
    
    Default thresholds:
    - < 100KB: Database (fast, simple)
    - 100KB - 1MB: Database (unless S3 preferred)
    - > 1MB: S3 (cost-effective, scalable)
    """
    size = len(content.encode('utf-8'))
    max_db_size = config.get("max_database_size_bytes", 100_000)  # 100KB default
    
    if size < max_db_size:
        return "database"
    else:
        return config.get("default_large_storage", "s3")
```

### 4.3 Dependency Graph Service

**Existing Service** (`omoi_os/services/dependency_graph.py`):

See [Main Design Document - Dependency Graph Implementation](./project_management_dashboard.md#4-dependency-graph-implementation) for API details.

### 4.4 Discovery Service

**Existing Service** (`omoi_os/services/discovery.py`):

- ✅ `record_discovery()` - Record discovery with type and description
- ✅ `record_discovery_and_branch()` - Record discovery and spawn task automatically
- ✅ `get_discoveries_by_task()` - Get all discoveries for a task
- ✅ `get_discoveries_by_type()` - Get discoveries by type (bug, optimization, etc.)
- ✅ `get_workflow_graph()` - Build workflow graph showing all discoveries and branches
- ✅ `mark_discovery_resolved()` - Mark discovery as resolved

See [API Specifications - Discovery API](./project_management_dashboard_api.md#10-discovery-api) for endpoint details.

---

## 5. Security Implementation

### 5.1 WebSocket Authentication

**Options:**
1. **Query Parameter Token**: `ws://api/v1/ws/events?token=JWT_TOKEN`
2. **Cookie-based**: Session cookie automatically sent
3. **Subprotocol**: Custom WebSocket subprotocol with auth

**Recommended Implementation:**

```typescript
// Frontend: Include JWT in WebSocket URL
const token = localStorage.getItem('auth_token');
const ws = new WebSocket(
  `ws://api/v1/ws/events?token=${token}&event_types=TICKET_UPDATED`
);
```

```python
# Backend: Validate token in WebSocket endpoint
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

### 5.2 GitHub Webhook Security

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

## 6. Performance Optimization

### 6.1 WebSocket Scalability

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

### 6.2 Graph Rendering

**Large Graph Handling:**
- Virtual rendering (only render visible nodes)
- Lazy loading (load sub-graphs on expand)
- Graph clustering (group related nodes)
- Incremental updates (only update changed nodes)

### 6.3 Board Performance

**Optimizations:**
- Pagination for large boards
- Virtual scrolling for columns
- Debounced updates (batch rapid changes)
- Client-side caching with TTL

### 6.4 Frontend Performance

**Optimizations:**
- Code splitting
- Lazy loading
- Virtual scrolling for large lists
- Memoization
- Debounced search
- Optimistic updates

### 6.5 Backend Performance

**Optimizations:**
- Database query optimization
- Caching (Redis)
- Pagination
- GraphQL for flexible queries (optional)
- CDN for static assets

### 6.6 WebSocket Performance

**Optimizations:**
- Event batching
- Connection pooling
- Message compression
- Filter at connection level

---

## 7. Transaction Management

### 7.1 Transaction Safety

**Current Issue**: Foreign key violation when creating tasks before ticket commit.

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

### 7.2 Database Session Management

**Pattern:**
```python
# Use DatabaseService context manager pattern
with db.get_session() as session:
    # Database operations here
    session.commit()  # Auto-commits on context exit
```

---

## 8. Error Handling

### 8.1 Error Handling UI

**Error Display:**
- User-friendly error messages
- Error recovery suggestions
- Retry buttons
- Error logging and reporting

**UI Components:**
- `ErrorBoundary.tsx` - React error boundary
- `ErrorMessage.tsx` - Error display component
- `ErrorToast.tsx` - Toast notifications for errors

### 8.2 Backend Error Handling

**Error Response Format:**

```json
{
  "error": {
    "code": "TICKET_NOT_FOUND",
    "message": "Ticket with ID ticket-123 not found",
    "details": {
      "ticket_id": "ticket-123",
      "suggestion": "Check if ticket exists or was deleted"
    }
  }
}
```

**Error Codes:**
- `TICKET_NOT_FOUND` - Ticket doesn't exist
- `TASK_DEPENDENCY_CYCLE` - Circular dependency detected
- `WIP_LIMIT_EXCEEDED` - Cannot move ticket, WIP limit reached
- `AGENT_NOT_AVAILABLE` - Agent is not available for assignment
- `VALIDATION_FAILED` - Task validation failed
- `GUARDIAN_INTERVENTION_REQUIRED` - Guardian intervention needed

---

## Configuration

### Document Storage Configuration

```python
# config.py
class DocumentStorageSettings(BaseSettings):
    # Storage defaults
    default_storage_location: str = "database"
    max_database_size_bytes: int = 100_000  # 100KB
    
    # S3 configuration
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    
    # Pre-signed URL settings
    presigned_url_expiration: int = 3600  # 1 hour
```

---

## Next Steps

See [Main Design Document - Next Steps](./project_management_dashboard.md#20-next-steps) for implementation priorities.

