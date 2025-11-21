# Project Management Dashboard Design

**Created**: 2025-01-30  
**Status**: Design Document  
**Purpose**: Comprehensive design for Kanban board, dependency graphs, GitHub integration, spec workspace, and project management UI

**Note**: OmoiOS follows a spec-driven workflow model (Requirements → Design → Tasks → Execution). All specs are stored in OmoiOS database/storage, not as repo files. Users can export specs to markdown/YAML for version control if desired. The dashboard provides a multi-tab spec workspace (Requirements | Design | Tasks | Execution) with structured blocks (Notion-style) for spec content.

**Related Vision**: See [Product Vision](../product_vision.md) for complete product concept and value proposition.

**Related Documents:**
- [API Specifications](./project_management_dashboard_api.md) - Complete API endpoint specifications
- [Implementation Details](./project_management_dashboard_implementation.md) - Code examples, database models, and technical implementation

---

## Executive Summary

This document designs a real-time project management dashboard that integrates:
- **Spec Workspace**: Multi-tab workspace (Requirements | Design | Tasks | Execution) with spec switcher, structured blocks (Notion-style) for requirements/design/tasks
- **Kanban Board**: Visual workflow management with real-time updates, ticket cards with commit indicators, organized by phase (INITIAL → IMPLEMENTATION → INTEGRATION → REFACTORING)
- **Dependency Graph**: Interactive visualization of task/ticket relationships with blocking indicators, animated as dependencies resolve
- **Activity Timeline/Feed**: Chronological feed showing when specs/tasks/tickets are created, discovery events, phase transitions, agent interventions, approvals
- **Command Palette**: Linear-style command palette (Cmd+K) for quick navigation across specs, tasks, workflows, and logs
- **GitHub Integration**: Repository management, webhook handling, PR/task sync, commit tracking
- **Commit Diff Viewer**: View code changes linked to tickets, see exactly what each agent modified
- **Audit Trails**: Complete history of all changes, commits, and agent actions
- **Project Management**: Multi-project support with agent/task spawning
- **Statistics Dashboard**: Analytics on tickets, tasks, agents, and code changes
- **Search & Filtering**: Advanced search across tickets, commits, agents, and code changes
- **Real-Time Updates**: WebSocket-powered live synchronization across all views
- **Guardian Intervention System**: Real-time agent steering and trajectory monitoring with live intervention delivery

**Visual Design**: Linear/Arc aesthetic with Notion-style structured blocks for specs. Clean, minimal, white-space-heavy with collapsible sidebar for spec navigation.

### Agent-Driven Workflow Architecture

**Core Principle**: Agents are autonomous actors that create, link, and manage their own work items in real-time.

**Agent Capabilities**:
- **Create Tickets**: Agents use MCP tools (`create_ticket`) to create new tickets during execution when they discover new requirements or work items
- **Create Tasks**: Agents can spawn new tasks via `DiscoveryService` when they find bugs, optimizations, or missing requirements
- **Link Work Items**: Agents automatically identify and link related tasks/tickets through dependency detection and discovery tracking
- **Memory System**: Agents use MCP tools (`save_memory`, `find_memory`) to share knowledge and learn from each other's discoveries in real-time
  - `save_memory`: Agents save discoveries, solutions, and learnings for other agents to find
  - `find_memory`: Agents search past memories semantically when encountering errors or needing implementation details
- **Real-Time State Updates**: All agent actions (ticket creation, task spawning, linking, memory operations) trigger immediate WebSocket events that update the dashboard in real-time

**Workflow Example**:
1. Agent working on Task A discovers a bug → Creates TaskDiscovery record → Spawns Task B to fix bug
2. Agent working on Task B encounters error → Calls `find_memory("PostgreSQL timeout")` → Finds solution from past memory → Applies fix → Calls `save_memory()` to share updated solution
3. Agent working on Task B needs clarification → Creates Ticket via MCP tool → Links ticket to Task B
4. Agent identifies missing dependency → Creates Task C → Links Task C as dependency of Task B
5. Dashboard receives WebSocket events → Updates Kanban board, dependency graph, and statistics in real-time

**Guardian Intervention Delivery**:
- **Real-Time Monitoring**: Guardian analyzes agent trajectories every 60 seconds, calculating alignment scores and detecting drift
- **Live Intervention**: When Guardian detects agents need steering, it sends intervention messages directly to active OpenHands conversations
- **Non-Blocking Delivery**: Interventions are delivered via `Conversation.send_message()` even while agents are running, allowing real-time course correction
- **Conversation Persistence**: All conversations are persisted with `conversation_id` and `persistence_dir`, enabling Guardian to resume and intervene in active conversations
- **Dashboard Integration**: Intervention events are broadcast via WebSocket, allowing dashboard to show real-time Guardian actions and agent responses

---

## Existing Codebase Mapping

### ✅ Already Implemented APIs

**Board API** (`omoi_os/api/routes/board.py`):
- ✅ `GET /api/v1/board/view` - Get complete Kanban board view
- ✅ `POST /api/v1/board/move` - Move ticket to different column
- ✅ `GET /api/v1/board/stats` - Get column statistics
- ✅ `GET /api/v1/board/wip-violations` - Check WIP limit violations
- ✅ `POST /api/v1/board/auto-transition/{ticket_id}` - Auto-transition ticket
- ✅ `GET /api/v1/board/column/{phase_id}` - Get column for phase

**Tasks API** (`omoi_os/api/routes/tasks.py`):
- ✅ `GET /api/v1/tasks/{task_id}` - Get task by ID
- ✅ `GET /api/v1/tasks` - List tasks (with filters)
- ✅ `GET /api/v1/tasks/{task_id}/dependencies` - Get task dependencies
- ✅ `POST /api/v1/tasks/{task_id}/check-circular` - Check for circular dependencies
- ✅ `POST /api/v1/tasks/{task_id}/cancel` - Cancel a task
- ✅ `GET /api/v1/tasks/{task_id}/timeout-status` - Get timeout status
- ✅ `GET /api/v1/tasks/timed-out` - List timed-out tasks
- ✅ `GET /api/v1/tasks/cancellable` - List cancellable tasks
- ✅ `POST /api/v1/tasks/cleanup-timed-out` - Cleanup timed-out tasks
- ✅ `POST /api/v1/tasks/{task_id}/set-timeout` - Set task timeout

**Tickets API** (`omoi_os/api/routes/tickets.py`):
- ✅ `POST /api/v1/tickets` - Create ticket
- ✅ `GET /api/v1/tickets/{ticket_id}` - Get ticket by ID
- ✅ `GET /api/v1/tickets/{ticket_id}/context` - Get ticket context
- ✅ `POST /api/v1/tickets/{ticket_id}/update-context` - Update ticket context
- ✅ `POST /api/v1/tickets/{ticket_id}/transition` - Transition ticket status
- ✅ `POST /api/v1/tickets/{ticket_id}/block` - Block ticket
- ✅ `POST /api/v1/tickets/{ticket_id}/unblock` - Unblock ticket
- ✅ `POST /api/v1/tickets/{ticket_id}/regress` - Regress ticket phase
- ✅ `POST /api/v1/tickets/{ticket_id}/progress` - Auto-progress ticket
- ✅ `POST /api/v1/tickets/detect-blocking` - Detect blocking tickets
- ✅ `POST /api/v1/tickets/approve` - Approve ticket
- ✅ `POST /api/v1/tickets/reject` - Reject ticket
- ✅ `GET /api/v1/tickets/pending-review-count` - Get pending count
- ✅ `GET /api/v1/tickets/approval-status` - Get approval status

**Agents API** (`omoi_os/api/routes/agents.py`):
- ✅ `POST /api/v1/agents/register` - Register agent
- ✅ `PATCH /api/v1/agents/{agent_id}` - Update agent
- ✅ `POST /api/v1/agents/{agent_id}/availability` - Toggle availability
- ✅ `GET /api/v1/agents/search` - Search agents by capabilities
- ✅ `GET /api/v1/agents/best-fit` - Get best-fit agent
- ✅ `GET /api/v1/agents/health` - Get all agents health
- ✅ `GET /api/v1/agents/statistics` - Get agent statistics
- ✅ `GET /api/v1/agents/{agent_id}/health` - Get agent health
- ✅ `POST /api/v1/agents/{agent_id}/heartbeat` - Emit heartbeat
- ✅ `GET /api/v1/agents/stale` - Get stale agents
- ✅ `POST /api/v1/agents/cleanup-stale` - Cleanup stale agents
- ✅ `GET /api/v1/agents` - List all agents
- ✅ `GET /api/v1/agents/{agent_id}` - Get agent by ID

**Graph API** (`omoi_os/api/routes/graph.py`):
- ✅ `GET /api/v1/graph/dependency-graph/ticket/{ticket_id}` - Get ticket dependency graph
- ✅ `GET /api/v1/graph/dependency-graph/project/{project_id}` - Get project graph
- ✅ `GET /api/v1/graph/dependency-graph/task/{task_id}/blocked` - Get blocked tasks
- ✅ `GET /api/v1/graph/dependency-graph/task/{task_id}/blocking` - Get blocking tasks

**WebSocket API** (`omoi_os/api/routes/events.py`):
- ✅ `WS /api/v1/ws/events` - Real-time event streaming with filters

**Additional APIs**:
- ✅ **Guardian API** (`omoi_os/api/routes/guardian.py`) - Emergency intervention and real-time steering
- ✅ **Alerts API** (`omoi_os/api/routes/alerts.py`) - Alert management
- ✅ **Memory API** (`omoi_os/api/routes/memory.py`) - Pattern storage & search
- ✅ **Quality API** (`omoi_os/api/routes/quality.py`) - Quality metrics
- ✅ **Costs API** (`omoi_os/api/routes/costs.py`) - Cost tracking
- ✅ **Validation API** (`omoi_os/api/routes/validation.py`) - Validation reviews
- ✅ **Collaboration API** (`omoi_os/api/routes/collaboration.py`) - Agent collaboration threads
- ✅ **Discovery API** (`omoi_os/services/discovery.py`) - Task discovery and workflow branching

### ✅ Already Implemented Models

**Core Models** (`omoi_os/models/`):
- ✅ `Ticket` - Ticket model with approval, context, phase history
- ✅ `Task` - Task model with dependencies (JSONB), retries, timeouts
- ✅ `Agent` - Agent model with capabilities, health status, heartbeats
- ✅ `TaskDiscovery` - Discovery tracking for workflow branching (`omoi_os/models/task_discovery.py`)
- ✅ `TicketComment` - Comments on tickets with mentions, attachments
- ✅ `PhaseHistory` - Phase transition history
- ✅ `AgentStatus` - Agent status tracking
- ✅ `AgentBaseline` - Agent baseline metrics
- ✅ `BoardColumn` - Kanban board column configuration
- ✅ `GuardianAction` - Guardian intervention audit records
- ✅ `CostRecord` - LLM cost tracking
- ✅ `Budget` - Budget management
- ✅ `QualityMetric` - Quality gate metrics
- ✅ `ValidationReview` - Validation reviews
- ✅ `CollaborationThread` - Agent collaboration threads
- ✅ `AgentMessage` - Agent messaging

### ✅ Already Implemented Services

**Core Services** (`omoi_os/services/`):
- ✅ `BoardService` - Kanban board operations (`omoi_os/services/board.py`)
- ✅ `TaskQueueService` - Task queue with dependencies (`omoi_os/services/task_queue.py`)
- ✅ `EventBusService` - Redis pub/sub event system (`omoi_os/services/event_bus.py`)
- ✅ `DatabaseService` - PostgreSQL session management (`omoi_os/services/database.py`)
- ✅ `AgentHealthService` - Agent heartbeat monitoring (`omoi_os/services/agent_health.py`)
- ✅ `AgentRegistryService` - Agent registration & capability matching (`omoi_os/services/agent_registry.py`)
- ✅ `GuardianService` - Emergency intervention (`omoi_os/services/guardian.py`)
- ✅ `DiscoveryService` - Task discovery & branching (`omoi_os/services/discovery.py`)
- ✅ `DependencyGraphService` - Dependency graph building (`omoi_os/services/dependency_graph.py`)
- ✅ `TicketWorkflowOrchestrator` - Ticket workflow management (`omoi_os/services/ticket_workflow.py`)
- ✅ `ApprovalService` - Approval workflow (`omoi_os/services/approval.py`)
- ✅ `PhaseGateService` - Phase gate validation (`omoi_os/services/phase_gate.py`)
- ✅ `ContextService` - Cross-phase context aggregation (`omoi_os/services/context_service.py`)
- ✅ `CostTrackingService` - Cost tracking (`omoi_os/services/cost_tracking.py`)
- ✅ `MemoryService` - Pattern storage & similarity search (`omoi_os/services/memory.py`)
- ✅ `ValidationAgent` - Validation agent (`omoi_os/services/validation_agent.py`)

### ❌ Not Yet Implemented

**Missing APIs**:
- ❌ Commits API - Commit tracking and diff viewing
- ❌ Projects API - Project management endpoints
- ❌ GitHub Integration API - Repository connection, webhooks
- ❌ Audit API - Audit trail endpoints
- ❌ Statistics API - Analytics endpoints
- ❌ Search API - Global search endpoints

**Missing Models**:
- ❌ Project model (if multi-project support needed)
- ❌ TicketCommit model (for linking commits to tickets)
- ❌ Commit model (for commit storage)

**Missing Services**:
- ❌ GitHubIntegrationService - GitHub API integration
- ❌ CommitDiffService - Commit diff fetching/parsing
- ❌ StatisticsService - Analytics computation
- ❌ SearchService - Global search across entities

**Recently Implemented Services**:
- ✅ **ConversationInterventionService** (`omoi_os/services/conversation_intervention.py`) - Real-time Guardian intervention delivery to active OpenHands conversations
- ✅ **DiscoveryService** (`omoi_os/services/discovery.py`) - Task discovery tracking and workflow branching
- ✅ **IntelligentGuardian** (`omoi_os/services/intelligent_guardian.py`) - Enhanced with conversation intervention delivery via `ConversationInterventionService`

---

## Agent-Driven Workflow Architecture

### Core Philosophy

**Agents as Autonomous Actors**: Unlike traditional project management systems where humans create all work items, this system enables agents to autonomously create, link, and manage their own work. The dashboard provides real-time visibility into this dynamic, adaptive workflow.

### Agent Capabilities

**1. Ticket Creation via MCP Tools**:
- Agents use `create_ticket` MCP tool (`omoi_os/ticketing/mcp_tools.py`) to create tickets during execution
- Use cases: Clarification needed, new requirement discovered, blocking issue found
- Real-time update: `TICKET_CREATED` WebSocket event → Dashboard updates Kanban board immediately

**1a. Memory System via MCP Tools**:
- Agents use `save_memory` MCP tool to save discoveries, solutions, and learnings during execution
  - Parameters: `content`, `agent_id`, `memory_type` (error_fix, discovery, decision, learning, warning, codebase_knowledge), optional `tags`, `related_files`
  - Stores memory using `MemoryService.store_execution()` with semantic embeddings for search
  - Enables collective intelligence where agents learn from each other's experiences
- Agents use `find_memory` MCP tool to search past memories semantically during execution
  - Parameters: `query` (natural language), `limit` (default 5), optional `memory_types` filter
  - Uses `MemoryService.search_similar()` with hybrid search (semantic + keyword using RRF)
  - Returns top matching memories with similarity scores
  - Use cases: Encountering errors, needing implementation details, finding related work
- Real-time update: `MEMORY_SAVED` and `MEMORY_SEARCHED` WebSocket events → Dashboard can show memory activity in activity timeline

**2. Task Spawning via DiscoveryService**:
- Agents call `DiscoveryService.record_discovery_and_branch()` when they discover:
  - Bugs that need fixing
  - Optimization opportunities
  - Missing requirements
  - Dependency issues
  - Security concerns
- Automatically creates `TaskDiscovery` record and spawns linked tasks
- Real-time update: `TASK_CREATED` + `DISCOVERY_MADE` WebSocket events → Dashboard updates dependency graph

**3. Task Linking & Dependency Management**:
- **Automatic Detection**: Agents analyze task descriptions and identify dependencies
- **Manual Linking**: Agents use MCP tools to explicitly link tasks via `Task.dependencies` JSONB field
- **Discovery-Based Linking**: When agent spawns task from discovery, automatic parent-child link created via `parent_task_id`
- **Real-time update**: `TASK_DEPENDENCY_UPDATED` WebSocket event → Dashboard updates graph edges

**4. Real-Time State Synchronization**:
- All agent actions trigger immediate WebSocket events
- Dashboard receives events and updates UI in real-time:
  - Kanban board shows new tickets/tasks immediately
  - Dependency graph shows new nodes and edges
  - Statistics update with new counts
  - Agent detail views show latest discoveries and interventions

**5. Conversation Control & Multi-Agent Workflows**:
- **Pause/Resume**: Conversations support `conversation.pause()` and `conversation.run()` for controlled execution
  - Useful for: Manual intervention, dependency waiting, resource management
  - Example: Pause agent when dependency task completes, then resume with updated context
- **Message While Running**: Agents can receive new messages via `conversation.send_message()` even while `conversation.run()` is executing (OpenHands event-driven architecture)
  - Guardian interventions leverage this capability
  - Messages are queued and processed asynchronously by agent's `step()` method
  - No interruption to current work - agent processes new messages when ready
- **Multi-Agent Patterns**: Planning agent + execution agent workflows
  - Planning agent: Analyzes task, creates detailed implementation plan (read-only tools via `get_planning_agent()`)
  - Execution agent: Implements plan with full editing capabilities (via `get_default_agent()`)
  - Pattern: Planning conversation creates plan → Execution conversation implements plan
- **Remote Conversations**: Support for `RemoteConversation` via `Workspace(host=...)` for client-server architecture
  - Local agent server: `Workspace(host="http://localhost:8001")` → automatically becomes `RemoteConversation`
  - Docker/API sandboxed servers: Same pattern, different workspace configuration
  - Event callbacks work with remote conversations for real-time monitoring
- **Conversation Persistence**: All conversations can be resumed using `conversation_id` and `persistence_dir`
  - Enables Guardian to resume and intervene in active conversations
  - Supports conversation migration between workspace instances

### Workflow Example

```
Agent Working on Task A (Implement Authentication)
    │
    ├─→ Discovers bug: "Database connection timeout"
    │   ├─→ Calls DiscoveryService.record_discovery_and_branch()
    │   ├─→ Creates TaskDiscovery record (type: "bug")
    │   ├─→ Spawns Task B: "Fix database connection timeout"
    │   ├─→ Links Task B as child of Task A (parent_task_id)
    │   └─→ WebSocket: TASK_CREATED, DISCOVERY_MADE → Dashboard updates
    │
    ├─→ Needs clarification on OAuth scope
    │   ├─→ Calls create_ticket MCP tool
    │   ├─→ Creates Ticket: "Clarify OAuth scope requirements"
    │   ├─→ Links ticket to Task A (related_task_ids)
    │   └─→ WebSocket: TICKET_CREATED → Dashboard updates Kanban board
    │
    ├─→ Identifies missing dependency
    │   ├─→ Analyzes task descriptions
    │   ├─→ Detects Task C must complete before Task A
    │   ├─→ Updates Task.dependencies JSONB field
    │   └─→ WebSocket: TASK_DEPENDENCY_UPDATED → Dashboard updates graph
    │
    └─→ Guardian detects drift (alignment_score drops to 45%)
        ├─→ Guardian generates SteeringIntervention
        ├─→ ConversationInterventionService resumes conversation (using conversation_id + persistence_dir)
        ├─→ Sends message via conversation.send_message() - **works even while agent is running**
        ├─→ Agent receives intervention: "[GUARDIAN INTERVENTION] Please focus on core authentication flow first"
        ├─→ Agent processes intervention asynchronously (OpenHands event-driven architecture)
        ├─→ Agent adjusts course based on intervention without interrupting current work
        └─→ WebSocket: STEERING_ISSUED → Dashboard shows intervention in agent detail view
```

### Guardian Intervention Integration

**Real-Time Steering**: Guardian monitors agent trajectories every 60 seconds and can send intervention messages directly to active OpenHands conversations without interrupting agent execution.

**OpenHands Capability**: The ability to send messages to running conversations is a core OpenHands feature. As demonstrated in the [OpenHands examples](https://docs.openhands.dev/sdk/guides/agent-server/local-server), agents can receive and process new messages even while actively working on a previous task. This event-driven architecture enables real-time intervention delivery.

**How Interventions Work**:
1. Guardian analyzes agent trajectory → detects `needs_steering=true`
2. Guardian finds agent's running task → retrieves `conversation_id` and `persistence_dir`
3. `ConversationInterventionService` resumes conversation using `Conversation(conversation_id=..., persistence_dir=...)`
4. Sends intervention message via `Conversation.send_message()` - **works even if agent is currently running**
5. Agent processes message asynchronously via event-driven architecture (no interruption)
6. WebSocket event broadcasts intervention → Dashboard updates in real-time

**Key OpenHands Features Used**:
- **`Conversation.send_message()` while running**: Messages can be sent to conversations even while `conversation.run()` is executing in a background thread
- **Event-driven processing**: Agent's `step()` method processes all events including newly added messages
- **Conversation persistence**: Conversations can be resumed using `conversation_id` and `persistence_dir`
- **Pause/Resume**: Conversations support `conversation.pause()` and `conversation.run()` for controlled execution

**Benefits**:
- **Non-Blocking**: Interventions don't pause agent execution - messages are queued and processed asynchronously
- **Real-Time**: Course correction happens immediately without waiting for agent to finish current task
- **Persistent**: All conversations persisted with `conversation_id` and `persistence_dir` for resumption
- **Visible**: Dashboard shows all interventions in agent detail views via WebSocket events
- **Proven Pattern**: Based on OpenHands's built-in message-while-processing capability

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

## 2. Complete Page Flow & Navigation

### 2.1 Overall Navigation Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Logo | Projects | Search | Notifications | Profile  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Sidebar │  │              │  │              │          │
│  │         │  │   Main       │  │   Right      │          │
│  │ • Home  │  │   Content    │  │   Panel      │          │
│  │ • Board │  │   Area       │  │   (optional) │          │
│  │ • Graph │  │              │  │              │          │
│  │ • Specs │  │              │  │              │          │
│  │ • Stats │  │              │  │              │          │
│  │ • Agents│  │              │  │              │          │
│  │ • Cost  │  │              │  │              │          │
│  │ • Audit │  │              │  │              │          │
│  │ • Chat  │  │              │  │              │          │
│  │         │  │              │  │              │          │
│  └─────────┘  └──────────────┘  └──────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Page Hierarchy

```
/ (Root)
├── /login                           # Authentication
├── /dashboard                       # Dashboard home
│   ├── /overview                    # System Overview (real-time monitoring)
│   └── /projects                    # Project list (default view)
│
├── /projects                        # Product Management
│   ├── /                            # Project list view
│   ├── /:projectId                  # Project overview
│   ├── /:projectId/explore          # AI Project Explorer
│   ├── /:projectId/specs            # Specs list
│   ├── /:projectId/specs/:specId    # Spec viewer/editor
│   └── /new                         # Create new project
│
├── /board                           # Kanban Board
│   ├── /:projectId                  # Board view for project
│   └── /:projectId/:ticketId        # Ticket detail
│
├── /graph                           # Dependency Graph
│   ├── /:projectId                  # Project graph
│   └── /:projectId/:ticketId        # Ticket-specific graph
│
├── /stats                           # Statistics
│   ├── /:projectId                  # Project statistics
│   ├── /:projectId/tickets          # Ticket statistics
│   ├── /:projectId/agents           # Agent statistics
│   └── /:projectId/commits          # Commit statistics
│
├── /agents                          # Agent Management
│   ├── /                            # Agent list
│   ├── /:agentId                    # Agent detail (with trajectory analysis)
│   ├── /:agentId/trajectory         # Full trajectory analysis view
│   └── /spawn                       # Spawn agent
│
├── /commits                         # Commit Tracking
│   ├── /:projectId                  # Project commits
│   ├── /:commitSha                  # Commit detail & diff
│   └── /tickets/:ticketId           # Commits for ticket
│
├── /search                          # Global Search
│   └── /?q=...                      # Search results
│
├── /audit                           # Audit Trails
│   ├── /projects/:projectId         # Project audit trail
│   ├── /tickets/:ticketId           # Ticket audit trail
│   └── /agents/:agentId             # Agent audit trail
│
├── /cost                            # Cost Tracking
│   ├── /projects/:projectId         # Project costs
│   ├── /agents/:agentId             # Agent costs
│   └── /forecast                    # Cost forecast
│
└── /settings                        # Settings
    ├── /profile                     # User profile
    ├── /notifications               # Notification settings
    ├── /permissions                 # Permissions (admin)
    └── /integrations                # Integrations (GitHub, etc.)
```

### 2.3 Page Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Entry Point: /dashboard                      │
│                         (Home Page)                             │
└───────────────────┬─────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌──────────────┐      ┌──────────────────┐
│   Projects   │      │   Quick Access   │
│   List Page  │      │   (Recent Board) │
└──────┬───────┘      └──────────────────┘
       │
       ├─→ Click Project
       │
       ▼
┌─────────────────────────────────────────┐
│   Project Overview (/projects/:id)      │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Project Header                 │   │
│  │  • Name, Description            │   │
│  │  • GitHub Connection Status     │   │
│  │  • Quick Stats                  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Navigation Tabs                │   │
│  │  [Board] [Graph] [Specs]        │   │
│  │  [Stats] [Agents] [Commits]     │   │
│  │  [Cost] [Audit]                 │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Recent Activity Feed           │   │
│  │  • Latest tickets               │   │
│  │  • Recent commits               │   │
│  │  • Agent activity               │   │
│  └─────────────────────────────────┘   │
│                                         │
│  [View Board] [Explore Project]        │
│  [View Graph] [View Stats]             │
└─────────────────────────────────────────┘
       │
       ├─→ Click "View Board"
       │
       ▼
┌─────────────────────────────────────────┐
│   Kanban Board (/board/:projectId)      │
│                                         │
│  [Backlog] [Phase 1] [Phase 2] [Done]  │
│                                         │
│  ┌──┐  ┌──┐      ┌──┐                  │
│  │T1│  │T2│      │T3│  ← Ticket Cards  │
│  └──┘  └──┘      └──┘                  │
│                                         │
│  [Filter] [Search] [View Graph]        │
└─────────────────────────────────────────┘
       │
       ├─→ Click Ticket Card
       │
       ▼
┌─────────────────────────────────────────┐
│   Ticket Detail (/board/:id/:ticketId)  │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Ticket Header                  │   │
│  │  • Title, Status, Priority      │   │
│  │  • Phase, Component Tags        │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Tabs: [Details] [Tasks]        │   │
│  │         [Commits] [Graph]       │   │
│  │         [Comments] [Audit]      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Details Tab                     │   │
│  │  • Description                   │   │
│  │  • Dependencies                  │   │
│  │  • Linked Requirements           │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Commits Tab                     │   │
│  │  • Commit List                   │   │
│  │  • Diff Viewer                   │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
       │
       ├─→ Click "View Graph"
       │
       ▼
┌─────────────────────────────────────────┐
│   Dependency Graph (/graph/:id/:ticketId)│
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Graph Controls                  │   │
│  │  [Zoom] [Pan] [Layout] [Filter]  │   │
│  └─────────────────────────────────┘   │
│                                         │
│         [Ticket Node]                   │
│              │                          │
│        [Task Nodes]                     │
│              │                          │
│        [Dependencies]                   │
│                                         │
│  [View Board] [Back to Ticket]         │
└─────────────────────────────────────────┘
```

### 2.4 Product Management Flow

```
┌─────────────────────────────────────────────────────────────┐
│              Product Management Journey                      │
└─────────────────────────────────────────────────────────────┘

1. Project List (/projects)
   │
   ├─→ [Create New Project] button
   │
   ▼
2. Create Project Modal/Page (/projects/new)
   │
   ├─→ Enter project details
   │   • Name, Description
   │   • GitHub Repository (optional)
   │   • Initial Phase
   │
   ├─→ Option A: Start from Scratch
   │   │
   │   └─→ [Create] → Empty project → Go to Board
   │
   ├─→ Option B: Use Template
   │   │
   │   └─→ Select template → [Create] → Pre-populated project
   │
   └─→ Option C: AI Project Explorer
       │
       └─→ [Explore with AI] → Go to Project Explorer
           │
           ▼
3. AI Project Explorer (/projects/:id/explore)
   │
   ├─→ Conversational Q&A
   │   • AI asks clarifying questions
   │   • User provides answers
   │
   ├─→ Requirements Generation
   │   • AI generates requirements document
   │   • User reviews and approves
   │
   ├─→ Design Generation
   │   • AI generates design document
   │   • User reviews and approves
   │
   ├─→ Task Generation (optional)
   │   • Generate initial tasks from requirements
   │   • Extract properties for PBT testing
   │
   └─→ [Initialize Project]
       │
       ▼
4. Project Initialized
   │
   ├─→ Initial tickets created from generated tasks
   │
   └─→ Redirect to Board (/board/:projectId)
       │
       ▼
5. Kanban Board View
   │
   ├─→ Tickets in columns (Backlog → Phases → Done)
   │
   ├─→ [Add Ticket] button
   │   │
   │   └─→ Create Ticket Modal
   │       • Link to requirement (if from spec)
   │       • Set priority, component
   │
   ├─→ Click Ticket Card
   │   │
   │   └─→ Ticket Detail Page
   │       • View tasks
   │       • View commits
   │       • View dependency graph
   │       • View linked requirements
   │
   └─→ [View Tasks] button
       │
       ▼
6. Task Management (/projects/:id/tasks)
   │
   ├─→ List of all tasks for project
   │
   ├─→ Click task
   │   │
   │   └─→ Task Detail View
   │       • Task description
   │       • Requirements traceability
   │       • Design references
   │       • Properties tab (PBT)
   │       • [Create Ticket from Task] button
   │
   └─→ [Create New Task] button
       │
       └─→ Generate from exploration or create manually
```

---

## 3. Product Management Interface Design

### 3.1 Project List Page (/projects)

**Purpose**: Central hub for all projects, product management entry point.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Products                                        [+ New]     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Filters: [All ▼] [Active] [Archived]               │  │
│  │  Search: [________________________] [🔍]             │  │
│  │  Sort: [Recent ▼]  View: [Grid] [List]              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Project 1   │  │  Project 2   │  │  Project 3   │     │
│  │              │  │              │  │              │     │
│  │  📁 auth-    │  │  📁 user-    │  │  📁 payment- │     │
│  │     system   │  │     profile  │  │     service  │     │
│  │              │  │              │  │              │     │
│  │  🟢 Active   │  │  🟢 Active   │  │  🟡 In Setup │     │
│  │              │  │              │  │              │     │
│  │  12 Tickets  │  │  8 Tickets   │  │  3 Tickets   │     │
│  │  5 Agents    │  │  3 Agents    │  │  1 Agent     │     │
│  │  $1,234 Cost │  │  $856 Cost   │  │  $123 Cost   │     │
│  │              │  │              │  │              │     │
│  │  [View]      │  │  [View]      │  │  [View]      │     │
│  │  [Settings]  │  │  [Settings]  │  │  [Settings]  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Recent Activity                                      │  │
│  │                                                       │  │
│  │  • auth-system: Ticket "Add OAuth" completed         │  │
│  │  • user-profile: New commit linked to ticket        │  │
│  │  • payment-service: Agent spawned                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Project Cards**: Visual cards with key metrics
- **Quick Stats**: Tickets count, active agents, cost
- **Status Indicators**: Active, In Setup, Archived
- **Quick Actions**: View, Settings, Archive
- **Recent Activity Feed**: Latest updates across projects
- **Search & Filter**: Find projects quickly
- **Create Button**: Quick access to create new project

### 3.2 Project Overview Page (/projects/:projectId)

**Purpose**: Central dashboard for a specific project, gateway to all project views.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Projects    auth-system              [Settings]  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Project Header                                       │  │
│  │                                                       │  │
│  │  📁 Authentication System with Plugins                │  │
│  │                                                       │  │
│  │  Description:                                         │  │
│  │  Multi-provider authentication system with OAuth2,    │  │
│  │  JWT, and API key support. Includes plugin system     │  │
│  │  for custom authentication methods.                   │  │
│  │                                                       │  │
│  │  🐙 GitHub: owner/repo  ✓ Connected                  │  │
│  │  📅 Created: Jan 15, 2025                            │  │
│  │  👥 Teams: Frontend, Backend                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Quick Stats (Cards)                                  │  │
│  │                                                       │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐            │  │
│  │  │  24  │  │  12  │  │  5   │  │ $1.2K│            │  │
│  │  │Tickets│  │ Done │  │Agents│  │ Cost │            │  │
│  │  └──────┘  └──────┘  └──────┘  └──────┘            │  │
│  │                                                       │  │
│  │  Progress: ████████░░░░░░░░░ 40%                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Navigation Tabs                                      │  │
│  │                                                       │  │
│  │  [📋 Board] [📊 Graph] [📄 Specs] [📈 Stats]        │  │
│  │  [🤖 Agents] [💻 Commits] [💰 Cost] [📜 Audit]     │  │
│  │                                                       │  │
│  │  [Explore] [Settings]                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Recent Activity                                      │  │
│  │                                                       │  │
│  │  🕐 2 hours ago                                       │  │
│  │  ✅ Ticket "Add OAuth2 Provider" completed           │  │
│  │  → Agent: worker-9a781fc3                            │  │
│  │  → Commit: 02979f6 (+2255 lines)                     │  │
│  │                                                       │  │
│  │  🕐 4 hours ago                                       │  │
│  │  📝 New ticket "Add JWT Validation" created          │  │
│  │  → Phase: PHASE_IMPLEMENTATION                        │  │
│  │                                                       │  │
│  │  🕐 6 hours ago                                       │  │
│  │  🔗 Commit linked to ticket "Add OAuth2 Provider"    │  │
│  │  → Commit: a1b2c3d (+456 lines)                      │  │
│  │                                                       │  │
│  │  [View All Activity]                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Quick Actions                                        │  │
│  │                                                       │  │
│  │  [➕ Create Ticket] [🤖 Spawn Agent]                 │  │
│  │  [📄 Create Spec] [🔍 Search]                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Project Header**: Name, description, GitHub connection
- **Quick Stats Cards**: Tickets, completion, agents, cost
- **Progress Bar**: Visual completion indicator
- **Navigation Tabs**: Quick access to all project views
- **Recent Activity Feed**: Timeline of project events
- **Quick Actions**: Common actions (create ticket, spawn agent)

### 3.3 Project Settings Page (/projects/:projectId/settings)

**Purpose**: Configure project settings, GitHub integration, phases, WIP limits.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Project    auth-system - Settings                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Settings Tabs                                       │  │
│  │                                                       │  │
│  │  [General] [GitHub] [Phases] [Board] [Notifications]│  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  General Settings                                    │  │
│  │                                                       │  │
│  │  Project Name: [authentication-system_____________]  │  │
│  │                                                       │  │
│  │  Description:                                        │  │
│  │  [_____________________________________________]     │  │
│  │  [Multi-line description...]                        │  │
│  │                                                       │  │
│  │  Default Phase: [PHASE_IMPLEMENTATION ▼]            │  │
│  │                                                       │  │
│  │  Status: ● Active                                    │  │
│  │          ○ Archived                                  │  │
│  │                                                       │  │
│  │  [Save Changes]                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  GitHub Integration                                  │  │
│  │                                                       │  │
│  │  Repository: owner/repo  ✓ Connected                 │  │
│  │  Webhook Status: ✓ Active                            │  │
│  │                                                       │  │
│  │  [Disconnect] [Reconnect] [Test Webhook]            │  │
│  │                                                       │  │
│  │  Sync Options:                                       │  │
│  │  ☑ Auto-create tickets from issues                   │  │
│  │  ☑ Auto-link commits to tickets                      │  │
│  │  ☐ Auto-complete tasks on PR merge                   │  │
│  │                                                       │  │
│  │  [Save Changes]                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Board Configuration                                 │  │
│  │                                                       │  │
│  │  Columns (Phases):                                   │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Backlog                                      │    │  │
│  │  │ WIP Limit: [∞]                               │    │  │
│  │  │ [Remove]                                     │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ PHASE_INITIAL                                │    │  │
│  │  │ WIP Limit: [5___]                            │    │  │
│  │  │ [Remove]                                     │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  [+ Add Phase]                                       │  │
│  │                                                       │  │
│  │  [Save Changes]                                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Tabbed Interface**: Organized settings sections
- **General Settings**: Name, description, default phase, status
- **GitHub Integration**: Repository connection, webhook status, sync options
- **Board Configuration**: Phase management, WIP limits
- **Notification Settings**: Alert preferences

### 3.4 Project Explorer Page (/projects/:projectId/explore)

**Purpose**: AI-powered project discovery and planning workflow.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Project    AI Project Explorer                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Exploration Progress                                │  │
│  │                                                       │  │
│  │  Stage: Requirements Review (3/5)                    │  │
│  │                                                       │  │
│  │  ████████░░░░░░░░░░ 40%                             │  │
│  │                                                       │  │
│  │  [1. Exploration] [2. Requirements] [3. Design]      │  │
│  │  [4. Spec] [5. Initialize]                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Conversation                                        │  │
│  │                                                       │  │
│  │  🤖 AI: "What authentication methods should be       │  │
│  │         supported?"                                   │  │
│  │                                                       │  │
│  │  👤 You: "OAuth2, JWT, and API keys"                │  │
│  │                                                       │  │
│  │  🤖 AI: "Should this support multi-tenant            │  │
│  │         scenarios?"                                   │  │
│  │                                                       │  │
│  │  👤 You: [Answer input field...]                     │  │
│  │                                                       │  │
│  │  [Send] [Skip Question]                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Documents                                           │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Requirements Document                        │    │  │
│  │  │ Status: ⚠ Pending Review                    │    │  │
│  │  │ [View] [Approve] [Request Changes]          │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Design Document                              │    │  │
│  │  │ Status: ⏳ Not Generated                     │    │  │
│  │  │ (Waiting for requirements approval)         │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Actions                                             │  │
│  │                                                       │  │
│  │  [Generate Requirements] [Generate Design]           │  │
│  │  [Generate Spec] [Initialize Project]                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 Specs Management Page (/projects/:projectId/specs)

**Purpose**: Manage project tasks and requirements (stored in database, not external files).

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Project    Specs                     [+ New Spec] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Filter: [All ▼]  Search: [____________] [🔍]       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  authentication-system                                │  │
│  │                                                       │  │
│  │  Status: ✓ Complete  |  Created: 2 days ago          │  │
│  │                                                       │  │
│  │  Files:                                              │  │
│  │    📋 Requirements (23 requirements in DB)            │  │
│  │    🏗️ Design Notes (6 sections in DB)                │  │
│  │    ✅ Tasks (15 tasks in DB)                         │  │
│  │                                                       │  │
│  │  Properties: 12 extracted | Tests: 11 passed, 1 failed│ │
│  │                                                       │  │
│  │  Linked Tickets: 15 tickets created                  │  │
│  │                                                       │  │
│  │  [View Spec] [Edit] [Run Tests] [Generate Tasks]     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  user-profile-management                              │  │
│  │                                                       │  │
│  │  Status: ⚠ In Progress  |  Created: 1 week ago      │  │
│  │                                                       │  │
│  │  Files:                                              │  │
│  │    📋 Requirements (18 requirements in DB)            │  │
│  │    🏗️ Design Notes (4 sections in DB)                │  │
│  │    ✅ Tasks (12 tasks in DB) - DRAFT                 │  │
│  │                                                       │  │
│  │  Properties: 8 extracted | Tests: Not run            │  │
│  │                                                       │  │
│  │  Linked Tickets: 0 tickets                           │  │
│  │                                                       │  │
│  │  [View Spec] [Edit] [Extract Properties] [Generate]  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Navigation & Page Relationships

### 4.1 Primary Navigation Flow

```
Dashboard Home (/)
    │
    ├─→ System Overview (/dashboard/overview)
    │       └─→ Real-time monitoring, agent alignment, system health
    │
    ├─→ Projects List (/projects)
    │       │
    │       ├─→ Project Overview (/projects/:id)
    │       │       │
    │       │       ├─→ Kanban Board (/board/:projectId)
    │       │       │       └─→ Ticket Detail (/board/:projectId/:ticketId)
    │       │       │
    │       │       ├─→ Dependency Graph (/graph/:projectId)
    │       │       │       └─→ Ticket Graph (/graph/:projectId/:ticketId)
    │       │       │
    │       │       ├─→ Specs Management (/projects/:id/specs)
    │       │       │       └─→ Spec Viewer (/projects/:id/specs/:specId)
    │       │       │
    │       │       ├─→ Statistics (/stats/:projectId)
    │       │       │       ├─→ Ticket Stats
    │       │       │       ├─→ Agent Stats
    │       │       │       └─→ Commit Stats
    │       │       │
    │       │       ├─→ Agents (/agents?project=:projectId)
    │       │       │       └─→ Agent Detail (/agents/:agentId)
    │       │       │
    │       │       ├─→ Commits (/commits/:projectId)
    │       │       │       └─→ Commit Detail (/commits/:commitSha)
    │       │       │
    │       │       ├─→ Cost Tracking (/cost/projects/:projectId)
    │       │       │
    │       │       ├─→ Audit Trail (/audit/projects/:projectId)
    │       │       │
    │       │       ├─→ Project Explorer (/projects/:id/explore)
    │       │       │
    │       │       └─→ Project Settings (/projects/:id/settings)
    │       │
    │       └─→ Create Project (/projects/new)
    │               └─→ Project Explorer (new project)
    │
    ├─→ Global Search (/search?q=...)
    │
    ├─→ Chat Assistant (/chat)
    │       └─→ Chat with Spec Context
    │
    └─→ Settings (/settings)
            ├─→ Profile
            ├─→ Notifications
            └─→ Integrations
```

### 4.2 Kanban Board Integration with Product Management

**Relationship:**
- **Kanban Board** is a view of project tickets organized by phases
- **Product Management** provides the project context and configuration
- **Tickets** link to requirements/specs from product exploration phase

**Integration Points:**

1. **From Project Overview → Board:**
   - Click "Board" tab or "View Board" button
   - Board shows all tickets for the project
   - Filters/scopes to current project

2. **From Board → Product Management:**
   - Ticket cards can show linked requirement ID (REQ-001)
   - Click requirement → View spec viewer at that requirement
   - Board settings link to project settings

3. **From Spec → Board:**
   - Generate tasks from spec creates tickets
   - Tickets appear in board automatically
   - Tickets show linked requirement/spec badge

4. **From Ticket Detail → Spec:**
   - Ticket detail shows "Linked Requirements" section
   - Click requirement → Jump to spec viewer
   - See requirement context in ticket

### 4.3 Sidebar Navigation

```
┌─────────────────┐
│   Navigation    │
├─────────────────┤
│ 🏠 Home         │
│                 │
│ 📊 Overview     │
│                 │
│ 📁 Projects     │
│   └─ Project 1  │
│   └─ Project 2  │
│                 │
│ 📋 Board        │
│   └─ Project 1  │
│                 │
│ 📊 Graph        │
│   └─ Project 1  │
│                 │
│ 📄 Specs        │
│   └─ Project 1  │
│                 │
│ 📈 Statistics   │
│                 │
│ 🤖 Agents       │
│                 │
│ 💻 Commits      │
│                 │
│ 💰 Cost         │
│                 │
│ 📜 Audit        │
│                 │
│ 🔍 Search       │
│                 │
│ 💬 Chat         │
│                 │
│ ⚙️  Settings     │
└─────────────────┘
```

---

## 5. WebSocket Integration

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

See [Implementation Details - Frontend Code Examples](./project_management_dashboard_implementation.md#21-frontend-code-examples) for complete code examples including `useBoard` hook, `DependencyGraph` component, and WebSocket integration.

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

**Note**: Graph API endpoints are already implemented. See [Existing Codebase Mapping](#existing-codebase-mapping) for details.

For API endpoint specifications, see [API Specifications - Graph API](./project_management_dashboard_api.md).

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

See [Implementation Details - Frontend Code Examples](./project_management_dashboard_implementation.md#22-dependency-graph-component) for complete `DependencyGraph` component implementation.

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

**Existing Model**: `TicketCommit` model exists. See [Implementation Details - Database Models](./project_management_dashboard_implementation.md#32-ticketcommit-model) for model structure.

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

See [API Specifications - Commits API](./project_management_dashboard_api.md#3-commits-api) for complete endpoint specifications.

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

See [Implementation Details - Service Implementations](./project_management_dashboard_implementation.md#41-github-integration-service) for `GitHubIntegrationService` implementation.

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

See [API Specifications - GitHub Integration API](./project_management_dashboard_api.md#4-github-integration-api) for complete endpoint specifications.

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

See [API Specifications - Audit API](./project_management_dashboard_api.md#5-audit-api) for complete endpoint specifications.

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

See [API Specifications - Statistics API](./project_management_dashboard_api.md#6-statistics-api) for complete endpoint specifications.

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

See [API Specifications - Search API](./project_management_dashboard_api.md#7-search-api) for complete endpoint specifications.

---

## 10. Project Management

### 10.1 Project Model

See [Implementation Details - Database Models](./project_management_dashboard_implementation.md#31-project-model) for complete `Project` model definition.

### 10.2 Project API

See [API Specifications - Projects API](./project_management_dashboard_api.md#8-projects-api) for complete endpoint specifications.

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

See [Implementation Details - Database Models](./project_management_dashboard_implementation.md#33-project-exploration-models) for complete model definitions including:
- `ProjectExploration` - Tracks AI-assisted exploration sessions
- `Requirements` - Stores requirements documents (with database/S3 storage support)
- `IndividualRequirement` - Stores individual requirements extracted from documents
- `Designs` - Stores design documents (with database/S3 storage support)
- `ExplorationQuestion` - Tracks questions asked during exploration

### 10.3.2.1 Document Storage Strategy

See [Implementation Details - Document Storage Service](./project_management_dashboard_implementation.md#42-document-storage-service) for complete storage abstraction, S3 bucket organization, migration strategy, and configuration details.

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

See [API Specifications - Project Exploration API](./project_management_dashboard_api.md#9-project-exploration-api) for complete endpoint specifications.

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

See [API Specifications - Project Exploration API](./project_management_dashboard_api.md#9-project-exploration-api) for complete endpoint specifications.

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

See [API Specifications - Project Exploration API](./project_management_dashboard_api.md#9-project-exploration-api) for complete endpoint specifications including document approval workflow.

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

See [API Specifications - Project Exploration API](./project_management_dashboard_api.md#9-project-exploration-api) for complete endpoint specifications.

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

### 10.3.12 Spec-Driven Development Integration

**Overview:**
Spec-driven development provides a structured approach to specification-driven development with three key files:
- Requirements (stored in database) - User stories and acceptance criteria in EARS notation
- Design Notes (stored in database) - Technical architecture, sequence diagrams, implementation considerations
- Tasks (stored in database) - Detailed implementation plan with discrete, trackable tasks

**Integration Points:**
1. **Spec Generation from Exploration**: Convert approved requirements and design documents into spec format
2. **EARS Notation Conversion**: Transform natural language requirements into structured EARS format (WHEN [condition] THE SYSTEM SHALL [behavior])
3. **Property-Based Testing**: Extract testable properties from requirements and generate PBT cases
4. **Task Execution**: Convert spec tasks into system tickets/tasks for agent execution
5. **Spec Management**: View, edit, and version control specs within the dashboard
6. **Chat Integration**: Reference specs in chat conversations for context-aware assistance

**Workflow Integration:**
```
Project Exploration → Requirements Document → Design Document
         ↓                        ↓                    ↓
    Convert to EARS      Convert to Spec      Generate Tasks
         ↓                        ↓                    ↓
    Requirements DB           Design DB          Tasks DB
         ↓                        ↓                    ↓
    Extract Properties    Architecture Docs    Create Tickets
         ↓                        ↓                    ↓
    PBT Test Cases        Implementation      Agent Execution
```

**Database Models:**
```python
# omoi_os/models/spec.py

class ProjectSpec(Base):
    """Specification linked to project exploration."""
    
    __tablename__ = "project_specs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("projects.id"), nullable=True, index=True
    )
    exploration_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("project_explorations.id"), nullable=True, index=True
    )
    
    # Spec metadata
    spec_name: Mapped[str] = mapped_column(String(255), nullable=False)
    spec_path: Mapped[str] = mapped_column(String(500), nullable=False)  # specs/{name}/
    
    # Spec files
    requirements_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    design_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    tasks_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )  # draft, requirements_complete, design_complete, tasks_generated, executing, completed
    
    # Property-based testing
    properties_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    pbt_test_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    linked_tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="spec")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class SpecProperty(Base):
    """Property extracted from requirements for PBT."""
    
    __tablename__ = "spec_properties"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    spec_id: Mapped[str] = mapped_column(
        String, ForeignKey("project_specs.id"), nullable=False, index=True
    )
    requirement_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Link to requirement
    
    # Property definition
    property_statement: Mapped[str] = mapped_column(Text, nullable=False)
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)  # invariant, contract, behavior
    
    # PBT status
    test_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    test_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_test_result: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # passed, failed, not_run
    last_test_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
```

**API Endpoints:**

See [API Specifications - Project Exploration API](./project_management_dashboard_api.md#9-project-exploration-api) for complete endpoint specifications including spec generation, property extraction, and task generation.

**UI Components:**
- `SpecGenerator.tsx` - Generate spec from exploration
- `TaskViewer.tsx` - View project tasks and requirements (from database)
- `SpecEditor.tsx` - Edit spec files inline
- `PropertyExtractor.tsx` - Extract and view properties
- `PropertyTestRunner.tsx` - Run and view PBT results
- `SpecTaskMapper.tsx` - Map spec tasks to system tickets
- `SpecList.tsx` - Browse all specs in project

**EARS Conversion:**
The system automatically converts natural language requirements into EARS notation:
- Input: "Users should be able to login with email and password"
- Output: "WHEN a user provides valid email and password credentials, THE SYSTEM SHALL authenticate the user and grant access"

**Property Extraction:**
Properties are automatically extracted from EARS requirements:
- Requirement: "WHEN a user adds a car to favorites, THE SYSTEM SHALL display it in their favorites list"
- Property: "For any user and any car, WHEN the user adds the car to favorites, THE SYSTEM SHALL display it in their favorites list"
- PBT generates hundreds of test cases with various users and cars

**Task Generation:**
Tasks from the project are automatically converted to system tickets:
- Each task becomes a ticket
- Subtasks become tasks linked to the parent ticket
- Dependencies are preserved
- Tasks can be executed by agents

### 10.3.13 ASCII Interface Mockups

#### 10.3.13.1 Spec Generation from Exploration

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Project Explorer: Authentication System                    [×] [Min] [Max]│
├─────────────────────────────────────────────────────────────────────────┤
│ Stage: Design Approved ✓                                              │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ Requirements Document: ✓ Approved                                 │ │
│ │ Design Document: ✓ Approved                                      │ │
│ │                                                                   │ │
│ │ [Generate Spec]  [View Documents]  [Initialize Project]            │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ Generate Spec                                                     │ │
│ ├───────────────────────────────────────────────────────────────────┤ │
│ │                                                                   │ │
│ │ Spec Name: [authentication-system________________]                │ │
│ │                                                                   │ │
│ │ Spec Path: specs/authentication-system/                           │ │
│ │                                                                   │ │
│ │ Files to Generate:                                               │ │
│ │ ☑ Requirements (EARS notation, stored in DB)                     │ │
│ │ ☑ Design Notes (Technical architecture, stored in DB)            │ │
│ │ ☑ Tasks (Implementation plan, stored in DB)                      │ │
│ │                                                                   │ │
│ │ Options:                                                          │ │
│ │ ☑ Extract properties for PBT                                    │ │
│ │ ☑ Generate property-based tests                                   │ │
│ │ ☐ Link to existing project                                       │ │
│ │                                                                   │ │
│ │ [Cancel]  [Generate Spec]                                         │ │
│ └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 10.3.13.2 Spec Viewer Interface

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Spec: authentication-system                        [×] [Edit] [Export]   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌──────────┬────────────────────────────────────────────────────────┐ │
│ │ Spec     │ Status: ✓ Requirements  ✓ Design  ✓ Tasks Generated   │ │
│ │ Files    │                                                         │ │
│ │          │ Properties: 12 extracted  |  Tests: 8 generated     │ │
│ │ 📄 req   │                                                         │ │
│ │   uire   │ [Extract Properties] [Run PBT] [Generate Tasks]        │ │
│ │   ments  │                                                         │ │
│ │   .md    │                                                         │ │
│ │          │                                                         │ │
│ │ 📄 des   │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ Design  │ │ Requirements                                          │ │ │
│ │          │ ├─────────────────────────────────────────────────────┤ │ │
│ │ 📄 task  │ │ # Authentication System Requirements                │ │ │
│ │   s.md   │ │                                                     │ │ │
│ │          │ │ ## User Authentication                              │ │ │
│ │          │ │                                                     │ │ │
│ │          │ │ **REQ-001**                                         │ │ │
│ │          │ │ WHEN a user provides valid email and password       │ │ │
│ │          │ │ THE SYSTEM SHALL authenticate the user and grant   │ │ │
│ │          │ │      access to the application                      │ │ │
│ │          │ │                                                     │ │ │
│ │          │ │ **REQ-002**                                         │ │ │
│ │          │ │ WHEN a user provides invalid credentials           │ │ │
│ │          │ │ THE SYSTEM SHALL reject the authentication         │ │ │
│ │          │ │      attempt and display an error message           │ │ │
│ │          │ │                                                     │ │ │
│ │          │ │ **REQ-003**                                        │ │ │
│ │          │ │ WHEN a user successfully authenticates             │ │ │
│ │          │ │ THE SYSTEM SHALL create a session and return      │ │ │
│ │          │ │      a JWT token                                    │ │ │
│ │          │ │                                                     │ │ │
│ │          │ │ [Scroll for more...]                               │ │ │
│ │          │ └─────────────────────────────────────────────────────┘ │ │
│ │          │                                                         │ │
│ │          │ ┌─────────────────────────────────────────────────────┐ │ │
│ │          │ │ Properties Extracted (12)                            │ │ │
│ │          │ ├─────────────────────────────────────────────────────┤ │ │
│ │          │ │ ✓ P-001: For any user with valid credentials,       │ │ │
│ │          │ │         authentication succeeds                     │ │ │
│ │          │ │ ✓ P-002: For any user with invalid credentials,    │ │ │
│ │          │ │         authentication fails                        │ │ │
│ │          │ │ ✓ P-003: For any authenticated user, session      │ │ │
│ │          │ │         token is valid                              │ │ │
│ │          │ │ ...                                                 │ │ │
│ │          │ └─────────────────────────────────────────────────────┘ │ │
│ └──────────┴────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 10.3.13.3 Property-Based Testing Interface

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Property-Based Testing: authentication-system          [×] [Run All]    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ Properties & Test Results                                         │ │
│ ├───────────────────────────────────────────────────────────────────┤ │
│ │                                                                   │ │
│ │ ┌─ P-001 ─────────────────────────────────────────────────────┐ │ │
│ │ │ Property: For any user with valid credentials,               │ │ │
│ │ │           authentication succeeds                           │ │ │
│ │ │                                                              │ │ │
│ │ │ Status: ✓ PASSED  |  Test Cases: 1,247  |  Duration: 2.3s │ │ │
│ │ │                                                              │ │ │
│ │ │ Test File: tests/properties/test_auth_001.py                │ │ │
│ │ │ [View Test] [View Results] [Re-run]                         │ │ │
│ │ └──────────────────────────────────────────────────────────────┘ │ │
│ │                                                                   │ │
│ │ ┌─ P-002 ─────────────────────────────────────────────────────┐ │ │
│ │ │ Property: For any user with invalid credentials,           │ │ │
│ │ │           authentication fails                               │ │ │
│ │ │                                                              │ │ │
│ │ │ Status: ✓ PASSED  |  Test Cases: 892  |  Duration: 1.8s   │ │ │
│ │ │                                                              │ │ │
│ │ │ Test File: tests/properties/test_auth_002.py                │ │ │
│ │ │ [View Test] [View Results] [Re-run]                         │ │ │
│ │ └──────────────────────────────────────────────────────────────┘ │ │
│ │                                                                   │ │
│ │ ┌─ P-003 ─────────────────────────────────────────────────────┐ │ │
│ │ │ Property: For any authenticated user, session token is      │ │ │
│ │ │           valid                                              │ │ │
│ │ │                                                              │ │ │
│ │ │ Status: ✗ FAILED  |  Test Cases: 1,045  |  Duration: 3.1s │ │ │
│ │ │                                                              │ │ │
│ │ │ Failure Found:                                               │ │ │
│ │ │   User: {"email": "test@example.com", "password": "..."}   │ │ │
│ │ │   Token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."          │ │ │
│ │ │   Error: Token validation failed for expired token          │ │ │
│ │ │                                                              │ │ │
│ │ │ [View Failure Details] [Fix Implementation] [Update Spec]  │ │ │
│ │ └──────────────────────────────────────────────────────────────┘ │ │
│ │                                                                   │ │
│ │ Summary: 11 passed | 1 failed | 0 not run                       │ │
│ └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 10.3.13.4 Task Generation from Spec

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Generate Tasks from Spec: authentication-system        [×] [Cancel]     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ Tasks to Create (from project tasks)                               │ │
│ ├───────────────────────────────────────────────────────────────────┤ │
│ │                                                                   │ │
│ │ ┌─ Task 1.1 ───────────────────────────────────────────────────┐ │ │
│ │ │ Title: Set up authentication service infrastructure         │ │ │
│ │ │                                                              │ │ │
│ │ │ Description:                                                │ │ │
│ │ │   - Create authentication service module                   │ │ │
│ │ │   - Set up database schema for users                        │ │ │
│ │ │   - Configure JWT token generation                          │ │ │
│ │ │                                                              │ │ │
│ │ │ Priority: HIGH  |  Phase: PHASE_INITIAL                    │ │ │
│ │ │ Dependencies: None                                          │ │ │
│ │ │                                                              │ │ │
│ │ │ ☑ Create as Ticket  |  Project: [auth-project ▼]           │ │ │
│ │ └──────────────────────────────────────────────────────────────┘ │ │
│ │                                                                   │ │
│ │ ┌─ Task 1.2 ───────────────────────────────────────────────────┐ │ │
│ │ │ Title: Implement user login endpoint                        │ │ │
│ │ │                                                              │ │ │
│ │ │ Description:                                                │ │ │
│ │ │   - Create POST /api/auth/login endpoint                    │ │ │
│ │ │   - Validate credentials                                    │ │ │
│ │ │   - Return JWT token on success                              │ │ │
│ │ │                                                              │ │ │
│ │ │ Priority: HIGH  |  Phase: PHASE_IMPLEMENTATION            │ │ │
│ │ │ Dependencies: Task 1.1                                      │ │ │
│ │ │                                                              │ │ │
│ │ │ ☑ Create as Ticket  |  Project: [auth-project ▼]           │ │ │
│ │ └──────────────────────────────────────────────────────────────┘ │ │
│ │                                                                   │ │
│ │ ┌─ Task 1.3 ───────────────────────────────────────────────────┐ │ │
│ │ │ Title: Add password validation                               │ │ │
│ │ │                                                              │ │ │
│ │ │ Description:                                                │ │ │
│ │ │   - Implement password strength requirements                │ │ │
│ │ │   - Add validation rules                                    │ │ │
│ │ │   - Return appropriate error messages                       │ │ │
│ │ │                                                              │ │ │
│ │ │ Priority: MEDIUM  |  Phase: PHASE_IMPLEMENTATION           │ │ │
│ │ │ Dependencies: Task 1.2                                      │ │ │
│ │ │                                                              │ │ │
│ │ │ ☑ Create as Ticket  |  Project: [auth-project ▼]           │ │ │
│ │ └──────────────────────────────────────────────────────────────┘ │ │
│ │                                                                   │ │
│ │ ... (12 more tasks)                                               │ │
│ │                                                                   │ │
│ │ [Select All] [Deselect All]  |  [Preview Tickets] [Generate]     │ │
│ └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 10.3.13.5 Spec List View

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Specs - Project: auth-project                          [+ New Spec]      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ Filter: [All ▼]  Search: [________________]  Sort: [Recent ▼]  │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ authentication-system ────────────────────────────────────────────┐ │
│ │ Status: ✓ Complete  |  Created: 2 days ago                       │ │
│ │                                                                     │ │
│ │ Files:                                                              │ │
│ │   📄 requirements.md (23 requirements)                             │ │
│ │   📄 design.md (6 sections)                                        │ │
│ │   📄 tasks.md (15 tasks)                                           │ │
│ │                                                                     │ │
│ │ Properties: 12 extracted | Tests: 11 passed, 1 failed            │ │
│ │                                                                     │ │
│ │ Linked Tickets: 15 tickets created                                │ │
│ │                                                                     │ │
│ │ [View Spec] [Edit] [Run Tests] [Generate Tasks] [Export]           │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ user-profile-management ────────────────────────────────────────┐ │
│ │ Status: ⚠ In Progress  |  Created: 1 week ago                    │ │
│ │                                                                     │ │
│ │ Files:                                                              │ │
│ │   📄 requirements.md (18 requirements)                             │ │
│ │   📄 design.md (4 sections)                                        │ │
│ │   📄 tasks.md (12 tasks) - DRAFT                                   │ │
│ │                                                                     │ │
│ │ Properties: 8 extracted | Tests: Not run                          │ │
│ │                                                                     │ │
│ │ Linked Tickets: 0 tickets                                         │ │
│ │                                                                     │ │
│ │ [View Spec] [Edit] [Extract Properties] [Generate Tasks]          │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ oauth-integration ───────────────────────────────────────────────┐ │
│ │ Status: 📝 Draft  |  Created: 3 days ago                          │ │
│ │                                                                     │ │
│ │ Files:                                                              │ │
│ │   📄 requirements.md (15 requirements) - DRAFT                   │ │
│ │   📄 design.md - Not generated                                     │ │
│ │   📄 tasks.md - Not generated                                      │ │
│ │                                                                     │ │
│ │ Properties: Not extracted                                          │ │
│ │                                                                     │ │
│ │ [View Spec] [Edit] [Generate Design]                              │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 10.3.13.6 Complete Workflow Visualization

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Complete Workflow: From Exploration to Execution                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐                                                    │
│  │ 1. Exploration  │                                                    │
│  │    Phase        │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           │ User: "I want authentication system"                        │
│           │ AI: Asks clarifying questions                               │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 2. Requirements │                                                    │
│  │    Document     │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           │ Generated from Q&A                                         │
│           │ User reviews & approves                                     │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 3. Design       │                                                    │
│  │    Document     │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           │ Generated from requirements                                 │
│           │ User reviews & approves                                     │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 4. Generate     │                                                    │
│  │    Spec         │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           │ Converts to:                                               │
│           │   • Requirements (EARS, stored in DB)                      │
│           │   • Design Notes (Architecture, stored in DB)              │
│           │   • Tasks (Implementation, stored in DB)                   │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 5. Extract      │                                                    │
│  │    Properties   │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           │ From EARS requirements:                                     │
│           │   "WHEN user adds car to favorites,                        │
│           │    THE SYSTEM SHALL display it"                            │
│           │                                                             │
│           │ Extracts:                                                   │
│           │   "For any user and any car,                               │
│           │    WHEN user adds car to favorites,                        │
│           │    THE SYSTEM SHALL display it"                            │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 6. Generate     │                                                    │
│  │    PBT Tests    │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           │ Generates hundreds of test cases                           │
│           │ Tests property across input space                          │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 7. Generate     │                                                    │
│  │    Tickets      │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           │ From project tasks:                                         │
│           │   • Each task → Ticket                                      │
│           │   • Subtasks → Tasks linked to ticket                      │
│           │   • Dependencies preserved                                 │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 8. Agent        │                                                    │
│  │    Execution    │                                                    │
│  └─────────────────┘                                                    │
│                                                                         │
│           Agents execute tasks, code changes tracked,                   │
│           PBT validates correctness                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 10.3.13.7 Spec Chat Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Chat Assistant                                    [×] [Settings] [Help] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ Context Providers                                    [+ Add Context]│ │
│ ├───────────────────────────────────────────────────────────────────┤ │
│ │ 📋 #spec:authentication-system  [×]                               │ │
│ │    • authentication-system: 23 requirements, 6 design sections, 15 tasks │ │
│ │                                                                     │ │
│ │ 📁 #code:omoi_os/services/auth/  [×]                              │ │
│ │                                                                     │ │
│ │ 🎫 #ticket:auth-001  [×]                                           │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ 👤 You: Implement task 2.3 from the spec                         │ │
│ │                                                                    │ │
│ │    [Attach File] [Reference] [Code]                               │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ 🤖 AI Assistant                                                   │ │
│ │                                                                    │ │
│ │ I'll implement task 2.3: "Add password validation"                │ │
│ │                                                                    │ │
│ │ Based on the spec (#spec:authentication-system):                   │ │
│ │   • REQ-005: Password strength requirements                        │ │
│ │     WHEN a user sets a password                                  │ │
│ │     THE SYSTEM SHALL validate it meets strength requirements      │ │
│ │                                                                    │ │
│ │   • Design: Validation service architecture                       │ │
│ │     - PasswordValidator service with rules                        │ │
│ │     - Configurable validation policies                           │ │
│ │                                                                    │ │
│ │ I'll create:                                                       │ │
│ │   1. PasswordValidator service                                   │ │
│ │   2. Validation rules (min length, complexity)                    │ │
│ │   3. Error messages matching spec requirements                   │ │
│ │                                                                    │ │
│ │ [Generate Code] [Show Plan] [Ask Questions]                       │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ 👤 You: Does my implementation meet REQ-005?                     │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ 🤖 AI Assistant                                                   │ │
│ │                                                                    │ │
│ │ Checking implementation against REQ-005...                        │ │
│ │                                                                    │ │
│ │ ✓ Password minimum length enforced (8+ characters)                │ │
│ │ ✓ Complexity requirements implemented (uppercase, lowercase,      │ │
│ │   numbers, special chars)                                         │ │
│ │ ✓ Error messages match specification format                      │ │
│ │ ✓ Validation runs on password set/change                         │ │
│ │                                                                    │ │
│ │ Your implementation meets all acceptance criteria for REQ-005!    │ │
│ │                                                                    │ │
│ │ Would you like me to run the property-based tests for this       │ │
│ │ requirement?                                                      │ │
│ │                                                                    │ │
│ │ [Run PBT] [View Spec] [Suggest Improvements]                      │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ 👤 You: Update the design to include password reset flow          │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ 🤖 AI Assistant                                                   │ │
│ │                                                                    │ │
│ │ I'll update the design document to include password reset flow.   │ │
│ │                                                                    │ │
│ │ Based on the current spec, I'll add:                              │ │
│ │   • Password reset request endpoint                               │ │
│ │   • Token-based reset link generation                             │ │
│ │   • Reset password endpoint                                       │ │
│ │   • Sequence diagram for reset flow                              │ │
│ │                                                                    │ │
│ │ Should I also update the requirements (in DB) to add the EARS    │ │
│ │ requirements for password reset?                                  │ │
│ │                                                                    │ │
│ │ [Update Design] [Update Requirements] [Update Both]               │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ Quick Actions:                                                     │ │
│ │   [#spec] [@ticket] [@agent] [@commit] [@file]                   │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ [Type your message...]                              [Send] [Enter]│ │
│ └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 10.3.13.8 Chat Interface with Spec Context Panel

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Chat Assistant                                    [×] [Settings] [Help] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌──────────────────────┬──────────────────────────────────────────────┐ │
│ │                      │                                              │ │
│ │ Context Panel        │ ┌────────────────────────────────────────┐ │ │
│ │                      │ │ 👤 You: Show me REQ-003                │ │ │
│ │ 📋 Specs             │ └────────────────────────────────────────┘ │ │
│ │   authentication-    │                                              │ │
│ │   system ✓           │ ┌────────────────────────────────────────┐ │ │
│ │                      │ │ 🤖 AI: REQ-003 from spec:               │ │ │
│ │   user-profile       │ │                                          │ │ │
│ │   management         │ │ **REQ-003**                             │ │ │
│ │                      │ │ WHEN a user successfully authenticates  │ │ │
│ │ 📁 Code              │ │ THE SYSTEM SHALL create a session and   │ │ │
│ │   omoi_os/services/  │ │      return a JWT token                 │ │ │
│ │   auth/ ✓            │ │                                          │ │ │
│ │                      │ │ Acceptance Criteria:                     │ │ │
│ │ 🎫 Tickets            │ │ • Token includes user ID and roles      │ │ │
│ │   auth-001 ✓         │ │ • Token expires after 24 hours          │ │ │
│ │   auth-002           │ │ • Token is signed with secret key       │ │ │
│ │                      │ │                                          │ │ │
│ │ [Clear All]          │ │ Related Design:                         │ │ │
│ │                      │ │ • JWT token generation service           │ │ │
│ │                      │ │ • Session management                     │ │ │
│ │                      │ │                                          │ │ │
│ │                      │ │ [View Full Spec] [View Implementation]  │ │ │
│ │                      │ └────────────────────────────────────────┘ │ │
│ │                      │                                              │ │
│ │                      │ ┌────────────────────────────────────────┐ │ │
│ │                      │ │ 👤 You: What tasks depend on REQ-003?  │ │ │
│ │                      │ └────────────────────────────────────────┘ │ │
│ │                      │                                              │ │
│ │                      │ ┌────────────────────────────────────────┐ │ │
│ │                      │ │ 🤖 AI: Tasks that depend on REQ-003:  │ │ │
│ │                      │ │                                          │ │ │
│ │                      │ │ • Task 2.1: Implement login endpoint   │ │ │
│ │                      │ │   (depends on REQ-003)                 │ │ │
│ │                      │ │                                          │ │ │
│ │                      │ │ • Task 2.2: Add token refresh          │ │ │
│ │                      │ │   (depends on REQ-003)                 │ │ │
│ │                      │ │                                          │ │ │
│ │                      │ │ [View Dependency Graph] [View Tasks]   │ │ │
│ │                      │ └────────────────────────────────────────┘ │ │
│ │                      │                                              │ │
│ │                      │ [Type your message...]        [Send] [Enter] │ │
│ └──────────────────────┴──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.3.14 Implementation Notes

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

**Spec-Driven Development Integration:**
- Store spec files in `specs/{spec_name}/` directory
- Version control specs alongside code
- Support spec references in chat with `#spec` context provider
- Enable property-based testing for correctness validation
- Chat interface allows referencing specs, tickets, code, and agents

---

## 11. Agent & Task Spawning UI

### 11.1 Agent Spawner Component

See [Implementation Details - Frontend Code Examples](./project_management_dashboard_implementation.md#25-agent-spawner-component) for complete `AgentSpawner` component implementation.

### 11.2 Task Creator Component

See [Implementation Details - Frontend Code Examples](./project_management_dashboard_implementation.md#26-task-creator-component) for complete `TaskCreator` component implementation.

---

## 11.5 Agent Goal Alignment & Progress Monitoring

### 11.5.1 Overview

**Purpose**: Monitor agent alignment with their goals and track progress on specific tasks in real-time, based on the monitoring architecture requirements.

**Requirements Documents:**
- [Monitoring Architecture Requirements](../requirements/monitoring/monitoring_architecture.md) - Guardian/Conductor phases, coherence scoring
- [Validation System Requirements](../requirements/workflows/validation_system.md) - Validation state machine and workflow
- [Fault Tolerance Requirements](../requirements/monitoring/fault_tolerance.md) - Heartbeat detection, restart, anomaly detection
- [Agent Lifecycle Management](../requirements/agents/lifecycle_management.md) - Guardian authority and intervention

**Key Features:**
- **Monitoring Loop**: Runs every 60s with Guardian Phase (per-agent) and Conductor Phase (system-wide) (REQ-MON-LOOP-001, REQ-MON-LOOP-002)
- **Guardian Alignment Scoring**: Calculates alignment_score (0-1) based on agent progress vs task goals (REQ-MON-GRD-002)
- **Trajectory Analysis**: Track alignment over time with trajectory_summary, detect needs_steering (REQ-MON-GRD-002)
- **Conductor Coherence**: System-wide coherence_score (0-1) with duplicate detection (REQ-MON-CND-001, REQ-MON-CND-002)
- **Validation State Machine**: pending → assigned → in_progress → under_review → validation_in_progress → done/needs_work (REQ-VAL-SM-001)
- **Progress Tracking**: Real-time updates on task progress with Guardian analysis
- **Discovery Tracking**: Monitor agent discoveries and workflow branching via TaskDiscovery model
- **Background Worker Integration**: Monitoring loop, Validation orchestrator, Guardian service, Alert system
- **Real-Time Intervention Delivery**: Guardian sends steering messages directly to active OpenHands conversations via `ConversationInterventionService`

### 11.5.1.1 Guardian Intervention Delivery System

**Implementation Status**: ✅ **COMPLETED**

**Architecture**:
- **Conversation Persistence**: All agent conversations are persisted with `conversation_id` and `persistence_dir` stored in `Task` model
- **Early Storage**: Conversation metadata is stored in database BEFORE execution starts, enabling Guardian to access active conversations
- **Intervention Service**: `ConversationInterventionService` resumes conversations and sends intervention messages via `Conversation.send_message()`
- **Non-Blocking**: Interventions can be sent while agents are running - OpenHands handles message queuing automatically
- **Real-Time Updates**: Intervention events are broadcast via WebSocket, updating dashboard immediately

**How It Works**:
1. **Task Execution Starts**: Worker calls `AgentExecutor.prepare_conversation()` to create conversation with persistence
2. **Early Storage**: Conversation `conversation_id` and `persistence_dir` stored in `Task` model before `conversation.run()` starts
3. **Guardian Monitoring**: Guardian analyzes agent trajectory every 60 seconds
4. **Intervention Detection**: Guardian detects `needs_steering=true` and generates `SteeringIntervention`
5. **Intervention Delivery**: `IntelligentGuardian._execute_intervention_action()`:
   - Finds agent's current running task
   - Retrieves `conversation_id` and `persistence_dir` from task
   - Resumes conversation using `ConversationInterventionService`:
     ```python
     conversation = Conversation(
         agent=agent,
         workspace=workspace,
         conversation_id=task.conversation_id,
         persistence_dir=task.persistence_dir
     )
     ```
   - Sends intervention message: `"[GUARDIAN INTERVENTION] {message}"` via `conversation.send_message()`
   - **OpenHands Feature**: Message is queued and processed asynchronously - agent continues current work and processes intervention when ready
6. **Dashboard Update**: WebSocket event `GUARDIAN_INTERVENTION` broadcasts to all connected clients
7. **Real-Time UI Update**: Dashboard shows intervention in agent detail view, trajectory analysis, and system overview

**OpenHands Message-While-Processing**: This leverages OpenHands's built-in capability where `Conversation.send_message()` can be called even while `conversation.run()` is executing in a background thread. The agent's event-driven architecture processes all queued messages, including interventions sent mid-execution. See [OpenHands examples](https://docs.openhands.dev/sdk/guides/agent-server/local-server) for demonstration of this pattern.

**Database Schema**:
- `Task.conversation_id` (String) - OpenHands conversation ID for resumption
- `Task.persistence_dir` (String) - Conversation persistence directory path

**Key Files**:
- `omoi_os/services/conversation_intervention.py` - Intervention delivery service
- `omoi_os/services/intelligent_guardian.py` - Enhanced with intervention delivery
- `omoi_os/services/agent_executor.py` - Conversation persistence setup
- `omoi_os/models/task.py` - Added `persistence_dir` field
- `migrations/versions/028_add_persistence_dir_to_tasks.py` - Database migration

**OpenHands Integration Details**:
- **Message While Running**: Uses OpenHands's built-in capability where `Conversation.send_message()` works even while `conversation.run()` is executing in a background thread
  - Demonstrated in OpenHands examples: Messages sent during agent processing are queued and processed asynchronously
  - Agent's event-driven architecture handles message queuing automatically
  - Reference: [OpenHands Local Agent Server Guide](https://docs.openhands.dev/sdk/guides/agent-server/local-server)
- **Event-Driven Processing**: Agent's `step()` method processes all events including newly added messages
  - Events include: `MessageEvent`, `ActionEvent`, `ObservationEvent`, `ConversationStateUpdateEvent`
  - Callbacks can be registered to monitor events in real-time
- **Conversation Resumption**: Uses `Conversation(conversation_id=..., persistence_dir=...)` to resume conversations
  - Workspace can change between resumptions (local → remote, different directories)
  - Conversation state persists across workspace instances
- **Pause/Resume Control**: Conversations support `conversation.pause()` and `conversation.run()` for controlled execution
  - Useful for dependency management, manual intervention, resource allocation
- **Remote Conversations**: Supports `RemoteConversation` via `Workspace(host=...)` for remote agent servers
  - Local server: `python -m openhands.agent_server --port 8001`
  - Client connects via `Workspace(host="http://localhost:8001")` → automatically becomes `RemoteConversation`
  - Event callbacks work with remote conversations via WebSocket
- **Multi-Agent Workflows**: Planning + execution agent patterns
  - `get_planning_agent()`: Read-only tools, creates implementation plans
  - `get_default_agent()`: Full editing capabilities, implements plans
  - Pattern: Planning conversation creates plan → Execution conversation implements plan

### 11.5.2 System Overview Dashboard

**Page**: `/dashboard/overview` or `/projects/:projectId/overview`

**Purpose**: Real-time monitoring and trajectory analysis across all agents and tasks.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  System Overview                      [Broadcast] [Refresh]  │
│  Real-time monitoring and trajectory analysis                 │
│  Last update: less than a minute ago                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  System Health                                        │  │
│  │  Real-time system performance metrics                 │  │
│  │                                                       │  │
│  │  Coherence Score:                                     │  │
│  │  ████████████████████░░░░  90%                      │  │
│  │                                                       │  │
│  │  Average Alignment:                                   │  │
│  │  █████████████████████░░░  92%                      │  │
│  │                                                       │  │
│  │  👤 2 Active Agents                                   │  │
│  │  📋 2 Running Tasks                                   │  │
│  │                                                       │  │
│  │  ✓ All systems nominal                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Active Phase Distribution                            │  │
│  │  Task and agent distribution across workflow phases   │  │
│  │                                                       │  │
│  │  18 tasks | 2 agents                                  │  │
│  │  Overall Progress: ███░░░░░░░░░░░░░░░░░  3/18 tasks │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Phase 1: Requirements Analysis               │    │  │
│  │  │ Progress: ██████████████████████  100%      │    │  │
│  │  │ No tasks | 0 agents | 1 completed ✓         │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Phase 2: Plan And Implementation            │    │  │
│  │  │ [ACTIVE]                                      │    │  │
│  │  │ Progress: ██░░░░░░░░░░░░░░░░░░░  13%        │    │  │
│  │  │ 1 active | 1 agents | 2 completed ✓         │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Phase 3: Validate And Document              │    │  │
│  │  │ [ACTIVE]                                      │    │  │
│  │  │ Progress: ░░░░░░░░░░░░░░░░░░░░░  0%         │    │  │
│  │  │ 1 active | 1 agents                          │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Current System Focus                                │  │
│  │  Latest conductor analysis from 1 minute ago        │  │
│  │                                                       │  │
│  │  3 agents | 90% coherent                             │  │
│  │                                                       │  │
│  │  The project is in the verification stage of its      │  │
│  │  infrastructure rollout. One agent has finished      │  │
│  │  configuring the frontend stack (ite+React+TypeScript)│  │
│  │  and is ready to mark the ticket as building-done    │  │
│  │  and create the Phase 3 validation task. A second    │  │
│  │  agent has verified the CI and development tooling   │  │
│  │  by running backend formatting, linting, tests,      │  │
│  │  installing frontend dependencies, fixing lint       │  │
│  │  errors, and successfully executing Vitest, and is   │  │
│  │  now preparing documentation for the CI test         │  │
│  │  instructions. A third agent has brought up the      │  │
│  │  FastAPI backend on port 8002, confirmed endpoint    │  │
│  │  functionality and CORS settings, and is poised to   │  │
│  │  analyze test results and produce the required test  │  │
│  │  report before final documentation. All three agents │  │
│  │  are aligned, progressing without overlap, and       │  │
│  │  moving toward completing their respective           │  │
│  │  validation tasks.                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **System Health Panel**: 
  - Coherence score (0-1) from Conductor Phase (REQ-MON-CND-001)
  - Average alignment from Guardian Phase (REQ-MON-GRD-002)
  - Active agents/tasks count from health service
  - API: `/api/v1/monitor/dashboard` (GET)
- **Phase Distribution**: Visual breakdown of tasks/agents across workflow phases
- **Current System Focus**: Narrative summary from Conductor Phase (REQ-MON-CND-003)
- **Real-Time Updates**: WebSocket-powered live updates via `MONITORING_UPDATE` events (REQ-MON-LOOP-002)

### 11.5.3 Agent Detail with Goal Alignment

**Page**: `/agents/:agentId` or Modal from Task Detail

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Agent Detail: worker-9a781fc3                    [×] [Min]  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent Header                                         │  │
│  │                                                       │  │
│  │  ID: worker-9a781fc3                                 │  │
│  │  Status: 🟢 Active                                   │  │
│  │  Type: Worker                                        │  │
│  │  Phase: PHASE_IMPLEMENTATION                         │  │
│  │                                                       │  │
│  │  Current Task: task-d7cb6ed8-...                     │  │
│  │  Ticket: ticket-0e39bcf9-...                         │  │
│  │                                                       │  │
│  │  Duration: 10m 21s                                   │  │
│  │  Priority: high                                      │  │
│  │  Complexity: 7/10                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Trajectory Analysis                          [▼]     │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │  Alignment Score Over Time                   │    │  │
│  │  │                                              │    │  │
│  │  │  100% ┤                                     │    │  │
│  │  │   75% ┤     ┌───┐                           │    │  │
│  │  │   50% ┤  ┌──┘   └─────┐        ⭐          │    │  │
│  │  │   25% ┤──┘             └─────┐              │    │  │
│  │  │    0% └──────────────────────┴──────────────│    │  │
│  │  │      0min  5min  10min  15min  20min        │    │  │
│  │  │                                              │    │  │
│  │  │  ⭐ 19 minutes ago | Alignment: 68%          │    │  │
│  │  │     Phase: implementation                     │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  Current Alignment:                                  │  │
│  │  ████████████████░░░░░░░░  68%                      │  │
│  │                                                       │  │
│  │  Phase: implementation                               │  │
│  │                                                       │  │
│  │  Legend:                                             │  │
│  │  • Alignment Score                                   │  │
│  │  • Phase Change                                      │  │
│  │  • Good (>80%)                                       │  │
│  │  • Partial (>40%)                                    │  │
│  │                                                       │  │
│  │  [View Full Trajectory] [Export Data]               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Accumulated Goal                                     │  │
│  │                                                       │  │
│  │  Analyze the LinkLite URL Shortener project and     │  │
│  │  produce a complete Phase-1 deliverable based on    │  │
│  │  the project requirements stored in the system.     │  │
│  │                                                       │  │
│  │  Specifically:                                        │  │
│  │  1. Retrieve project requirements from database.    │  │
│  │  2. Extract **all functional requirements** (96      │  │
│  │     items) and **all non-functional requirements**   │  │
│  │     (performance, usability, maintainability, etc.)  │  │
│  │     and organize them into clear, numbered lists.    │  │
│  │  3. Identify every logical system component          │  │
│  │     described in the requirements and create component │  │
│  │     requirements matrix...                           │  │
│  │                                                       │  │
│  │  [View Full Goal] [Edit Goal]                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Progress Summary                                     │  │
│  │                                                       │  │
│  │  ✓ Task started                                      │  │
│  │  ✓ Project requirements retrieved                    │  │
│  │  ✓ Requirements extracted (96 functional, 12 non-    │  │
│  │    functional)                                        │  │
│  │  ⏳ Component matrix in progress (8/15 components)   │  │
│  │  ⏳ Design document generation                        │  │
│  │  ⏳ Implementation plan                               │  │
│  │                                                       │  │
│  │  Progress: ████████░░░░░░░░░░░░  42%                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Discoveries                                          │  │
│  │                                                       │  │
│  │  🐛 Bug Found: Database connection timeout            │  │
│  │     → Spawned task: task-abc123 (Fix DB timeout)     │  │
│  │                                                       │  │
│  │  💡 Optimization: Caching layer can improve          │  │
│  │     performance by 40%                                │  │
│  │     → Spawned task: task-def456 (Add caching)        │  │
│  │                                                       │  │
│  │  [View All Discoveries]                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [Restart Task] [Live Output] [Terminate Agent]            │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Trajectory Analysis Graph**: Alignment score over time with phase changes
- **Current Alignment**: Real-time alignment percentage with visual indicator
- **Accumulated Goal**: Full task description and requirements
- **Progress Summary**: Checklist of completed/in-progress items
- **Discoveries**: Bugs, optimizations, and workflow branching events

### 11.5.4 Task Detail with Trajectory Analysis

**Page**: `/board/:projectId/:ticketId` or Modal from Board

**Enhanced Layout with Trajectory:**
```
┌─────────────────────────────────────────────────────────────┐
│  Task Details: d7cb6ed8-de3b-...              [×] [Restart] │
│  Status: done | P2 Plan And Implementation                  │
│  Duration: 10m 21s | Priority: high | Created: 22m ago     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Task Overview                                        │  │
│  │                                                       │  │
│  │  Analyze the LinkLite URL Short...                    │  │
│  │                                                       │  │
│  │  You are an AI agent in the Hephaestus orchestration  │  │
│  │  system.                                             │  │
│  │                                                       │  │
│  │  Phase 2 - Plan & Implement Backend Project Setup    │  │
│  │  Ticket: ticket-0e39bcf9-a353-4322-b374-9d9f3ead9b18│  │
│  │                                                       │  │
│  │  Instructions:                                        │  │
│  │  1. **Read the ticket** and move it from 'backlog'   │  │
│  │     → 'building'.                                    │  │
│  │  2. **Design** a complete backend infrastructure      │  │
│  │     spec:                                            │  │
│  │     - FastAPI project initialized with Poetry        │  │
│  │     - Project layout under 'backend/' with sub-      │  │
│  │       folders 'api/' 'models/'                       │  │
│  │  ...                                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Done Definition                              ✓       │  │
│  │                                                       │  │
│  │  Backend infrastructure designed + implemented.      │  │
│  │  Design at backend_infrastructure_design.md, setup   │  │
│  │  complete and verified, server runs on port 8002.    │  │
│  │  Ticket ticket-0e39bcf9-... moved to 'building-done'.│  │
│  │  Phase 3 validation task created with ticket ID.     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Trajectory Analysis                          [▼]     │  │
│  │                                                       │  │
│  │  Trajectory Analysis monitors each agent every 60     │  │
│  │  seconds. The Guardian system evaluates if agents     │  │
│  │  are aligned with their goals, tracking progress      │  │
│  │  summaries and detecting drift.                       │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │  Alignment Score Over Time                   │    │  │
│  │  │                                              │    │  │
│  │  │  100% ┤                                     │    │  │
│  │  │   75% ┤                                     │    │  │
│  │  │   50% ┤  ┌──────────────────┐      ⭐      │    │  │
│  │  │   25% ┤──┘                  └──────────────│    │  │
│  │  │    0% └─────────────────────────────────────│    │  │
│  │  │      0min  5min  10min  15min  20min        │    │  │
│  │  │                                              │    │  │
│  │  │  ⭐ 19 minutes ago | Alignment: 50%          │    │  │
│  │  │     Phase: unknown                            │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  Final Alignment:                                    │  │
│  │  ██████████████░░░░░░░░░░  50%                      │  │
│  │                                                       │  │
│  │  Phase Transitions:                                  │  │
│  │  • Started → Implementation (0m)                    │  │
│  │  • Implementation → Validation (10m)                │  │
│  │                                                       │  │
│  │  Even terminated agents remain accessible! View      │  │
│  │  trajectory analysis, logs, and full execution       │  │
│  │  history of any agent. Nothing is lost when agents   │  │
│  │  complete their work - full session replay available │  │
│  │  anytime.                                           │  │
│  │                                                       │  │
│  │  [View Full Trajectory] [View Agent Logs]           │  │
│  │  [Session Replay]                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 11.5.5 Background Worker Integration

**Background Systems** (Requirements-Based):

1. **Monitoring Architecture** (`docs/requirements/monitoring/monitoring_architecture.md`):
   - **Monitoring Loop**: Runs every 60s (REQ-MON-LOOP-001)
   - **Guardian Phase**: Per-agent analysis producing alignment_score (0-1), trajectory_summary, needs_steering (REQ-MON-GRD-002)
   - **Conductor Phase**: System-wide coherence scoring, duplicate detection, intervention decisions (REQ-MON-CND-001, REQ-MON-CND-002, REQ-MON-CND-003)
   - **Vector Search**: PGVector-based semantic similarity for duplicate detection (REQ-MON-DATA-002)
   - **API**: `/api/agent_trajectories`, `/api/system_coherence`, `/api/steer_agent`

2. **Validation System** (`docs/requirements/workflows/validation_system.md`):
   - **State Machine**: pending → assigned → in_progress → under_review → validation_in_progress → done/needs_work (REQ-VAL-SM-001)
   - **Validator Spawn**: Automatic spawn when task enters `under_review` with `validation_enabled=true` (REQ-VAL-LC-001)
   - **Review Submission**: Validator agents submit reviews via `/api/validation/give_review` (REQ-VAL-API, REQ-VAL-SEC-001)
   - **Feedback Delivery**: Transport-agnostic feedback delivery to originating agent (REQ-VAL-LC-002)
   - **Diagnosis Integration**: Auto-spawn on repeated failures or timeout (REQ-VAL-DIAG-001, REQ-VAL-DIAG-002)
   - **Memory Integration**: Persist validation outcomes and use prior memories (REQ-VAL-MEM-001, REQ-VAL-MEM-002)
   - **API**: `/api/validation/give_review`, `/api/validation/spawn_validator`, `/api/validation/send_feedback`, `/api/validation/status`

3. **Guardian Service** (`docs/requirements/agents/lifecycle_management.md`):
   - **Authority Hierarchy**: SYSTEM(5) > GUARDIAN(4) > MONITOR(3) > WATCHDOG(2) > WORKER(1) (REQ-AGENT-GUARDIAN-002)
   - **Emergency Intervention**: Task cancellation, capacity reallocation, priority override (REQ-AGENT-GUARDIAN-002)
   - **Complete Audit Trail**: GuardianAction records all interventions
   - **API**: `/api/v1/guardian/intervention/cancel-task`, `/api/v1/guardian/intervention/reallocate`, `/api/v1/guardian/intervention/override-priority`

4. **Fault Tolerance** (`docs/requirements/monitoring/fault_tolerance.md`):
   - **Heartbeat Detection**: Bidirectional heartbeats with TTL thresholds (REQ-FT-HB-001)
   - **Automatic Restart**: Escalation ladder, graceful stop, force terminate, spawn replacement (REQ-FT-AR-001, REQ-FT-AR-002)
   - **Anomaly Detection**: Composite anomaly score from latency, error rate, resource skew, queue impact (REQ-FT-AN-001)
   - **Quarantine Protocol**: Isolation, forensics, clearance by Guardian (REQ-FT-QN-001, REQ-FT-QN-002, REQ-FT-QN-003)
   - **Escalation**: SEV-1/2/3 mapping with notification matrix (REQ-FT-ES-001, REQ-FT-ES-002)

**Integration Flow:**
```
Agent Working on Task
    │
    ├─→ Agent emits heartbeat (every 30s)
    │       │
    │       └─→ EventBusService.publish(AGENT_HEARTBEAT)
    │
    ├─→ Monitoring Loop (runs every 60s per REQ-MON-LOOP-001)
    │       │
    │       ├─→ Guardian Phase (per-agent analysis per REQ-MON-GRD-001)
    │       │   │
    │       │   ├─→ Trajectory Context Builder
    │       │   │   • Recent agent logs (last 200 lines)
    │       │   │   • Prior summaries (last 10 Guardian analyses)
    │       │   │   • Agent status and resource metrics
    │       │   │   • Grace period check (min_agent_age: 60s per REQ-MON-GRD-003)
    │       │   │
    │       │   ├─→ Guardian Analysis
    │       │   │   • Calculates alignment_score (0-1) per REQ-MON-GRD-002
    │       │   │   • Generates trajectory_summary
    │       │   │   • Detects needs_steering (bool)
    │       │   │   • Suggests steering_type if needed
    │       │   │
    │       │   └─→ EventBusService.publish(
    │       │           SystemEvent(
    │       │               event_type="GUARDIAN_ANALYSIS_COMPLETE",
    │       │               entity_type="agent",
    │       │               entity_id=agent_id,
    │       │               payload={
    │       │                   "alignment_score": 0.68,
    │       │                   "trajectory_summary": "...",
    │       │                   "needs_steering": false,
    │       │                   "steering_type": null,
    │       │                   "phase": "implementation"
    │       │               }
    │       │           )
    │       │       )
    │       │
    │       └─→ Conductor Phase (system-wide aggregation per REQ-MON-CND-001)
    │           │
    │           ├─→ Coherence Scoring
    │           │   • Computes system coherence_score (0-1)
    │           │   • Based on Guardian alignment outputs
    │           │   • Thresholds: healthy (0.7), warning (0.5), critical (0.3)
    │           │
    │           ├─→ Duplicate Detection (per REQ-MON-CND-002)
    │           │   • Compares agent work descriptions via vector search
    │           │   • Detects duplicates above threshold (0.8)
    │           │   • Persists DuplicatePair records
    │           │
    │           ├─→ Actions (per REQ-MON-CND-003)
    │           │   • Suggests task termination if needed
    │           │   • Redistributes work for duplicates
    │           │   • Escalates to Guardian if critical
    │           │   • All actions auditable
    │           │
    │           └─→ EventBusService.publish(
    │                   SystemEvent(
    │                       event_type="MONITORING_UPDATE",
    │                       entity_type="system",
    │                       payload={
    │                           "coherence_score": 0.75,
    │                           "average_alignment": 0.68,
    │                           "duplicates": [...],
    │                           "interventions": [...],
    │                           "system_focus": "Narrative summary of current activities"
    │                       }
    │                   )
    │               )
    │
    ├─→ Validation System (state machine per REQ-VAL-SM-001)
    │       │
    │       ├─→ Task enters under_review state
    │       │   • Agent publishes completion signal
    │       │   • Commit SHA required (if applicable)
    │       │   • validation_iteration incremented
    │       │
    │       ├─→ Validator Spawn (REQ-VAL-LC-001)
    │       │   • IF validation_enabled=true AND state=under_review
    │       │   • Spawn validator agent via /api/validation/spawn_validator
    │       │   • Transition to validation_in_progress
    │       │   • Validator accesses workspace at Git commit
    │       │
    │       ├─→ Validation Review (REQ-VAL-API)
    │       │   • Validator calls /api/validation/give_review
    │       │   • Only validator agents allowed (REQ-VAL-SEC-001)
    │       │   • Provides validation_passed, feedback, evidence, recommendations
    │       │   • Creates ValidationReview record (REQ-VAL-DM-003)
    │       │
    │       ├─→ State Transition
    │       │   • IF validation_passed=true → done (REQ-VAL-SM-002)
    │       │     • Set review_done=true
    │       │   • IF validation_passed=false → needs_work (REQ-VAL-SM-002)
    │       │     • Set last_validation_feedback
    │       │     • Agent resumes (same session)
    │       │
    │       ├─→ Feedback Delivery (REQ-VAL-LC-002)
    │       │   • Via /api/validation/send_feedback
    │       │   • Transport-agnostic (HTTP, event bus, IPC)
    │       │
    │       ├─→ Diagnosis Integration (REQ-VAL-DIAG-001, REQ-VAL-DIAG-002)
    │       │   • IF consecutive_validation_failures >= 2
    │       │   • Spawn Diagnosis Agent automatically
    │       │   • IF validation timeout → spawn diagnosis on timeout causes
    │       │
    │       ├─→ Memory Integration (REQ-VAL-MEM-001, REQ-VAL-MEM-002)
    │       │   • Persist validation outcomes to Memory System
    │       │   • Validators retrieve prior validation memories
    │       │
    │       └─→ EventBusService.publish(
    │               SystemEvent(
    │                   event_type="VALIDATION_REVIEW_SUBMITTED",
    │                   entity_type="task",
    │                   entity_id=task_id,
    │                   payload={
    │                       "validation_passed": true,
    │                       "iteration": 1,
    │                       "validator_agent_id": "..."
    │                   }
    │               )
    │           )
    │
    └─→ Alert System (monitors for issues)
            │
            ├─→ Checks alignment thresholds
            ├─→ Monitors for drift (>20% drop)
            ├─→ Detects stalled agents (>5min no progress)
            │
            └─→ EventBusService.publish(
                    SystemEvent(
                        event_type="AGENT_ALERT",
                        entity_type="agent",
                        payload={
                            "alert_type": "alignment_drift",
                            "severity": "warning",
                            "message": "Alignment dropped to 45%"
                        }
                    )
                )
```

**WebSocket Events** (per REQ-MON-LOOP-002, REQ-VAL-API):

```typescript
// Monitoring events (per REQ-MON-LOOP-002)
MONITORING_UPDATE → {
    cycle_id: string,
    timestamp: string,
    agents: Array<{
        agent_id: string,
        alignment_score: number,  // 0-1 per REQ-MON-GRD-002
        trajectory_summary: string,
        needs_steering: boolean,
        steering_type: string | null
    }>,
    systemCoherence: number,  // 0-1 per REQ-MON-CND-001
    duplicates: Array<{
        agent1_id: string,
        agent2_id: string,
        similarity_score: number,
        work_description: string | null
    }>,
    interventions: Array<{
        action_type: string,
        target_agent_ids: string[],
        reason: string
    }>
}

STEERING_ISSUED → {
    agent_id: string,
    steering_type: string,
    message: string,
    timestamp: string
}

// Validation events (per REQ-VAL-API)
VALIDATION_STARTED → {
    task_id: string,
    iteration: number,
    timestamp: string
}

VALIDATION_REVIEW_SUBMITTED → {
    task_id: string,
    iteration: number,
    passed: boolean,
    validator_agent_id: string,
    timestamp: string
}

VALIDATION_PASSED → {
    task_id: string,
    iteration: number,
    timestamp: string
}

VALIDATION_FAILED → {
    task_id: string,
    iteration: number,
    feedback: string,
    timestamp: string
}

// Guardian intervention events
GUARDIAN_INTERVENTION → {
    action_id: string,
    action_type: "cancel_task" | "reallocate" | "override_priority" | "steering_message",
    target_entity: string,
    authority_level: number,  // 4=GUARDIAN, 5=SYSTEM
    reason: string,
    initiated_by: string,
    timestamp: string,
    conversation_id?: string,  // OpenHands conversation ID for steering messages
    intervention_message?: string  // Steering message sent to agent
}

STEERING_ISSUED → {
    agent_id: string,
    conversation_id: string,
    steering_type: "guidance" | "correction" | "emergency",
    message: string,
    alignment_score: number,  // 0-1 alignment score when intervention triggered
    trajectory_summary: string,
    timestamp: string,
    delivered: boolean  // Whether message was successfully delivered to conversation
}
```

### 11.5.6 Agent Discovery & Workflow Branching

**Overview**: Agents autonomously discover issues, opportunities, and missing requirements during execution, automatically spawning new tasks and creating tickets to address them. This creates a dynamic, adaptive workflow where the system evolves based on agent discoveries.

**Discovery Types:**
- **Bug Discovery**: Agent finds a bug, spawns new task to fix it
- **Optimization Discovery**: Agent identifies optimization opportunity
- **Missing Requirement**: Agent discovers missing requirement
- **Dependency Issue**: Agent finds unhandled dependency
- **Security Concern**: Agent identifies security issue

**Agent-Driven Task Creation**:
- **MCP Tools**: Agents use `create_ticket` MCP tool to create tickets during execution
- **DiscoveryService**: Agents call `DiscoveryService.record_discovery_and_branch()` to:
  - Record what was discovered (bug, optimization, etc.)
  - Automatically spawn new tasks linked to the discovery
  - Track workflow branching via `TaskDiscovery` model
- **Automatic Linking**: Spawned tasks are automatically linked to source task via `parent_task_id` and `TaskDiscovery.spawned_task_ids`

**Real-Time Updates**:
- When agent creates ticket → `TICKET_CREATED` WebSocket event → Dashboard updates Kanban board
- When agent spawns task → `TASK_CREATED` WebSocket event → Dashboard updates dependency graph
- When agent links tasks → `TASK_DEPENDENCY_UPDATED` WebSocket event → Dashboard updates graph edges

**Discovery UI Component:**
```
┌─────────────────────────────────────────────────────────────┐
│  Discoveries (3)                                     [▼]     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  🐛 Bug Found                                         │  │
│  │  Database connection timeout occurs after 5 minutes  │  │
│  │                                                       │  │
│  │  Discovered by: worker-9a781fc3                      │  │
│  │  Discovered at: 2 hours ago                          │  │
│  │                                                       │  │
│  │  Spawned Task: task-abc123                           │  │
│  │  Status: assigned                                    │  │
│  │                                                       │  │
│  │  [View Task] [View Details]                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  💡 Optimization Opportunity                         │  │
│  │  Caching layer can improve performance by 40%        │  │
│  │                                                       │  │
│  │  Discovered by: worker-def456                        │  │
│  │  Discovered at: 1 hour ago                           │  │
│  │                                                       │  │
│  │  Spawned Task: task-def456                           │  │
│  │  Status: completed ✓                                 │  │
│  │                                                       │  │
│  │  [View Task] [View Details]                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ⚠️  Missing Requirement                              │  │
│  │  API rate limiting not specified in requirements     │  │
│  │                                                       │  │
│  │  Discovered by: worker-ghi789                        │  │
│  │  Discovered at: 30 minutes ago                       │  │
│  │                                                       │  │
│  │  Spawned Task: task-ghi789                           │  │
│  │  Status: in_progress                                 │  │
│  │                                                       │  │
│  │  [View Task] [View Details]                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [View All Discoveries]                                     │
└─────────────────────────────────────────────────────────────┘
```

**Discovery API Endpoints:**

See [API Specifications - Discovery API](./project_management_dashboard_api.md#10-discovery-api) for complete endpoint specifications.

**Existing Discovery Service** (`omoi_os/services/discovery.py`):
- ✅ `record_discovery()` - Record discovery with type and description
- ✅ `record_discovery_and_branch()` - Record discovery and spawn task automatically
- ✅ `get_discoveries_by_task()` - Get all discoveries for a task
- ✅ `get_discoveries_by_type()` - Get discoveries by type (bug, optimization, etc.)
- ✅ `get_workflow_graph()` - Build workflow graph showing all discoveries and branches
- ✅ `mark_discovery_resolved()` - Mark discovery as resolved

### 11.5.7 Agent Workflow: Start & Let Discover

**Core Workflow Philosophy**: Agents are autonomous actors that create, link, and manage their own work. The dashboard provides real-time visibility into this dynamic, agent-driven workflow.

**Agent-Driven Workflow Characteristics**:
1. **Autonomous Creation**: Agents create tickets and tasks as they discover needs
2. **Automatic Linking**: Agents identify and link related work items through dependency analysis
3. **Real-Time Updates**: All agent actions trigger immediate WebSocket events
4. **Adaptive Branching**: Workflow branches dynamically based on agent discoveries
5. **Guardian Steering**: Guardian monitors and intervenes in real-time when agents drift or need guidance

**Simplified Agent Spawning Flow:**

```
1. User Action: "Start Agent"
   │
   ├─→ Option A: Spawn for Specific Task
   │   │
   │   ├─→ Select task from board/graph
   │   ├─→ Click "Assign Agent" or "Spawn Agent"
   │   ├─→ Agent automatically assigned to task
   │   └─→ Agent starts working immediately
   │
   ├─→ Option B: Spawn for Project/Phase
   │   │
   │   ├─→ Select project and phase
   │   ├─→ Click "Spawn Agent" button
   │   ├─→ Agent registers and waits for task assignment
   │   └─→ Orchestrator assigns task automatically
   │
   └─→ Option C: Spawn with Discovery Mode
       │
       ├─→ Enable "Allow Discoveries" option
       ├─→ Agent works on task and can spawn new tasks
       └─→ Discoveries tracked automatically
           │
           ▼
2. Agent Working
   │
   ├─→ Agent executes task instructions
   ├─→ Agent emits heartbeat (every 30s per REQ-ALM-002)
   ├─→ Monitoring Loop runs Guardian Phase (every 60s per REQ-MON-LOOP-001)
   ├─→ Guardian calculates alignment_score (0-1) per REQ-MON-GRD-002
   ├─→ Guardian generates trajectory_summary and detects needs_steering
   ├─→ Conductor Phase computes coherence_score and detects duplicates
   │
   ├─→ Agent Discovery (if enabled)
   │   │
   │   ├─→ Agent identifies bug/optimization/issue
   │   ├─→ Creates TaskDiscovery record via DiscoveryService
   │   ├─→ Optionally spawns new task automatically (via `record_discovery_and_branch()`)
   │   ├─→ Agent may create ticket via MCP tool if clarification needed
   │   ├─→ Agent links tasks via dependency detection
   │   └─→ EventBusService.publish(DISCOVERY_MADE) → Dashboard updates in real-time
   │
   └─→ Agent Completion
       │
       ├─→ Agent publishes completion signal with commit SHA (if applicable)
       ├─→ Task transitions to under_review (REQ-VAL-SM-001)
       ├─→ IF validation_enabled=true → Validator spawns (REQ-VAL-LC-001)
       ├─→ Validation state machine executes (REQ-VAL-SM-001)
       ├─→ IF validation_passed → done, ELSE → needs_work → in_progress (loop)
       ├─→ Guardian trajectory analysis saved to database
       ├─→ Memory System stores validation outcomes (REQ-VAL-MEM-001)
       └─→ Agent remains accessible for replay even after termination
           │
           ▼
3. Monitoring & Management
   │
   ├─→ System Overview Dashboard shows real-time status
   ├─→ Agent Detail view shows trajectory analysis
   ├─→ Task Detail shows alignment over time
   ├─→ Discoveries panel shows all workflow branching
   │
   ├─→ Background Workers:
   │   │
   │   ├─→ Guardian: Monitors alignment, detects drift
   │   ├─→ Validation: Validates completed tasks
   │   ├─→ Alert: Sends notifications for issues
   │   └─→ Conductor: Orchestrates system focus
   │
   └─→ User can:
       ├─→ View trajectory analysis for any agent
       ├─→ See alignment score over time
       ├─→ Review discoveries and spawned tasks
       ├─→ Restart or terminate agents if needed
       └─→ Replay agent sessions after completion
```

**UI: Simple Agent Spawn Button:**
```
┌─────────────────────────────────────────────────────────────┐
│  Kanban Board                                  [Spawn Agent] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Backlog] [Phase 1] [Phase 2] [Done]                      │
│                                                              │
│  ┌──┐  ┌──┐      ┌──┐                                       │
│  │T1│  │T2│      │T3│  ← Ticket Cards                       │
│  └──┘  └──┘      └──┘                                       │
│                                                              │
│  Click "Spawn Agent" →                                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Spawn Agent                                         │  │
│  │                                                       │  │
│  │  Project: auth-system                                │  │
│  │                                                       │  │
│  │  Assignment:                                         │  │
│  │  ○ Auto-assign next available task                   │  │
│  │  ● Assign to specific task                           │  │
│  │    [Select Task: task-abc123 ▼]                      │  │
│  │                                                       │  │
│  │  Options:                                            │  │
│  │  ☑ Allow discoveries (auto-spawn tasks)             │  │
│  │  ☑ Enable trajectory tracking                        │  │
│  │  ☐ Enable validation checks                          │  │
│  │                                                       │  │
│  │  Agent Type: [Worker ▼]                              │  │
│  │  Phase: [PHASE_IMPLEMENTATION ▼]                     │  │
│  │                                                       │  │
│  │  [Cancel] [Spawn Agent]                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
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

See [API Specifications - WebSocket Events](./project_management_dashboard_api.md#11-websocket-events) for complete event type specifications including:
- Board Events (TICKET_CREATED, TICKET_UPDATED, etc.)
- Graph Events (TASK_CREATED, TASK_ASSIGNED, etc.)
- Agent Events (AGENT_REGISTERED, AGENT_STATUS_CHANGED, etc.)
- GitHub Events (GITHUB_ISSUE_CREATED, COMMIT_PUSHED, etc.)
- Monitoring Events (MONITORING_UPDATE, STEERING_ISSUED, etc.)
- Validation Events (VALIDATION_STARTED, VALIDATION_REVIEW_SUBMITTED, etc.)
- Guardian Intervention Events
- Discovery Events
- Project Exploration Events

---

## 15. Frontend State Management

See [Implementation Details - Frontend Code Examples](./project_management_dashboard_implementation.md#24-zustand-store-example) for complete Zustand store and WebSocket hook implementations.

---

## 16. Security Considerations

See [Implementation Details - Security Implementation](./project_management_dashboard_implementation.md#5-security-implementation) for complete security implementation including:
- WebSocket Authentication (JWT token validation)
- GitHub Webhook Security (signature verification)

---

## 17. Performance Considerations

See [Implementation Details - Performance Optimization](./project_management_dashboard_implementation.md#6-performance-optimization) for complete performance optimization strategies including:
- WebSocket Scalability (connection management, filtering)
- Graph Rendering (virtual rendering, lazy loading, clustering)
- Board Performance (pagination, virtual scrolling, debouncing)
- Frontend Performance (code splitting, memoization)
- Backend Performance (query optimization, caching)

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

### 19.1 Existing Endpoints (Ready to Use)

See [Existing Codebase Mapping](#existing-codebase-mapping) above for complete list of implemented endpoints.

### 19.2 New Endpoints Needed

See [API Specifications](./project_management_dashboard_api.md) for complete specifications of all new endpoints needed:
- [Commits API](./project_management_dashboard_api.md#3-commits-api)
- [Projects API](./project_management_dashboard_api.md#8-projects-api)
- [GitHub Integration API](./project_management_dashboard_api.md#4-github-integration-api)
- [Audit API](./project_management_dashboard_api.md#5-audit-api)
- [Statistics API](./project_management_dashboard_api.md#6-statistics-api)
- [Search API](./project_management_dashboard_api.md#7-search-api)
- [Project Exploration API](./project_management_dashboard_api.md#9-project-exploration-api)
- [Discovery API](./project_management_dashboard_api.md#10-discovery-api)
- [Comments API](./project_management_dashboard_api.md#12-comments-api)
- [Notifications API](./project_management_dashboard_api.md#13-notifications-api)
- [User Management API](./project_management_dashboard_api.md#14-user-management-api)
- [Time Tracking API](./project_management_dashboard_api.md#15-time-tracking-api)
- [Cost Tracking API](./project_management_dashboard_api.md#16-cost-tracking-api)
- [Export/Import API](./project_management_dashboard_api.md#17-exportimport-api)
- [File Attachments API](./project_management_dashboard_api.md#18-file-attachments-api)

---

## 20. Next Steps

### Immediate Actions:
1. ✅ **Graph API** (`omoi_os/api/routes/graph.py`) - **ALREADY IMPLEMENTED**
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

**Existing Backend**: `TicketComment` model exists with support for agent-authored comments, mentions, and attachments.

**Frontend Components Needed:**
- `CommentThread.tsx` - Threaded comment display
- `CommentEditor.tsx` - Rich text comment editor
- `MentionAutocomplete.tsx` - @mention autocomplete
- `AttachmentUploader.tsx` - File attachment UI

**API Endpoints:**

See [API Specifications - Comments API](./project_management_dashboard_api.md#12-comments-api) for complete endpoint specifications.

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

See [API Specifications - Notifications API](./project_management_dashboard_api.md#13-notifications-api) for complete endpoint specifications.

### 23.2 Alert Rules Configuration UI

**Component**: `AlertRulesEditor.tsx`
- Visual editor for alert rules (YAML-based)
- Test alert rules
- Enable/disable rules
- View alert history

---

## 24. User Management & Permissions

### 24.1 Authentication

**Current State**: ✅ **Full authentication system implemented** (see updated [User Journey](../user_journey.md) and [Page Flow](../page_flow.md))

**Implemented Features**:
- Email/password registration with verification
- OAuth login (GitHub/GitLab)
- Password reset flow
- API key generation for programmatic access
- Session management
- Multi-tenant organizations with RBAC
- Organization resource limits (max agents, runtime hours)

**UI Pages Required**:
- `/register` - Email registration form
- `/login` - Email login form
- `/login/oauth` - OAuth redirect
- `/verify-email` - Email verification
- `/forgot-password` - Password reset request
- `/reset-password` - Password reset confirmation
- `/settings/api-keys` - API key management
- `/organizations` - Organization list and management

**See**: [User Journey - Phase 1: Onboarding & Authentication](../user_journey.md#phase-1-onboarding--first-project-setup) for complete authentication flows.

**Needed:**
- User login/logout
- JWT token management
- Session management
- Password reset
- OAuth integration (GitHub, Google)

**API Endpoints:**

See [API Specifications - User Management API](./project_management_dashboard_api.md#14-user-management-api) for complete endpoint specifications.

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

See [API Specifications - Time Tracking API](./project_management_dashboard_api.md#15-time-tracking-api) for complete endpoint specifications.

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

See [API Specifications - Cost Tracking API](./project_management_dashboard_api.md#16-cost-tracking-api) for complete endpoint specifications.

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

See [API Specifications - Export/Import API](./project_management_dashboard_api.md#17-exportimport-api) for complete endpoint specifications.

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

See [API Specifications - File Attachments API](./project_management_dashboard_api.md#18-file-attachments-api) for complete endpoint specifications.

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

See [Implementation Details - Transaction Management](./project_management_dashboard_implementation.md#7-transaction-management) for complete transaction safety patterns and code examples.

### 35.2 Error Handling UI

See [Implementation Details - Error Handling](./project_management_dashboard_implementation.md#8-error-handling) for error handling UI components and backend error response formats.

---

## 36. Performance Optimization

See [Implementation Details - Performance Optimization](./project_management_dashboard_implementation.md#6-performance-optimization) for complete performance optimization strategies including frontend, backend, and WebSocket optimizations.

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

**Key Differentiators**:
1. **Agent-Driven Workflow**: Agents autonomously create tickets, spawn tasks, and link work items - the system adapts dynamically to agent discoveries
2. **Real-Time Guardian Interventions**: Guardian sends steering messages directly to active agent conversations, enabling live course correction without interrupting agent execution
3. **Complete Traceability**: Full audit trail from ticket → task → agent → commit → code changes, with real-time updates via WebSocket
4. **Adaptive Workflow Branching**: System automatically branches workflow based on agent discoveries (bugs, optimizations, missing requirements)

**Recent Implementation Highlights**:
- ✅ **Guardian Intervention Delivery**: Real-time steering messages sent to active OpenHands conversations via `ConversationInterventionService`
- ✅ **Conversation Persistence**: All conversations persisted with `conversation_id` and `persistence_dir` stored in `Task` model for intervention delivery
- ✅ **Agent-Driven Creation**: Agents use MCP tools (`create_ticket`) to create tickets and `DiscoveryService` to spawn tasks during execution
- ✅ **Memory System**: Agents use MCP tools (`save_memory`, `find_memory`) to share knowledge and learn from each other's discoveries in real-time
- ✅ **Discovery Tracking**: Complete workflow branching history via `TaskDiscovery` model, tracking WHY workflows branch and WHAT agents discovered
- ✅ **Real-Time Updates**: WebSocket infrastructure enables live dashboard updates for all agent actions (ticket creation, task spawning, linking, interventions)

**Modifications Made**:
1. **Database Schema**: Added `persistence_dir` field to `Task` model (migration `028_add_persistence_dir_to_tasks.py`)
2. **AgentExecutor**: Enhanced with `prepare_conversation()` method to enable conversation persistence before execution
3. **ConversationInterventionService**: New service for resuming conversations and sending Guardian intervention messages
4. **IntelligentGuardian**: Updated `_execute_intervention_action()` to deliver interventions via OpenHands conversations
5. **Worker Integration**: Updated both `execute_task()` and `execute_task_with_retry()` to store conversation metadata early

**How Agent-Driven Workflow Works**:
- Agents create tickets via MCP tools when they discover new requirements or need clarification
- Agents spawn tasks via `DiscoveryService.record_discovery_and_branch()` when they find bugs, optimizations, or missing requirements
- Agents use `find_memory` MCP tool to search past memories when encountering errors or needing implementation details
- Agents use `save_memory` MCP tool to share discoveries, solutions, and learnings for other agents to find
- Agents automatically link tasks through dependency detection and discovery tracking
- All agent actions trigger WebSocket events → Dashboard updates in real-time
- Guardian monitors agent trajectories and sends intervention messages directly to active conversations when agents drift or need guidance
- **OpenHands Message-While-Processing**: Guardian interventions use OpenHands's built-in capability to send messages to running conversations - agents process interventions asynchronously without interrupting current work

**OpenHands Capabilities Leveraged**:
- **Message While Running**: `Conversation.send_message()` works even while `conversation.run()` is executing ([OpenHands examples](https://docs.openhands.dev/sdk/guides/agent-server/local-server))
- **Pause/Resume**: Conversations support `conversation.pause()` and `conversation.run()` for controlled execution
- **Multi-Agent Workflows**: Planning agent + execution agent patterns (planning creates plan, execution implements)
- **Remote Conversations**: Support for `RemoteConversation` via `Workspace(host=...)` for distributed agent execution

**Workspace Isolation System** (✅ Implemented):
- Each agent gets isolated workspace automatically
- Git-backed workspaces with branch per agent
- Workspace inheritance from parent agents
- Automatic merge conflict resolution
- Workspace checkpoint commits for validation
- Workspace retention and cleanup policies

**UI Pages Required**:
- `/agents/:agentId/workspace` - Workspace detail view
- `/workspaces` - Workspace list view
- Workspace tabs: Commits, Merge Conflicts, Settings

**See**: [User Journey - Workspace Management](../user_journey.md#workspace-management) and [Page Flow - Flow 7](../page_flow.md#flow-7-workspace-management--isolation) for complete workspace flows.
- **Event-Driven Architecture**: Agent's `step()` processes all queued events including newly added messages

The WebSocket infrastructure and Guardian intervention system provide the foundation for real-time, agent-driven project management with live steering and adaptive workflow branching!

