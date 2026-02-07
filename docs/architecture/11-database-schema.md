# Part 11: Database Schema

> Summary doc — this system has no prior design doc; this is the primary architecture reference.

## Overview

OmoiOS uses **PostgreSQL 16** with **pgvector** for semantic search and **SQLAlchemy 2.0+** for ORM. The database has ~60 domain entities organized across core resources, workflow management, agent execution, monitoring, auth/billing, and collaboration.

## Technology

| Component | Technology |
|-----------|-----------|
| **Database** | PostgreSQL 16 |
| **Vector Search** | pgvector extension |
| **ORM** | SQLAlchemy 2.0+ (async) |
| **Migrations** | Alembic (71 migrations as of last count) |
| **Connection** | AsyncSession via connection pool |

## Model Groups

### Core Entities

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | User accounts with hashed passwords |
| `Organization` | `organizations` | Multi-tenant org grouping |
| `Project` | `projects` | Project containers for specs/tickets |
| `Spec` | `specs` | Feature specifications (EXPLORE → SYNC) |
| `Ticket` | `tickets` | Work groupings (TKT-NNN) |
| `Task` | `tasks` | Atomic work units (TSK-NNN) |

### Workflow & State

| Model | Table | Purpose |
|-------|-------|---------|
| `Phase` | `phases` | Workflow phases (implementation, testing, etc.) |
| `PhaseGate` | `phase_gates` | Quality gate configurations |
| `PhaseHistory` | `phase_history` | Phase transition audit log |
| `PhaseContext` | `phase_context` | Cross-phase context aggregation |
| `TicketStatus` | `ticket_statuses` | Ticket status transitions |
| `ApprovalStatus` | `approval_statuses` | Phase gate approval tracking |

### Agents & Execution

| Model | Table | Purpose |
|-------|-------|---------|
| `Agent` | `agents` | Registered agent instances |
| `AgentStatus` | `agent_statuses` | Agent health state tracking |
| `AgentLog` | `agent_logs` | Agent execution logs |
| `AgentMessage` | `agent_messages` | Guardian → Agent message queue |
| `AgentResult` | `agent_results` | Task execution results |
| `AgentBaseline` | `agent_baselines` | Performance baselines |
| `Workspace` | `workspaces` | Daytona sandbox workspace records |
| `SandboxEvent` | `sandbox_events` | All events from sandbox execution |

### Monitoring & Analysis

| Model | Table | Purpose |
|-------|-------|---------|
| `GuardianAnalysis` | `guardian_analyses` | Per-agent trajectory analysis results |
| `TrajectoryAnalysis` | `trajectory_analyses` | Detailed trajectory data |
| `WatchdogAlert` | `watchdog_alerts` | Stuck detection alerts |
| `WatchdogPolicy` | `watchdog_policies` | Configurable watchdog rules |
| `MonitorAnomaly` | `monitor_anomalies` | Detected agent anomalies |
| `DiagnosticRun` | `diagnostic_runs` | Diagnostic investigation records |

### Auth & Billing

| Model | Table | Purpose |
|-------|-------|---------|
| `Auth` | (via User) | Authentication data |
| `Billing` | `billing` | Billing account records |
| `Subscription` | `subscriptions` | Active subscription tracking |
| `CostRecord` | `cost_records` | Per-workflow cost tracking |
| `PromoCode` | `promo_codes` | Promotional discount codes |
| `UserCredentials` | `user_credentials` | Stored integration credentials |
| `UserOnboarding` | `user_onboarding` | Onboarding progress tracking |

### Version Control Integration

| Model | Table | Purpose |
|-------|-------|---------|
| `TicketCommit` | `ticket_commits` | Git commits linked to tickets |
| `TicketPullRequest` | `ticket_pull_requests` | PRs linked to tickets |
| `MergeAttempt` | `merge_attempts` | DAG merge attempt records |
| `BranchWorkflow` | `branch_workflows` | Branch lifecycle tracking |

### Collaboration & Memory

| Model | Table | Purpose |
|-------|-------|---------|
| `TaskMemory` | `task_memories` | Agent-learned patterns (with pgvector embeddings) |
| `MemoryType` | (enum) | Memory classification |
| `LearnedPattern` | `learned_patterns` | Reusable patterns from execution |
| `Playbook` | `playbooks` | Automated response playbooks |
| `Reasoning` | `reasoning` | Agent reasoning chain records |

### Quality & Validation

| Model | Table | Purpose |
|-------|-------|---------|
| `QualityCheck` | `quality_checks` | Quality gate check results |
| `ValidationReview` | `validation_reviews` | Validation agent review records |
| `TaskDiscovery` | `task_discoveries` | Discovery-spawned task tracking |

### Infrastructure

| Model | Table | Purpose |
|-------|-------|---------|
| `Event` | `events` | System event log |
| `HeartbeatMessage` | `heartbeat_messages` | Agent heartbeat records |
| `ResourceLock` | `resource_locks` | Distributed lock tracking |
| `MCPServer` | `mcp_servers` | Registered MCP server configs |
| `ClaudeSessionTranscript` | `claude_session_transcripts` | Full agent conversation logs |

## Key Relationships

```
Organization ──1:N──→ Project ──1:N──→ Spec ──1:N──→ Ticket ──1:N──→ Task
                                                         │              │
                                                         │              ├──→ SandboxEvent
                                                         │              ├──→ AgentResult
                                                         │              └──→ TaskDiscovery
                                                         │
                                                         ├──→ TicketCommit
                                                         └──→ TicketPullRequest
```

## Migration Strategy

- Migrations managed via Alembic in `backend/omoi_os/alembic/`
- Migration naming: `{hash}_{description}.py`
- Run with: `uv run alembic upgrade head`
- Create with: `uv run alembic revision -m "description"`

## SQLAlchemy Reserved Keyword Rule

**NEVER** use `metadata` or `registry` as column/attribute names — they conflict with SQLAlchemy internals. Use alternatives:
- `metadata` → `change_metadata`, `item_metadata`, `config_data`
- `registry` → `agent_registry`, `service_registry`
