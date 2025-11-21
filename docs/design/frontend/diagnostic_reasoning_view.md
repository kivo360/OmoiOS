# Diagnostic Reasoning View

**Created**: 2025-01-30
**Status**: Design Document
**Purpose**: Unified diagnostic view for understanding WHY actions happened (task spawning, ticket connections, agent decisions)
**Related**: [Hephaestus Workflow Enhancements](../implementation/workflows/hephaestus_workflow_enhancements.md), [Task Discovery Model](../../omoi_os/models/task_discovery.py)

---

## Overview

The **Diagnostic Reasoning View** provides a unified interface for understanding the complete reasoning chain behind agent actions. It answers questions like:

- **Why was this task spawned?** → Shows TaskDiscovery record with context
- **Why are these tickets connected?** → Shows blocking relationship reasoning
- **Why was this task linked to that ticket?** → Shows agent decision rationale
- **What was the agent thinking?** → Shows memory entries, decisions, and reasoning

Inspired by **Hephaestus patterns** where workflows are "interconnected problem-solving graphs" and agents discover work rather than execute predefined plans.

---

## Page Structure

### Route: `/diagnostic/:entityType/:entityId`

**Entity Types:**
- `ticket` - Diagnostic view for a ticket
- `task` - Diagnostic view for a task
- `agent` - Diagnostic view for an agent's actions

**Example Routes:**
- `/diagnostic/ticket/33cb642c-ebb9-46d3-b021-...`
- `/diagnostic/task/task-123`
- `/diagnostic/agent/agent-456`

---

## UI Components

### 1. Reasoning Chain Visualization

**Component**: `ReasoningChain.tsx`

**Visualization**: Interactive graph showing the complete reasoning chain

```
┌─────────────────────────────────────────────────────────┐
│  Reasoning Chain for Ticket: Infrastructure Setup      │
│                                                         │
│  [Timeline View] [Graph View] [Details View]           │
└─────────────────────────────────────────────────────────┘

Timeline View:
───────────────────────────────────────────────────────────
Oct 30, 10:23 AM  Agent worker-1 created ticket
                   └─ Reason: "Infrastructure needed for auth system"
                   
Oct 30, 10:25 AM  Task task-001 spawned
                   └─ Discovery: "bug" - "Found missing Redis dependency"
                   └─ Source: Task task-000 (Phase 2 Implementation)
                   └─ Metadata: {"evidence": "import redis failed", "file": "src/auth/cache.py"}
                   
Oct 30, 10:26 AM  Task task-001 linked to ticket
                   └─ Reason: "Task addresses infrastructure requirement"
                   └─ Agent Decision: "This task implements the Redis cache setup needed by auth"
                   
Oct 30, 10:28 AM  Ticket ticket-002 blocked by ticket-001
                   └─ Reason: "Auth system requires Redis cache to be operational"
                   └─ Agent Decision: "Cannot proceed with auth until cache is ready"
                   └─ Evidence: {"dependency_type": "infrastructure", "required_for": "auth"}
```

**Graph View**:
```
                    ┌──────────────┐
                    │ Ticket-001   │
                    │ Infrastructure│
                    └──────┬───────┘
                           │ blocked_by
                           │ reason: "Auth requires Redis"
                           ▼
                    ┌──────────────┐
                    │ Ticket-002   │
                    │ Auth System  │
                    └──────┬───────┘
                           │ linked_to
                           │ reason: "Implements auth requirement"
                           ▼
                    ┌──────────────┐
                    │ Task-001     │
                    │ Redis Setup  │
                    └──────┬───────┘
                           │ spawned_from
                           │ discovery: "bug" - "Missing Redis"
                           ▼
                    ┌──────────────┐
                    │ Task-000     │
                    │ Phase 2 Impl │
                    └──────────────┘
```

---

### 2. Discovery Details Panel

**Component**: `DiscoveryDetails.tsx`

Shows TaskDiscovery records with full context:

```typescript
interface DiscoveryDetails {
  id: string;
  source_task_id: string;
  source_task_title: string;
  discovery_type: "bug" | "optimization" | "missing_requirement" | ...;
  description: string;
  discovered_at: string;
  spawned_task_ids: string[];
  priority_boost: boolean;
  resolution_status: "open" | "resolved" | "invalid";
  discovery_metadata: {
    evidence?: string;
    context?: string;
    files_involved?: string[];
    error_message?: string;
    code_snippet?: string;
  };
}
```

**UI Example**:
```
┌─────────────────────────────────────────────────────────┐
│  Discovery: Bug Found                                  │
│                                                         │
│  Source Task: task-000 - "Implement Auth Cache"        │
│  Type: bug                                             │
│  Discovered: Oct 30, 10:25 AM                          │
│                                                         │
│  Description:                                          │
│  Found missing Redis dependency when attempting to    │
│  import redis module. The auth cache implementation    │
│  requires Redis to be set up first.                    │
│                                                         │
│  Evidence:                                             │
│  • File: src/auth/cache.py:12                          │
│  • Error: ModuleNotFoundError: No module named 'redis' │
│  • Code: import redis                                  │
│                                                         │
│  Spawned Tasks:                                        │
│  • task-001: "Setup Redis Infrastructure"             │
│                                                         │
│  Priority Boost: ✓ Yes                                │
│  Status: open                                          │
│                                                         │
│  [View Source Task] [View Spawned Tasks] [Mark Resolved]│
└─────────────────────────────────────────────────────────┘
```

---

### 3. Blocking Relationship Reasoning

**Component**: `BlockingReasoning.tsx`

Shows WHY tickets are connected:

```typescript
interface BlockingRelationship {
  blocking_ticket_id: string;
  blocking_ticket_title: string;
  blocked_ticket_id: string;
  blocked_ticket_title: string;
  reason: string;
  created_by_agent_id: string;
  created_at: string;
  relationship_metadata: {
    dependency_type?: "infrastructure" | "component" | "data" | "api";
    required_for?: string[];
    evidence?: string;
    agent_reasoning?: string;
  };
}
```

**UI Example**:
```
┌─────────────────────────────────────────────────────────┐
│  Blocking Relationship                                 │
│                                                         │
│  Ticket "Auth System" is blocked by                    │
│  Ticket "Redis Cache Setup"                            │
│                                                         │
│  Reason:                                               │
│  Auth system requires Redis cache to be operational     │
│  before authentication can be implemented. The cache  │
│  is used for session storage and token validation.     │
│                                                         │
│  Dependency Type: infrastructure                       │
│  Required For: ["session_storage", "token_validation"] │
│                                                         │
│  Agent Reasoning:                                      │
│  "Cannot proceed with auth until cache is ready.       │
│   Auth endpoints depend on Redis for session           │
│   management and token caching."                       │
│                                                         │
│  Created: Oct 30, 10:28 AM                            │
│  By: Agent worker-1                                    │
│                                                         │
│  Evidence:                                             │
│  • Code dependency: src/auth/cache.py imports redis    │
│  • Design doc: "Auth requires Redis for sessions"      │
│                                                         │
│  [View Blocking Ticket] [View Blocked Ticket] [Remove]│
└─────────────────────────────────────────────────────────┘
```

---

### 4. Task-Ticket Link Reasoning

**Component**: `TaskLinkReasoning.tsx`

Shows WHY a task was linked to a ticket:

```typescript
interface TaskTicketLink {
  task_id: string;
  task_title: string;
  ticket_id: string;
  ticket_title: string;
  link_reason: string;
  linked_by_agent_id: string;
  linked_at: string;
  link_metadata: {
    agent_reasoning?: string;
    discovery_id?: string;
    automatic?: boolean;
    evidence?: string;
  };
}
```

**UI Example**:
```
┌─────────────────────────────────────────────────────────┐
│  Task-Ticket Link                                      │
│                                                         │
│  Task "Setup Redis Infrastructure"                    │
│  is linked to                                          │
│  Ticket "Infrastructure: Redis Cache Setup"           │
│                                                         │
│  Link Reason:                                          │
│  Task addresses infrastructure requirement identified  │
│  in ticket. This task implements the Redis cache setup │
│  needed by the authentication system.                  │
│                                                         │
│  Agent Reasoning:                                      │
│  "This task implements the Redis cache setup needed    │
│   by auth. The ticket describes the infrastructure     │
│   requirement, and this task fulfills that need."      │
│                                                         │
│  Linked: Oct 30, 10:26 AM                            │
│  By: Agent worker-1                                    │
│  Method: automatic (via discovery)                    │
│                                                         │
│  Related Discovery: discovery-001                     │
│  [View Discovery]                                      │
│                                                         │
│  [View Task] [View Ticket] [Unlink]                   │
└─────────────────────────────────────────────────────────┘
```

---

### 5. Agent Memory & Decisions

**Component**: `AgentMemoryView.tsx`

Shows agent's memory entries and decisions related to this entity:

```typescript
interface MemoryEntry {
  id: string;
  memory_type: "decision" | "discovery" | "error_fix" | "learning";
  content: string;
  agent_id: string;
  created_at: string;
  related_files?: string[];
  tags?: string[];
}
```

**UI Example**:
```
┌─────────────────────────────────────────────────────────┐
│  Agent Memory & Decisions                              │
│                                                         │
│  Filter: [All Types ▼] [All Agents ▼]                 │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │ decision - Oct 30, 10:26 AM                      │ │
│  │ Agent: worker-1                                  │ │
│  │                                                  │ │
│  │ Chose Redis over Memcached for pub/sub support. │ │
│  │ Redis provides better integration with Python   │ │
│  │ and supports pub/sub patterns needed for         │ │
│  │ real-time updates.                               │ │
│  │                                                  │ │
│  │ Related Files: src/auth/cache.py                │ │
│  │ Tags: infrastructure, decision                  │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │ discovery - Oct 30, 10:25 AM                    │ │
│  │ Agent: worker-1                                  │ │
│  │                                                  │ │
│  │ Found missing Redis dependency. Auth cache       │ │
│  │ implementation requires Redis to be set up first.│ │
│  │                                                  │ │
│  │ Related Files: src/auth/cache.py                │ │
│  │ Tags: bug, infrastructure                        │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### GET `/api/v1/diagnostic/:entityType/:entityId`

Returns complete diagnostic information for an entity.

**Response**:
```json
{
  "entity_type": "ticket",
  "entity_id": "33cb642c-ebb9-46d3-b021-...",
  "entity_title": "Infrastructure: Redis Cache Setup",
  
  "reasoning_chain": {
    "discoveries": [
      {
        "id": "discovery-001",
        "source_task_id": "task-000",
        "discovery_type": "bug",
        "description": "Found missing Redis dependency",
        "discovered_at": "2025-10-30T10:25:00Z",
        "spawned_task_ids": ["task-001"],
        "discovery_metadata": {
          "evidence": "import redis failed",
          "file": "src/auth/cache.py"
        }
      }
    ],
    "task_links": [
      {
        "task_id": "task-001",
        "task_title": "Setup Redis Infrastructure",
        "link_reason": "Task addresses infrastructure requirement",
        "linked_at": "2025-10-30T10:26:00Z",
        "link_metadata": {
          "agent_reasoning": "This task implements the Redis cache setup needed by auth",
          "discovery_id": "discovery-001"
        }
      }
    ],
    "blocking_relationships": [
      {
        "blocking_ticket_id": "ticket-001",
        "blocked_ticket_id": "ticket-002",
        "reason": "Auth system requires Redis cache to be operational",
        "created_at": "2025-10-30T10:28:00Z",
        "relationship_metadata": {
          "dependency_type": "infrastructure",
          "required_for": ["session_storage", "token_validation"],
          "agent_reasoning": "Cannot proceed with auth until cache is ready"
        }
      }
    ]
  },
  
  "agent_memories": [
    {
      "id": "memory-001",
      "memory_type": "decision",
      "content": "Chose Redis over Memcached for pub/sub support",
      "agent_id": "worker-1",
      "created_at": "2025-10-30T10:26:00Z",
      "related_files": ["src/auth/cache.py"]
    }
  ],
  
  "timeline": [
    {
      "timestamp": "2025-10-30T10:23:00Z",
      "event_type": "ticket_created",
      "description": "Ticket created by agent worker-1",
      "reason": "Infrastructure needed for auth system"
    },
    {
      "timestamp": "2025-10-30T10:25:00Z",
      "event_type": "discovery_made",
      "description": "Discovery: bug - Missing Redis dependency",
      "discovery_id": "discovery-001"
    },
    {
      "timestamp": "2025-10-30T10:26:00Z",
      "event_type": "task_linked",
      "description": "Task task-001 linked to ticket",
      "reason": "Task addresses infrastructure requirement"
    }
  ]
}
```

---

## Hephaestus Patterns

### How Hephaestus Handles Diagnostic Reasoning

**Key Principle**: "Workflows are interconnected problem-solving graphs, not linear pipelines."

**Hephaestus Approach**:
1. **Discovery Tracking**: Every workflow branch is tracked via discovery records
2. **Reasoning Context**: Agents provide reasoning when spawning tasks
3. **Memory Integration**: Decisions and rationale stored in memory system
4. **Graph Visualization**: Shows WHY workflows branch, not just WHAT happened

**OmoiOS Implementation**:
- ✅ `TaskDiscovery` model tracks WHY tasks spawned
- ✅ `DiscoveryService` records context and metadata
- ✅ Memory system stores agent decisions
- ⚠️ **Missing**: Reasoning fields for ticket blocking relationships
- ⚠️ **Missing**: Reasoning fields for task-ticket links
- ⚠️ **Missing**: Unified diagnostic view UI

---

## Integration Points

### 1. Task Discovery Integration
- Diagnostic view pulls from `TaskDiscovery` records
- Shows discovery type, description, metadata
- Links to source task and spawned tasks

### 2. Ticket History Integration
- Pulls blocking relationship history from `TicketHistory`
- Shows when relationships were created/modified
- Includes agent reasoning if available

### 3. Memory System Integration
- Searches memory entries related to entity
- Filters by memory type (decision, discovery, etc.)
- Shows agent reasoning and context

### 4. Guardian Actions Integration
- Shows Guardian interventions related to entity
- Includes intervention reasoning
- Links to trajectory analysis

---

## User Flows

### Flow 1: Diagnose Why Task Was Spawned

```
User clicks on task in Kanban board
  ↓
Clicks "Why was this created?" button
  ↓
Navigates to /diagnostic/task/task-001
  ↓
Sees Discovery Details panel
  ↓
Views source task that made discovery
  ↓
Sees discovery metadata (evidence, context)
  ↓
Views spawned tasks from this discovery
```

### Flow 2: Diagnose Why Tickets Are Connected

```
User views dependency graph
  ↓
Clicks on edge between two tickets
  ↓
Navigates to /diagnostic/ticket/ticket-002
  ↓
Sees Blocking Relationship Reasoning panel
  ↓
Views reason, dependency type, agent reasoning
  ↓
Sees evidence and related tasks
```

### Flow 3: View Complete Reasoning Chain

```
User opens ticket detail view
  ↓
Clicks "View Reasoning Chain" button
  ↓
Navigates to /diagnostic/ticket/ticket-001
  ↓
Sees complete timeline of events
  ↓
Views graph visualization
  ↓
Drills down into specific discoveries/links
```

---

## Related Documents

- [Database Schema Changes](./diagnostic_reasoning_schema.md) - Proposed schema additions
- [Hephaestus Workflow Enhancements](../implementation/workflows/hephaestus_workflow_enhancements.md) - Discovery tracking implementation
- [Task Discovery Model](../../omoi_os/models/task_discovery.py) - Model definition
- [Memory System](../../omoi_os/services/memory.py) - Agent memory storage

