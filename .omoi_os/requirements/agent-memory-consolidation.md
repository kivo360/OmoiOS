---
id: REQ-AMC-001
title: Agent Memory Consolidation Requirements
feature: agent-memory-consolidation
created: 2025-01-08
updated: 2025-01-08
status: draft
category: functional
priority: HIGH
prd_ref: docs/prd-agent-memory-consolidation.md
design_ref: designs/agent-memory-consolidation.md
---

# Agent Memory Consolidation Requirements

## Overview

This specification defines requirements for the Agent Memory Consolidation System, a background knowledge synthesis service that transforms raw task execution memories into higher-level insights, patterns, and principles. The system integrates with the existing memory infrastructure (TaskMemory, MemoryService, hybrid search) and maintains full traceability to source memories.

## Functional Requirements

### Consolidation Engine

#### REQ-AMC-FUNC-001: Trigger Consolidation

**Priority**: HIGH
**Category**: Functional

WHEN the consolidation trigger conditions are met, THE SYSTEM SHALL automatically initiate a consolidation job for the project.

**Acceptance Criteria**:
- [ ] Supports time-based triggers (configurable schedule, e.g., nightly)
- [ ] Supports threshold-based triggers (e.g., every 100 new memories)
- [ ] Supports manual trigger via admin API endpoint
- [ ] Queues consolidation job in TaskQueueService
- [ ] Returns job ID for tracking

**Notes**: Default configuration: nightly at 2 AM + every 100 new memories.

---

#### REQ-AMC-FUNC-002: Execute Consolidation Workflow

**Priority**: HIGH
**Category**: Functional

WHEN a consolidation job is executed, THE SYSTEM SHALL process memories through a multi-phase workflow: Pattern Extraction → Memory Merging → Hierarchy Creation → Playbook Enrichment.

**Acceptance Criteria**:
- [ ] Executes phases sequentially
- [ ] Handles phase failures gracefully (continues to next phase)
- [ ] Logs progress and metrics for each phase
- [ ] Updates job status (running, completed, failed)
- [ ] Executes within timeout (default: 10 minutes per 1000 memories)

---

### Pattern Extraction

#### REQ-AMC-FUNC-003: Extract Patterns from Memories

**Priority**: HIGH
**Category**: Functional

WHEN processing memories for consolidation, THE SYSTEM SHALL analyze groups of similar memories to extract recurring patterns, best practices, and principles.

**Acceptance Criteria**:
- [ ] Groups memories by semantic similarity (threshold: 0.85)
- [ ] Uses LLM to extract patterns from each group
- [ ] Validates extracted patterns (confidence score > 0.7)
- [ ] Stores patterns in ConsolidatedMemory table
- [ ] Links patterns to source memories

---

#### REQ-AMC-FUNC-004: Pattern Types

**Priority**: MEDIUM
**Category**: Functional

THE SYSTEM SHALL extract the following pattern types from memories:

1. **Success Patterns**: Actions that consistently lead to successful outcomes
2. **Failure Patterns**: Common mistakes and how to avoid them
3. **Decision Patterns**: Rationales for architectural or technical choices
4. **Workflow Patterns**: Optimal sequences for completing tasks
5. **Gotcha Patterns**: Edge cases and pitfalls to watch for

**Acceptance Criteria**:
- [ ] Classifies patterns into one of the above types
- [ ] Stores pattern_type in ConsolidatedMemory.memory_type
- [ ] Provides examples for each pattern type

---

### Memory Merging

#### REQ-AMC-FUNC-005: Merge Similar Memories

**Priority**: HIGH
**Category**: Functional

WHEN two or more memories have semantic similarity > 0.95, THE SYSTEM SHALL merge them into a single consolidated memory.

**Acceptance Criteria**:
- [ ] Detects near-duplicate memories via vector similarity
- [ ] Creates consolidated memory with merged content
- [ ] Preserves unique information from all source memories
- [ ] Marks source memories as consolidated (not deleted)
- [ ] Links consolidated memory to all source memories

**Notes**: Similarity threshold of 0.95 ensures only near-duplicates are merged.

---

#### REQ-AMC-FUNC-006: Track Memory Lineage

**Priority**: HIGH
**Category**: Functional

WHEN a consolidated memory is created, THE SYSTEM SHALL maintain full traceability to source memories.

**Acceptance Criteria**:
- [ ] ConsolidatedMemory.source_memory_ids array contains all source memory IDs
- [ ] TaskMemory.consolidated_into_id references the consolidated memory
- [ ] Supports N-level consolidation (consolidated → consolidated → raw)
- [ ] Provides API to trace consolidation lineage

---

### Hierarchy Creation

#### REQ-AMC-FUNC-007: Multi-Level Memory Hierarchy

**Priority**: MEDIUM
**Category**: Functional

THE SYSTEM SHALL organize memories into a three-level hierarchy:

1. **Raw Memories** (TaskMemory): Individual task execution logs
2. **Consolidated Memories** (ConsolidatedMemory): Merged memories and extracted patterns
3. **Abstract Principles** (ConsolidatedMemory with high abstraction): Cross-pattern principles

**Acceptance Criteria**:
- [ ] ConsolidatedMemory.abstraction_level field (1=merged, 2=pattern, 3=principle)
- [ ] Supports querying by abstraction level
- [ ] Agent tools can filter results by level

---

#### REQ-AMC-FUNC-008: Promote Patterns to Principles

**Priority**: MEDIUM
**Category**: Functional

WHEN multiple patterns share common themes, THE SYSTEM SHALL promote them to abstract principles.

**Acceptance Criteria**:
- [ ] Groups patterns by semantic similarity
- [ ] Uses LLM to synthesize principle from patterns
- [ ] Stores principle as ConsolidatedMemory with abstraction_level=3
- [ ] Links principle to source patterns

---

### Playbook Integration

#### REQ-AMC-FUNC-009: Auto-Generate Playbook Entries

**Priority**: HIGH
**Category**: Functional

WHEN high-confidence patterns are extracted (confidence > 0.8), THE SYSTEM SHALL automatically create or update playbook entries.

**Acceptance Criteria**:
- [ ] Creates PlaybookEntry for each high-confidence pattern
- [ ] Infers category from pattern content and memory types
- [ ] Adds supporting_memory_ids linking to source memories
- [ ] Sets priority based on pattern confidence and reuse count

**Notes**: Integrates with existing playbook_entries table from memory system design.

---

#### REQ-AMC-FUNC-010: Update Existing Playbook Entries

**Priority**: MEDIUM
**Category**: Functional

WHEN a new pattern reinforces an existing playbook entry, THE SYSTEM SHALL update the entry with additional evidence.

**Acceptance Criteria**:
- [ ] Detects similarity to existing playbook entries (> 0.9 similarity)
- [ ] Appends new memory IDs to supporting_memory_ids
- [ ] Increments priority based on evidence count
- [ ] Records change in playbook_changes table

---

### Agent Tools

#### REQ-AMC-FUNC-011: Search Consolidated Memories Tool

**Priority**: HIGH
**Category**: Functional

THE SYSTEM SHALL provide a tool for agents to search consolidated memories.

**Acceptance Criteria**:
- [ ] Tool name: `omoi__search_consolidated_memories`
- [ ] Accepts query string, filters (abstraction_level, memory_type, date_range)
- [ ] Returns results with source memory references
- [ ] Results sorted by relevance_score
- [ ] Response time < 100ms

---

#### REQ-AMC-FUNC-012: Get Consolidation Context Tool

**Priority**: MEDIUM
**Category**: Functional

THE SYSTEM SHALL provide a tool for agents to retrieve consolidated context for a task.

**Acceptance Criteria**:
- [ ] Tool name: `omoi__get_consolidated_context`
- [ ] Accepts task_description, project_id
- [ ] Returns relevant consolidated memories + playbook entries
- [ ] Includes abstraction_level distribution
- [ ] Returns recommendations for which levels to query

---

#### REQ-AMC-FUNC-013: Trace Memory Lineage Tool

**Priority**: LOW
**Category**: Functional

THE SYSTEM SHALL provide a tool for tracing the consolidation lineage of a memory.

**Acceptance Criteria**:
- [ ] Tool name: `omoi__trace_memory_lineage`
- [ ] Accepts memory_id (raw or consolidated)
- [ ] Returns full consolidation tree (ancestors and descendants)
- [ ] Includes similarity scores for merged memories
- [ ] Supports depth limit for large trees

---

### Admin API

#### REQ-AMC-FUNC-014: Manual Consolidation Endpoint

**Priority**: HIGH
**Category**: Functional

THE SYSTEM SHALL provide an admin API endpoint for manual consolidation.

**Acceptance Criteria**:
- [ ] Endpoint: `POST /api/v1/admin/consolidate-memories`
- [ ] Accepts project_id, optional scope (all, unconsolidated_only, date_range)
- [ ] Returns job_id for tracking
- [ ] Requires admin authentication
- [ ] Queues job in TaskQueueService

---

#### REQ-AMC-FUNC-015: Consolidation Status Endpoint

**Priority**: MEDIUM
**Category**: Functional

THE SYSTEM SHALL provide an endpoint for checking consolidation status.

**Acceptance Criteria**:
- [ ] Endpoint: `GET /api/v1/admin/consolidation-status/{job_id}`
- [ ] Returns status (pending, running, completed, failed)
- [ ] Returns progress (phases_completed, total_phases)
- [ ] Returns metrics (memories_processed, patterns_extracted, time_elapsed)

---

#### REQ-AMC-FUNC-016: Consolidation Metrics Endpoint

**Priority**: MEDIUM
**Category**: Functional

THE SYSTEM SHALL provide an endpoint for retrieving consolidation metrics.

**Acceptance Criteria**:
- [ ] Endpoint: `GET /api/v1/admin/consolidation-metrics/{project_id}`
- [ ] Returns: total_memories, consolidated_count, raw_count, last_run_time, next_run_time
- [ ] Returns: memory_type_distribution, abstraction_level_distribution
- [ ] Returns: consolidation_efficiency (reduction_percentage)

---

## Non-Functional Requirements

### Performance

#### REQ-AMC-NFR-001: Consolidation Throughput

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL consolidate at least 1000 memories per 5 minutes when processing similar memories.

**Metrics**:
- P50 consolidation time: <2 min per 1000 memories
- P95 consolidation time: <5 min per 1000 memories
- Pattern extraction time: <30 sec per 100 memories

---

#### REQ-AMC-NFR-002: Query Latency

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL return consolidated memory search results within specified time limits.

**Metrics**:
- P50 search latency: <50ms
- P95 search latency: <100ms
- P99 search latency: <200ms

---

#### REQ-AMC-NFR-003: Database Load

**Priority**: MEDIUM
**Category**: Performance

THE SYSTEM SHALL not significantly impact database performance during consolidation.

**Metrics**:
- Consolidation queries use read replicas when available
- Batch processing limited to 100 memories per transaction
- Database CPU <80% during consolidation

---

### Scalability

#### REQ-AMC-NFR-004: Memory Scale

**Priority**: HIGH
**Category**: Scalability

THE SYSTEM SHALL support projects with up to 100,000 raw memories.

**Metrics**:
- Consolidation time scales linearly (O(n)) with memory count
- Search performance degrades <20% from 1K to 100K memories
- Supports incremental consolidation (only new memories)

---

#### REQ-AMC-NFR-005: Concurrent Consolidation

**Priority**: MEDIUM
**Category**: Scalability

THE SYSTEM SHALL support concurrent consolidation jobs for different projects.

**Metrics**:
- Up to 10 concurrent consolidation jobs
- No resource contention between jobs
- Proper isolation and cleanup

---

### Reliability

#### REQ-AMC-NFR-006: Failure Handling

**Priority**: HIGH
**Category**: Reliability

THE SYSTEM SHALL handle consolidation failures gracefully.

**Acceptance Criteria**:
- [ ] Phase failure doesn't crash entire job
- [ ] Failed jobs are retryable with exponential backoff
- [ ] Dead letter queue for permanently failed jobs
- [ ] Alerting on repeated failures

---

#### REQ-AMC-NFR-007: Idempotency

**Priority**: MEDIUM
**Category**: Reliability

Consolidation operations SHALL be idempotent.

**Acceptance Criteria**:
- [ ] Re-running consolidation produces consistent results
- [ ] Duplicate job executions are detected and skipped
- [ ] Consolidated memories are not duplicated

---

### Security & Audit

#### REQ-AMC-NFR-008: Access Control

**Priority**: HIGH
**Category**: Security

THE SYSTEM SHALL enforce proper access control for consolidation operations.

**Acceptance Criteria**:
- [ ] Admin endpoints require elevated permissions
- [ ] Project-scoped consolidation requires project access
- [ ] Audit logging for all consolidation operations

---

#### REQ-AMC-NFR-009: Audit Trail

**Priority**: MEDIUM
**Category**: Security

THE SYSTEM SHALL maintain an audit trail for consolidation activities.

**Acceptance Criteria**:
- [ ] All consolidations logged with timestamp, actor, project_id
- [ ] Consolidation changes recorded (created, updated, deleted)
- [ ] Source memory IDs preserved for traceability
- [ ] Audit trail exportable via API

---

## Data Model Requirements

#### REQ-AMC-DM-001: ConsolidatedMemory Table

**Priority**: HIGH
**Category**: Functional

THE SYSTEM SHALL include a ConsolidatedMemory table with the following fields:

```sql
CREATE TABLE consolidated_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,
    memory_type VARCHAR(50) NOT NULL,  -- Inherits from MemoryType enum
    abstraction_level INTEGER NOT NULL,  -- 1=merged, 2=pattern, 3=principle

    -- Context
    pattern_type VARCHAR(50),  -- success, failure, decision, workflow, gotcha
    confidence_score FLOAT,  -- 0.0-1.0
    source_memory_ids UUID[] NOT NULL,  -- Source TaskMemory IDs

    -- Embedding for search
    embedding vector(3072),

    -- Metadata
    tags TEXT[],
    consolidation_method VARCHAR(100),  -- llm, heuristic, hybrid
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    consolidated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Statistics
    source_count INTEGER NOT NULL,  -- Number of source memories
    reuse_count INTEGER DEFAULT 0,

    -- Indexes
    INDEX idx_cm_project (project_id),
    INDEX idx_cm_abstraction (abstraction_level),
    INDEX idx_cm_type (memory_type),
    INDEX idx_cm_embedding USING hnsw (embedding vector_cosine_ops)
);
```

---

#### REQ-AMC-DM-002: ConsolidationJob Table

**Priority**: HIGH
**Category**: Functional

THE SYSTEM SHALL include a ConsolidationJob table for tracking consolidation jobs:

```sql
CREATE TABLE consolidation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Job info
    status VARCHAR(50) NOT NULL,  -- pending, running, completed, failed, cancelled
    trigger_type VARCHAR(50) NOT NULL,  -- scheduled, manual, threshold

    -- Scope
    scope JSONB,  -- {date_range, memory_types, unconsolidated_only}

    -- Results
    phases_completed TEXT[],
    metrics JSONB,  -- {memories_processed, patterns_extracted, memories_merged}

    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    triggered_by VARCHAR(255),  -- user_id or 'system'

    INDEX idx_cj_project_status (project_id, status),
    INDEX idx_cj_created (created_at DESC)
);
```

---

#### REQ-AMC-DM-003: TaskMemory Enhancements

**Priority**: MEDIUM
**Category**: Functional

THE SYSTEM SHALL enhance the existing TaskMemory table with consolidation fields:

```sql
-- Add to existing task_memories table
ALTER TABLE task_memories ADD COLUMN consolidated_into_id UUID REFERENCES consolidated_memories(id) ON DELETE SET NULL;
ALTER TABLE task_memories ADD COLUMN is_consolidated BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_tm_consolidated ON task_memories(is_consolidated) WHERE is_consolidated = TRUE;
```

---

## Traceability

| Requirement ID | PRD Section | Design Section | Ticket |
|----------------|-------------|----------------|--------|
| REQ-AMC-FUNC-001 | Goals & Success Metrics | Consolidation Engine | TKT-001 |
| REQ-AMC-FUNC-002 | Goals & Success Metrics | Consolidation Engine | TKT-001 |
| REQ-AMC-FUNC-003 | Goals & Success Metrics | Pattern Extraction | TKT-002 |
| REQ-AMC-FUNC-004 | Goals & Success Metrics | Pattern Extraction | TKT-002 |
| REQ-AMC-FUNC-005 | Goals & Success Metrics | Memory Merging | TKT-003 |
| REQ-AMC-FUNC-006 | Goals & Success Metrics | Memory Merging | TKT-003 |
| REQ-AMC-FUNC-007 | User Stories #1 | Hierarchy Creation | TKT-004 |
| REQ-AMC-FUNC-008 | User Stories #1 | Hierarchy Creation | TKT-004 |
| REQ-AMC-FUNC-009 | Goals & Success Metrics | Playbook Integration | TKT-005 |
| REQ-AMC-FUNC-010 | Goals & Success Metrics | Playbook Integration | TKT-005 |
| REQ-AMC-FUNC-011 | User Stories #1 | Agent Tools | TKT-006 |
| REQ-AMC-FUNC-012 | User Stories #1 | Agent Tools | TKT-006 |
| REQ-AMC-FUNC-013 | User Stories #5 | Agent Tools | TKT-006 |
| REQ-AMC-FUNC-014 | User Stories #3 | Admin API | TKT-007 |
| REQ-AMC-FUNC-015 | User Stories #3 | Admin API | TKT-007 |
| REQ-AMC-FUNC-016 | User Stories #4 | Admin API | TKT-007 |
| REQ-AMC-DM-001 | Data Model | Database Schema | TKT-008 |
| REQ-AMC-DM-002 | Data Model | Database Schema | TKT-008 |
| REQ-AMC-DM-003 | Data Model | Database Schema | TKT-008 |
