# Agent Memory Consolidation System - Requirements Analysis

**Document Version:** 1.0
**Date:** 2026-01-08
**Status:** Requirements Analysis

---

## Executive Summary

This document analyzes the requirements for implementing an **Agent Memory Consolidation System** within the OmoiOS agent orchestration platform. The system aims to optimize memory storage, improve retrieval performance, and implement automated retention policies for the growing volume of agent execution memories stored in the `task_memories` table.

### Current State Analysis

The platform already implements a sophisticated memory system with:
- **ACE Workflow** (Executor → Reflector → Curator) for transforming task completions into knowledge
- **Semantic search** with 1536-dimensional embeddings using hybrid (semantic + keyword) search
- **Memory taxonomy** with 6 types: error_fix, discovery, decision, learning, warning, codebase_knowledge
- **Pattern extraction** from completed tasks for reusable knowledge
- **Reuse tracking** via `reused_count` field

### Identified Gaps

1. **No automated archival mechanism** - Old memories remain in active storage indefinitely
2. **No retention policies** - No configurable rules for memory lifecycle management
3. **Storage cost optimization** - Embeddings (1536 floats × 4 bytes = ~6KB per memory) accumulate without consolidation
4. **No tiered storage** - All memories stored with equal priority regardless of usage patterns
5. **Limited consolidation** - No merging of similar memories or deduplication

---

## 1. Business Requirements

### 1.1 Primary Objectives

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| BR-001 | Reduce active memory storage costs by 40% within 6 months | High | Embedding storage scales linearly with task execution |
| BR-002 | Maintain >95% retrieval relevance for recent memories (< 30 days) | High | Agent performance depends on context availability |
| BR-003 | Enable configurable retention policies per memory type | Medium | Different memory types have different value decay rates |
| BR-004 | Provide audit trail for all memory lifecycle operations | High | Compliance and debugging requirements |
| BR-005 | Support manual override of automated consolidation decisions | Medium | Operator control for edge cases |

### 1.2 Success Criteria

- **Storage Efficiency**: Active memory table size stabilizes despite continued task execution
- **Performance Impact**: Memory search latency increases by <10% after consolidation
- **Data Preservation**: No loss of high-value memories (top 20% by reuse count)
- **Operational Overhead**: Consolidation runs autonomously with <5% CPU impact

---

## 2. Functional Requirements

### 2.1 Memory Consolidation Engine

| ID | Requirement | Description | Acceptance Criteria |
|----|-------------|-------------|---------------------|
| FR-001 | **Automatic Consolidation Trigger** | System initiates consolidation based on configurable thresholds | - Consolidation triggers when table exceeds threshold<br>- Configurable thresholds: row count, storage size, time interval |
| FR-002 | **Memory Value Scoring** | Calculate consolidation priority score per memory | - Score = f(reused_count, recency, memory_type, success)<br>- Scores calculated in batch for efficiency |
| FR-003 | **Tiered Storage Classification** | Classify memories into hot/warm/cold tiers | - Hot: Last 30 days OR top 10% score<br>- Warm: 31-90 days OR 10-30% score<br>- Cold: >90 days OR bottom 70% score |
| FR-004 | **Memory Archival** | Move cold memories to archival storage | - Cold memories moved to `archived_memories` table<br>- Embeddings removed from active table<br>- Metadata preserved for restoration |
| FR-005 | **Memory Deletion** | Permanently delete expired low-value memories | - Memories older than retention period deleted<br>- Requires confirmation from retention policy<br>- Audit log entry created |
| FR-006 | **Memory Consolidation** | Merge semantically similar memories | - Similarity threshold > 0.95<br>- Combined memory aggregates reuse counts<br>- Original memory IDs preserved in linkage |

### 2.2 Retention Policy Management

| ID | Requirement | Description | Acceptance Criteria |
|----|-------------|-------------|---------------------|
| FR-007 | **Policy CRUD Operations** | Create, read, update, delete retention policies | - Policies stored in database<br>- API endpoints for policy management<br>- Validation prevents conflicts |
| FR-008 | **Memory-Type-Specific Policies** | Different retention per memory type | - Each of 6 memory types can have unique policy<br>- Default policy applies if unspecified |
| FR-009 | **Policy Priority Resolution** | Resolve conflicts when multiple policies apply | - Explicit policy beats default<br>- More specific policy wins<br>- Audit trail of policy application |
| FR-010 | **Policy Evaluation Engine** | Determine applicable policy for each memory | - Evaluates policies in priority order<br>- Caches policy decisions for batch processing |
| FR-011 | **Policy Versioning** | Track policy changes over time | - Historical policy versions maintained<br>- Policies effective-dated<br>- Rollback capability |

### 2.3 Restoration and Retrieval

| ID | Requirement | Description | Acceptance Criteria |
|----|-------------|-------------|---------------------|
| FR-012 | **Archived Memory Search** | Search across archived memories | - Separate search endpoint for archives<br>- Results include archived_at timestamp<br>- Restoration option in results |
| FR-013 | **Memory Restoration** | Restore archived memory to active storage | - Single or bulk restoration<br>- Recalculates embedding on restore<br>- Updates restoration metadata |
| FR-014 | **Unified Memory Search** | Optionally include archives in main search | - Configuration flag to include archives<br>- Archives ranked lower in results<br>- Clear indication of archived status |
| FR-015 | **Restoration Justification** | Track why memory was restored | - Reason required for manual restore<br>- Automatic restoration logs triggering event |

### 2.4 Monitoring and Reporting

| ID | Requirement | Description | Acceptance Criteria |
|----|-------------|-------------|---------------------|
| FR-016 | **Consolidation Metrics** | Track consolidation operations | - Memories archived/deleted count<br>- Storage saved calculation<br>- Execution time tracking |
| FR-017 | **Policy Compliance Dashboard** | Visual overview of retention compliance | - Memories per policy status<br>- Upcoming expirations forecast<br>- Policy violation alerts |
| FR-018 | **Memory Value Analytics** | Analyze memory usage patterns | - Reuse distribution by type/age<br>- Value score trends<br>- Retention policy effectiveness |
| FR-019 | **Consolidation Events Log** | Detailed audit trail | - Every consolidation operation logged<br>- Before/after state captured<br>- Operator actions recorded |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement | Metric | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Consolidation Throughput | Process >10,000 memories/hour | Batch processing benchmark |
| NFR-002 | Search Latency | <200ms p95 for active memory search | APM monitoring |
| NFR-003 | Archive Search Latency | <500ms p95 for archive search | APM monitoring |
| NFR-004 | Storage Optimization | Reduce embedding storage by 40% | Database size metrics |

### 3.2 Reliability

| ID | Requirement | Metric | Measurement |
|----|-------------|--------|-------------|
| NFR-005 | Data Integrity | Zero data loss during consolidation | Checksum validation |
| NFR-006 | Recovery Capability | Restore from any archival point | Disaster recovery testing |
| NFR-007 | Failure Handling | Rollback on consolidation failure | Transactional operations |

### 3.3 Security

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-008 | Access Control | Role-based permissions for consolidation operations |
| NFR-009 | Audit Trail | Immutable log of all policy and data changes |
| NFR-010 | Secure Deletion | Embeddings securely scrubbed before deletion |

### 3.4 Maintainability

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-011 | Configuration | Consolidation settings externally configurable |
| NFR-012 | Observability | Metrics exported for monitoring |
| NFR-013 | Testability | Consolidation logic fully unit tested |

---

## 4. Data Model Extensions

### 4.1 New Tables

#### `memory_retention_policies`
```sql
CREATE TABLE memory_retention_policies (
    id UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    memory_type VARCHAR(50),  -- NULL = applies to all types
    retention_days INTEGER NOT NULL,
    archive_before_delete BOOLEAN DEFAULT TRUE,
    min_reuse_count INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    effective_until TIMESTAMP WITH TIME ZONE
);
```

#### `archived_task_memories`
```sql
CREATE TABLE archived_task_memories (
    id UUID PRIMARY KEY,
    original_memory_id UUID NOT NULL,
    task_id VARCHAR NOT NULL,
    execution_summary TEXT NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    goal TEXT,
    result TEXT,
    feedback TEXT,
    tool_usage JSONB,
    success BOOLEAN NOT NULL,
    error_patterns JSONB,
    learned_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reused_count INTEGER NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    archive_reason VARCHAR(100),
    consolidation_score FLOAT,
    policy_id UUID REFERENCES memory_retention_policies(id),
    embedding_removed BOOLEAN DEFAULT TRUE,
    restoration_count INTEGER DEFAULT 0,
    last_restored_at TIMESTAMP WITH TIME ZONE
);
```

#### `memory_consolidation_log`
```sql
CREATE TABLE memory_consolidation_log (
    id UUID PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL,  -- archive, delete, consolidate, restore
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    memories_processed INTEGER NOT NULL,
    memories_archived INTEGER DEFAULT 0,
    memories_deleted INTEGER DEFAULT 0,
    memories_consolidated INTEGER DEFAULT 0,
    memories_restored INTEGER DEFAULT 0,
    storage_saved_bytes BIGINT,
    status VARCHAR(50) NOT NULL,  -- running, completed, failed, rolled_back
    error_message TEXT,
    triggered_by VARCHAR(100),  -- automatic, manual, schedule
    triggered_by_user_id UUID,
    configuration_snapshot JSONB,
    metadata JSONB
);
```

#### `memory_consolidation_links`
```sql
CREATE TABLE memory_consolidation_links (
    id UUID PRIMARY KEY,
    primary_memory_id UUID NOT NULL,  -- The surviving consolidated memory
    merged_memory_id UUID NOT NULL,   -- Memory that was merged
    similarity_score FLOAT NOT NULL,
    consolidated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    consolidation_log_id UUID REFERENCES memory_consolidation_log(id)
);
```

### 4.2 Model Extensions

#### `task_memory` Table Additions
```sql
ALTER TABLE task_memories
ADD COLUMN consolidation_score FLOAT,
ADD COLUMN is_consolidated BOOLEAN DEFAULT FALSE,
ADD COLUMN consolidation_id UUID REFERENCES memory_consolidation_log(id),
ADD COLUMN archived BOOLEAN DEFAULT FALSE,
ADD COLUMN archived_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN restoration_count INTEGER DEFAULT 0;
```

---

## 5. Architecture Design

### 5.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Consolidation Orchestrator                          │
│  - Schedules consolidation runs                                            │
│  - Monitors thresholds                                                     │
│  - Coordinates workers                                                     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                   ┌───────────────┼───────────────┐
                   │               │               │
                   ▼               ▼               ▼
        ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
        │ Value Scorer     │ │ Policy       │ │ Consolidation     │
        │ - Calculates     │ │ Engine       │ │ Workers           │
        │   priority       │ │ - Evaluates  │ │ - Archiver        │
        │   scores         │ │   policies   │ │ - Deleter         │
        │ - Batch          │ │ - Resolves   │ │ - Merger          │
        │   processing     │ │   conflicts  │ │ - Restorer        │
        └──────────────────┘ └──────────────┘ └──────────────────┘
                   │               │                    │
                   └───────────────┼────────────────────┘
                                   ▼
                        ┌──────────────────────┐
                        │ Audit & Event Bus    │
                        │ - Logs all actions   │
                        │ - Publishes events   │
                        └──────────────────────┘
```

### 5.2 Consolidation Workflow

```
                    ┌─────────────────┐
                    │ Threshold Check │
                    │ (Storage/Count/ │
                    │   Schedule)     │
                    └────────┬────────┘
                             │ Yes
                             ▼
                    ┌─────────────────┐
                    │  Score Memories │
                    │  (Value = f(    │
                    │   reuse, age,   │
                    │   type))        │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ Classify Tiers  │
                    │ (Hot/Warm/Cold) │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │Apply Policies   │
                    │ (Determine      │
                    │  Action per     │
                    │  Memory)        │
                    └────────┬────────┘
                             ▼
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
     ┌─────────────────┐         ┌─────────────────┐
     │   Archive Cold  │         │  Delete         │
     │   (Move to      │         │  (Expired       │
     │    archive tbl) │         │   Low Value)    │
     └─────────────────┘         └─────────────────┘
              │
              ▼
     ┌─────────────────┐
     │ Detect Similar  │
     │ (Merge >0.95    │
     │  similarity)    │
     └────────┬────────┘
              ▼
     ┌─────────────────┐
     │  Log & Publish  │
     │  Events         │
     └─────────────────┘
```

### 5.3 Value Scoring Algorithm

```python
def calculate_consolidation_score(memory: TaskMemory) -> float:
    """
    Calculate consolidation priority score (0.0 to 1.0).

    Higher score = More valuable = Keep in active storage
    Lower score = Less valuable = Candidate for archival

    Formula:
    score = (w1 * normalized_reuse) +
            (w2 * recency_factor) +
            (w3 * type_weight) +
            (w4 * success_bonus)

    Weights (configurable):
    - w1 (reuse): 0.35
    - w2 (recency): 0.25
    - w3 (type): 0.25
    - w4 (success): 0.15
    """
    import math
    from datetime import timedelta

    # Normalize reuse count (log scale to handle outliers)
    normalized_reuse = math.log1p(memory.reused_count) / 10  # 0-1 range

    # Recency factor (exponential decay)
    days_old = (utc_now() - memory.learned_at).days
    recency_factor = math.exp(-days_old / 90)  # 90-day half-life

    # Memory type weights
    type_weights = {
        "error_fix": 0.9,      # High value - fixes are reusable
        "decision": 0.8,       # High value - decision context
        "codebase_knowledge": 0.85,  # High value - structural
        "warning": 0.6,        # Medium - prevents errors
        "learning": 0.7,       # Medium - insights
        "discovery": 0.5,      # Lower - one-time findings
    }
    type_weight = type_weights.get(memory.memory_type, 0.5)

    # Success bonus
    success_bonus = 1.0 if memory.success else 0.3

    # Calculate weighted score
    score = (
        0.35 * normalized_reuse +
        0.25 * recency_factor +
        0.25 * type_weight +
        0.15 * success_bonus
    )

    return min(1.0, max(0.0, score))
```

---

## 6. API Specification

### 6.1 Consolidation Management API

#### POST /api/v1/memory/consolidation/run
**Description:** Trigger manual consolidation run

**Request Body:**
```json
{
  "dry_run": true,
  "force": false,
  "filters": {
    "memory_types": ["discovery"],
    "min_age_days": 90
  }
}
```

**Response:**
```json
{
  "consolidation_id": "uuid",
  "status": "running",
  "estimated_memories": 1234,
  "estimated_storage_saved_bytes": 8472832
}
```

#### GET /api/v1/memory/consolidation/status/{id}
**Description:** Get consolidation run status

**Response:**
```json
{
  "id": "uuid",
  "status": "completed",
  "started_at": "2026-01-08T10:00:00Z",
  "completed_at": "2026-01-08T10:15:23Z",
  "memories_processed": 1523,
  "memories_archived": 892,
  "memories_deleted": 234,
  "memories_consolidated": 45,
  "storage_saved_bytes": 12458723,
  "errors": []
}
```

### 6.2 Retention Policy API

#### POST /api/v1/memory/retention/policies
**Description:** Create retention policy

**Request Body:**
```json
{
  "name": "discovery-90-day",
  "description": "Archive discovery memories after 90 days",
  "memory_type": "discovery",
  "retention_days": 90,
  "archive_before_delete": true,
  "min_reuse_count": 2,
  "priority": 10
}
```

#### GET /api/v1/memory/retention/policies
**Description:** List all retention policies

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "discovery-90-day",
    "memory_type": "discovery",
    "retention_days": 90,
    "min_reuse_count": 2,
    "priority": 10,
    "is_active": true,
    "effective_from": "2026-01-08T00:00:00Z"
  }
]
```

### 6.3 Archive Management API

#### POST /api/v1/memory/archives/search
**Description:** Search archived memories

**Request Body:**
```json
{
  "query": "OAuth authentication implementation",
  "memory_types": ["error_fix", "discovery"],
  "archived_after": "2025-01-01T00:00:00Z",
  "archived_before": "2025-12-31T23:59:59Z",
  "limit": 20
}
```

#### POST /api/v1/memory/archives/{id}/restore
**Description:** Restore archived memory to active storage

**Request Body:**
```json
{
  "reason": "Required for new authentication task",
  "recalculate_embedding": true
}
```

---

## 7. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Core data model and basic consolidation

- [ ] Create database migrations for new tables
- [ ] Implement `MemoryConsolidationService` class
- [ ] Build value scoring algorithm
- [ ] Create tier classification logic
- [ ] Implement basic archival worker
- [ ] Add unit tests for scoring logic

**Deliverables:**
- Migrations applied
- Consolidation service with archiving capability
- Test coverage >80%

### Phase 2: Policy Engine (Weeks 3-4)
**Goal:** Retention policy management

- [ ] Implement `RetentionPolicyService`
- [ ] Build policy evaluation engine
- [ ] Create policy CRUD API endpoints
- [ ] Add policy conflict resolution
- [ ] Implement policy versioning
- [ ] Add integration tests

**Deliverables:**
- Policy management API
- Policy evaluation engine
- API documentation

### Phase 3: Advanced Consolidation (Weeks 5-6)
**Goal:** Consolidation and deletion workers

- [ ] Implement similarity-based memory merger
- [ ] Build deletion worker with safety checks
- [ ] Create restoration service
- [ ] Add archive search capability
- [ ] Implement rollback mechanism
- [ ] Performance optimization

**Deliverables:**
- Full consolidation pipeline
- Archive search endpoint
- Restoration API

### Phase 4: Monitoring & Automation (Weeks 7-8)
**Goal:** Automation and observability

- [ ] Implement consolidation scheduler
- [ ] Create metrics collection
- [ ] Build compliance dashboard
- [ ] Add alerting for policy violations
- [ ] Create audit log viewer
- [ ] Performance tuning

**Deliverables:**
- Automated consolidation runs
- Monitoring dashboard
- Alert configuration

---

## 8. Testing Strategy

### 8.1 Unit Tests

| Component | Test Coverage | Key Scenarios |
|-----------|---------------|---------------|
| Value Scorer | 95%+ | Edge cases, boundary values |
| Policy Engine | 90%+ | Conflict resolution, priority |
| Archiver | 90%+ | Transaction safety, rollback |
| Merger | 85%+ | Similarity thresholds |
| REST API | 85%+ | Validation, error handling |

### 8.2 Integration Tests

- End-to-end consolidation workflow
- Policy application across memory types
- Archive search and restoration
- Concurrent consolidation runs
- Database transaction rollback

### 8.3 Performance Tests

- 100K memory consolidation run
- Search latency with archives
- Concurrent user load on policy API
- Storage optimization validation

### 8.4 Chaos Testing

- Database connection failures
- Partial consolidation failures
- Concurrent consolidation attempts
- Policy conflicts during active consolidation

---

## 9. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Accidental data loss** | Critical | Low | - Transactional operations<br>- Dry-run mode<br>- Approval workflows for deletions |
| **Performance degradation** | High | Medium | - Run consolidation off-peak<br>- Rate limit operations<br>- Monitor and pause if impact detected |
| **Incorrect policy application** | High | Medium | - Policy validation<br>- Preview mode<br>- Audit trail for review |
| **Storage cost miscalculation** | Medium | Low | - Pilot with subset<br>- Measure before/after<br>- Gradual rollout |
| **Restoration complexity** | Medium | Medium | - Automated restoration<br>- Batch operations<br>- Version tracking |

---

## 10. Operational Considerations

### 10.1 Configuration Parameters

```yaml
consolidation:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  thresholds:
    max_active_memories: 100000
    max_storage_gb: 50
    min_interval_hours: 24
  scoring:
    reuse_weight: 0.35
    recency_weight: 0.25
    type_weight: 0.25
    success_weight: 0.15
  tiers:
    hot:
      max_age_days: 30
      min_score_percentile: 90
    warm:
      max_age_days: 90
      min_score_percentile: 70
    cold:
      min_age_days: 90
      max_score_percentile: 70
  operations:
    batch_size: 1000
    parallel_workers: 4
    dry_run_default: false
```

### 10.2 Monitoring Metrics

- `consolidation_run_duration_seconds`
- `consolidation_memories_processed_total`
- `consolidation_storage_saved_bytes`
- `consolidation_errors_total`
- `memory_archive_search_latency_seconds`
- `policy_evaluation_duration_seconds`
- `active_memories_count`
- `archived_memories_count`

### 10.3 Alerting Rules

- **Critical:** Consolidation failure >3 consecutive runs
- **Warning:** Active memory storage >80% threshold
- **Info:** Daily consolidation summary
- **Warning:** Policy violation detected
- **Critical:** Data integrity check failure

---

## 11. References and Research

### Industry Research

1. **[AI Memory Systems: A Deep Dive into Cognitive Architecture](https://pub.towardsai.net/ai-memory-systems-a-deep-dive-into-cognitive-architecture-83190b3e1ac5)** (2025)
   - Covers access control for memory access and data retention policies

2. **[Vector Storage Based Long-term Memory Research on LLM](https://www.researchgate.net/publication/384803161_Vector_Storage_Based_Long-term_Memory_Research_on_LLM)** (2025)
   - VIMBank model for enhancing long-term context retention

3. **[Building Memory Architectures for AI Agents](https://hackernoon.com/llms-vector-databases-building-memory-architectures-for-ai-agents)** (2025)
   - Indexing strategies and hierarchical memory approaches

4. **[Vector Embeddings at Scale: Guide to Cutting Storage Costs](https://www.linkedin.com/pulse/vector-embeddings-scale-guide-cutting-storage-costs-90-rajni-singh-cwh6c)**
   - Strategies for optimizing embedding storage budgets

5. **[Data Retention Guide 2026](https://concentric.ai/a-technical-guide-to-data-retention/)**
   - Frameworks for data retention, archival, and secure deletion

### Internal References

- `docs/page_flows/12_agent_memory.md` - Current memory system architecture
- `backend/omoi_os/models/task_memory.py` - TaskMemory model definition
- `backend/omoi_os/services/memory.py` - MemoryService implementation
- `backend/omoi_os/services/ace_engine.py` - ACE workflow orchestration
- `backend/omoi_os/services/resource_lock.py` - Reference for cleanup patterns

---

## 12. Glossary

| Term | Definition |
|------|------------|
| **Active Storage** | Primary database table (`task_memories`) for frequently accessed memories |
| **Archival Storage** | Secondary table (`archived_task_memories`) for infrequently accessed memories |
| **Consolidation** | Process of optimizing memory storage through archival, deletion, and merging |
| **Memory Tier** | Classification (hot/warm/cold) based on access patterns and value |
| **Retention Policy** | Rules defining how long memories should be kept and when to archive/delete |
| **Value Score** | Calculated priority (0-1) indicating memory value for consolidation decisions |
| **ACE Workflow** | Aggregation, Consolidation, Extraction workflow for task-to-knowledge transformation |
| **Embedding** | 1536-dimensional vector representing semantic content of memory |

---

## Appendix A: Consolidation Score Examples

| Memory Type | Reuse Count | Age (Days) | Success | Calculated Score | Action |
|-------------|-------------|------------|---------|------------------|--------|
| error_fix | 15 | 20 | true | 0.82 | Keep (Hot) |
| discovery | 0 | 120 | true | 0.35 | Archive |
| decision | 5 | 45 | true | 0.65 | Keep (Warm) |
| warning | 2 | 200 | true | 0.48 | Archive |
| codebase_knowledge | 8 | 10 | true | 0.88 | Keep (Hot) |
| error_fix | 1 | 400 | false | 0.25 | Delete |

---

## Appendix B: Sample Retention Policies

```yaml
# Default policy - applies to all memories without specific policy
- name: default-365-day
  memory_type: null
  retention_days: 365
  archive_before_delete: true
  min_reuse_count: 0
  priority: 0

# High-value policies
- name: error-fix-keep-forever
  memory_type: error_fix
  retention_days: -1  # Never auto-delete
  archive_before_delete: false
  min_reuse_count: 5
  priority: 100

- name: decision-keep-2-years
  memory_type: decision
  retention_days: 730
  archive_before_delete: true
  min_reuse_count: 2
  priority: 90

# Standard policies
- name: discovery-90-day
  memory_type: discovery
  retention_days: 90
  archive_before_delete: true
  min_reuse_count: 0
  priority: 50

- name: learning-180-day
  memory_type: learning
  retention_days: 180
  archive_before_delete: true
  min_reuse_count: 1
  priority: 50

# Low-value policies
- name: warning-60-day
  memory_type: warning
  retention_days: 60
  archive_before_delete: true
  min_reuse_count: 0
  priority: 30
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-08 | System | Initial requirements analysis |

---

*This document is the output of an exploration and research task. No implementation code has been written. The next step would be to review these requirements with stakeholders and create a detailed implementation plan.*
