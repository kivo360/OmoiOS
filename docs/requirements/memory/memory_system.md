# Agent Memory System Requirements

## Document Overview

This document defines normative requirements for the server-based Agent Memory System. It specifies memory taxonomy, data models, hybrid search behavior, ACE workflow responsibilities, APIs, and non-functional constraints. The implementation is expected to use PostgreSQL with pgvector for semantic search, but all search requirements MUST be expressed in terms of a generic vector search capability.

**Parent Document**: [Multi-Agent Orchestration Requirements](../multi_agent_orchestration.md)

---

## 1. Goals

#### REQ-MEM-GOAL-001
THE SYSTEM SHALL provide a centralized, server-based memory service that allows agents to store, retrieve, and evolve project knowledge across sessions and workflows.

#### REQ-MEM-GOAL-002
THE SYSTEM SHALL support automatic capture of task outcomes into structured memories, with minimal additional burden on agents.

#### REQ-MEM-GOAL-003
THE SYSTEM SHALL enable hybrid search (semantic + keyword) over stored memories, with filtering by project, files, tags, time, and type.

---

## 2. Memory Taxonomy

#### REQ-MEM-TAX-001: Memory Types
Memories MUST be classified into one of the following types:
- `error_fix`
- `discovery`
- `decision`
- `learning`
- `warning`
- `codebase_knowledge`

#### REQ-MEM-TAX-002: Type Safety
THE SYSTEM SHALL enforce memory_type via a strict enumeration, rejecting or flagging any memory that does not conform to the allowed set.

---

## 3. Data Model Requirements

> Implementation note: The following requirements assume PostgreSQL storage with pgvector and tsvector support. However, any relational store with equivalent capabilities MAY be used, provided all constraints are preserved.

### 3.1 Project

#### REQ-MEM-DM-001
Each memory MUST belong to exactly one `project`. Projects SHALL include at minimum:
- `id` (UUID),
- `name` (unique per installation),
- `description` (optional),
- repository metadata (e.g., `repository_url`, `current_branch`),
- `settings` (JSON),
- `created_at`, `updated_at`.

### 3.2 Memory

#### REQ-MEM-DM-002
The `memories` entity SHALL include at least:
- `id` (UUID),
- `project_id` (FK → projects),
- `agent_id` (string),
- `content` (text),
- `memory_type` (taxonomy enum),
- `goal` (optional text),
- `result` (optional text),
- `feedback` (optional text),
- `tool_usage` (JSON),
- `embedding` (vector; semantic search),
- `content_tsv` (full-text index),
- `tags` (string array),
- audit fields: `created_at`, `updated_at`,
- deduplication fields: `similarity_hash`, `is_duplicate`, `duplicate_of`.

#### REQ-MEM-DM-003
Memories marked `is_duplicate=true` SHALL reference the original memory via `duplicate_of`, and MUST be excluded from primary search results by default.

### 3.3 File and Memory–File Link

#### REQ-MEM-DM-004
The `files` entity SHALL represent codebase files and include:
- `id` (UUID),
- `project_id` (FK),
- `file_path` (unique per project),
- optional `file_type`, `last_content_hash`,
- stats: `memory_count`,
- timestamps (`first_seen_at`, `last_seen_at`).

#### REQ-MEM-DM-005
The `memory_files` link entity SHALL support many-to-many relationships between memories and files, including:
- `memory_id` (FK → memories),
- `file_id` (FK → files),
- `relation_type` (e.g., read, modified, created, deleted, referenced),
- optional `line_start`, `line_end`.

### 3.4 Playbook Entries

#### REQ-MEM-DM-006
The system SHALL maintain a `playbook_entries` entity representing project-wide guidance bullets, including:
- `id`, `project_id`,
- `content`,
- `category` (e.g., `dependencies`, `architecture`, `gotchas`, `patterns`),
- `embedding` (vector),
- `content_tsv` (tsvector),
- `tags` (string array),
- `priority` (int; higher = more important),
- `supporting_memory_ids` (array of UUIDs),
- `created_at`, `created_by`, `updated_at`,
- `is_active` (soft-delete).

### 3.5 Playbook Changes

#### REQ-MEM-DM-007
All modifications to the playbook MUST be recorded in `playbook_changes` with:
- `operation` ∈ {add, update, delete},
- old/new content and/or structured `delta`,
- `reason`,
- `related_memory_id` (optional),
- `changed_at`, `changed_by`.

### 3.6 Tags

#### REQ-MEM-DM-008
Tags SHALL be modeled as first-class entities with:
- `name` (unique per project),
- `description`,
- `category` (e.g., language, framework, concept),
- `usage_count`.

---

## 4. Hybrid Search & Retrieval

#### REQ-MEM-SEARCH-001: Hybrid Modes
THE SYSTEM SHALL support at least three search modes over memories:
- `semantic` (vector similarity only),
- `keyword` (full-text only),
- `hybrid` (combination of both).

#### REQ-MEM-SEARCH-002: Vector Search
Semantic search SHALL use a vector similarity index; pgvector with HNSW is the preferred implementation. Similarity MUST be computed via cosine similarity or equivalent.

#### REQ-MEM-SEARCH-003: Keyword Search
Keyword search SHALL use full-text capabilities, such as PostgreSQL’s tsvector/tsquery, and MUST support ranking (`ts_rank` or equivalent) and snippet generation.

#### REQ-MEM-SEARCH-004: Hybrid Ranking
Hybrid search MUST fuse semantic and keyword rankings via a stable, documented strategy (e.g., Reciprocal Rank Fusion with configurable semantic/keyword weights).

#### REQ-MEM-SEARCH-005: Filters
Search requests MUST support optional filters for:
- `memory_types`,
- `tags`,
- `file_paths`,
- `agent_ids`,
- `date_from`, `date_to`.

---

## 5. ACE Workflow Requirements

> The ACE (Executor, Reflector, Curator) workflow is the primary mechanism for automatic memory creation and playbook updates.

### 5.1 Executor Phase

#### REQ-MEM-ACE-001
Executor SHALL:
- parse `tool_usage` to extract file paths and classify relations,
- classify `memory_type` based on `goal` and `result`,
- generate embeddings for content,
- create a memory record,
- link memory to relevant files.

### 5.2 Reflector Phase

#### REQ-MEM-ACE-002
Reflector SHALL:
- analyze task feedback for errors and root causes,
- search playbook for related entries using semantic search,
- tag related entries with supporting memory IDs,
- extract structured insights (e.g., patterns, gotchas, best practices).

### 5.3 Curator Phase

#### REQ-MEM-ACE-003
Curator SHALL:
- propose playbook updates based on insights,
- generate delta operations (add/update/delete),
- validate deltas (no duplicates, minimal quality thresholds),
- apply accepted deltas to the playbook,
- record changes in `playbook_changes`.

### 5.4 ACE Trigger

#### REQ-MEM-ACE-004
The ACE workflow MUST be invocable via a single `complete-task` style API that:
- accepts `goal`, `result`, `tool_usage`, and `feedback`,
- runs Executor → Reflector → Curator in sequence,
- returns a structured `ACEResult`.

---

## 6. API Requirements

> The following endpoints describe required capabilities; URL paths and exact naming MAY vary, but equivalent functionality and contracts MUST exist.

### 6.1 Complete Task (ACE)

#### REQ-MEM-API-001
The system SHALL expose an endpoint to execute the ACE workflow on task completion (e.g., `POST /complete-task`), accepting:
- `project_id`, `agent_id`,
- `goal`, `result`,
- `tool_usage` (list),
- `feedback`.

Response MUST include:
- `memory_id`, `memory_type`, `files_linked`,
- tags, insights, errors, related playbook entries,
- playbook delta and updated bullets,
- `change_id` (playbook change record).

### 6.2 Memory CRUD & Search

#### REQ-MEM-API-002
The system SHALL support:
- `POST /memories` to create a memory manually,
- `GET /memories/{memory_id}` to retrieve full details,
- `POST /search` (or equivalent) to perform hybrid memory search.

### 6.3 Playbook & History

#### REQ-MEM-API-003
The system SHALL allow:
- retrieving the current playbook for a project,
- filtering by category/tags,
- retrieving playbook change history with filters (operation, agent_id, date).

### 6.4 File Knowledge Graph

#### REQ-MEM-API-004
The system SHALL provide an endpoint to retrieve the knowledge graph for a file (linked memories, playbook entries, related files, stats).

### 6.5 Task Context

#### REQ-MEM-API-005
The system SHALL support a “get context for task” endpoint that:
- accepts `project_id` and `task_description`,
- returns top-k relevant memories, playbook entries, and recommended files.

---

## 7. Deduplication Requirements

#### REQ-MEM-DEDUP-001
On memory creation, THE SYSTEM SHALL check for near-duplicates via semantic similarity and mark new memories as duplicate if similarity exceeds a configurable threshold (default 0.95).

#### REQ-MEM-DEDUP-002
The system SHOULD provide a deduplication maintenance operation to scan and mark duplicates in bulk for a project.

---

## 8. Non-Functional Requirements

### 8.1 Performance

#### REQ-MEM-NFR-001
- Search latency P95:
  - hybrid search: < 100ms under nominal load,
  - semantic-only: < 50ms,
  - keyword-only: < 20ms.
- ACE `complete-task` P95: < 2s including embedding calls.

### 8.2 Scalability

#### REQ-MEM-NFR-002
The system SHALL support:
- horizontal scaling of stateless API servers,
- optional read replicas for search-heavy workloads,
- future sharding by `project_id`.

### 8.3 Security & Audit

#### REQ-MEM-NFR-003
All API calls MUST be authenticated and authorized; sensitive operations (playbook changes, deduplication) MUST be audited with actor, project_id, and timestamp.

---

## 9. Pydantic Reference Models

```python
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    ERROR_FIX = "error_fix"
    DISCOVERY = "discovery"
    DECISION = "decision"
    LEARNING = "learning"
    WARNING = "warning"
    CODEBASE_KNOWLEDGE = "codebase_knowledge"


class ToolUsage(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None


class CreateMemoryRequest(BaseModel):
    project_id: str
    agent_id: str
    content: str = Field(..., min_length=10)
    memory_type: MemoryType
    goal: Optional[str] = None
    result: Optional[str] = None
    feedback: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    file_paths: List[str] = Field(default_factory=list)


class CompleteTaskRequest(BaseModel):
    project_id: str
    agent_id: str
    goal: str
    result: str
    tool_usage: List[ToolUsage]
    feedback: str
```

---

## Related Documents

- [Monitoring Architecture Requirements](../monitoring/monitoring_architecture.md)
- [Task Queue Management Requirements](../workflows/task_queue_management.md)
- [Diagnosis Agent Requirements](../workflows/diagnosis_agent.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial requirements derived from design doc |


