# Feature Inventory - Complete Vertical Slices

**Date**: 2025-11-30
**Purpose**: Track every feature as a complete vertical (Route → Service → Model → DB)

---

## Summary

| Layer | Count |
|-------|-------|
| Services | 66 |
| Models | 47 |
| Routes | 25 |
| Tools | 6 |
| Tests | 58 |

---

## Feature Verticals

### Legend
- ✅ Complete vertical (Route + Service + Model + Tests)
- 🔶 Partial (missing tests or route)
- ⬜ Service only (no route exposed)

---

## Core Workflow Features

### 1. Ticket Management
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/tickets.py` | ✅ |
| Service | `services/ticket_workflow.py` | ✅ |
| Model | `models/ticket.py` | ✅ |
| Status Enum | `models/ticket_status.py` | ✅ |

**Vertical**: `POST /api/v1/tickets` → `TicketWorkflowOrchestrator` → `Ticket` → DB
**Status**: ✅ **COMPLETE**

---

### 2. Task Queue
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/tasks.py` | ✅ |
| Service | `services/task_queue.py` | ✅ |
| Scorer | `services/task_scorer.py` | ✅ |
| Model | `models/task.py` | ✅ |

**Vertical**: `POST /api/v1/tasks` → `TaskQueueService` → `Task` → DB
**Status**: ✅ **COMPLETE**

---

### 3. Phase Management
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/phases.py` | ✅ |
| Gate Service | `services/phase_gate.py` | ✅ |
| Loader | `services/phase_loader.py` | ✅ |
| Model | `models/phase.py` | ✅ |
| History | `models/phase_history.py` | ✅ |

**Vertical**: `GET /api/v1/phases` → `PhaseGateService` → `PhaseModel` → DB
**Status**: ✅ **COMPLETE**

---

### 4. Discovery System
| Component | File | Status |
|-----------|------|--------|
| Route | (via tasks) | 🔶 |
| Service | `services/discovery.py` | ✅ |
| Model | `models/task_discovery.py` | ✅ |

**Vertical**: `record_discovery_and_branch()` → `TaskDiscovery` → spawns Task
**Status**: 🔶 **Service complete, no dedicated route**

---

### 5. Validation System
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/validation.py` | ✅ |
| Orchestrator | `services/validation_orchestrator.py` | ✅ |
| Agent | `services/validation_agent.py` | ✅ |
| Helpers | `services/validation_helpers.py` | ✅ |

**Vertical**: `POST /api/validation/review` → `ValidationOrchestrator` → spawns validator
**Status**: ✅ **COMPLETE**

---

### 6. Result Submission
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/results.py` | ✅ |
| Service | `services/result_submission.py` | ✅ |

**Vertical**: `POST /api/v1/results` → `ResultSubmissionService` → triggers validation
**Status**: ✅ **COMPLETE**

---

## Agent Features

### 7. Agent Registry
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/agents.py` | ✅ |
| Registry | `services/agent_registry.py` | ✅ |
| Status Manager | `services/agent_status_manager.py` | ✅ |
| Model | `models/agent.py` | ✅ |
| Status Enum | `models/agent_status.py` | ✅ |

**Vertical**: `POST /api/v1/agents/register` → `AgentRegistryService` → `Agent` → DB
**Status**: ✅ **COMPLETE**

---

### 8. Agent Health
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/agents.py` (health endpoints) | ✅ |
| Service | `services/agent_health.py` | ✅ |
| Heartbeat | `services/heartbeat_protocol.py` | ✅ |

**Vertical**: `POST /api/v1/agents/{id}/heartbeat` → `HeartbeatProtocolService` → updates health
**Status**: ✅ **COMPLETE**

---

### 9. Agent Executor
| Component | File | Status |
|-----------|------|--------|
| Route | (internal) | ⬜ |
| Service | `services/agent_executor.py` | ✅ |
| Output Collector | `services/agent_output_collector.py` | ✅ |

**Vertical**: `orchestrator_loop` → `AgentExecutor` → OpenHands → LLM
**Status**: ⬜ **Internal service, no direct route**

---

## Monitoring Features

### 10. Diagnostic System
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/diagnostic.py` | ✅ |
| Service | `services/diagnostic.py` | ✅ |
| Model | `models/diagnostic_run.py` | ✅ |

**Vertical**: `POST /api/v1/diagnostic/run` → `DiagnosticService` → `DiagnosticRun` → DB
**Status**: ✅ **COMPLETE**

---

### 11. Guardian (Intelligent Monitoring)
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/guardian.py` | ✅ |
| Service | `services/guardian.py` | ✅ |
| Intelligent | `services/intelligent_guardian.py` | ✅ |
| Actions | `models/guardian_action.py` | ✅ |

**Vertical**: `GET /api/v1/guardian/status` → `GuardianService` → trajectory analysis
**Status**: ✅ **COMPLETE**

---

### 12. Conductor (System Coherence)
| Component | File | Status |
|-----------|------|--------|
| Route | (via guardian) | 🔶 |
| Service | `services/conductor.py` | ✅ |

**Vertical**: `monitoring_loop` → `Conductor` → coherence analysis
**Status**: 🔶 **Service complete, accessed via Guardian routes**

---

### 13. Watchdog (Meta-Monitoring)
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/watchdog.py` | ✅ |
| Service | `services/watchdog.py` | ✅ |
| Restart | `services/restart_orchestrator.py` | ✅ |
| Actions | `models/watchdog_action.py` | ✅ |

**Vertical**: `GET /api/v1/watchdog/status` → `WatchdogService` → remediation
**Status**: ✅ **COMPLETE**

---

### 14. Monitoring Loop
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/monitoring.py` | ✅ |
| Service | `services/monitoring_loop.py` | ✅ |
| Monitor | `services/monitor.py` | ✅ |

**Vertical**: Background task → Guardian (60s) + Conductor (300s)
**Status**: ✅ **COMPLETE**

---

### 15. Alerting
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/alerts.py` | ✅ |
| Service | `services/alerting.py` | ✅ |
| Model | `models/monitor_anomaly.py` (Alert) | ✅ |

**Vertical**: `GET /api/v1/alerts` → `AlertService` → `Alert` → DB
**Status**: ✅ **COMPLETE**

---

## Collaboration Features

### 16. Multi-Agent Collaboration
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/collaboration.py` | ✅ |
| Service | `services/collaboration.py` | ✅ |
| Coordination | `services/coordination.py` | ✅ |
| Intervention | `services/conversation_intervention.py` | ✅ |

**Vertical**: `POST /api/v1/collaboration/messages` → `CollaborationService` → message delivery
**Status**: ✅ **COMPLETE**

---

### 17. Resource Locking
| Component | File | Status |
|-----------|------|--------|
| Route | (internal) | ⬜ |
| Service | `services/resource_lock.py` | ✅ |

**Vertical**: `CollaborationService` → `ResourceLockService` → Redis/DB locks
**Status**: ⬜ **Internal service**

---

## Cost & Budget Features

### 18. Cost Tracking
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/costs.py` | ✅ |
| Service | `services/cost_tracking.py` | ✅ |
| Model | `models/cost_record.py` | ✅ |

**Vertical**: `GET /api/v1/costs/summary` → `CostTrackingService` → `CostRecord` → DB
**Status**: ✅ **COMPLETE**

---

### 19. Budget Enforcement
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/costs.py` (budget endpoints) | ✅ |
| Service | `services/budget_enforcer.py` | ✅ |
| Model | `models/budget.py` | ✅ |

**Vertical**: `POST /api/v1/costs/budgets` → `BudgetEnforcerService` → `Budget` → DB
**Status**: ✅ **COMPLETE**

---

## Memory & Learning Features

### 20. ACE Memory System
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/memory.py` | ✅ |
| Engine | `services/ace_engine.py` | ✅ |
| Executor | `services/ace_executor.py` | ✅ |
| Reflector | `services/ace_reflector.py` | ✅ |
| Curator | `services/ace_curator.py` | ✅ |
| Model | `models/task_memory.py` | ✅ |

**Vertical**: Task completion → `ACEEngine` → memory + insights + playbook
**Status**: ✅ **COMPLETE**

---

### 21. Context Service
| Component | File | Status |
|-----------|------|--------|
| Route | (internal) | ⬜ |
| Service | `services/context_service.py` | ✅ |
| Summarizer | `services/context_summarizer.py` | ✅ |
| Trajectory | `services/trajectory_context.py` | ✅ |

**Vertical**: `AgentExecutor` → `ContextService` → builds task prompt
**Status**: ⬜ **Internal service**

---

### 22. Memory Search
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/memory.py` | ✅ |
| Service | `services/memory.py` | ✅ |
| Embedding | `services/embedding.py` | ✅ |

**Vertical**: `GET /api/v1/memory/search` → `MemoryService` → vector search
**Status**: ✅ **COMPLETE**

---

## Quality Features

### 23. Quality Prediction
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/quality.py` | ✅ |
| Predictor | `services/quality_predictor.py` | ✅ |
| Checker | `services/quality_checker.py` | ✅ |

**Vertical**: `GET /api/v1/quality/predict` → `QualityPredictorService` → LLM score
**Status**: ✅ **COMPLETE**

---

### 24. Baseline Learning
| Component | File | Status |
|-----------|------|--------|
| Route | (internal) | ⬜ |
| Service | `services/baseline_learner.py` | ✅ |
| Anomaly Scorer | `services/composite_anomaly_scorer.py` | ✅ |

**Vertical**: `MonitoringLoop` → `BaselineLearner` → adaptive thresholds
**Status**: ⬜ **Internal service**

---

## Auth & Multi-Tenant Features

### 25. Authentication
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/auth.py` | ✅ |
| Service | `services/auth_service.py` | ✅ |
| Supabase | `services/supabase_auth.py` | ✅ |
| Model | `models/user.py` | ✅ |
| API Keys | `models/api_key.py` | ✅ |

**Vertical**: `POST /api/v1/auth/login` → `AuthService` → JWT token
**Status**: ✅ **COMPLETE**

---

### 26. Authorization (RBAC)
| Component | File | Status |
|-----------|------|--------|
| Route | (middleware) | ✅ |
| Service | `services/authorization_service.py` | ✅ |
| MCP Auth | `services/mcp_authorization.py` | ✅ |

**Vertical**: Middleware → `AuthorizationService` → permission check
**Status**: ✅ **COMPLETE**

---

### 27. Organizations
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/organizations.py` | ✅ |
| Model | `models/organization.py` | ✅ |

**Vertical**: `POST /api/v1/organizations` → creates org → user becomes owner
**Status**: ✅ **COMPLETE**

---

### 28. Projects
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/projects.py` | ✅ |
| Model | `models/project.py` | ✅ |

**Vertical**: `POST /api/v1/projects` → `Project` → org-scoped
**Status**: ✅ **COMPLETE**

---

## Integration Features

### 29. GitHub Integration
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/github.py` | ✅ |
| Route | `routes/commits.py` | ✅ |
| Service | `services/github_integration.py` | ✅ |
| Model | `models/ticket_commit.py` | ✅ |

**Vertical**: `POST /api/v1/github/webhook` → `GitHubIntegrationService` → commit linking
**Status**: ✅ **COMPLETE**

---

### 30. MCP Server
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/mcp.py` | ✅ |
| Client | `services/mcp_client.py` | ✅ |
| Registry | `services/mcp_registry.py` | ✅ |
| Integration | `services/mcp_integration.py` | ✅ |
| Circuit Breaker | `services/mcp_circuit_breaker.py` | ✅ |
| Retry | `services/mcp_retry.py` | ✅ |

**Vertical**: `/mcp/*` → `MCPClient` → external tools
**Status**: ✅ **COMPLETE**

---

## UI Support Features

### 31. Kanban Board
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/board.py` | ✅ |
| Service | `services/board.py` | ✅ |

**Vertical**: `GET /api/v1/board/view` → `BoardService` → Kanban columns
**Status**: ✅ **COMPLETE**

---

### 32. Dependency Graph
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/graph.py` | ✅ |
| Service | `services/dependency_graph.py` | ✅ |

**Vertical**: `GET /api/v1/graph/{ticket_id}` → `DependencyGraphService` → nodes/edges
**Status**: ✅ **COMPLETE**

---

### 33. Event Stream (SSE)
| Component | File | Status |
|-----------|------|--------|
| Route | `routes/events.py` | ✅ |
| Service | `services/event_bus.py` | ✅ |

**Vertical**: `GET /api/v1/events/stream` → SSE → real-time updates
**Status**: ✅ **COMPLETE**

---

### 34. Approval Workflow
| Component | File | Status |
|-----------|------|--------|
| Route | (via tickets) | 🔶 |
| Service | `services/approval.py` | ✅ |
| Status | `models/approval_status.py` | ✅ |

**Vertical**: Ticket creation → `ApprovalService` → human-in-loop gate
**Status**: 🔶 **Service complete, integrated into ticket routes**

---

## Agent Tools

### 35. Task Tools
| Component | File | Status |
|-----------|------|--------|
| Tool | `tools/task_tools.py` | ✅ |

**Tools**: `create_task`, `update_task_status`, `get_task`, `list_pending_tasks`
**Status**: ✅ **COMPLETE**

---

### 36. Collaboration Tools
| Component | File | Status |
|-----------|------|--------|
| Tool | `tools/collaboration_tools.py` | ✅ |

**Tools**: `broadcast_message`, `send_message`, `request_handoff`
**Status**: ✅ **COMPLETE**

---

### 37. Planning Tools
| Component | File | Status |
|-----------|------|--------|
| Tool | `tools/planning_tools.py` | ✅ |

**Tools**: `get_ticket_details`, `search_similar_tasks`, `analyze_blockers`
**Status**: ✅ **COMPLETE**

---

## Summary by Status

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Complete | 30 | 81% |
| 🔶 Partial | 4 | 11% |
| ⬜ Internal | 3 | 8% |
| **Total** | **37** | 100% |

---

## Next Steps

1. **Close the circuit**: Verify V1 basic flow works end-to-end
2. **Test partial features**: Discovery, Conductor, Approval (add routes or tests)
3. **Document internal services**: Context, Resource Lock, Baseline (for future routes)
4. **Connect frontend**: 30 complete verticals ready for UI
