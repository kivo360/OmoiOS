# Project Management Dashboard - API Specifications

**Created**: 2025-01-30  
**Status**: API Design Document  
**Purpose**: Complete API endpoint specifications for the project management dashboard

**Related Documents:**
- [Main Design Document](./project_management_dashboard.md) - UI/UX design and user flows
- [Implementation Details](./project_management_dashboard_implementation.md) - Code examples and technical implementation

---

## Table of Contents

1. [Existing Endpoints](#1-existing-endpoints)
2. [Board API](#2-board-api)
3. [Commits API](#3-commits-api)
4. [GitHub Integration API](#4-github-integration-api)
5. [Audit API](#5-audit-api)
6. [Statistics API](#6-statistics-api)
7. [Search API](#7-search-api)
8. [Projects API](#8-projects-api)
9. [Project Exploration API](#9-project-exploration-api)
10. [Discovery API](#10-discovery-api)
11. [WebSocket Events](#11-websocket-events)
12. [Comments API](#12-comments-api)
13. [Notifications API](#13-notifications-api)
14. [User Management API](#14-user-management-api)
15. [Time Tracking API](#15-time-tracking-api)
16. [Cost Tracking API](#16-cost-tracking-api)
17. [Export/Import API](#17-exportimport-api)
18. [File Attachments API](#18-file-attachments-api)
19. [Tasks API (Additional)](#19-tasks-api-additional)

---

## 1. Existing Endpoints

See [Main Design Document - Existing Codebase Mapping](./project_management_dashboard.md#existing-codebase-mapping) for complete list of implemented endpoints.

**Summary:**
- ✅ Board API (`omoi_os/api/routes/board.py`)
- ✅ Tasks API (`omoi_os/api/routes/tasks.py`)
- ✅ Tickets API (`omoi_os/api/routes/tickets.py`)
- ✅ Agents API (`omoi_os/api/routes/agents.py`)
- ✅ Graph API (`omoi_os/api/routes/graph.py`)
- ✅ WebSocket API (`omoi_os/api/routes/events.py`)
- ✅ Guardian API (`omoi_os/api/routes/guardian.py`)
- ✅ Alerts API (`omoi_os/api/routes/alerts.py`)
- ✅ Memory API (`omoi_os/api/routes/memory.py`)
- ✅ Quality API (`omoi_os/api/routes/quality.py`)
- ✅ Costs API (`omoi_os/api/routes/costs.py`)
- ✅ Validation API (`omoi_os/api/routes/validation.py`)
- ✅ Collaboration API (`omoi_os/api/routes/collaboration.py`)

---

## 2. Board API

**File**: `omoi_os/api/routes/board.py`

### Existing Endpoints

- ✅ `GET /api/v1/board/view` - Get complete Kanban board view
- ✅ `POST /api/v1/board/move` - Move ticket to different column
- ✅ `GET /api/v1/board/stats` - Get column statistics
- ✅ `GET /api/v1/board/wip-violations` - Check WIP limit violations
- ✅ `POST /api/v1/board/auto-transition/{ticket_id}` - Auto-transition ticket
- ✅ `GET /api/v1/board/column/{phase_id}` - Get column for phase

See [Main Design Document](./project_management_dashboard.md#3-kanban-board-implementation) for usage details.

---

## 3. Commits API

**File**: `omoi_os/api/routes/commits.py` (to be created)

### Endpoints

#### `GET /api/v1/commits/{commit_sha}`

Get commit details including diff.

**Parameters:**
- `commit_sha` (path): Full commit SHA

**Response:**
```json
{
  "commit_sha": "02979f61095b7d...",
  "commit_message": "Merge agent work",
  "author": "Ido Levi",
  "date": "2025-10-30T12:47:00Z",
  "summary": {
    "files": 17,
    "insertions": 2255,
    "deletions": 0
  },
  "files": [
    {
      "path": "backend/core/database.py",
      "additions": 35,
      "deletions": 0,
      "changes": 35,
      "status": "added"
    }
  ],
  "ticket_id": "ticket-123",
  "agent_id": "agent-456",
  "diff_url": "https://github.com/owner/repo/commit/02979f6..."
}
```

#### `GET /api/v1/commits/{commit_sha}/diff`

Get commit diff (full or for specific file).

**Parameters:**
- `commit_sha` (path): Full commit SHA
- `file_path` (query, optional): Specific file path

**Response:**
```json
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
            {"type": "added", "content": "+new line"}
          ]
        }
      ]
    }
  ]
}
```

#### `GET /api/v1/tickets/{ticket_id}/commits`

Get all commits linked to a ticket.

**Parameters:**
- `ticket_id` (path): Ticket ID

**Response:**
```json
[
  {
    "commit_sha": "...",
    "commit_message": "...",
    "author": "...",
    "date": "...",
    "summary": {"files": 5, "insertions": 100, "deletions": 20},
    "agent_id": "agent-123"
  }
]
```

#### `POST /api/v1/tickets/{ticket_id}/commits/link`

Manually link a commit to a ticket.

**Request Body:**
```json
{
  "commit_sha": "02979f61095b7d...",
  "agent_id": "agent-456"
}
```

**Response:**
```json
{
  "commit_sha": "...",
  "ticket_id": "ticket-123",
  "linked_at": "2025-01-30T12:00:00Z"
}
```

#### `GET /api/v1/agents/{agent_id}/commits`

Get all commits made by an agent.

**Parameters:**
- `agent_id` (path): Agent ID

**Response:**
```json
[
  {
    "commit_sha": "...",
    "commit_message": "...",
    "ticket_id": "ticket-123",
    "date": "...",
    "summary": {"files": 5, "insertions": 100, "deletions": 20}
  }
]
```

---

## 4. GitHub Integration API

**File**: `omoi_os/api/routes/github.py` (to be created)

### Endpoints

#### `POST /api/v1/github/repositories/connect`

Connect a GitHub repository.

**Request Body:**
```json
{
  "owner": "owner",
  "name": "repo",
  "access_token": "ghp_..."
}
```

**Response:**
```json
{
  "repository_id": "repo-123",
  "webhook_url": "https://api.github.com/repos/owner/repo/hooks/123"
}
```

#### `POST /api/v1/webhooks/github`

Receive GitHub webhook events.

**Headers:**
- `X-GitHub-Event`: Event type (e.g., "push", "pull_request", "issues")
- `X-Hub-Signature-256`: Webhook signature for verification

**Request Body:**
GitHub webhook payload (varies by event type)

**Response:**
```json
{
  "status": "processed"
}
```

#### `GET /api/v1/github/repositories`

List connected repositories.

**Response:**
```json
[
  {
    "id": "repo-123",
    "owner": "owner",
    "name": "repo",
    "webhook_status": "active",
    "connected_at": "2025-01-30T12:00:00Z"
  }
]
```

#### `GET /api/v1/github/repositories/{repo_id}/issues`

List GitHub issues for a repository.

**Response:**
```json
[
  {
    "number": 123,
    "title": "Issue title",
    "state": "open",
    "linked_ticket_id": "ticket-456"
  }
]
```

#### `POST /api/v1/github/repositories/{repo_id}/create-issue`

Create a GitHub issue from a ticket.

**Request Body:**
```json
{
  "ticket_id": "ticket-123",
  "title": "Issue title",
  "body": "Issue description"
}
```

**Response:**
```json
{
  "issue_number": 123,
  "url": "https://github.com/owner/repo/issues/123"
}
```

---

## 5. Audit API

**File**: `omoi_os/api/routes/audit.py` (to be created)

### Endpoints

#### `GET /api/v1/audit/tickets/{ticket_id}`

Get complete audit trail for a ticket.

**Response:**
```json
[
  {
    "id": "audit-123",
    "timestamp": "2025-01-30T12:00:00Z",
    "type": "commit",
    "agent_id": "agent-456",
    "agent_name": "worker-abc",
    "description": "Commit linked to ticket",
    "details": {
      "commit_sha": "...",
      "files_changed": 5,
      "insertions": 100,
      "deletions": 20
    }
  }
]
```

#### `GET /api/v1/audit/agents/{agent_id}`

Get all actions by an agent.

**Response:**
```json
[
  {
    "id": "audit-123",
    "timestamp": "2025-01-30T12:00:00Z",
    "type": "commit",
    "ticket_id": "ticket-123",
    "description": "Made commit",
    "details": {...}
  }
]
```

#### `GET /api/v1/audit/projects/{project_id}`

Get audit trail for entire project.

**Query Parameters:**
- `start_date` (optional): Filter start date
- `end_date` (optional): Filter end date

**Response:**
```json
[
  {
    "id": "audit-123",
    "timestamp": "2025-01-30T12:00:00Z",
    "type": "ticket_created",
    "entity_id": "ticket-123",
    "description": "Ticket created",
    "details": {...}
  }
]
```

---

## 6. Statistics API

**File**: `omoi_os/api/routes/statistics.py` (to be created)

### Endpoints

#### `GET /api/v1/statistics/projects/{project_id}/overview`

Get comprehensive project statistics.

**Response:**
```json
{
  "tickets": {
    "total": 100,
    "by_status": {"open": 20, "in_progress": 10, "done": 70},
    "by_priority": {"CRITICAL": 5, "HIGH": 15, "MEDIUM": 50, "LOW": 30},
    "blocked_count": 3,
    "completion_rate": 0.7
  },
  "agents": {
    "active": 5,
    "tasks_completed": 150,
    "average_completion_time": "2h 30m"
  },
  "commits": {
    "total": 200,
    "total_lines_changed": 50000,
    "files_changed": 500
  },
  "health": {
    "wip_violations": 2,
    "dependency_blockers": 3,
    "agent_health_status": "healthy"
  }
}
```

#### `GET /api/v1/statistics/tickets`

Get ticket statistics.

**Query Parameters:**
- `project_id` (optional): Filter by project

**Response:**
```json
{
  "total": 100,
  "by_status": {...},
  "by_priority": {...},
  "average_time_in_phase": {
    "PHASE_INITIAL": "1h",
    "PHASE_IMPLEMENTATION": "4h",
    "PHASE_INTEGRATION": "2h"
  }
}
```

#### `GET /api/v1/statistics/agents`

Get agent performance statistics.

**Query Parameters:**
- `project_id` (optional): Filter by project

**Response:**
```json
{
  "active_agents": 5,
  "tasks_completed_per_agent": 30,
  "commits_per_agent": 40,
  "lines_changed_per_agent": 10000,
  "average_task_completion_time": "2h 30m"
}
```

#### `GET /api/v1/statistics/commits`

Get code change statistics.

**Query Parameters:**
- `project_id` (optional): Filter by project
- `agent_id` (optional): Filter by agent

**Response:**
```json
{
  "total_commits": 200,
  "total_lines_changed": 50000,
  "files_changed": 500,
  "commits_per_ticket": 2,
  "most_active_files": [
    {"path": "backend/main.py", "commits": 20, "changes": 500}
  ]
}
```

---

## 7. Search API

**File**: `omoi_os/api/routes/search.py` (to be created)

### Endpoints

#### `GET /api/v1/search`

Global search across all entities.

**Query Parameters:**
- `q` (required): Search query
- `types` (optional): Comma-separated entity types (ticket,task,commit,agent)
- `project_id` (optional): Filter by project

**Response:**
```json
{
  "tickets": [...],
  "tasks": [...],
  "commits": [...],
  "agents": [...],
  "total": 42
}
```

#### `GET /api/v1/search/tickets`

Search tickets with filters.

**Query Parameters:**
- `q` (required): Search query
- `filters` (optional, JSON): Additional filters

**Response:**
```json
[
  {
    "id": "ticket-123",
    "title": "Implement feature",
    "status": "in_progress",
    "priority": "HIGH"
  }
]
```

#### `GET /api/v1/search/commits`

Search commits with filters.

**Query Parameters:**
- `q` (required): Search query
- `agent_id` (optional): Filter by agent
- `ticket_id` (optional): Filter by ticket
- `date_from` (optional): Filter start date
- `date_to` (optional): Filter end date

**Response:**
```json
[
  {
    "commit_sha": "...",
    "commit_message": "...",
    "author": "...",
    "date": "...",
    "ticket_id": "ticket-123",
    "agent_id": "agent-456"
  }
]
```

---

## 8. Projects API

**File**: `omoi_os/api/routes/projects.py` (to be created)

### Endpoints

#### `GET /api/v1/projects`

List all projects.

**Response:**
```json
[
  {
    "id": "project-123",
    "name": "auth-system",
    "description": "Authentication system",
    "github_owner": "owner",
    "github_repo": "repo",
    "default_phase_id": "PHASE_IMPLEMENTATION",
    "created_at": "2025-01-30T12:00:00Z"
  }
]
```

#### `POST /api/v1/projects`

Create a new project.

**Request Body:**
```json
{
  "name": "auth-system",
  "description": "Authentication system",
  "github_owner": "owner",
  "github_repo": "repo",
  "default_phase_id": "PHASE_IMPLEMENTATION"
}
```

**Response:**
```json
{
  "id": "project-123",
  "name": "auth-system",
  ...
}
```

#### `GET /api/v1/projects/{project_id}`

Get project details.

**Response:**
```json
{
  "id": "project-123",
  "name": "auth-system",
  "description": "...",
  "github_connection": {
    "owner": "owner",
    "repo": "repo",
    "webhook_status": "active"
  },
  "stats": {
    "tickets": 24,
    "done": 12,
    "agents": 5,
    "cost": 1200
  }
}
```

#### `POST /api/v1/projects/{project_id}/spawn-agent`

Spawn a new agent for this project.

**Request Body:**
```json
{
  "agent_type": "worker",
  "phase_id": "PHASE_IMPLEMENTATION",
  "capabilities": ["python", "fastapi"],
  "capacity": 1
}
```

**Response:**
```json
{
  "id": "agent-123",
  "agent_type": "worker",
  "phase_id": "PHASE_IMPLEMENTATION",
  ...
}
```

#### `POST /api/v1/projects/{project_id}/create-ticket`

Create a ticket in this project.

**Request Body:**
```json
{
  "title": "Implement feature",
  "description": "...",
  "priority": "HIGH",
  "phase_id": "PHASE_IMPLEMENTATION"
}
```

**Response:**
```json
{
  "id": "ticket-123",
  "title": "Implement feature",
  ...
}
```

---

## 9. Project Exploration API

**File**: `omoi_os/api/routes/project_exploration.py` (to be created)

### Endpoints

#### `POST /api/v1/projects/explore/start`

Start new project exploration session.

**Request Body:**
```json
{
  "initial_idea": "I want to create an authentication system with plugins",
  "user_id": "user-123"
}
```

**Response:**
```json
{
  "exploration_id": "explore-123",
  "current_stage": "exploring",
  "initial_idea": "...",
  "questions": [
    {
      "id": "q-1",
      "question_text": "What authentication methods should be supported?",
      "question_category": "technical"
    }
  ]
}
```

#### `POST /api/v1/projects/explore/{exploration_id}/answer`

Answer a question and get next questions.

**Request Body:**
```json
{
  "question_id": "q-1",
  "answer_text": "OAuth2, JWT, and API keys"
}
```

**Response:**
```json
{
  "exploration_id": "explore-123",
  "current_stage": "exploring",
  "questions": [...],
  "ready_for_requirements": false
}
```

#### `POST /api/v1/projects/explore/{exploration_id}/generate-requirements`

Generate requirements document from exploration.

**Response:**
```json
{
  "document_id": "req-123",
  "title": "Authentication System Requirements",
  "status": "draft",
  "total_requirements": 23,
  "content": "..."
}
```

#### `POST /api/v1/projects/explore/{exploration_id}/refine-requirements`

Refine requirements based on user feedback.

**Request Body:**
```json
{
  "feedback": "Add multi-tenant support",
  "changes": ["Add REQ-024 for multi-tenant isolation"]
}
```

**Response:**
```json
{
  "document_id": "req-124",
  "version": 2,
  "status": "pending_review",
  ...
}
```

#### `POST /api/v1/projects/explore/{exploration_id}/generate-design`

Generate design document from approved requirements.

**Response:**
```json
{
  "document_id": "design-123",
  "title": "Authentication System Design",
  "status": "draft",
  "sections": ["Architecture Overview", "Component Design", ...],
  "content": "..."
}
```

#### `POST /api/v1/documents/{document_id}/approve`

Approve a document.

**Request Body:**
```json
{
  "user_id": "user-123"
}
```

**Response:**
```json
{
  "document_id": "req-123",
  "status": "approved",
  "approved_by": "user-123",
  "approved_at": "2025-01-30T12:00:00Z"
}
```

#### `POST /api/v1/documents/{document_id}/reject`

Reject a document with feedback.

**Request Body:**
```json
{
  "rejection_reason": "Missing security requirements"
}
```

**Response:**
```json
{
  "document_id": "req-123",
  "status": "rejected",
  "rejection_reason": "..."
}
```

#### `GET /api/v1/documents/{document_id}/versions`

Get version history for a document.

**Response:**
```json
[
  {
    "id": "req-124",
    "version": 2,
    "status": "approved",
    "created_at": "2025-01-30T12:00:00Z"
  },
  {
    "id": "req-123",
    "version": 1,
    "status": "superseded",
    "created_at": "2025-01-29T10:00:00Z"
  }
]
```

#### `POST /api/v1/projects/explore/{exploration_id}/generate-spec`

Generate spec from approved requirements and design.

**Request Body:**
```json
{
  "spec_name": "authentication-system"
}
```

**Response:**
```json
{
  "spec_id": "spec-123",
  "spec_name": "authentication-system",
  "status": "requirements_complete",
  "requirements_file_path": "specs/authentication-system/requirements.md",
  "design_file_path": "specs/authentication-system/design.md",
  "tasks_file_path": "specs/authentication-system/tasks.md"
}
```

#### `POST /api/v1/specs/{spec_id}/extract-properties`

Extract testable properties from requirements.

**Response:**
```json
[
  {
    "id": "prop-1",
    "property_statement": "For any user with valid credentials, authentication succeeds",
    "property_type": "behavior",
    "test_generated": true
  }
]
```

#### `POST /api/v1/specs/{spec_id}/generate-tasks`

Create tickets/tasks from project tasks stored in database.

**Response:**
```json
[
  {
    "id": "ticket-123",
    "title": "Set up authentication service infrastructure",
    "priority": "HIGH",
    "phase_id": "PHASE_INITIAL"
  }
]
```

#### `POST /api/v1/projects/explore/{exploration_id}/initialize-project`

Create project and initial tickets from approved design.

**Request Body:**
```json
{
  "project_name": "auth-system",
  "create_tickets": true
}
```

**Response:**
```json
{
  "project_id": "project-123",
  "tickets_created": 15,
  "tasks_created": 45
}
```

---

## 10. Discovery API

**File**: `omoi_os/api/routes/discoveries.py` (to be created)

**Note**: DiscoveryService exists at `omoi_os/services/discovery.py` and TaskDiscovery model exists at `omoi_os/models/task_discovery.py`. These endpoints need to be implemented.

### Endpoints

#### `GET /api/v1/agents/{agent_id}/discoveries`

Get all discoveries made by an agent.

**Response:**
```json
[
  {
    "id": "discovery-123",
    "type": "bug",
    "description": "Database connection timeout occurs after 5 minutes",
    "discovered_at": "2025-01-30T12:00:00Z",
    "task_id": "task-456",
    "spawned_task_ids": ["task-789"],
    "resolution_status": "in_progress"
  }
]
```

#### `GET /api/v1/tasks/{task_id}/discoveries`

Get all discoveries from a task.

**Query Parameters:**
- `resolution_status` (optional): Filter by status (open, in_progress, resolved, invalid)

**Response:**
```json
[
  {
    "id": "discovery-123",
    "type": "optimization",
    "description": "Caching layer can improve performance by 40%",
    "discovered_at": "2025-01-30T12:00:00Z",
    "agent_id": "agent-456",
    "spawned_task_ids": ["task-789"],
    "resolution_status": "resolved"
  }
]
```

#### `POST /api/v1/discoveries/{discovery_id}/spawn-task`

Spawn a new task from a discovery.

**Request Body:**
```json
{
  "description": "Fix database connection timeout",
  "priority": "HIGH",
  "phase_id": "PHASE_IMPLEMENTATION"
}
```

**Response:**
```json
{
  "id": "task-789",
  "description": "Fix database connection timeout",
  "discovery_id": "discovery-123",
  "status": "pending"
}
```

---

## 11. WebSocket Events

**Endpoint**: `WS /api/v1/ws/events`

See [Main Design Document - WebSocket Integration](./project_management_dashboard.md#5-websocket-integration) for connection details.

### Event Types

#### Board Events

```typescript
TICKET_CREATED → {
  ticket_id: string,
  title: string,
  phase_id: string,
  status: string
}

TICKET_UPDATED → {
  ticket_id: string,
  changes: {
    phase_id?: string,
    status?: string
  }
}

TICKET_BLOCKED → {
  ticket_id: string,
  blocked_reason: string
}

TICKET_UNBLOCKED → {
  ticket_id: string
}

BOARD_WIP_VIOLATION → {
  column_id: string,
  current_count: number,
  wip_limit: number
}

BOARD_TICKET_MOVED → {
  ticket_id: string,
  from_column: string,
  to_column: string
}
```

#### Graph Events

```typescript
TASK_CREATED → {
  task_id: string,
  ticket_id: string,
  dependencies: string[]
}

TASK_ASSIGNED → {
  task_id: string,
  agent_id: string
}

TASK_COMPLETED → {
  task_id: string,
  result: any
}

TASK_FAILED → {
  task_id: string,
  error_message: string
}

TASK_DEPENDENCY_ADDED → {
  task_id: string,
  depends_on_task_id: string
}
```

#### Agent Events

```typescript
AGENT_REGISTERED → {
  agent_id: string,
  agent_type: string,
  phase_id: string
}

AGENT_STATUS_CHANGED → {
  agent_id: string,
  old_status: string,
  new_status: string
}

AGENT_HEARTBEAT → {
  agent_id: string,
  health_metrics: any
}
```

#### GitHub Events

```typescript
GITHUB_ISSUE_CREATED → {
  issue_number: number,
  repo: string,
  title: string
}

GITHUB_PR_OPENED → {
  pr_number: number,
  repo: string,
  linked_task_id: string
}

GITHUB_PR_MERGED → {
  pr_number: number,
  commit_sha: string,
  linked_task_id: string
}

COMMIT_PUSHED → {
  commit_sha: string,
  message: string,
  author: string,
  files_changed: number,
  insertions: number,
  deletions: number
}

COMMIT_LINKED → {
  commit_sha: string,
  ticket_id: string,
  agent_id: string
}

COMMIT_COMMENTED → {
  commit_sha: string,
  comment: string,
  ticket_id: string
}
```

#### Monitoring Events

```typescript
MONITORING_UPDATE → {
  cycle_id: string,
  timestamp: string,
  agents: Array<{
    agent_id: string,
    alignment_score: number,  // 0-1
    trajectory_summary: string,
    needs_steering: boolean,
    steering_type: string | null
  }>,
  systemCoherence: number,  // 0-1
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
```

#### Validation Events

```typescript
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
```

#### Guardian Intervention Events

```typescript
GUARDIAN_INTERVENTION → {
  action_id: string,
  action_type: "cancel_task" | "reallocate" | "override_priority",
  target_entity: string,
  authority_level: number,  // 4=GUARDIAN, 5=SYSTEM
  reason: string,
  initiated_by: string,
  timestamp: string
}
```

#### Discovery Events

```typescript
DISCOVERY_MADE → {
  discovery_id: string,
  type: "bug" | "optimization" | "missing_requirement" | "dependency_issue" | "security_concern",
  task_id: string,
  agent_id: string,
  description: string,
  spawned_task_id: string | null
}
```

#### Project Exploration Events

```typescript
EXPLORATION_STARTED → {
  exploration_id: string,
  initial_idea: string
}

QUESTION_GENERATED → {
  exploration_id: string,
  question_id: string,
  question_text: string
}

QUESTION_ANSWERED → {
  exploration_id: string,
  question_id: string,
  answer_text: string
}

REQUIREMENTS_GENERATED → {
  exploration_id: string,
  document_id: string
}

REQUIREMENTS_APPROVED → {
  exploration_id: string,
  document_id: string
}

DESIGN_GENERATED → {
  exploration_id: string,
  document_id: string
}

DESIGN_APPROVED → {
  exploration_id: string,
  document_id: string
}

PROJECT_INITIALIZED → {
  exploration_id: string,
  project_id: string
}
```

---

## 12. Comments API

**File**: `omoi_os/api/routes/comments.py` (to be created)

**Note**: `TicketComment` model exists with support for agent-authored comments, mentions, and attachments.

### Endpoints

#### `GET /api/v1/tickets/{ticket_id}/comments`

Get all comments for a ticket.

**Response:**
```json
[
  {
    "id": "comment-123",
    "ticket_id": "ticket-123",
    "author_id": "agent-456",
    "author_name": "worker-abc",
    "content": "Comment text",
    "comment_type": "general",
    "mentions": ["agent-789"],
    "attachments": ["file://path/to/file"],
    "created_at": "2025-01-30T12:00:00Z",
    "edited_at": null
  }
]
```

#### `POST /api/v1/tickets/{ticket_id}/comments`

Add comment to ticket.

**Request Body:**
```json
{
  "content": "Comment text",
  "comment_type": "general",
  "mentions": ["agent-789"],
  "attachments": []
}
```

**Response:**
```json
{
  "id": "comment-123",
  "ticket_id": "ticket-123",
  "content": "Comment text",
  ...
}
```

#### `PUT /api/v1/comments/{comment_id}`

Edit existing comment.

**Request Body:**
```json
{
  "content": "Updated comment text"
}
```

**Response:**
```json
{
  "id": "comment-123",
  "content": "Updated comment text",
  "edited_at": "2025-01-30T13:00:00Z"
}
```

#### `DELETE /api/v1/comments/{comment_id}`

Delete comment.

**Response:**
```json
{
  "status": "deleted"
}
```

---

## 13. Notifications API

**File**: `omoi_os/api/routes/notifications.py` (to be created)

**Note**: Alert rules exist in `config/alert_rules/`.

### Endpoints

#### `GET /api/v1/notifications`

Get user notifications.

**Query Parameters:**
- `unread_only` (optional, default: false): Filter unread only
- `limit` (optional, default: 50): Limit results

**Response:**
```json
[
  {
    "id": "notif-123",
    "type": "ticket_blocked",
    "title": "Ticket blocked",
    "message": "Ticket ticket-123 is blocked",
    "entity_type": "ticket",
    "entity_id": "ticket-123",
    "read": false,
    "created_at": "2025-01-30T12:00:00Z"
  }
]
```

#### `POST /api/v1/notifications/{notification_id}/read`

Mark notification as read.

**Response:**
```json
{
  "id": "notif-123",
  "read": true,
  "read_at": "2025-01-30T13:00:00Z"
}
```

#### `POST /api/v1/notifications/read-all`

Mark all notifications as read.

**Response:**
```json
{
  "marked_read": 10
}
```

---

## 14. User Management API

**File**: `omoi_os/api/routes/auth.py` (to be created)

**Note**: Currently no general user authentication system (only agent-scoped MCP permissions).

### Endpoints

#### `POST /api/v1/auth/login`

User login.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "name": "User Name",
    "role": "admin"
  }
}
```

#### `POST /api/v1/auth/logout`

User logout.

**Response:**
```json
{
  "status": "logged_out"
}
```

#### `GET /api/v1/auth/me`

Get current authenticated user.

**Response:**
```json
{
  "id": "user-123",
  "email": "user@example.com",
  "name": "User Name",
  "role": "admin",
  "permissions": ["create_tickets", "spawn_agents", "view_costs"]
}
```

---

## 15. Time Tracking API

**File**: `omoi_os/api/routes/time_tracking.py` (to be created)

**Note**: Tasks have `started_at`, `completed_at` timestamps.

### Endpoints

#### `GET /api/v1/tickets/{ticket_id}/time`

Get time tracking data for ticket.

**Response:**
```json
{
  "ticket_id": "ticket-123",
  "total_time": "5h 30m",
  "time_by_phase": {
    "PHASE_INITIAL": "1h",
    "PHASE_IMPLEMENTATION": "3h 30m",
    "PHASE_INTEGRATION": "1h"
  },
  "agent_time": [
    {
      "agent_id": "agent-456",
      "time_spent": "3h",
      "tasks_completed": 5
    }
  ]
}
```

#### `GET /api/v1/agents/{agent_id}/time`

Get time tracking data for agent.

**Response:**
```json
{
  "agent_id": "agent-456",
  "total_time": "20h",
  "time_by_phase": {
    "PHASE_IMPLEMENTATION": "15h",
    "PHASE_INTEGRATION": "5h"
  },
  "tasks_completed": 10,
  "average_task_time": "2h"
}
```

---

## 16. Cost Tracking API

**File**: `omoi_os/api/routes/costs.py` (already exists)

**Note**: `CostRecord` model tracks LLM API costs.

### Additional Endpoints Needed

#### `GET /api/v1/costs/projects/{project_id}`

Get cost summary for project.

**Response:**
```json
{
  "project_id": "project-123",
  "total_cost": 1234.56,
  "cost_by_agent": [
    {
      "agent_id": "agent-456",
      "cost": 500.00,
      "tasks_completed": 10
    }
  ],
  "cost_by_phase": {
    "PHASE_IMPLEMENTATION": 800.00,
    "PHASE_INTEGRATION": 434.56
  },
  "forecast": {
    "estimated_monthly": 5000.00,
    "budget_remaining": 3765.44
  }
}
```

#### `GET /api/v1/costs/agents/{agent_id}`

Get cost summary for agent.

**Response:**
```json
{
  "agent_id": "agent-456",
  "total_cost": 500.00,
  "cost_per_task": 50.00,
  "cost_trend": "increasing",
  "recent_costs": [
    {
      "date": "2025-01-30",
      "cost": 50.00
    }
  ]
}
```

#### `GET /api/v1/costs/forecast`

Get cost forecast based on queue depth.

**Response:**
```json
{
  "estimated_monthly": 5000.00,
  "estimated_weekly": 1250.00,
  "queue_depth": 50,
  "average_cost_per_task": 25.00,
  "budget_status": "within_budget"
}
```

---

## 17. Export/Import API

**File**: `omoi_os/api/routes/export.py` (to be created)

### Endpoints

#### `GET /api/v1/export/tickets`

Export tickets.

**Query Parameters:**
- `project_id` (required): Project ID
- `format` (optional, default: "csv"): Export format (csv, json, pdf, excel)
- `filters` (optional, JSON): Additional filters

**Response:**
Streaming response with exported file

#### `GET /api/v1/export/audit-trail`

Export audit trail.

**Query Parameters:**
- `ticket_id` (optional): Filter by ticket
- `agent_id` (optional): Filter by agent
- `project_id` (optional): Filter by project
- `format` (optional, default: "json"): Export format

**Response:**
Streaming response with exported file

---

## 18. File Attachments API

**File**: `omoi_os/api/routes/attachments.py` (to be created)

**Note**: `TicketComment.attachments` (JSONB field) exists.

### Endpoints

#### `POST /api/v1/tickets/{ticket_id}/attachments`

Upload file attachment.

**Request:**
- Multipart form data with `file` field

**Response:**
```json
{
  "id": "attachment-123",
  "ticket_id": "ticket-123",
  "filename": "document.pdf",
  "file_path": "attachments/ticket-123/document.pdf",
  "file_size": 1024000,
  "content_type": "application/pdf",
  "uploaded_at": "2025-01-30T12:00:00Z"
}
```

#### `GET /api/v1/attachments/{attachment_id}`

Download attachment.

**Response:**
File download stream

#### `DELETE /api/v1/attachments/{attachment_id}`

Delete attachment.

**Response:**
```json
{
  "status": "deleted"
}
```

---

## 19. Tasks API (Additional)

**File**: `omoi_os/api/routes/tasks.py` (existing file, new endpoints)

### Endpoints

#### `POST /api/v1/tickets/{ticket_id}/tasks`

Create a new task linked to a ticket.

**Request Body:**
```json
{
  "description": "Task description",
  "priority": "MEDIUM",
  "phase_id": "PHASE_IMPLEMENTATION",
  "task_type": "implementation",
  "dependencies": {
    "depends_on": ["task-123"]
  }
}
```

**Response:**
```json
{
  "id": "task-789",
  "ticket_id": "ticket-123",
  "description": "Task description",
  "status": "pending",
  "priority": "MEDIUM",
  "created_at": "2025-01-30T12:00:00Z"
}
```

#### `PUT /api/v1/tasks/{task_id}`

Update task details.

**Request Body:**
```json
{
  "description": "Updated description",
  "priority": "HIGH",
  "status": "in_progress"
}
```

**Response:**
```json
{
  "id": "task-789",
  "description": "Updated description",
  ...
}
```

---

## Next Steps

See [Main Design Document - Next Steps](./project_management_dashboard.md#20-next-steps) for implementation priorities.

