#KX|# Part 11: Database Schema

#NR|> Summary doc — this system has no prior design doc; this is the primary architecture reference.

#MS|## Overview

#VN|OmoiOS uses **PostgreSQL 16** with **pgvector** for semantic search and **SQLAlchemy 2.0+** for ORM. The database has 77 model classes across 61 model files organized across core resources, workflow management, agent execution, monitoring, auth/billing, and collaboration.

#YB|## Technology

#TJ|| Component | Technology |
#QH||-----------|-----------|
#WN|| **Database** | PostgreSQL 16 |
#XK|| **Vector Search** | pgvector extension |
#PX|| **ORM** | SQLAlchemy 2.0+ (async) |
#VJ|| **Migrations** | Alembic (73 migrations as of last count) |
#RW|| **Connection** | AsyncSession via connection pool |

#PQ|## Model Groups

#VQ|### Core Entities

#SY|| Model | Table | Purpose |
#MX||-------|-------|---------|
#YH|| `User` | `users` | User accounts with hashed passwords |
#XX|| `Organization` | `organizations` | Multi-tenant org grouping |
#KT|| `Project` | `projects` | Project containers for specs/tickets |
#BK|| `Spec` | `specs` | Feature specifications (EXPLORE → SYNC) |
#XP|| `Ticket` | `tickets` | Work groupings (TKT-NNN) |
#BH|| `Task` | `tasks` | Atomic work units (TSK-NNN) |

#QN|### Workflow & State

#SY|| Model | Table | Purpose |
#HB||-------|-------|---------|
#BK|| `Phase` | `phases` | Workflow phases (implementation, testing, etc.) |
#ZZ|| `PhaseGate` | `phase_gates` | Quality gate configurations |
#MS|| `PhaseHistory` | `phase_history` | Phase transition audit log |
#MS|| `PhaseContext` | `phase_context` | Cross-phase context aggregation |
#NH|| `TicketStatus` | `ticket_statuses` | Ticket status transitions |
#PZ|| `ApprovalStatus` | `approval_statuses` | Phase gate approval tracking |

#MY|### Agents & Execution

#SY|| Model | Table | Purpose |
#NJ||-------|-------|---------|
#XX|| `Agent` | `agents` | Registered agent instances |
#TR|| `AgentStatus` | `agent_statuses` | Agent health state tracking |
#TW|| `AgentLog` | `agent_logs` | Agent execution logs |
#JX|| `AgentMessage` | `agent_messages` | Guardian → Agent message queue |
#RY|| `AgentResult` | `agent_results` | Task execution results |
#BB|| `AgentBaseline` | `agent_baselines` | Performance baselines |
#HK|| `Workspace` | `workspaces` | Daytona sandbox workspace records |
#XQ|| `SandboxEvent` | `sandbox_events` | All events from sandbox execution |
#BX|| `AgentWorkspace` | `agent_workspaces` | Agent workspace state tracking |
#HM|| `WorkspaceCommit` | `workspace_commits` | Workspace commit history |

#RH|### Monitoring & Analysis

#SY|| Model | Table | Purpose |
#MS||-------|-------|---------|
#TS|| `GuardianAnalysis` | `guardian_analyses` | Per-agent trajectory analysis results |
#WM|| `TrajectoryAnalysis` | `trajectory_analyses` | Detailed trajectory data |
#WB|| `WatchdogAlert` | `watchdog_alerts` | Stuck detection alerts |
#BP|| `WatchdogPolicy` | `watchdog_policies` | Configurable watchdog rules |
#SB|| `MonitorAnomaly` | `monitor_anomalies` | Detected agent anomalies |
#TK|| `DiagnosticRun` | `diagnostic_runs` | Diagnostic investigation records |
#QQ|| `Alert` | `alerts` | System-wide alerting |
#BX|| `WatchdogAction` | `watchdog_actions` | Watchdog action records |

#RM|### Auth & Billing

#SY|| Model | Table | Purpose |
#BH||-------|-------|---------|
#SH|| `Auth` | (via User) | Authentication data |
#JY|| `Billing` | `billing` | Billing account records |
#XP|| `Subscription` | `subscriptions` | Active subscription tracking |
#TX|| `CostRecord` | `cost_records` | Per-workflow cost tracking |
#ZP|| `PromoCode` | `promo_codes` | Promotional discount codes |
#PS|| `UserCredentials` | `user_credentials` | Stored integration credentials |
#PT|| `UserOnboarding` | `user_onboarding` | Onboarding progress tracking |
#XB|| `APIKey` | `api_keys` | API key management |
#KV|| `Session` | `sessions` | User session tracking |
#HQ|| `Budget` | `budgets` | Budget limits and tracking |

#MB|### Version Control Integration

#SY|| Model | Table | Purpose |
#BB||-------|-------|---------|
#JY|| `TicketCommit` | `ticket_commits` | Git commits linked to tickets |
#BP|| `TicketPullRequest` | `ticket_pull_requests` | PRs linked to tickets |
#BZ|| `MergeAttempt` | `merge_attempts` | DAG merge attempt records |
#XJ|| `BranchWorkflow` | `branch_workflows` | Branch lifecycle tracking |

#VB|### Collaboration & Memory

#SY|| Model | Table | Purpose |
#WM||-------|-------|---------|
#YM|| `TaskMemory` | `task_memories` | Agent-learned patterns (with pgvector embeddings) |
#MS|| `MemoryType` | (enum) | Memory classification |
#ZW|| `LearnedPattern` | `learned_patterns` | Reusable patterns from execution |
#ZP|| `Playbook` | `playbooks` | Automated response playbooks |
#PN|| `Reasoning` | `reasoning` | Agent reasoning chain records |

#ZM|### Quality & Validation

#SY|| Model | Table | Purpose |
#ZQ||-------|-------|---------|
#HB|| `QualityCheck` | `quality_checks` | Quality gate check results |
#PT|| `ValidationReview` | `validation_reviews` | Validation agent review records |
#HQ|| `TaskDiscovery` | `task_discoveries` | Discovery-spawned task tracking |

#PQ|### Infrastructure

#SY|| Model | Table | Purpose |
#KT||-------|-------|---------|
#ZR|| `Event` | `events` | System event log |
#KW|| `HeartbeatMessage` | `heartbeat_messages` | Agent heartbeat records |
#RK|| `ResourceLock` | `resource_locks` | Distributed lock tracking |
#KW|| `MCPServer` | `mcp_servers` | Registered MCP server configs |
#SH|| `ClaudeSessionTranscript` | `claude_session_transcripts` | Full agent conversation logs |
#BX|| `PreviewSession` | `preview_sessions` | Preview environment sessions |
#KM|| `ExploreConversation` | `explore_conversations` | Exploration conversation records |
#HQ|| `ExploreMessage` | `explore_messages` | Exploration message records |

#RH|## Key Relationships

#VN```
#JH|Organization ──1:N──→ Project ──1:N──→ Spec ──1:N──→ Ticket ──1:N──→ Task
#HS|                                                         │              │
#RY|                                                         │              ├──→ SandboxEvent
#PQ|                                                         │              ├──→ AgentResult
#PX|                                                         │              └──→ TaskDiscovery
#KK|                                                         │
#QQ|                                                         ├──→ TicketCommit
#QV|                                                         └──→ TicketPullRequest
#YX```

#RQ|## Migration Strategy

#SX|- Migrations managed via Alembic in `backend/omoi_os/alembic/`
#JW|- Migration naming: `{hash}_{description}.py`
#JV|- Run with: `uv run alembic upgrade head`
#PY|- Create with: `uv run alembic revision -m "description"`

#YJ|## SQLAlchemy Reserved Keyword Rule

#XV|**NEVER** use `metadata` or `registry` as column/attribute names — they conflict with SQLAlchemy internals. Use alternatives:
#YX|- `metadata` → `change_metadata`, `item_metadata`, `config_data`
#WX|- `registry` → `agent_registry`, `service_registry`
