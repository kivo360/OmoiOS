---
id: PRD-AMC-001
title: Agent Memory Consolidation System PRD
feature: agent-memory-consolidation
created: 2025-01-08
updated: 2025-01-08
status: draft
author: Claude
---

# Agent Memory Consolidation System

## Executive Summary

The Agent Memory Consolidation System is a background knowledge synthesis service that transforms raw task execution memories into higher-level insights, patterns, and principles. As AI agents complete tasks, they accumulate individual memories stored in the `task_memories` table. Without consolidation, this leads to memory overload, redundant information, and difficulty finding relevant knowledge. The consolidation system solves this by periodically analyzing accumulated memories, identifying patterns, merging redundancies, and creating hierarchical knowledge structures that agents can efficiently query.

The system extends the existing memory infrastructure (TaskMemory, MemoryService, hybrid search) with new consolidation capabilities while maintaining full traceability to source memories. It integrates seamlessly with the existing ACE workflow and agent tools.

## Problem Statement

### Current State

The existing memory system (defined in `/workspace/docs/requirements/memory/memory_system.md`) provides:
- Individual task memory storage with embeddings
- Memory type classification (error_fix, discovery, decision, learning, warning, codebase_knowledge)
- Hybrid search (semantic + keyword)
- ACE workflow for automatic memory creation
- Reuse tracking via `reused_count` field

**Critical gaps**:
1. **Memory Overload**: As agents complete hundreds of tasks, the memories table grows linearly, making search slower and results noisier
2. **No Synthesis**: Raw execution logs don't extract higher-level patterns or principles
3. **Redundancy**: Similar tasks create duplicate memories (e.g., five separate "fixed auth middleware bug" memories)
4. **Knowledge Silos**: Each agent's learnings aren't synthesized into shared project wisdom

### Desired State

After consolidation, the system will:
- Maintain a condensed, high-signal knowledge base
- Provide multi-level knowledge access (raw → consolidated → abstract)
- Auto-generate playbook entries from patterns
- Enable agents to query both specific memories and general principles
- Track consolidation lineage (what memories created what insights)

### Impact of Not Building

Without consolidation:
- Memory search quality degrades as memory count grows (signal-to-noise ratio drops)
- Agents repeat mistakes because they can't see patterns across past tasks
- No institutional knowledge accumulation—only raw execution logs
- Scaling to larger projects becomes impractical (tens of thousands of memories)

## Goals & Success Metrics

### Primary Goals

1. **Reduce memory redundancy**: Merge similar memories while preserving unique information
2. **Extract actionable patterns**: Identify recurring success/failure patterns across tasks
3. **Create knowledge hierarchy**: Organize memories into levels (raw, consolidated, abstract)
4. **Enrich playbook**: Auto-generate and update playbook entries from consolidated insights
5. **Maintain traceability**: Keep full lineage from consolidated memories back to sources

### Success Metrics

| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| Memory count reduction | N/A | 30-50% reduction after consolidation | Compare pre/post consolidation memory counts |
| Search relevance (top-10 precision) | ~60% | >85% | User feedback on search results |
| Pattern extraction rate | 0% | >5 patterns per 100 memories | Count patterns in consolidated_memories table |
| Consolidation time | N/A | <5 min per 1000 memories | Background job duration metrics |
| Agent query latency | ~200ms | <100ms for consolidated queries | API response time metrics |

## User Stories

### Primary User: AI Agent (Worker, Monitor, Watchdog)

1. **Access Consolidated Knowledge**
   As a worker agent, I want to query consolidated memories so that I can access higher-level patterns without searching through hundreds of raw memories.

   Acceptance Criteria:
   - [ ] Agent can call `consolidated_memory_search` tool
   - [ ] Results include both patterns and supporting raw memories
   - [ ] Query latency <100ms for consolidated knowledge

2. **Contribute to Consolidation**
   As a worker agent, I want my task memories to be automatically consolidated so that future agents benefit from my learnings without manual curation.

   Acceptance Criteria:
   - [ ] Completed tasks trigger consolidation evaluation
   - [ ] Consolidation runs in background without blocking agent
   - [ ] Agent receives notification when consolidation completes

### Secondary User: System Administrator

3. **Manual Consolidation Control**
   As a system administrator, I want to trigger consolidation on-demand so that I can force knowledge synthesis before important milestones.

   Acceptance Criteria:
   - [ ] Admin API endpoint: `POST /admin/consolidate-memories`
   - [ ] Returns job ID for tracking
   - [ ] Webhook notification on completion

4. **Monitor Consolidation Health**
   As a system administrator, I want to see consolidation metrics so that I can ensure the system is working correctly.

   Acceptance Criteria:
   - [ ] Dashboard shows: total memories, consolidated count, last run time, next scheduled run
   - [ ] Alerts for consolidation failures or anomalies
   - [ ] Export consolidation lineage report

### Tertiary User: Developer/Human Analyst

5. **Explore Consolidated Knowledge**
   As a developer, I want to browse consolidated memories and patterns so that I can understand what the system has learned.

   Acceptance Criteria:
   - [ ] Web UI shows consolidated memories with drill-down to sources
   - [ ] Filter by memory type, confidence, date range
   - [ ] Visual representation of memory hierarchy

## Scope

### In Scope

- **Consolidation Engine**: Background service that analyzes and consolidates memories
- **Pattern Extraction**: Identify recurring patterns using LLM and heuristics
- **Memory Merging**: Combine highly similar memories (>0.95 similarity)
- **Hierarchy Creation**: Create multi-level memory structures
- **Playbook Integration**: Auto-generate playbook entries from consolidated insights
- **Traceability**: Maintain full lineage (consolidated_memory → source memories)
- **Agent Tools**: New tools for querying consolidated knowledge
- **Admin API**: Endpoints for manual consolidation and monitoring
- **Scheduling**: Configurable consolidation triggers (time-based, threshold-based)

### Out of Scope

- **Cross-project consolidation** (single project scope only)
- **Memory deletion/archival** (consolidation adds, doesn't remove)
- **Manual memory editing** (automation-only approach)
- **Real-time consolidation** (async batch processing only)
- **Multi-modal memories** (text-only, no image/audio support)

### Future Considerations

- Consolidation across multiple projects (organization-level patterns)
- User feedback loop for consolidations (thumbs up/down to improve quality)
- Memory archival policy (auto-archive old raw memories)
- Real-time consolidation streaming
- Cross-agent learning (consolidate across different agent types)

## Constraints

### Technical Constraints

- **Must integrate with existing memory system**: TaskMemory, MemoryService, hybrid search
- **Must use existing database**: PostgreSQL with pgvector (already configured)
- **Must use existing embedding service**: OpenAI text-embedding-3-large
- **Must work with existing agent tools**: Planning tools, task tools
- **Background processing only**: No blocking consolidation during agent execution
- **LLM budget**: Prefer efficient consolidation (minimize API calls)

### Business Constraints

- **No breaking changes**: Existing memory APIs must continue working
- **Backward compatible**: Old agents without consolidation tools must still function
- **Cost aware**: Consolidation should not significantly increase LLM costs

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Poor quality consolidations (LLM hallucinations) | Medium | High | Use confidence thresholds, manual review workflow, pattern validation |
| Consolidation too slow (blocks system) | Low | Medium | Background jobs with timeouts, incremental consolidation |
| Over-consolidation (loss of nuance) | Medium | Medium | Conservative similarity thresholds, keep raw memories |
| Agent confusion (raw vs consolidated) | Medium | Low | Clear tool naming, documentation, examples |
| Database load during consolidation | Low | Medium | Rate limiting, off-peak scheduling, read replicas |

## Dependencies

- **Existing memory system**: TaskMemory model, MemoryService, hybrid search
- **Existing embedding service**: EmbeddingService (OpenAI)
- **Existing task queue**: TaskQueueService for background jobs
- **Existing agent tools**: Planning tools, SearchSimilarTasksTool
- **PostgreSQL extensions**: pgvector (already installed)

## Open Questions

- [ ] What should be the default consolidation schedule? (Proposed: nightly + every 100 memories)
- [ ] Should consolidation be automatic or opt-in per project? (Proposed: automatic, configurable)
- [ ] How to handle conflicting patterns from similar memories? (Proposed: keep both with confidence scores)
- [ ] Should raw memories be soft-deleted after consolidation? (Proposed: no, keep for traceability)
