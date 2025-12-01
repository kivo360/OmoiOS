# E2E Testing Plan - Comprehensive Coverage

**Date**: 2025-11-30  
**Status**: Draft  
**Goal**: Verify the entire system actually works end-to-end

---

## Critical Question: Does The Code Actually Work?

This document defines every test needed to prove the system works. No mocking where it matters.

---

## Part 1: LLM Integration Tests

### 1.1 PydanticAI/Fireworks Path (Diagnostics, Structured Outputs)

**File**: `tests/test_e2e_llm_fireworks.py`

| Test | What It Proves |
|------|----------------|
| `test_simple_completion` | Fireworks API responds |
| `test_structured_output_simple` | JSON schema extraction works |
| `test_diagnostic_analysis_schema` | `DiagnosticAnalysis` model parses correctly |
| `test_quality_prediction_schema` | Quality predictor LLM works |
| `test_context_summarization` | Context summarizer LLM works |
| `test_memory_embedding_generation` | Embedding service works |

**Env required**: `LLM_FIREWORKS_API_KEY`

---

### 1.2 OpenHands/z.ai Path (Main Agents)

**File**: `tests/test_e2e_llm_openhands.py`

| Test | What It Proves |
|------|----------------|
| `test_llm_initialization` | OpenHands LLM object creates |
| `test_agent_creation` | Agent with tools initializes |
| `test_simple_prompt_response` | LLM responds to prompt |
| `test_tool_calling` | Agent can call bash/file tools |
| `test_conversation_lifecycle` | Conversation start → run → close works |
| `test_cost_tracking` | Usage metrics captured |

**Env required**: `LLM_API_KEY`, `LLM_BASE_URL`

---

## Part 2: Agent Executor Tests

### 2.1 AgentExecutor with Real LLM

**File**: `tests/test_e2e_agent_executor.py`

| Test | What It Proves |
|------|----------------|
| `test_executor_initialization` | AgentExecutor creates without error |
| `test_execute_simple_task` | Agent reads file and responds |
| `test_execute_with_file_creation` | Agent creates files in workspace |
| `test_execute_with_bash_command` | Agent runs shell commands |
| `test_planning_mode_readonly` | Planning agent can't edit files |
| `test_phase_instructions_loaded` | Phase prompt injected correctly |
| `test_omoi_tools_registered` | OmoiOS tools available to agent |
| `test_conversation_persistence` | Conversation ID saved |
| `test_error_handling` | Failed task doesn't crash system |
| `test_cost_returned` | Execution cost tracked |

**Env required**: `LLM_API_KEY`, temp workspace

---

### 2.2 Agent Tool Integration

**File**: `tests/test_e2e_agent_tools.py`

| Test | What It Proves |
|------|----------------|
| `test_create_task_tool` | Agent can spawn child tasks |
| `test_update_task_status_tool` | Agent can mark tasks done |
| `test_get_ticket_details_tool` | Agent reads ticket context |
| `test_search_similar_tasks_tool` | Memory search works |
| `test_analyze_blockers_tool` | Blocker analysis returns data |
| `test_broadcast_message_tool` | Agent can message other agents |
| `test_request_handoff_tool` | Handoff protocol works |

**Env required**: `LLM_API_KEY`, database

---

## Part 3: Workflow Engine Tests

### 3.1 Ticket Lifecycle

**File**: `tests/test_e2e_ticket_lifecycle.py`

| Test | What It Proves |
|------|----------------|
| `test_create_ticket` | POST /api/tickets works |
| `test_ticket_approval_gate` | Pending → approved transition |
| `test_ticket_auto_task_creation` | First task auto-created |
| `test_ticket_phase_progression` | REQUIREMENTS → IMPLEMENTATION |
| `test_ticket_blocking_detection` | Stuck ticket marked blocked |
| `test_ticket_completion` | All tasks done → ticket done |

**Env required**: Database, API running

---

### 3.2 Task Queue & Scoring

**File**: `tests/test_e2e_task_queue.py`

| Test | What It Proves |
|------|----------------|
| `test_enqueue_task` | Task created with correct priority |
| `test_task_scoring` | Priority + age + deadline scoring |
| `test_task_assignment` | Best agent matched to task |
| `test_task_dependencies` | Blocked tasks not assigned |
| `test_starvation_prevention` | Old tasks get boosted |
| `test_sla_urgency_boost` | Deadline tasks prioritized |

**Env required**: Database

---

### 3.3 Discovery & Branching

**File**: `tests/test_e2e_discovery.py`

| Test | What It Proves |
|------|----------------|
| `test_record_discovery` | Discovery saved to DB |
| `test_discovery_spawns_task` | `record_discovery_and_branch` creates task |
| `test_discovery_bypasses_phase_rules` | Can spawn task in any phase |
| `test_priority_boost` | High-priority discovery boosts child |
| `test_workflow_graph_built` | Graph shows discovery edges |
| `test_discovery_resolution` | Discovery marked resolved |

**Env required**: Database

---

### 3.4 Phase Transitions

**File**: `tests/test_e2e_phases.py`

| Test | What It Proves |
|------|----------------|
| `test_load_workflow_config` | YAML config loads |
| `test_phase_prompt_injection` | Phase prompt in agent system prompt |
| `test_done_definitions_checked` | Phase exit criteria enforced |
| `test_expected_outputs_validated` | Required deliverables checked |
| `test_phase_gate_blocking` | Can't advance without approval |
| `test_feedback_loop_to_prior_phase` | Testing fail → back to impl |

**Env required**: Database

---

## Part 4: Validation System Tests

### 4.1 Validation Orchestrator

**File**: `tests/test_e2e_validation.py`

| Test | What It Proves |
|------|----------------|
| `test_transition_to_under_review` | Task → under_review works |
| `test_validator_spawned` | Validator agent created |
| `test_validation_in_progress` | State machine transition |
| `test_validation_passed` | Passed review → done |
| `test_validation_failed` | Failed review → needs_work |
| `test_feedback_stored` | `last_validation_feedback` set |
| `test_validation_iteration_increment` | Iteration counter works |
| `test_repeated_failure_triggers_diagnostic` | 2 fails → diagnostic spawned |
| `test_validator_timeout_handling` | Timeout → diagnostic |

**Env required**: Database

---

### 4.2 Validation Agent Execution

**File**: `tests/test_e2e_validation_agent.py`

| Test | What It Proves |
|------|----------------|
| `test_validator_reads_code` | Validator accesses workspace |
| `test_validator_runs_tests` | Validator executes test suite |
| `test_validator_submits_review` | `give_review` tool called |
| `test_validator_feedback_quality` | Feedback is actionable |

**Env required**: `LLM_API_KEY`, database

---

## Part 5: Diagnostic System Tests

### 5.1 Stuck Workflow Detection

**File**: `tests/test_e2e_diagnostic_detection.py`

| Test | What It Proves |
|------|----------------|
| `test_find_stuck_workflows` | Detection query works |
| `test_cooldown_respected` | Same workflow not re-diagnosed |
| `test_stuck_threshold_respected` | Must be stuck long enough |
| `test_active_tasks_not_stuck` | Running tasks = not stuck |
| `test_validated_result_not_stuck` | Has result = not stuck |

**Env required**: Database

---

### 5.2 Diagnostic Agent Spawning

**File**: `tests/test_e2e_diagnostic_spawn.py`

| Test | What It Proves |
|------|----------------|
| `test_build_diagnostic_context` | Context includes all data |
| `test_generate_hypotheses` | LLM returns DiagnosticAnalysis |
| `test_spawn_recovery_tasks` | Recovery tasks created |
| `test_diagnostic_run_recorded` | DiagnosticRun in DB |
| `test_agent_intervention_sent` | Active agents notified |
| `test_diagnostic_completion` | Run marked completed |

**Env required**: `LLM_FIREWORKS_API_KEY`, database

---

### 5.3 Monitoring Loops

**File**: `tests/test_e2e_monitoring_loops.py`

| Test | What It Proves |
|------|----------------|
| `test_diagnostic_monitoring_loop` | Loop detects and spawns |
| `test_heartbeat_monitoring_loop` | Unresponsive agents restarted |
| `test_anomaly_monitoring_loop` | High anomaly → diagnostic |
| `test_blocking_detection_loop` | Blocked tickets marked |
| `test_approval_timeout_loop` | Expired approvals processed |

**Env required**: Database, Redis

---

## Part 6: Multi-Agent Coordination Tests

### 6.1 Collaboration Service

**File**: `tests/test_e2e_collaboration.py`

| Test | What It Proves |
|------|----------------|
| `test_broadcast_message` | All agents receive message |
| `test_direct_message` | Specific agent receives message |
| `test_handoff_request` | Task handoff works |
| `test_handoff_acceptance` | Receiving agent accepts |
| `test_resource_lock_acquire` | Lock prevents conflicts |
| `test_resource_lock_release` | Lock released properly |
| `test_deadlock_detection` | Circular locks detected |

**Env required**: Database, Redis

---

### 6.2 Guardian & Conductor

**File**: `tests/test_e2e_intelligent_monitoring.py`

| Test | What It Proves |
|------|----------------|
| `test_guardian_trajectory_analysis` | Agent alignment scored |
| `test_guardian_steering_detection` | Off-track agents flagged |
| `test_guardian_intervention` | Steering message sent |
| `test_conductor_coherence_analysis` | System coherence scored |
| `test_conductor_duplicate_detection` | Duplicate work flagged |
| `test_conductor_recommendations` | Actionable recommendations |
| `test_monitoring_loop_orchestration` | Full loop executes |

**Env required**: `LLM_FIREWORKS_API_KEY`, database

---

## Part 7: Auth & Multi-Tenant Tests

### 7.1 Authentication

**File**: `tests/test_e2e_auth.py`

| Test | What It Proves |
|------|----------------|
| `test_user_registration` | New user created |
| `test_user_login` | JWT tokens returned |
| `test_token_refresh` | Refresh token works |
| `test_password_validation` | Weak passwords rejected |
| `test_api_key_creation` | API key generated |
| `test_api_key_authentication` | API key grants access |
| `test_api_key_scopes` | Scoped permissions work |

**Env required**: Database

---

### 7.2 Authorization & RBAC

**File**: `tests/test_e2e_authorization.py`

| Test | What It Proves |
|------|----------------|
| `test_super_admin_access` | Super admin bypasses checks |
| `test_org_owner_permissions` | Owner has full access |
| `test_org_member_permissions` | Member has limited access |
| `test_permission_wildcards` | `org:*` matches `org:read` |
| `test_role_inheritance` | Child role inherits parent |
| `test_agent_authorization` | Agents have org roles |
| `test_cross_org_denied` | Can't access other orgs |

**Env required**: Database

---

### 7.3 Organization Management

**File**: `tests/test_e2e_organizations.py`

| Test | What It Proves |
|------|----------------|
| `test_create_organization` | Org created, user becomes owner |
| `test_invite_member` | Member added with role |
| `test_update_member_role` | Role change works |
| `test_remove_member` | Member removed |
| `test_org_resource_limits` | `max_concurrent_agents` stored |
| `test_org_soft_delete` | Archived org not accessible |

**Env required**: Database

---

## Part 8: Workspace & Sandbox Tests

### 8.1 Local Workspace

**File**: `tests/test_e2e_workspace_local.py`

| Test | What It Proves |
|------|----------------|
| `test_workspace_creation` | Directory created |
| `test_file_operations` | Read/write/delete work |
| `test_bash_execution` | Commands run |
| `test_workspace_isolation` | Agents can't escape |
| `test_workspace_cleanup` | Cleanup removes files |

**Env required**: Temp directory

---

### 8.2 Daytona Cloud Workspace

**File**: `tests/test_e2e_workspace_daytona.py`

| Test | What It Proves |
|------|----------------|
| `test_daytona_workspace_creation` | Workspace provisioned |
| `test_daytona_execute_action` | Action runs in sandbox |
| `test_daytona_git_integration` | Git operations work |
| `test_daytona_workspace_close` | Workspace destroyed |
| `test_daytona_timeout_handling` | Timeout doesn't hang |

**Env required**: `DAYTONA_API_KEY`

---

## Part 9: MCP Server Tests

### 9.1 MCP Tools

**File**: `tests/test_e2e_mcp_tools.py`

| Test | What It Proves |
|------|----------------|
| `test_mcp_server_initialization` | Server starts |
| `test_create_ticket_tool` | Ticket created via MCP |
| `test_create_task_tool` | Task created via MCP |
| `test_update_task_status_tool` | Status updated via MCP |
| `test_get_task_discoveries_tool` | Discoveries returned |
| `test_get_workflow_graph_tool` | Graph structure returned |
| `test_change_ticket_status_tool` | Ticket status changed |

**Env required**: Database, MCP server

---

## Part 10: Full System Integration

### 10.1 Complete Autonomous Workflow

**File**: `tests/test_e2e_full_workflow.py`

| Test | What It Proves |
|------|----------------|
| `test_ticket_to_completion` | Full ticket lifecycle |
| `test_requirements_to_implementation` | Phase transition with discovery |
| `test_implementation_to_testing` | Code → tests |
| `test_testing_failure_recovery` | Test fail → fix → retest |
| `test_stuck_workflow_recovery` | Diagnostic spawns recovery |
| `test_multi_agent_collaboration` | Agents coordinate |

**Env required**: All services running

---

### 10.2 Load & Stress Tests

**File**: `tests/test_e2e_load.py`

| Test | What It Proves |
|------|----------------|
| `test_concurrent_tickets` | 10 tickets processed |
| `test_concurrent_agents` | 5 agents running |
| `test_high_task_volume` | 100 tasks queued |
| `test_rapid_status_changes` | No race conditions |
| `test_event_bus_throughput` | Events delivered |

**Env required**: All services, higher resources

---

## Test Infrastructure

### Pytest Markers

```python
# In conftest.py
pytest.mark.smoke        # < 30s, no external deps
pytest.mark.unit         # No external deps
pytest.mark.integration  # Requires DB/Redis
pytest.mark.llm          # Requires LLM API keys  
pytest.mark.e2e          # Full system required
pytest.mark.daytona      # Requires Daytona
pytest.mark.slow         # > 60s
```

### Running Tests

```bash
# Quick validation (no LLM costs)
pytest tests/ -m "smoke or unit" -v

# Integration (DB/Redis required)
pytest tests/ -m "integration" -v

# LLM tests (costs money)
pytest tests/ -m "llm" -v

# Full E2E (everything)
pytest tests/ -m "e2e" -v

# Skip slow tests
pytest tests/ -m "not slow" -v
```

---

## Environment Setup

### Required Services

```bash
# Start PostgreSQL
docker run -d --name omoi-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 15432:5432 postgres:15

# Start Redis
docker run -d --name omoi-redis \
  -p 16379:6379 redis:7
```

### Environment Variables

```bash
# .env.test
DATABASE_URL_TEST=postgresql+psycopg://postgres:postgres@localhost:15432/app_db
REDIS_URL_TEST=redis://localhost:16379

# LLM - Main agents (z.ai)
LLM_API_KEY=<key-from-base.yaml>
LLM_MODEL=openai/glm-4.6
LLM_BASE_URL=https://api.z.ai/api/coding/paas/v4

# LLM - Diagnostics (Fireworks)
LLM_FIREWORKS_API_KEY=<your-fireworks-key>

# Daytona (optional)
DAYTONA_API_KEY=<your-daytona-key>
```

---

## Coverage Targets

| Category | Current | Target |
|----------|---------|--------|
| LLM Integration | 10% | 90% |
| Agent Execution | 5% | 80% |
| Workflow Engine | 40% | 90% |
| Validation System | 60% | 90% |
| Diagnostic System | 30% | 85% |
| Auth/RBAC | 20% | 90% |
| Multi-Tenant | 10% | 85% |
| Workspace | 0% | 70% |
| ACE Memory | 0% | 85% |
| Cost/Budget | 0% | 90% |
| Agent Registry | 15% | 85% |
| GitHub Integration | 0% | 70% |
| Approval Workflow | 10% | 85% |
| Alerting | 0% | 80% |
| Event Bus | 20% | 85% |
| Context/Memory | 5% | 80% |
| Quality/Baseline | 0% | 75% |
| Watchdog | 0% | 85% |
| Restart Protocol | 0% | 80% |
| Dependency Graph | 0% | 75% |
| Full E2E | 5% | 50% |

---

## Part 11: ACE Memory Learning System

### 11.1 ACE Executor (Memory Storage)

**File**: `tests/test_e2e_ace_executor.py`

| Test | What It Proves |
|------|----------------|
| `test_execute_stores_memory` | Task outcome stored in DB |
| `test_memory_embedding_generated` | Memory gets vector embedding |
| `test_file_linking_tracked` | Files touched are recorded |
| `test_tool_usage_captured` | Tool calls logged |
| `test_memory_searchable` | Memory retrievable by similarity |
| `test_memory_type_correct` | Memory categorized (success/fail/partial) |

**Env required**: Database, `LLM_FIREWORKS_API_KEY` for embeddings

---

### 11.2 ACE Reflector (Pattern Analysis)

**File**: `tests/test_e2e_ace_reflector.py`

| Test | What It Proves |
|------|----------------|
| `test_extract_insights` | Insights extracted from memory |
| `test_identify_errors` | Error patterns detected |
| `test_tag_generation` | Auto-tags applied to memory |
| `test_playbook_lookup` | Related playbook entries found |
| `test_confidence_scoring` | Insight confidence computed |
| `test_feedback_parsing` | Test output / stderr parsed |

**Env required**: Database, `LLM_FIREWORKS_API_KEY`

---

### 11.3 ACE Curator (Playbook Updates)

**File**: `tests/test_e2e_ace_curator.py`

| Test | What It Proves |
|------|----------------|
| `test_generate_playbook_delta` | Delta computed from insights |
| `test_add_playbook_bullet` | New bullet added |
| `test_update_playbook_bullet` | Existing bullet modified |
| `test_playbook_versioning` | Change ID tracked |
| `test_category_assignment` | Bullets categorized |
| `test_playbook_retrieval` | Playbook searchable |

**Env required**: Database

---

### 11.4 ACE End-to-End Workflow

**File**: `tests/test_e2e_ace_workflow.py`

| Test | What It Proves |
|------|----------------|
| `test_full_ace_pipeline` | Executor → Reflector → Curator |
| `test_ace_event_emission` | `ace.workflow.completed` event |
| `test_ace_result_structure` | ACEResult has all fields |
| `test_ace_failure_handling` | Errors don't crash pipeline |
| `test_ace_idempotency` | Re-running doesn't duplicate |

**Env required**: Database, `LLM_FIREWORKS_API_KEY`

---

## Part 12: Cost & Budget System

### 12.1 Cost Tracking

**File**: `tests/test_e2e_cost_tracking.py`

| Test | What It Proves |
|------|----------------|
| `test_record_llm_cost` | CostRecord created |
| `test_cost_calculation` | Token-to-USD math works |
| `test_cost_by_task` | Aggregate by task |
| `test_cost_by_agent` | Aggregate by agent |
| `test_cost_by_ticket` | Aggregate by ticket |
| `test_cost_by_phase` | Aggregate by phase |
| `test_cost_event_published` | `cost.recorded` event |
| `test_cost_model_yaml_loaded` | Pricing config reads |
| `test_forecast_costs` | Pending queue forecast |

**Env required**: Database

---

### 12.2 Budget Enforcement

**File**: `tests/test_e2e_budget_enforcer.py`

| Test | What It Proves |
|------|----------------|
| `test_create_global_budget` | Global budget created |
| `test_create_ticket_budget` | Per-ticket budget works |
| `test_create_agent_budget` | Per-agent budget works |
| `test_check_budget_remaining` | Remaining calculation |
| `test_update_spent` | Spent amount updated |
| `test_alert_threshold_trigger` | 80% warning event |
| `test_budget_exceeded_event` | `cost.budget.exceeded` event |
| `test_is_budget_available` | Pre-check for estimated cost |
| `test_budget_blocks_execution` | Over-budget task rejected |

**Env required**: Database

---

## Part 13: Agent Registry & Lifecycle

### 13.1 Agent Registration

**File**: `tests/test_e2e_agent_registry.py`

| Test | What It Proves |
|------|----------------|
| `test_register_agent` | Agent created with UUID |
| `test_agent_name_generation` | Human-readable name |
| `test_crypto_identity` | Public key generated |
| `test_initial_heartbeat_wait` | 60s timeout enforced |
| `test_registration_timeout` | No heartbeat → rejected |
| `test_capability_normalization` | Caps lowercased, sorted |
| `test_event_bus_subscription` | Agent subscribed to events |
| `test_spawning_to_idle_transition` | Status change after heartbeat |
| `test_registration_event` | `AGENT_REGISTERED` published |

**Env required**: Database

---

### 13.2 Agent Health & Status

**File**: `tests/test_e2e_agent_health.py`

| Test | What It Proves |
|------|----------------|
| `test_heartbeat_updates_timestamp` | `last_heartbeat_at` set |
| `test_missed_heartbeats_detected` | Unresponsive flagged |
| `test_status_transitions` | State machine enforced |
| `test_invalid_transition_rejected` | Bad state change fails |
| `test_agent_termination` | Agent removed cleanly |
| `test_stale_agent_cleanup` | Dead agents reaped |
| `test_health_status_enum` | healthy/degraded/critical |
| `test_capacity_tracking` | Agent workload tracked |

**Env required**: Database

---

### 13.3 Agent Discovery

**File**: `tests/test_e2e_agent_discovery.py`

| Test | What It Proves |
|------|----------------|
| `test_find_by_capability` | Match agents by skill |
| `test_find_idle_agents` | Only IDLE returned |
| `test_match_scoring` | Best match ranked first |
| `test_phase_affinity` | Phase-specific agents |
| `test_exclude_busy` | BUSY agents excluded |
| `test_tag_filtering` | Filter by tags |

**Env required**: Database

---

## Part 14: GitHub Integration

### 14.1 Webhook Handling

**File**: `tests/test_e2e_github_webhooks.py`

| Test | What It Proves |
|------|----------------|
| `test_verify_webhook_signature` | HMAC-SHA256 validation |
| `test_invalid_signature_rejected` | Bad signature fails |
| `test_push_event_processing` | Push webhook handled |
| `test_pr_event_processing` | PR webhook handled |
| `test_issue_event_processing` | Issue webhook handled |
| `test_unknown_event_ignored` | Unknown events safe |

**Env required**: None (mocked)

---

### 14.2 Commit Linking

**File**: `tests/test_e2e_github_commits.py`

| Test | What It Proves |
|------|----------------|
| `test_extract_ticket_id_uuid` | `ticket-{uuid}` pattern |
| `test_extract_ticket_id_hash` | `#{id}` pattern |
| `test_link_commit_to_ticket` | TicketCommit created |
| `test_duplicate_commit_ignored` | Re-linking is no-op |
| `test_commit_stats_captured` | Files changed/insertions/deletions |
| `test_commit_linked_event` | `COMMIT_LINKED` published |

**Env required**: Database

---

### 14.3 Repository Connection

**File**: `tests/test_e2e_github_repo.py`

| Test | What It Proves |
|------|----------------|
| `test_connect_repository` | Project linked to GitHub |
| `test_fetch_commit_diff` | GitHub API called |
| `test_project_not_found` | Error handled |
| `test_webhook_secret_stored` | Secret persisted |

**Env required**: `GITHUB_TOKEN` (optional)

---

## Part 15: Approval Workflow

### 15.1 Ticket Approval Gate

**File**: `tests/test_e2e_approval_workflow.py`

| Test | What It Proves |
|------|----------------|
| `test_create_ticket_pending_review` | Approval gate enabled |
| `test_create_ticket_auto_approved` | Gate disabled works |
| `test_approval_deadline_set` | Deadline computed |
| `test_approve_ticket` | PENDING → APPROVED |
| `test_reject_ticket` | PENDING → REJECTED |
| `test_rejection_reason_stored` | Reason persisted |
| `test_approve_invalid_state` | Non-pending fails |
| `test_reject_invalid_state` | Non-pending fails |

**Env required**: Database

---

### 15.2 Approval Timeout

**File**: `tests/test_e2e_approval_timeout.py`

| Test | What It Proves |
|------|----------------|
| `test_check_timeouts` | Expired tickets found |
| `test_handle_timeout` | PENDING → TIMED_OUT |
| `test_timeout_delete_action` | Ticket deleted |
| `test_timeout_archive_action` | Ticket archived |
| `test_already_approved_skip` | Approved skipped |
| `test_timeout_event` | `TICKET_TIMED_OUT` event |

**Env required**: Database

---

### 15.3 Approval Events

**File**: `tests/test_e2e_approval_events.py`

| Test | What It Proves |
|------|----------------|
| `test_pending_event` | `TICKET_APPROVAL_PENDING` |
| `test_approved_event` | `TICKET_APPROVED` |
| `test_rejected_event` | `TICKET_REJECTED` |
| `test_pending_count` | Query pending tickets |
| `test_get_approval_status` | Status retrieval |

**Env required**: Database

---

## Part 16: Alerting System

### 16.1 Alert Rules

**File**: `tests/test_e2e_alerting_rules.py`

| Test | What It Proves |
|------|----------------|
| `test_load_rules_from_yaml` | Rules parsed |
| `test_rule_condition_gt` | `value > threshold` |
| `test_rule_condition_gte` | `value >= threshold` |
| `test_rule_condition_lt` | `value < threshold` |
| `test_rule_disabled` | Disabled rules skip |
| `test_metric_name_filter` | Only matching metric |
| `test_severity_levels` | critical/warning/info |

**Env required**: None

---

### 16.2 Alert Triggering

**File**: `tests/test_e2e_alerting_trigger.py`

| Test | What It Proves |
|------|----------------|
| `test_evaluate_rules_triggers` | Alert created |
| `test_alert_stored_in_db` | Alert persisted |
| `test_alert_event_published` | `alert.triggered` event |
| `test_deduplication` | No repeat alerts |
| `test_dedup_window_expires` | Re-alert after window |
| `test_labels_attached` | Agent/phase labels |

**Env required**: Database

---

### 16.3 Alert Routing

**File**: `tests/test_e2e_alerting_routing.py`

| Test | What It Proves |
|------|----------------|
| `test_route_to_email` | Email router called |
| `test_route_to_slack` | Slack router called |
| `test_route_to_webhook` | Webhook router called |
| `test_route_to_multiple` | Multi-channel routing |
| `test_unknown_channel_logged` | Bad channel safe |

**Env required**: None (mocked)

---

### 16.4 Alert Lifecycle

**File**: `tests/test_e2e_alerting_lifecycle.py`

| Test | What It Proves |
|------|----------------|
| `test_acknowledge_alert` | `acknowledged_at` set |
| `test_resolve_alert` | `resolved_at` set |
| `test_resolution_note` | Note persisted |
| `test_get_active_alerts` | Unresolved filtered |
| `test_filter_by_severity` | Severity filter works |
| `test_acknowledge_event` | `alert.acknowledged` |
| `test_resolve_event` | `alert.resolved` |

**Env required**: Database

---

## Part 17: Event Bus & Coordination

### 17.1 Event Bus Core

**File**: `tests/test_e2e_event_bus.py`

| Test | What It Proves |
|------|----------------|
| `test_publish_event` | Event sent |
| `test_subscribe_handler` | Handler receives event |
| `test_event_type_filtering` | Only matching types |
| `test_wildcard_subscription` | `task.*` matches |
| `test_async_handler` | Async handlers work |
| `test_handler_exception` | Bad handler isolated |
| `test_event_payload_serialization` | JSON roundtrip |

**Env required**: Redis (for distributed)

---

### 17.2 Orchestrator Coordination

**File**: `tests/test_e2e_orchestrator_coordination.py`

| Test | What It Proves |
|------|----------------|
| `test_register_orchestrator` | Orchestrator registered |
| `test_heartbeat_orchestrator` | Leader heartbeat |
| `test_leader_election` | Leader chosen |
| `test_leader_failover` | New leader on timeout |
| `test_work_distribution` | Tasks split |

**Env required**: Database, Redis

---

### 17.3 Resource Locking

**File**: `tests/test_e2e_resource_lock.py`

| Test | What It Proves |
|------|----------------|
| `test_acquire_lock` | Lock obtained |
| `test_lock_prevents_access` | Second acquire blocked |
| `test_release_lock` | Lock freed |
| `test_lock_timeout` | Auto-release on expire |
| `test_deadlock_detection` | Circular detected |
| `test_lock_renewal` | Extend lock TTL |

**Env required**: Redis

---

## Part 18: Context & Memory Services

### 18.1 Context Service

**File**: `tests/test_e2e_context_service.py`

| Test | What It Proves |
|------|----------------|
| `test_build_task_context` | Context assembled |
| `test_include_ticket_info` | Ticket in context |
| `test_include_discoveries` | Discoveries in context |
| `test_include_prior_tasks` | History included |
| `test_include_playbook` | Playbook bullets |
| `test_context_size_limit` | Max tokens enforced |

**Env required**: Database

---

### 18.2 Context Summarization

**File**: `tests/test_e2e_context_summarizer.py`

| Test | What It Proves |
|------|----------------|
| `test_summarize_conversation` | Summary generated |
| `test_preserve_key_decisions` | Decisions retained |
| `test_summarize_long_context` | Long context compressed |
| `test_summary_token_budget` | Budget respected |

**Env required**: `LLM_FIREWORKS_API_KEY`

---

### 18.3 Memory Search

**File**: `tests/test_e2e_memory_service.py`

| Test | What It Proves |
|------|----------------|
| `test_search_by_similarity` | Vector search works |
| `test_search_by_task_id` | Exact task lookup |
| `test_search_by_agent` | Filter by agent |
| `test_search_by_tags` | Tag filtering |
| `test_search_results_ranked` | Most similar first |
| `test_memory_retrieval` | Full memory fetched |

**Env required**: Database, embeddings

---

## Part 19: Quality & Baseline Learning

### 19.1 Quality Predictor

**File**: `tests/test_e2e_quality_predictor.py`

| Test | What It Proves |
|------|----------------|
| `test_predict_task_quality` | Score returned |
| `test_quality_features` | Agent/task features used |
| `test_low_quality_warning` | Low score flagged |
| `test_quality_history` | Historical scores |

**Env required**: `LLM_FIREWORKS_API_KEY`

---

### 19.2 Baseline Learner

**File**: `tests/test_e2e_baseline_learner.py`

| Test | What It Proves |
|------|----------------|
| `test_record_baseline` | Baseline stored |
| `test_compare_to_baseline` | Delta computed |
| `test_adaptive_threshold` | Threshold adjusts |
| `test_anomaly_from_baseline` | Large delta flagged |

**Env required**: Database

---

### 19.3 Composite Anomaly Scoring

**File**: `tests/test_e2e_anomaly_scorer.py`

| Test | What It Proves |
|------|----------------|
| `test_compute_anomaly_score` | Score calculated |
| `test_multiple_signals` | Signals combined |
| `test_high_anomaly_trigger` | Alert threshold |
| `test_anomaly_event` | `anomaly.detected` |

**Env required**: Database

---

## Part 20: Template & Pattern Loading

### 20.1 Template Service

**File**: `tests/test_e2e_template_service.py`

| Test | What It Proves |
|------|----------------|
| `test_load_template` | Template parsed |
| `test_render_template` | Variables interpolated |
| `test_missing_var_error` | Missing var raises |
| `test_template_caching` | Cached on second load |
| `test_phase_templates` | Phase prompts load |

**Env required**: None

---

### 20.2 Pattern Loader

**File**: `tests/test_e2e_pattern_loader.py`

| Test | What It Proves |
|------|----------------|
| `test_load_workflow_pattern` | Pattern parsed |
| `test_phase_requirements` | PHASE_REQUIREMENTS load |
| `test_done_definitions` | Exit criteria load |
| `test_expected_outputs` | Deliverables load |
| `test_hot_reload` | Config reloads |

**Env required**: None

---

## Part 21: Watchdog & Remediation

### 21.1 Watchdog Monitoring

**File**: `tests/test_e2e_watchdog.py`

| Test | What It Proves |
|------|----------------|
| `test_monitor_monitor_agents` | Watchdog finds monitor agents |
| `test_detect_unresponsive_15s` | 15s TTL heartbeat detection |
| `test_detect_missed_heartbeats` | 3 missed = flagged |
| `test_detect_no_heartbeat_ever` | Never sent = flagged |
| `test_detect_status_failure` | FAILED status detected |
| `test_5s_check_interval` | Watchdog checks every 5s |

**Env required**: Database

---

### 21.2 Remediation Policies

**File**: `tests/test_e2e_watchdog_policies.py`

| Test | What It Proves |
|------|----------------|
| `test_load_policies_from_yaml` | Policies parsed |
| `test_default_policies_created` | Defaults exist |
| `test_monitor_restart_policy` | Restart policy works |
| `test_monitor_failover_policy` | Failover policy works |
| `test_escalation_config` | Escalation settings loaded |
| `test_get_policies` | API returns all policies |

**Env required**: None

---

### 21.3 Remediation Execution

**File**: `tests/test_e2e_watchdog_remediation.py`

| Test | What It Proves |
|------|----------------|
| `test_execute_restart_remediation` | Agent restarted |
| `test_execute_failover_remediation` | Tasks moved to backup |
| `test_execute_escalation` | Guardian notified |
| `test_remediation_audit_trail` | WatchdogAction created |
| `test_remediation_before_state` | Before snapshot captured |
| `test_remediation_event_published` | `watchdog.remediation.started` |
| `test_escalate_on_failure` | Failure → Guardian |
| `test_remediation_history` | History queryable |

**Env required**: Database

---

## Part 22: Restart Orchestrator

### 22.1 Restart Protocol

**File**: `tests/test_e2e_restart_orchestrator.py`

| Test | What It Proves |
|------|----------------|
| `test_initiate_restart` | Restart protocol runs |
| `test_graceful_stop` | 10s graceful timeout |
| `test_force_terminate` | Force kill after graceful |
| `test_spawn_replacement` | New agent with same config |
| `test_reassign_tasks` | Incomplete tasks moved |
| `test_restart_event` | `AGENT_RESTARTED` published |
| `test_authority_check` | Low authority rejected |
| `test_agent_not_found` | Missing agent returns None |

**Env required**: Database

---

### 22.2 Restart Limits

**File**: `tests/test_e2e_restart_limits.py`

| Test | What It Proves |
|------|----------------|
| `test_max_restart_attempts` | 3 attempts max |
| `test_escalation_window` | 1 hour window |
| `test_restart_cooldown` | 60s cooldown |
| `test_escalate_on_max_attempts` | Guardian notified |
| `test_cooldown_respected` | Too-soon restart blocked |

**Env required**: Database

---

## Part 23: Dependency Graph

### 23.1 Graph Building

**File**: `tests/test_e2e_dependency_graph.py`

| Test | What It Proves |
|------|----------------|
| `test_build_ticket_graph` | Graph built for ticket |
| `test_build_project_graph` | Graph built for project |
| `test_include_resolved` | Completed tasks optional |
| `test_include_discoveries` | Discovery nodes optional |
| `test_empty_graph` | Empty ticket handled |
| `test_node_structure` | Node has required fields |
| `test_edge_structure` | Edge has from/to/type |

**Env required**: Database

---

### 23.2 Graph Analysis

**File**: `tests/test_e2e_dependency_analysis.py`

| Test | What It Proves |
|------|----------------|
| `test_blocked_task_detection` | Blocked tasks flagged |
| `test_blocks_count` | Downstream count computed |
| `test_critical_path_calculation` | Longest path found |
| `test_critical_path_tasks` | Path task list returned |
| `test_metadata_total_tasks` | Count correct |
| `test_metadata_blocked_count` | Blocked count correct |
| `test_metadata_total_edges` | Edge count correct |
| `test_topological_sort` | Tasks sortable |

**Env required**: Database

---

## Part 24: Conversation Intervention

### 24.1 Guardian Intervention

**File**: `tests/test_e2e_conversation_intervention.py`

| Test | What It Proves |
|------|----------------|
| `test_send_intervention` | Message sent to conversation |
| `test_intervention_prefix` | `[GUARDIAN INTERVENTION]` added |
| `test_conversation_resume` | Conversation resumed |
| `test_idle_conversation_starts` | Idle conv starts processing |
| `test_running_conversation_queued` | Running conv queues message |
| `test_intervention_failure_handled` | Bad conv ID returns False |
| `test_llm_required` | Missing API key raises |

**Env required**: `LLM_API_KEY`, workspace

---

## Summary: Test Count by Part

| Part | Tests | Description |
|------|-------|-------------|
| 1 | 12 | LLM Integration |
| 2 | 17 | Agent Executor |
| 3 | 24 | Workflow Engine |
| 4 | 13 | Validation System |
| 5 | 16 | Diagnostic System |
| 6 | 14 | Multi-Agent Coordination |
| 7 | 20 | Auth & Multi-Tenant |
| 8 | 10 | Workspace & Sandbox |
| 9 | 7 | MCP Server |
| 10 | 11 | Full System Integration |
| 11 | 23 | ACE Memory System |
| 12 | 18 | Cost & Budget |
| 13 | 22 | Agent Registry |
| 14 | 16 | GitHub Integration |
| 15 | 18 | Approval Workflow |
| 16 | 21 | Alerting System |
| 17 | 17 | Event Bus & Coordination |
| 18 | 16 | Context & Memory |
| 19 | 13 | Quality & Baseline |
| 20 | 10 | Template & Pattern |
| 21 | 20 | Watchdog & Remediation |
| 22 | 13 | Restart Orchestrator |
| 23 | 15 | Dependency Graph |
| 24 | 7 | Conversation Intervention |
| **TOTAL** | **394** | |

---

## Implementation Priority

### Phase 1: Prove LLMs Work (Day 1)
1. `test_e2e_llm_fireworks.py` - verify Fireworks path
2. `test_e2e_llm_openhands.py` - verify z.ai path
3. `test_e2e_agent_executor.py` - verify agent runs

### Phase 2: Prove Core Workflow Works (Day 2-3)
4. `test_e2e_ticket_lifecycle.py`
5. `test_e2e_discovery.py`
6. `test_e2e_validation.py`
7. `test_e2e_diagnostic_spawn.py`

### Phase 3: Prove Multi-Tenant Works (Day 4)
8. `test_e2e_auth.py`
9. `test_e2e_authorization.py`
10. `test_e2e_organizations.py`

### Phase 4: Cost & Budget (Day 5)
11. `test_e2e_cost_tracking.py`
12. `test_e2e_budget_enforcer.py`

### Phase 5: Agent Lifecycle (Day 6)
13. `test_e2e_agent_registry.py`
14. `test_e2e_agent_health.py`
15. `test_e2e_approval_workflow.py`

### Phase 6: Memory & Learning (Day 7)
16. `test_e2e_ace_workflow.py`
17. `test_e2e_memory_service.py`
18. `test_e2e_context_service.py`

### Phase 7: Full System (Day 8-9)
19. `test_e2e_full_workflow.py`
20. `test_e2e_mcp_tools.py`
21. `test_e2e_workspace_daytona.py`
22. `test_e2e_alerting_lifecycle.py`
23. `test_e2e_github_commits.py`

### Phase 8: Monitoring & Remediation (Day 10)
24. `test_e2e_watchdog.py`
25. `test_e2e_restart_orchestrator.py`
26. `test_e2e_dependency_graph.py`
27. `test_e2e_conversation_intervention.py`

### Phase 9: Advanced Services (Day 11-12)
28. `test_e2e_quality_predictor.py`
29. `test_e2e_baseline_learner.py`
30. `test_e2e_anomaly_scorer.py`
31. `test_e2e_template_service.py`
32. `test_e2e_pattern_loader.py`

---

## Test Priority Matrix

### Critical Path (Must Pass Before Deploy)
| Test File | Why Critical |
|-----------|-------------|
| `test_e2e_llm_fireworks.py` | LLM is core functionality |
| `test_e2e_llm_openhands.py` | Agent execution depends on LLM |
| `test_e2e_ticket_lifecycle.py` | Core workflow |
| `test_e2e_auth.py` | Security gate |
| `test_e2e_budget_enforcer.py` | Cost control |
| `test_e2e_agent_registry.py` | Agent lifecycle |

### High Priority (Should Pass)
| Test File | Why Important |
|-----------|---------------|
| `test_e2e_validation.py` | Quality gate |
| `test_e2e_diagnostic_spawn.py` | Self-healing |
| `test_e2e_approval_workflow.py` | Human-in-loop |
| `test_e2e_watchdog.py` | Meta-monitoring |
| `test_e2e_cost_tracking.py` | Cost visibility |

### Medium Priority (Nice to Have)
| Test File | Purpose |
|-----------|--------|
| `test_e2e_ace_workflow.py` | Learning system |
| `test_e2e_github_commits.py` | Integration |
| `test_e2e_alerting_lifecycle.py` | Observability |
| `test_e2e_dependency_graph.py` | Visualization |
