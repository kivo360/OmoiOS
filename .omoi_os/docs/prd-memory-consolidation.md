---
id: PRD-MEMCONS-001
title: Agent Memory Consolidation System PRD
feature: memory-consolidation
created: 2025-01-08
updated: 2025-01-08
status: draft
author: Claude
---

# Agent Memory Consolidation System

## Executive Summary

The Agent Memory Consolidation System adds automated memory management capabilities to the existing Agent Memory System. As agents create memories during task execution, the memory store grows with many similar, redundant, or low-value entries. This feature introduces intelligent consolidation operations that merge similar memories, synthesize higher-level insights from groups of related memories, archive stale memories, and promote high-value patterns to the playbook.

The consolidation system operates through both scheduled background jobs and manual triggers, using semantic similarity clustering and LLM-based synthesis to maintain a lean, high-value memory store while preserving important knowledge.

## Problem Statement

### Current State

The existing Agent Memory System (as defined in `docs/requirements/memory/memory_system.md`) provides robust storage and retrieval of task execution memories. However, as agents work continuously:

1. **Memory proliferation**: Each task execution creates a new memory, leading to thousands of entries that become difficult to navigate
2. **Semantic duplication**: Multiple agents (or the same agent over time) create memories about the same concept with slight variations
3. **Information decay**: Older memories may reference outdated code patterns or architectural decisions
4. **Search degradation**: Hybrid search performance degrades as memory count increases
5. **Noise accumulation**: Low-value or transient memories dilute the signal from important insights

### Desired State

After implementing memory consolidation:

1. **Lean memory store**: Similar memories are automatically merged into consolidated entries
2. **Knowledge synthesis**: Groups of related memories are synthesized into higher-level insights
3. **Smart archiving**: Stale or rarely-used memories are archived to maintain performance
4. **Automatic promotion**: High-confidence patterns are promoted to playbook entries
5. **Audit trail**: All consolidation operations are tracked and reversible

### Impact of Not Building

Without consolidation, the memory system will suffer from:
- Degraded search performance as vector index grows
- Difficulty finding relevant information due to noise
- Increased storage costs without proportional value
- Poor user experience when reviewing memory history

## Goals & Success Metrics

### Primary Goals

1. **Reduce memory count by 40-60%** through intelligent merging while preserving unique knowledge
2. **Maintain or improve search relevance** after consolidation operations
3. **Provide full auditability** of all consolidation changes with rollback capability
4. **Enable automated knowledge synthesis** from groups of related memories

### Success Metrics

| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| Memory reduction rate | N/A | 40-60% reduction | Compare pre/post consolidation counts |
| Search latency P95 | <100ms | <100ms | Hybrid search benchmarks |
| Consolidation confidence | N/A | >0.85 auto-approval | Track confidence scores |
| Knowledge preservation | N/A | <5% information loss | Manual sampling audit |
| Processing time | N/A | <30s for 1000 memories | Consolidation job duration |

## User Stories

### Primary User: System Administrator

1. **Manual Consolidation Trigger**
   As a system administrator, I want to manually trigger consolidation for a project so that I can control when memory optimization occurs.

   Acceptance Criteria:
   - [ ] API endpoint exists to trigger consolidation
   - [ ] Returns job ID for tracking
   - [ ] Supports options (merge, archive, promote)
   - [ ] Requires admin authentication

2. **View Consolidation History**
   As a system administrator, I want to view consolidation history so that I can understand what changes were made and why.

   Acceptance Criteria:
   - [ ] API returns list of consolidation operations
   - [ ] Shows before/after memory counts
   - [ ] Links to affected memory IDs
   - [ ] Allows filtering by date and operation type

3. **Rollback Consolidation**
   As a system administrator, I want to rollback a consolidation operation so that I can recover if incorrect consolidations were applied.

   Acceptance Criteria:
   - [ ] Rollback endpoint accepts consolidation_id
   - [ ] Restores original memory state
   - [ ] Records rollback in audit log
   - [ ] Validates no conflicting changes exist

### Secondary User: Agent (Automatic)

4. **Post-Task Consolidation Check**
   As an agent, I want the system to automatically check if consolidation is needed after I complete a task so that memory quality is maintained without manual intervention.

   Acceptance Criteria:
   - [ ] System checks memory count threshold after each task
   - [ ] Triggers background consolidation if threshold exceeded
   - [ ] Does not block task completion
   - [ ] Publishes event when consolidation completes

## Scope

### In Scope

- **Memory merging**: Detect and merge semantically similar memories using embedding similarity
- **Memory summarization**: Create synthetic summary memories from clusters of related memories
- **Memory archiving**: Move old/unused memories to archived status with retrieval capability
- **Playbook promotion**: Automatically promote high-value consolidated memories to playbook entries
- **Scheduled consolidation**: Background job that runs periodically (configurable)
- **Manual trigger**: API endpoint to trigger consolidation on-demand
- **Audit logging**: Track all consolidation operations in `consolidation_changes` table
- **Rollback capability**: Ability to undo consolidation operations

### Out of Scope

- **Cross-project consolidation**: Each project's memories are consolidated independently (future)
- **Real-time consolidation during search**: Consolidation is a batch operation, not integrated into search (future)
- **Advanced conflict resolution**: Human-in-the-loop review is flagged but UI is not built (future)
- **Memory export to external systems**: Integration with external knowledge bases (future)
- **Tiered storage**: Cold storage to S3 or similar is tracked but not implemented (future)

### Future Considerations

- **Cross-project knowledge sharing**: Consolidate similar patterns across multiple projects
- **Incremental consolidation**: Real-time merging during memory creation
- **Machine learning clustering**: Use more sophisticated clustering algorithms beyond simple similarity
- **User feedback loop**: Allow agents/users to provide feedback on consolidation quality

## Constraints

### Technical Constraints

- Must integrate with existing `MemoryService` class in `omoi_os/services/memory.py`
- Must use existing embedding service (text-embedding-3-large, 3072 dimensions)
- Must work with PostgreSQL + pgvector for semantic search
- Consolidation jobs must run asynchronously to avoid blocking API requests
- Must maintain compatibility with existing ACE workflow

### Business Constraints

- Consolidation must not lose critical knowledge (information loss <5%)
- Must be configurable per project (some projects may disable consolidation)
- Audit trail must be retained for at least 90 days
- Rollback must be possible within 7 days of consolidation

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Over-aggressive merging loses important details | Medium | High | Conservative thresholds (0.95 similarity), track original memory IDs, enable rollback |
| Consolidation job causes performance degradation | Low | Medium | Run during low-traffic periods, use pagination, add rate limiting |
| Poor quality summary memories | Medium | Medium | Use LLM with quality validation, require confidence >0.8, flag for review |
| Conflicts with concurrent memory operations | Low | High | Use row-level locking, queue consolidations during high activity |
| Increased storage due to audit trail | Low | Low | Compact old audit records, configurable retention period |

## Dependencies

- **Existing Memory System**: Depends on `TaskMemory` model, `MemoryService` class
- **Embedding Service**: Requires existing embedding generation for similarity computation
- **Event Bus**: Uses `EventBusService` to publish consolidation events
- **Background Job System**: Requires task queue (Celery/RQ) for scheduled jobs
- **LLM Service**: Requires access to LLM for memory summarization (same as existing Reflector)

## Open Questions

- [ ] What should the default consolidation schedule be? (daily, weekly?)
- [ ] What is the memory count threshold to trigger automatic consolidation? (1000, 5000?)
- [ ] Should consolidation preserve all original memory IDs or only the canonical ID?
- [ ] How should we handle memories linked to files that have been deleted?
- [ ] Should playbook promotion require manual approval or be fully automatic?

## Related Documents

- [Memory System Requirements](../../../docs/requirements/memory/memory_system.md)
- [Memory System Design](../../../docs/design/memory/memory_system.md)
- [ACE Workflow Implementation](../../../docs/implementation/memory/phase5_memory_implementation.md)
