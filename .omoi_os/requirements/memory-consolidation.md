---
id: REQ-MEMCONS-001
title: Memory Consolidation Requirements
feature: memory-consolidation
created: 2025-01-08
updated: 2025-01-08
status: draft
category: functional
priority: HIGH
prd_ref: docs/prd-memory-consolidation.md
design_ref: designs/memory-consolidation.md
---

# Memory Consolidation Requirements

## Overview

These requirements define the Memory Consolidation System, which adds automated memory management capabilities to the existing Agent Memory System. The system supports memory merging, summarization, archiving, and playbook promotion through both scheduled and manual triggers.

## Functional Requirements

### REQ-MEMCONS-FUNC-001: Memory Similarity Detection

**Priority**: HIGH
**Category**: Functional

WHEN a consolidation job runs for a project, THE SYSTEM SHALL identify groups of semantically similar memories using embedding-based cosine similarity with a configurable threshold (default 0.90).

**Acceptance Criteria**:
- [ ] Similarity threshold is configurable per project
- [ ] Uses existing pgvector cosine similarity for efficient computation
- [ ] Groups memories into clusters where all members meet threshold criteria
- [ ] Excludes archived memories from similarity detection
- [ ] Respects memory_type filters (same-type only or cross-type based on config)

**Notes**: Builds on existing deduplication logic (REQ-MEM-DEDUP-001) but extends to clustering rather than pairwise comparison.

---

### REQ-MEMCONS-FUNC-002: Memory Merging

**Priority**: HIGH
**Category**: Functional

WHEN a cluster of similar memories is identified, THE SYSTEM SHALL merge them into a single consolidated memory preserving the most important information from all source memories.

**Acceptance Criteria**:
- [ ] Creates a new memory with `memory_type = "consolidated"`
- [ ] Stores source memory IDs in `consolidated_from` array
- [ ] Marks source memories as `is_duplicate = true` pointing to consolidated memory
- [ ] Generates new embedding from merged content
- [ ] Preserves all unique file links from source memories
- [ ] Combines tags from all sources, deduplicating
- [ ] Sets `consolidated_at` timestamp

**Notes**: Requires new fields on TaskMemory model (consolidated_from, consolidated_at).

---

### REQ-MEMCONS-FUNC-003: Memory Summarization

**Priority**: HIGH
**Category**: Functional

WHEN a memory cluster has 3+ members covering a related topic, THE SYSTEM SHALL optionally create a higher-level summary memory that synthesizes key insights across the cluster.

**Acceptance Criteria**:
- [ ] Uses LLM to generate summary from cluster contents
- [ ] Summary memory has `memory_type = "synthesis"`
- [ ] Links summary to source cluster via `synthesized_from` array
- [ ] Validates summary quality with confidence score >0.80
- [ ] Flags low-confidence summaries for human review
- [ ] Includes metadata: cluster_size, synthesis_date, synthesis_confidence

**Notes**: LLM prompt should extract patterns, best practices, and architectural insights from the cluster.

---

### REQ-MEMCONS-FUNC-004: Memory Archiving

**Priority**: MEDIUM
**Category**: Functional

WHEN a memory has not been accessed (reused_count unchanged) for a configurable period (default 90 days) AND has low reuse count (<3), THE SYSTEM SHALL archive the memory to reduce noise in search results.

**Acceptance Criteria**:
- [ ] Sets `is_archived = true` on memory
- [ ] Archived memories are excluded from default search results
- [ ] Archived memories remain accessible via `include_archived=true` flag
- [ ] Updates `archived_at` timestamp
- [ ] Logs archive reason (staleness, low_value, or manual)
- [ ] Supports bulk archival via scheduled job

**Notes**: Archiving is reversible; memories can be unarchived if needed.

---

### REQ-MEMCONS-FUNC-005: Playbook Promotion

**Priority**: MEDIUM
**Category**: Functional

WHEN a consolidated or synthesis memory has high confidence (>0.85) and represents a repeatable pattern, THE SYSTEM SHALL automatically promote it to a playbook entry.

**Acceptance Criteria**:
- [ ] Creates playbook entry from consolidated memory content
- [ ] Sets category based on memory_type and content analysis
- [ ] Links playbook entry to source memory via `supporting_memory_ids`
- [ ] Records promotion in `playbook_changes` with operation="promote"
- [ ] Flags high-value entries for priority sorting
- [ ] Requires minimum confidence threshold (configurable, default 0.85)

---

### REQ-MEMCONS-FUNC-006: Scheduled Consolidation

**Priority**: HIGH
**Category**: Functional

WHEN the scheduled consolidation job runs (configurable interval, default daily), THE SYSTEM SHALL execute consolidation operations on all projects that exceed the memory count threshold.

**Acceptance Criteria**:
- [ ] Runs as background job via Celery/RQ task queue
- [ ] Checks project memory count against threshold (configurable, default 1000)
- [ ] Processes projects in parallel with rate limiting
- [ ] Skips projects with consolidation disabled
- [ ] Records job execution in consolidation_jobs table
- [ ] Sends notification on completion with summary statistics

**Notes**: Should handle failures gracefully and retry per project.

---

### REQ-MEMCONS-FUNC-007: Manual Consolidation Trigger

**Priority**: HIGH
**Category**: Functional

WHEN an authorized user triggers consolidation via API endpoint, THE SYSTEM SHALL execute consolidation operations for the specified project.

**Acceptance Criteria**:
- [ ] Requires admin-level authentication
- [ ] Accepts project_id and consolidation options (merge, summarize, archive, promote)
- [ ] Returns job_id for tracking
- [ ] Executes asynchronously in background
- [ ] Validates project exists and user has access
- [ ] Returns 202 Accepted with job location URL

---

### REQ-MEMCONS-FUNC-008: Consolidation History Tracking

**Priority**: HIGH
**Category**: Functional

WHEN a consolidation operation completes, THE SYSTEM SHALL record detailed information in the consolidation_changes table for audit and rollback.

**Acceptance Criteria**:
- [ ] Creates consolidation_change record with operation type
- [ ] Records before/after memory counts
- [ ] Lists all affected memory IDs
- [ ] Stores consolidation parameters (thresholds, options)
- [ ] Includes timestamp and actor (system or user_id)
- [ ] Links to parent consolidation_job

---

### REQ-MEMCONS-FUNC-009: Consolidation Rollback

**Priority**: MEDIUM
**Category**: Functional

WHEN an authorized user requests rollback of a consolidation operation via consolidation_id, THE SYSTEM SHALL restore the memory state to before the consolidation.

**Acceptance Criteria**:
- [ ] Validates consolidation exists and is within rollback window (7 days)
- [ ] Checks for conflicting changes after consolidation
- [ ] Unmarks source memories from duplicate status
- [ ] Deletes consolidated memory
- [ ] Restores original file links
- [ ] Records rollback operation in audit log
- [ ] Returns error if rollback not possible

---

### REQ-MEMCONS-FUNC-010: Consolidation Status Query

**Priority**: MEDIUM
**Category**: Functional

WHEN a client requests consolidation status via job_id, THE SYSTEM SHALL return current progress and results.

**Acceptance Criteria**:
- [ ] Returns job status (pending, running, completed, failed)
- [ ] Includes progress percentage for running jobs
- [ ] Shows consolidation statistics (memories_merged, archived, promoted)
- [ ] Lists generated memory IDs
- [ ] Returns error message if failed
- [ ] Includes links to consolidation_change records

---

## Non-Functional Requirements

### REQ-MEMCONS-NFR-001: Performance

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL complete consolidation of 1000 memories in less than 30 seconds.

**Metrics**:
- Memory similarity detection: <10s for 1000 memories
- Merge operations: <5s per 100 memories
- Summary generation: <2s per summary (LLM-bound)
- Archival: <1s per 100 memories

---

### REQ-MEMCONS-NFR-002: Information Preservation

**Priority**: HIGH
**Category**: Quality

THE SYSTEM SHALL preserve at least 95% of unique information during consolidation as measured by manual sampling audit.

**Metrics**:
- Information loss rate: <5%
- Unique concept retention: >95%
- File link preservation: 100%
- Tag preservation: 100%

---

### REQ-MEMCONS-NFR-003: Concurrency Safety

**Priority**: HIGH
**Category**: Reliability

THE SYSTEM SHALL handle concurrent memory operations during consolidation without data corruption using row-level locking and optimistic concurrency control.

**Metrics**:
- No lost updates under concurrent consolidation
- No orphaned memory references
- Serializable isolation for merge operations

---

### REQ-MEMCONS-NFR-004: Audit Retention

**Priority**: MEDIUM
**Category**: Compliance

THE SYSTEM SHALL retain consolidation audit records for minimum 90 days with configurable retention period.

**Metrics**:
- Audit record completeness: 100%
- Record accessibility: <100ms query time
- Automatic cleanup after retention period

---

## Data Model Extensions

### New Table: consolidation_jobs

```sql
CREATE TABLE consolidation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Job details
    status VARCHAR(20) NOT NULL,  -- pending, running, completed, failed
    trigger_type VARCHAR(20) NOT NULL,  -- scheduled, manual

    -- Configuration
    options JSONB DEFAULT '{}',  -- merge, summarize, archive, promote flags

    -- Results
    memories_merged INTEGER DEFAULT 0,
    memories_archived INTEGER DEFAULT 0,
    memories_promoted INTEGER DEFAULT 0,
    summaries_created INTEGER DEFAULT 0,

    -- Metadata
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    triggered_by VARCHAR(255),  -- user_id or "system"

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_consolidation_jobs_project ON consolidation_jobs(project_id, created_at DESC);
CREATE INDEX idx_consolidation_jobs_status ON consolidation_jobs(status) WHERE status IN ('pending', 'running');
```

### New Table: consolidation_changes

```sql
CREATE TABLE consolidation_changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    consolidation_job_id UUID REFERENCES consolidation_jobs(id) ON DELETE CASCADE,

    -- Change details
    operation VARCHAR(20) NOT NULL,  -- merge, archive, promote, summarize, rollback
    memory_id UUID NOT NULL REFERENCES task_memories(id) ON DELETE CASCADE,

    -- Before state
    previous_state JSONB,

    -- After state
    new_state JSONB,

    -- Context
    reason TEXT,
    confidence FLOAT,

    -- Metadata
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(255)  -- user_id or "system"
);

CREATE INDEX idx_consolidation_changes_job ON consolidation_changes(consolidation_job_id);
CREATE INDEX idx_consolidation_changes_memory ON consolidation_changes(memory_id);
```

### Extensions to task_memories Table

```sql
-- Add consolidation-related fields
ALTER TABLE task_memories
ADD COLUMN consolidated_from UUID[],  -- source memory IDs if this is a consolidation
ADD COLUMN consolidated_at TIMESTAMP,
ADD COLUMN synthesized_from UUID[],  -- source cluster IDs if this is a synthesis
ADD COLUMN synthesized_at TIMESTAMP,
ADD COLUMN synthesis_confidence FLOAT,
ADD COLUMN is_archived BOOLEAN DEFAULT FALSE,
ADD COLUMN archived_at TIMESTAMP,
ADD COLUMN archive_reason VARCHAR(50);  -- staleness, low_value, manual

CREATE INDEX idx_task_memories_consolidated ON task_memories(consolidated_at) WHERE consolidated_at IS NOT NULL;
CREATE INDEX idx_task_memories_archived ON task_memories(is_archived) WHERE is_archived = TRUE;
```

## Traceability

| Requirement ID | PRD Section | Design Section | Ticket |
|----------------|-------------|----------------|--------|
| REQ-MEMCONS-FUNC-001 | User Stories #1-3 | Component Design | TKT-001 |
| REQ-MEMCONS-FUNC-002 | User Stories #1-3 | Component Design | TKT-001 |
| REQ-MEMCONS-FUNC-003 | User Stories #2 | Component Design | TKT-002 |
| REQ-MEMCONS-FUNC-004 | Scope: In Scope | Component Design | TKT-003 |
| REQ-MEMCONS-FUNC-005 | Scope: In Scope | Component Design | TKT-004 |
| REQ-MEMCONS-FUNC-006 | User Stories #4 | API Specification | TKT-005 |
| REQ-MEMCONS-FUNC-007 | User Stories #1 | API Specification | TKT-005 |
| REQ-MEMCONS-FUNC-008 | User Stories #2 | API Specification | TKT-006 |
| REQ-MEMCONS-FUNC-009 | User Stories #3 | API Specification | TKT-006 |
| REQ-MEMCONS-FUNC-010 | User Stories #2 | API Specification | TKT-006 |
| REQ-MEMCONS-NFR-001 | Success Metrics | Performance | TKT-007 |
| REQ-MEMCONS-NFR-002 | Success Metrics | Testing | TKT-007 |
| REQ-MEMCONS-NFR-003 | Constraints | Implementation | TKT-008 |
| REQ-MEMCONS-NFR-004 | Constraints | Implementation | TKT-009 |
