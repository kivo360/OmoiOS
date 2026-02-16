# OmoiOS Architecture: Dynamic Swarm Orchestration

> **This is the critical reference document for understanding OmoiOS.**
> Read this before diving into any specific component.
>
> Each section links to a deep-dive doc with full implementation details.

## Executive Summary

OmoiOS is an autonomous engineering platform that orchestrates multiple AI agents through a **spec-driven, discovery-enabled, self-adjusting workflow**. The system handles three core capabilities:

| Capability | System | Purpose |
|------------|--------|---------|
| **Plans** | Spec-Sandbox State Machine | Convert feature ideas into structured requirements, designs, and atomic tasks |
| **Discoveries** | DiscoveryService + Analyzer | Detect new work during execution and spawn adaptive branch tasks |
| **Readjustments** | MonitoringLoop + Guardian + Conductor | Monitor agent trajectories and intervene when goals drift |

**Production URLs:**
- Frontend: `https://omoios.dev`
- Backend API: `https://api.omoios.dev`

---

## Architecture Overview

```txt
                                 ┌─────────────────────────────────────────┐
                                 │              User / Frontend            │
                                 │  (Specs, Tickets, Tasks, Monitoring)    │
                                 └────────────────────┬────────────────────┘
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                       API Layer                                          │
│                         FastAPI Routes + WebSocket Events                                │
└───────────────┬─────────────────────────────┬───────────────────────────┬───────────────┘
                │                             │                           │
                ▼                             ▼                           ▼
┌───────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────┐
│     PLANNING SYSTEM       │   │    EXECUTION SYSTEM         │   │   READJUSTMENT SYSTEM   │
│  ┌─────────────────────┐  │   │  ┌─────────────────────┐    │   │  ┌─────────────────────┐│
│  │  Spec-Sandbox       │  │   │  │ OrchestratorWorker  │    │   │  │   MonitoringLoop    ││
│  │  State Machine      │  │   │  │ (task dispatch)     │    │   │  │  ┌───────────────┐  ││
│  │                     │  │   │  └──────────┬──────────┘    │   │  │  │   Guardian    │  ││
│  │ EXPLORE → PRD →     │  │   │             │               │   │  │  │  (trajectory) │  ││
│  │ REQUIREMENTS →      │  │   │             ▼               │   │  │  └───────────────┘  ││
│  │ DESIGN → TASKS →    │  │   │  ┌─────────────────────┐    │   │  │  ┌───────────────┐  ││
│  │ SYNC               │  │   │  │  DaytonaSpawner     │    │   │  │  │   Conductor   │  ││
│  │                     │  │   │  │  (sandbox creation) │    │   │  │  │  (coherence)  │  ││
│  └─────────────────────┘  │   │  └──────────┬──────────┘    │   │  │  └───────────────┘  ││
│           │               │   │             │               │   │  └─────────────────────┘│
│           ▼               │   │             ▼               │   │            │            │
│  ┌─────────────────────┐  │   │  ┌─────────────────────┐    │   │            ▼            │
│  │  Phase Evaluators   │  │   │  │ ClaudeSandboxWorker │    │   │  ┌─────────────────────┐│
│  │  (quality gates)    │  │   │  │ + EventReporter     │    │   │  │  Steering           ││
│  └─────────────────────┘  │   │  │ + MessagePoller     │    │   │  │  Interventions      ││
│           │               │   │  │ + FileChangeTracker │    │   │  └─────────────────────┘│
│           ▼               │   │  └──────────┬──────────┘    │   └─────────────────────────┘
│  ┌─────────────────────┐  │   │             │               │
│  │  HTTPReporter       │  │   │             │ (discoveries) │
│  │  (event streaming)  │  │   │             ▼               │
│  └─────────────────────┘  │   │  ┌─────────────────────┐    │
└───────────────────────────┘   │  │  DiscoveryService   │    │
                                │  │  (adaptive branch)  │    │
                                │  └─────────────────────┘    │
                                └─────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   DATA LAYER                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  MemoryService  │  │  ContextService │  │ SynthesisService│  │  DAG Merge      │     │
│  │  (hybrid search)│  │  (phase context)│  │ (parallel merge)│  │  System         │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  SpecDedup      │  │ EmbeddingService│  │  BillingService │  │ CostTracking    │     │
│  │  (hash+semantic)│  │  (pgvector 1536)│  │  (Stripe+tiers) │  │ (per-task LLM)  │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                                          │
│                          PostgreSQL + pgvector + Redis                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## System Deep-Dives

### 1. Planning System

Convert a high-level feature idea into structured, executable work units through a 7-phase pipeline: EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE. Each phase has an LLM evaluator (quality gate) that scores output and retries on failure. All phases use incremental writing to prevent data loss.

**Key components**: Spec-Sandbox State Machine, Phase Evaluators, HTTPReporter

[Deep-dive: Planning System →](docs/architecture/01-planning-system.md)

---

### 2. Execution System

Execute tasks in isolated Daytona sandboxes with full audit trail. The OrchestratorWorker polls for tasks, spawns sandboxes via DaytonaSpawner, and ClaudeSandboxWorker runs inside the sandbox using the Claude Agent SDK. Three execution modes: exploration (read-only), implementation (full access), and validation (test execution). Background workers handle task dispatch, stale cleanup, idle sandbox termination, and health monitoring.

**Key components**: OrchestratorWorker, DaytonaSpawner, ClaudeSandboxWorker, ContinuousSandboxWorker, IdleSandboxMonitor

[Deep-dive: Execution System →](docs/architecture/02-execution-system.md)

---

### 3. Discovery System

Enable adaptive workflow branching when agents discover new requirements during execution. The Hephaestus pattern allows discovery-based branching to bypass normal phase transitions — a Phase 3 validation agent can spawn Phase 1 investigation tasks. The DiscoveryAnalyzerService uses LLM-powered analysis to find recurring patterns, predict blockers, and recommend agent types.

**Key components**: DiscoveryService, DiscoveryAnalyzerService

[Deep-dive: Discovery System →](docs/architecture/03-discovery-system.md)

---

### 4. Readjustment System

Monitor agent trajectories and system coherence, intervening when agents drift from goals. The MonitoringLoop runs three background loops: Guardian (60s, per-agent trajectory analysis), Conductor (5min, system-wide coherence + duplicate detection), and Health Check (30s, critical state alerts). Steering interventions can redirect, refocus, or stop agents.

**Key components**: MonitoringLoop, IntelligentGuardian, ConductorService, ValidationOrchestrator

[Deep-dive: Readjustment System →](docs/architecture/04-readjustment-system.md) | [Monitoring Architecture →](docs/design/monitoring/monitoring_architecture.md)

---

### 5. Frontend Architecture

Next.js 15 App Router with ShadCN UI, dual state management (Zustand + React Query), and real-time WebSocket integration. Route groups separate auth flows from the dashboard shell. ~94 pages covering organization management, spec workspaces, Kanban boards, dependency graphs, statistics dashboards, and agent management.

**Key components**: Route groups, Zustand middleware stack, React Query cache, WebSocket bridge

[Deep-dive: Frontend Architecture →](docs/architecture/05-frontend-architecture.md) | [Design: Frontend Architecture →](docs/design/frontend/frontend_architecture_shadcn_nextjs.md) | [Page Architecture →](docs/page_architecture.md)

---

### 6. Real-Time Event System

Redis pub/sub EventBus for all inter-service communication with WebSocket forwarding to the frontend. Events cover agent lifecycle, task status, sandbox health, coordination, and monitoring updates. React Query cache invalidation and Zustand state sync both trigger from WebSocket events.

**Key components**: EventBusService, WebSocket server, Frontend event bridge

[Deep-dive: Real-Time Events →](docs/architecture/06-realtime-events.md) | [Design: React Query + WebSocket →](docs/design/frontend/react_query_websocket.md)

---

### 7. Authentication & Security

Self-hosted JWT authentication with bcrypt password hashing, refresh tokens, OAuth (GitHub/Google), and agent-scoped API keys. Organization-level RBAC with owner/admin/member/viewer roles. (Note: Supabase auth exists as a design alternative but was not implemented.)

**Key components**: AuthService, JWT middleware, OAuth routes, API key management

[Deep-dive: Auth & Security →](docs/architecture/07-auth-and-security.md) | [Design: Auth System Plan →](docs/design/auth/auth_system_plan.md)

---

### 8. Billing & Subscriptions

Full Stripe integration with 5 subscription tiers (Free/Pro/Team/Enterprise/Lifetime), prepaid credit purchases, usage-based billing, automated dunning (3 retries before suspension), promo codes, and per-task LLM cost tracking. Workflow execution is gated by `check_and_reserve_workflow()` before sandbox spawning. Background tasks handle monthly invoice generation, payment reminders, and low credit warnings.

**Key components**: BillingService, StripeService, SubscriptionService, CostTrackingService, BudgetEnforcerService

[Deep-dive: Billing & Subscriptions →](docs/architecture/08-billing-and-subscriptions.md)

---

### 9. MCP Integration

Model Context Protocol integration with circuit breakers, retry logic, authorization enforcement, and vector-based tool discovery. Per server+tool circuit breakers with exponential backoff retries.

**Key components**: MCPIntegrationService, Tool Registry, Authorization Engine, Circuit Breaker

[Deep-dive: MCP Integration →](docs/architecture/09-mcp-integration.md) | [Design: MCP Server Integration →](docs/design/integration/mcp_server_integration.md)

---

### 10. GitHub Integration

Branch management, commit tracking, pull request workflows, and webhook processing. Branches are created before sandbox spawning. Commits are automatically linked to tickets via regex matching in commit messages.

**Key components**: GitHubIntegrationService, DaytonaSpawner (branch creation), sandbox_git_operations

[Deep-dive: GitHub Integration →](docs/architecture/10-github-integration.md)

---

### 11. Database Schema

PostgreSQL 16 with pgvector for semantic search and deduplication, ~60 domain entities across SQLAlchemy 2.0+ models, and 71 Alembic migrations. 8 tables use `Vector(1536)` columns with IVFFlat indexes for cosine similarity search. PostgreSQL `tsvector` provides full-text keyword search for hybrid retrieval. Models cover core resources, workflow state, agent execution, monitoring, auth/billing, version control, memory, and quality.

**Key components**: SQLAlchemy models, Alembic migrations, pgvector embeddings, tsvector full-text search

[Deep-dive: Database Schema →](docs/architecture/11-database-schema.md)

---

### 12. Configuration System

Dual configuration: YAML files (version-controlled) for application settings with Pydantic validation, .env files (gitignored) for secrets. Priority: init args > env vars > YAML defaults. All config classes extend `OmoiBaseSettings` with `@lru_cache` factories.

**Key components**: OmoiBaseSettings, YAML loaders, environment-specific overrides

[Deep-dive: Configuration System →](docs/architecture/12-configuration-system.md) | [Design: Configuration Architecture →](docs/architecture/configuration/configuration_architecture.md)

---

### 13. API Route Catalog

FastAPI REST API with ~30 route files organized by domain. All protected routes require JWT authentication. Auto-generated Swagger UI at `/docs` and ReDoc at `/redoc`.

**Key components**: FastAPI routes, auth middleware, service injection

[Deep-dive: API Route Catalog →](docs/architecture/13-api-route-catalog.md)

---

## Memory & Context System

Learn from execution history and provide relevant context to new tasks using pgvector-powered semantic search combined with PostgreSQL full-text search.

| Component | File | Purpose |
|-----------|------|---------|
| **MemoryService** | `services/memory.py` (~910 lines) | Pattern learning + hybrid search (semantic + keyword with RRF) |
| **EmbeddingService** | `services/embedding.py` | Multi-provider embeddings (Fireworks, OpenAI, FastEmbed local) |
| **ContextService** | `services/context_service.py` | Cross-phase context aggregation |
| **TaskContextBuilder** | `services/task_context_builder.py` | Full context assembly for task execution |
| **SynthesisService** | `services/synthesis_service.py` | Parallel task result merging (combine/union/intersection) |

**Memory Types**: `ERROR_FIX`, `DECISION`, `LEARNING`, `WARNING`, `CODEBASE_KNOWLEDGE`, `DISCOVERY` (LLM-classified with rule-based fallback)

### Hybrid Search (Reciprocal Rank Fusion)

Memories are searched using three modes:
- **Semantic**: pgvector cosine similarity on 1536-dim embeddings
- **Keyword**: PostgreSQL `tsvector` full-text search with `ts_rank`
- **Hybrid (default)**: RRF fusion — `score = 0.6 * (1/(60 + sem_rank)) + 0.4 * (1/(60 + kw_rank))`

### ACE Workflow

When a task completes, the ACE (Analyze-Curate-Extract) workflow runs:
1. **Executor**: Parse tool usage, classify memory type, generate embeddings, create TaskMemory
2. **Reflector**: Analyze feedback for errors, search playbook, extract insights
3. **Curator**: Propose playbook updates, generate deltas, validate and apply changes

**Storage**: TaskMemory (execution records), LearnedPattern (extracted patterns), PlaybookEntry (knowledge bullets per ticket)

[Design: Memory System →](docs/design/memory/memory_system.md) | [Requirements: Memory System →](docs/requirements/memory/memory_system.md)

---

## Deduplication System

Prevent duplicate work across specs, requirements, tasks, and tickets using dual-path deduplication: SHA256 content hashing (fast exact match) + pgvector embedding similarity (semantic near-duplicate detection).

| Component | File | Purpose |
|-----------|------|---------|
| **SpecDeduplicationService** | `services/spec_dedup.py` (~855 lines) | Dedup specs, requirements, tasks within project/spec scope |
| **TaskDeduplicationService** | `services/task_dedup.py` | Prevent runaway diagnostic task spawning |
| **TicketDeduplicationService** | `services/ticket_dedup.py` | Global ticket duplicate detection |
| **EmbeddingService** | `services/embedding.py` | Shared embedding generation for all dedup services |

### Similarity Thresholds

| Entity | Threshold | Scope | Method |
|--------|-----------|-------|--------|
| Spec | 0.92 | Within project | Hash + semantic |
| Requirement | 0.88 | Within spec | Hash + semantic |
| Task (spec) | 0.85 | Within spec | Hash + semantic |
| Task (queue) | 0.85 | Within ticket | Semantic only |
| Ticket | 0.85 | Global | Semantic only |
| Acceptance Criteria | 1.0 (exact) | Within requirement | Hash only |

### pgvector Usage

All vector columns use `Vector(1536)` with IVFFlat indexes (`vector_cosine_ops`, lists=100). Similarity queries use cosine distance: `1 - (embedding <=> query_vector)`. Default embedding provider: Fireworks (`qwen3-embedding-8b`), with OpenAI and local FastEmbed as alternatives.

| Table | Vector Column | Purpose |
|-------|--------------|---------|
| `specs` | `embedding_vector` | Spec-level dedup within project |
| `spec_requirements` | `embedding_vector` | Requirement dedup within spec |
| `spec_tasks` | `embedding_vector` | Task dedup within spec |
| `tasks` | `embedding_vector` | Queue task dedup within ticket |
| `tickets` | `embedding_vector` | Global ticket dedup |
| `task_memories` | `context_embedding` | Memory similarity search |
| `learned_patterns` | `embedding` | Pattern matching |
| `playbook_entries` | `embedding` | Playbook entry search (ACE) |

---

## DAG Merge System

Coordinate parallel work branches and merge them back together.

| Component | File | Purpose |
|-----------|------|---------|
| **DependencyGraphService** | `services/dependency_graph.py` | DAG visualization + critical path |
| **CoordinationService** | `services/coordination.py` | SYNC, SPLIT, JOIN, MERGE primitives |
| **ConflictScorer** | `services/conflict_scorer.py` | git merge-tree dry-run scoring |
| **ConvergenceMergeService** | `services/convergence_merge_service.py` | Multi-branch merge orchestration |
| **AgentConflictResolver** | `services/agent_conflict_resolver.py` | LLM-powered conflict resolution |

See [Coordination Patterns →](docs/design/workflows/coordination_patterns.md) for pattern definitions.

---

## Service Initialization Map (CRITICAL REFERENCE)

OmoiOS has **two separate service initialization points** that don't share state:

| Location | File | Function | Purpose | Services |
|----------|------|----------|---------|----------|
| **API Server** | `api/main.py` | `lifespan()` | FastAPI app startup | 25+ services |
| **Orchestrator Worker** | `workers/orchestrator_worker.py` | `init_services()` | Background worker | 9 services |

**These run as separate processes.** Services initialized in one are NOT available in the other.

### Service Availability Matrix

| Service | API Server | Orchestrator | Notes |
|---------|:----------:|:------------:|-------|
| DatabaseService | **yes** | **yes** | Both have own connections |
| EventBusService | **yes** | **yes** | Both have own Redis connections |
| TaskQueueService | **yes** | **yes** | Both have own instances |
| AgentRegistryService | **yes** | **yes** | Both have own instances |
| PhaseGateService | **yes** | **yes** | Both have own instances |
| PhaseManager | **yes** | no | API-only (routes use it) |
| PhaseProgressionService | no | **yes** | Worker-only (auto-advance) |
| SynthesisService | no | **yes** | Worker-only (result merging) |
| MonitoringLoop | **yes** | no | API-only (Guardian + Conductor) |
| MemoryService | **yes** | no | API-only (pattern RAG) |
| DiscoveryService | **yes** | no | API-only (adaptive branching) |
| DiagnosticService | **yes** | no | API-only |
| ValidationOrchestrator | **yes** | no | API-only |
| BillingService | **yes** | no | API-only |
| LLMService | **yes** | no | API-only |
| CoordinationService | no | **yes** | Worker-only (SYNC/SPLIT/JOIN/MERGE patterns) |
| ConvergenceMergeService | no | **yes** | Worker-only (git branch merging at convergence) |
| OwnershipValidationService | no | **yes** | Worker-only (file conflict prevention) |

See [Integration Gaps →](docs/architecture/14-integration-gaps.md) for the full gap analysis and fix instructions.

---

## Testing Requirements

### What Needs Testing

- [ ] Spec-Sandbox state machine (EXPLORE through SYNC)
- [ ] Phase evaluators and retry logic
- [ ] DaytonaSpawner sandbox creation
- [ ] ClaudeSandboxWorker execution modes
- [ ] Full spec → tickets → tasks → execution flow
- [ ] Discovery branching during execution
- [ ] MonitoringLoop with real agents
- [ ] Parallel task execution with SynthesisService
- [ ] DAG merge with conflict resolution

---

## Glossary

| Term | Definition |
|------|------------|
| **Spec** | A feature specification that goes through EXPLORE → SYNC phases |
| **Ticket** | A work grouping (TKT-NNN) containing multiple tasks |
| **Task** | An atomic work unit (TSK-NNN) executable by an agent |
| **Discovery** | New work found during execution that spawns branch tasks |
| **Trajectory** | An agent's conversation and tool usage history |
| **Alignment** | How well an agent's trajectory matches its goal |
| **Coherence** | System-wide measure of agent coordination |
| **Synthesis** | Merging results from parallel predecessor tasks |
| **Phase Gate** | Quality evaluation that must pass to proceed |
| **EARS** | "Easy Approach to Requirements Syntax" format |

---

## Additional Documentation

| Document | Content |
|----------|---------|
| [Agent System Overview](docs/AGENT_SYSTEM_OVERVIEW.md) | Multi-agent orchestration framework, agent lifecycle, heartbeat protocol |
| [App Overview](docs/app_overview.md) | User-centric product perspective, 12-step user flow, page catalog |
| [Spec-Sandbox Subsystem Strategy](docs/architecture/spec_sandbox_subsystem_strategy.md) | Extraction strategy for independent spec-sandbox subsystem |
| [Architecture: Current vs Target](docs/architecture/services/architecture_comparison_current_vs_target.md) | Gap analysis between implemented and designed architecture |
| [Integration Gaps & Known Issues](docs/architecture/14-integration-gaps.md) | Orphaned services, event gaps, DAG wiring, TODOs, fix instructions |

---

## Next Steps

1. ~~**Fix Integration Gaps**: Address critical gaps first~~ — DAG wiring complete, services initialized in orchestrator
2. **Verify Event Flow**: Use checklist in Integration Gaps doc to verify each event; ~135 orphaned events remain
3. **Test DAG System**: Services are wired; needs integration tests with parallel tasks
4. **Complete Live Preview**: ~80% done, needs HMR WebSocket connection (see [#87](https://github.com/kivo360/OmoiOS/issues/87))
5. **Add Frontend Tests**: No test infrastructure exists yet (see [#86](https://github.com/kivo360/OmoiOS/issues/86))
6. **Implement Alerting Channels**: Slack/email routers are stubs (see [#78](https://github.com/kivo360/OmoiOS/issues/78))
7. **Update This Document**: Keep the Service Initialization Map current as services change
