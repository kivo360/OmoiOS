# Multi-Agent Orchestration System - Implementation Questions

**Document Purpose**: This document contains focused implementation questions to guide the development of the multi-agent orchestration system using the OpenHands Software Agent SDK framework.

**Target Audience**: Development team, AI spec agents, system architects

**Related Documents**:
- [OpenHands SDK Documentation](https://deepwiki.com/OpenHands/software-agent-sdk)
- [Multi-Agent Orchestration Design](./design/multi_agent_orchestration.md)
- [Requirements](./requirements/multi_agent_orchestration.md)

**Created**: 2025-11-16

---

## Document Index

1. [Foundation & OpenHands Integration](#1-foundation--openhands-integration) (8 questions)
2. [Agent Architecture & Types](#2-agent-architecture--types) (8 questions)
3. [Conversation & Event Management](#3-conversation--event-management) (6 questions)
4. [Task Queue & Workflow Orchestration](#4-task-queue--workflow-orchestration) (6 questions)
5. [Workspace & Tool Integration](#5-workspace--tool-integration) (6 questions)
6. [Monitoring & Health Management](#6-monitoring--health-management) (6 questions)

**Total Questions**: 40

---

## 1. Foundation & OpenHands Integration

### Q1.1: OpenHands Package Selection [CRITICAL]
**Context**: OpenHands provides 4 packages: openhands-sdk (core), openhands-tools, openhands-workspace, openhands-agent-server.

**Question**: Which OpenHands packages should we use as the foundation for each agent type (Worker, Monitor, Watchdog, Guardian), and should we use the openhands-agent-server package for our orchestration layer or build a custom service?

**Considerations**:
- Worker agents need SDK + Tools + Workspace
- Monitor/Watchdog agents might only need SDK for metrics
- Agent server provides REST/WebSocket APIs we might leverage
- Custom orchestration might need direct SDK integration

**Related Requirements**: REQ-ALM-001, REQ-ALM-002

---

### Q1.2: Agent Base Class Extension [CRITICAL]
**Context**: OpenHands provides `openhands.sdk.agent.Agent` as the core agent orchestration class.

**Question**: Should we extend the `openhands.sdk.agent.Agent` class for our worker agents or create separate agent classes that compose/wrap the OpenHands Agent? What properties and methods do we need to add for our multi-agent architecture (heartbeat emission, status management, anomaly detection)?

**Considerations**:
- OpenHands Agent handles LLM calls, tool execution, event generation
- We need additional lifecycle management (registration, heartbeat, status transitions)
- Monitor/Watchdog agents have different behavior than execution agents
- Need to maintain compatibility with OpenHands patterns

**Related Requirements**: REQ-ALM-001, REQ-ALM-004

---

### Q1.3: LLM Configuration Strategy [HIGH]
**Context**: OpenHands uses `litellm` for multi-provider LLM support with unified interface.

**Question**: How should we configure LLM access for different agent types - should each agent type have dedicated LLM configurations (models, providers, rate limits), or use a shared configuration? Do we need different models for different phases (e.g., Claude for implementation, GPT-4 for analysis)?

**Considerations**:
- Different phases may need different model capabilities
- Cost optimization per agent type
- Rate limiting per agent vs. global
- Model routing based on task complexity

**Related Requirements**: REQ-PERF-001, REQ-REL-003

---

### Q1.4: Event Bus Architecture [CRITICAL]
**Context**: OpenHands has an internal event system (`MessageEvent`, `ActionEvent`, `ObservationEvent`). Our design requires a central Event Bus for inter-agent communication.

**Question**: Should we use OpenHands' internal event system as our Event Bus, or integrate an external message broker (Redis Pub/Sub, RabbitMQ, Kafka)? How do we bridge OpenHands agent-level events with our system-level events (AGENT_REGISTERED, HEARTBEAT_MISSED, etc.)?

**Considerations**:
- OpenHands events are agent-scoped, we need system-wide events
- Need pub/sub for Monitor → Worker communication
- Event persistence and replay requirements
- Scalability for 100+ concurrent agents

**Related Requirements**: REQ-MON-001, REQ-PERF-003

---

### Q1.5: State Store Selection [CRITICAL]
**Context**: OpenHands agent-server uses SQLite with Alembic migrations. Our design requires ACID transactions and high availability.

**Question**: Should we extend OpenHands' SQLite schema for our multi-agent state (agents, tasks, tickets, alerts), or use a separate database (PostgreSQL)? How do we integrate OpenHands' conversation persistence with our ticket workflow persistence?

**Considerations**:
- SQLite limitations for concurrent writes
- Need for complex queries (task assignment, blocking detection)
- Separate databases means sync complexity
- Schema migration strategy

**Related Requirements**: REQ-REL-002, REQ-TQM-001

---

### Q1.6: Workspace Isolation Strategy [HIGH]
**Context**: OpenHands provides LocalWorkspace, DockerWorkspace, and RemoteWorkspace implementations.

**Question**: Which workspace mode should we use for worker agents - Docker for isolation, Local for performance, or Remote for scalability? Should each ticket get a dedicated workspace instance, or do we pool workspaces across agents?

**Considerations**:
- Docker provides isolation but adds overhead
- Local is fast but lacks isolation
- Remote enables distributed execution
- Workspace lifecycle management (create, cleanup, reuse)

**Related Requirements**: REQ-SEC-001, REQ-PERF-004

---

### Q1.7: OpenHands Server Integration [MEDIUM]
**Context**: OpenHands provides a REST/WebSocket API server with ConversationService and EventService.

**Question**: Should we run OpenHands agent-server as a microservice that our orchestration layer calls via REST/WebSocket, or embed the SDK directly in our orchestration service? If using the server, how do we map our concepts (tickets, tasks, agents) to OpenHands conversations?

**Considerations**:
- Server mode adds network hop but provides isolation
- Direct SDK integration is tighter but more coupled
- WebSocket streaming for real-time events
- Conversation-to-ticket mapping complexity

**Related Requirements**: REQ-PERF-001, REQ-OBS-004

---

### Q1.8: Deployment Model Decision [CRITICAL]
**Context**: OpenHands supports standalone SDK, managed server, Docker container, and remote API modes.

**Question**: What deployment architecture should we use - monolithic service with embedded OpenHands SDK, microservices with agent-server instances per phase, or hybrid with Guardian/Watchdog as separate services? How does this affect our scaling strategy for 100+ agents?

**Considerations**:
- Monolith is simpler but harder to scale
- Microservices enable independent scaling
- Hybrid balances complexity and flexibility
- Container orchestration (Kubernetes) requirements

**Related Requirements**: REQ-PERF-004, REQ-REL-001

---

## 2. Agent Architecture & Types

### Q2.1: Worker Agent Implementation [HIGH]
**Context**: We have 5 worker agent types (Requirements, Implementation, Validation, Analysis, Testing). OpenHands Agent is generic.

**Question**: Should we create 5 separate agent classes inheriting from `openhands.sdk.agent.Agent`, or use a single `WorkerAgent` class with phase-specific configuration and tool sets? How do we map our phase_id to OpenHands agent capabilities?

**Considerations**:
- Separate classes allow phase-specific logic
- Single class with config is more maintainable
- Tool availability differs by phase
- LLM prompts need phase-specific context

**Related Requirements**: REQ-ALM-001, REQ-PHS-001

---

### Q2.2: Monitor Agent Design [HIGH]
**Context**: Monitor agents don't execute tasks - they watch worker agents. OpenHands Agent is designed for task execution.

**Question**: Should Monitor agents use the OpenHands SDK at all, or should they be pure Python services that only interact with the Event Bus and State Store? If using OpenHands, what subset of functionality do they need?

**Considerations**:
- Monitors don't need LLM capabilities
- Monitors don't need workspace or tools
- Monitors need efficient metrics collection
- Simpler implementation might be better

**Related Requirements**: REQ-MON-001, REQ-MON-002

---

### Q2.3: Agent-to-Conversation Mapping [HIGH]
**Context**: OpenHands uses `Conversation` objects to manage agent lifecycle and message history. Our system has tickets with multiple tasks.

**Question**: What is the mapping between OpenHands Conversations and our concepts - one Conversation per agent instance, per task, per ticket, or per phase? How do we handle conversation persistence when agents restart?

**Considerations**:
- Conversation per task enables task-level isolation
- Conversation per ticket maintains context across phases
- Conversation per agent limits context switching
- Persistence affects memory usage and performance

**Related Requirements**: REQ-ALM-003, REQ-TQM-003

---

### Q2.4: Agent Registration Protocol [HIGH]
**Context**: Our design requires pre-registration validation (binary integrity, version compatibility, resource checks). OpenHands has no built-in registration protocol.

**Question**: Where and how do we implement the agent registration protocol - in a custom `AgentRegistry` service that wraps OpenHands agent instantiation, or by extending the OpenHands Agent class with registration hooks? What triggers registration - agent startup or first action?

**Considerations**:
- Registration must happen before agent accepts tasks
- Validation checks need external dependencies
- Crypto identity generation for agents
- Registry must be highly available

**Related Requirements**: REQ-ALM-001

---

### Q2.5: Heartbeat Mechanism [HIGH]
**Context**: Our design requires bidirectional heartbeat with adaptive frequency (30s IDLE, 15s RUNNING). OpenHands has no built-in heartbeat.

**Question**: How do we implement the heartbeat protocol - as a background thread in each agent, an async task in the event loop, or through OpenHands' event system? Where does the HeartbeatManager live - in each agent or as a central service?

**Considerations**:
- Heartbeats must continue during LLM calls
- Missed heartbeats trigger restart protocol
- Heartbeat payloads include health metrics
- Clock skew and network latency handling

**Related Requirements**: REQ-ALM-002, REQ-MON-001

---

### Q2.6: Agent Status State Machine [MEDIUM]
**Context**: Our design has 7 agent statuses (SPAWNING, IDLE, RUNNING, DEGRADED, FAILED, QUARANTINED, TERMINATED). OpenHands doesn't have status management.

**Question**: Where do we enforce the agent status state machine - in each agent instance (local state), in the AgentRegistry (central authority), or both with synchronization? How do status transitions integrate with OpenHands event emission?

**Considerations**:
- Local state is faster but can diverge
- Central authority ensures consistency
- Status transitions need to be atomic
- Status affects task assignment eligibility

**Related Requirements**: REQ-ALM-004

---

### Q2.7: Guardian Agent Authority [MEDIUM]
**Context**: Guardian agent needs override authority (force terminate any agent, resource reallocation). OpenHands has no privilege model.

**Question**: How do we implement Guardian override authority - through special authentication tokens, direct database access, or a privileged API? What safety mechanisms prevent Guardian abuse (rate limiting, audit logging, human notification)?

**Considerations**:
- Override must work even when target agent is unresponsive
- Need complete audit trail of override actions
- Rate limiting to prevent Guardian runaway
- Singleton Guardian vs. active/standby pattern

**Related Requirements**: REQ-MON-003, REQ-SEC-004

---

### Q2.8: Agent Resurrection Logic [MEDIUM]
**Context**: Our design requires agent resurrection with state reconstruction, task continuity, and identity preservation. OpenHands has conversation persistence but no agent resurrection.

**Question**: How do we implement agent resurrection - by persisting agent state to the database and rehydrating on spawn, or by leveraging OpenHands' conversation persistence? What state needs to be preserved (configuration, capabilities, learned baselines, task checkpoints)?

**Considerations**:
- New agent gets new agent_id but links to old
- Task checkpoint strategy (per-action, per-phase, none)
- Anomaly baseline inheritance with decay
- Maximum resurrection limit enforcement (10)

**Related Requirements**: REQ-ALM-003, REQ-MON-002

---

## 3. Conversation & Event Management

### Q3.1: Event Type Hierarchy [HIGH]
**Context**: OpenHands has 3 event types (MessageEvent, ActionEvent, ObservationEvent). Our design needs system events (AGENT_REGISTERED, HEARTBEAT_MISSED, TASK_COMPLETED, etc.).

**Question**: Should we extend OpenHands' event types to include our system events, or maintain two parallel event systems (OpenHands events for agent execution, custom events for orchestration)? How do we serialize and route both types?

**Considerations**:
- OpenHands events are agent-scoped
- Our events are system-wide
- Event schema versioning
- Event persistence and replay

**Related Requirements**: REQ-TQM-003, REQ-OBS-003

---

### Q3.2: Event Delivery Guarantees [HIGH]
**Context**: Our design requires reliable event delivery with retry logic and dead letter queue. OpenHands has in-process event handling.

**Question**: What delivery guarantees do we need for different event types - at-most-once for heartbeats, at-least-once for task completion, exactly-once for ticket state transitions? How do we implement retries and idempotency?

**Considerations**:
- Different events have different criticality
- Idempotency tokens for duplicate detection
- Retry backoff strategy
- Dead letter queue for failed deliveries

**Related Requirements**: REQ-REL-002, REQ-PERF-003

---

### Q3.3: Conversation Context Management [MEDIUM]
**Context**: OpenHands provides context condensation to manage token limits. Our agents need cross-phase context (requirements → implementation → validation).

**Question**: How do we manage conversation context across phase transitions - do we pass the full OpenHands conversation object, extract and summarize key information, or use a separate memory system? How do we balance context richness vs. token cost?

**Considerations**:
- Full context maintains continuity but costs tokens
- Summarization loses detail
- Memory system adds complexity
- Different phases need different context depth

**Related Requirements**: REQ-PHS-002, REQ-PERF-001

---

### Q3.4: Event Filtering and Routing [MEDIUM]
**Context**: With 100+ agents, event volume will be high. Agents only need events relevant to their phase/tasks.

**Question**: How do we implement event filtering and routing - at the Event Bus level with topic-based subscriptions, or at the agent level with client-side filtering? What is the subscription model (agent subscribes to ticket_id, phase_id, agent_id)?

**Considerations**:
- Server-side filtering reduces network traffic
- Client-side filtering is more flexible
- Subscription management as agents join/leave
- Wildcard subscriptions for monitors

**Related Requirements**: REQ-PERF-004, REQ-MON-001

---

### Q3.5: Event Persistence Strategy [MEDIUM]
**Context**: OpenHands persists conversation events to SQLite. Our system needs event history for audit, debugging, and metrics.

**Question**: What is our event retention policy - how long do we keep events in hot storage vs. cold storage vs. delete? Do we persist all events or only critical ones (state transitions, errors, alerts)? How do we query historical events efficiently?

**Considerations**:
- Full event history enables replay and debugging
- Storage costs grow with event volume
- Query patterns: by agent_id, ticket_id, time range
- Compliance requirements for audit trail

**Related Requirements**: REQ-OBS-003, REQ-SEC-004

---

### Q3.6: WebSocket vs. REST for Events [MEDIUM]
**Context**: OpenHands agent-server provides both REST API and WebSocket streaming. Our design needs real-time event propagation.

**Question**: Should agents connect to the orchestration layer via WebSocket for bidirectional events, or poll via REST API? What about Monitor agents - do they need WebSocket connections to all workers they monitor?

**Considerations**:
- WebSocket enables real-time push
- REST is simpler but adds polling latency
- Connection limits with 100+ agents
- Fallback when WebSocket unavailable

**Related Requirements**: REQ-PERF-002, REQ-MON-001

---

## 4. Task Queue & Workflow Orchestration

### Q4.1: Task Queue Implementation [CRITICAL]
**Context**: Our design requires priority queue (CRITICAL > HIGH > MEDIUM > LOW) with phase-based routing. OpenHands has no task queue.

**Question**: Should we implement the task queue as a custom service using Redis (sorted sets for priority), PostgreSQL (with indexes), or a dedicated queue system (Celery, RQ)? How do we integrate with OpenHands agent task execution?

**Considerations**:
- Redis sorted sets are fast but memory-intensive
- PostgreSQL is durable but slower
- Dedicated queue adds dependency
- Task assignment atomicity requirements

**Related Requirements**: REQ-TQM-001, REQ-TQM-002

---

### Q4.2: Task-to-Action Mapping [HIGH]
**Context**: OpenHands Actions are tool invocations. Our Tasks are high-level work units (e.g., "Analyze requirements").

**Question**: What is the relationship between our Task and OpenHands Actions - does one Task generate multiple Actions, or is a Task a container for an OpenHands conversation? How do we track task progress (% complete, current action)?

**Considerations**:
- Tasks may require multiple LLM interactions
- Progress tracking needs granularity
- Task checkpointing for resurrection
- Partial task completion on failure

**Related Requirements**: REQ-TQM-003, REQ-TQM-005

---

### Q4.3: Discovery-Based Task Spawning [HIGH]
**Context**: Tasks can discover issues (security_issue, requires_clarification, optimization_opportunity) that spawn new tasks.

**Question**: How do we implement discovery detection - by parsing OpenHands observation content, providing agents with explicit "report discovery" tools, or analyzing conversation patterns? How do we prevent discovery spam?

**Considerations**:
- LLM must explicitly signal discoveries
- Discovery validation to prevent false positives
- Priority calculation for discovered tasks
- Cycle detection (discovery → task → discovery)

**Related Requirements**: REQ-TQM-004

---

### Q4.4: Validation Feedback Loop [HIGH]
**Context**: Failed validation creates fix task in PHASE_IMPLEMENTATION with retry limit (5).

**Question**: How do we detect validation failure and create fix tasks - does the ValidationAgent explicitly return a "needs_fix" signal, or do we parse validation results? How do we attach validation feedback to the fix task context?

**Considerations**:
- Structured validation results (pass/fail + details)
- Fix task must include error context
- Retry count tracking per ticket
- Infinite loop prevention

**Related Requirements**: REQ-TQM-005

---

### Q4.5: Phase Gate Validation [HIGH]
**Context**: Phases have completion criteria and required artifacts (e.g., building-done requires CI green + packaging bundle).

**Question**: How do we implement phase gate validation - as a dedicated ValidationOrchestrator service, as part of the PhaseGateManager, or as special validation tasks in the task queue? Who triggers gate validation (agent on task complete, orchestrator on phase monitoring)?

**Considerations**:
- Gate validation may be complex (run tests, check CI status)
- Validation may require external API calls
- Validation results affect ticket state transitions
- Validation errors need detailed feedback

**Related Requirements**: REQ-PHS-001, REQ-PHS-002

---

### Q4.6: Parallel Task Execution [MEDIUM]
**Context**: Independent tickets can run in parallel (up to MAX_CONCURRENT_TICKETS). Tasks within a ticket may have dependencies.

**Question**: How do we manage task dependencies - in the Task model (parent_task_id, dependencies[]), in a separate dependency graph, or dynamically based on phase ordering? How do we detect dependency cycles?

**Considerations**:
- Explicit dependencies are clearer but more manual
- Implicit dependencies (phase order) are automatic
- Cross-ticket dependencies (rare)
- Deadlock detection algorithm

**Related Requirements**: REQ-TKT-004, REQ-PHS-001

---

## 5. Workspace & Tool Integration

### Q5.1: Workspace Provisioning [HIGH]
**Context**: OpenHands DockerWorkspace requires Docker daemon. Worker agents need isolated workspaces per ticket.

**Question**: How do we provision workspaces - pre-create a pool of warm containers, create on-demand when ticket starts, or use serverless (Lambda, Cloud Run)? What is the workspace lifecycle (create, use, cleanup, reuse)?

**Considerations**:
- Container startup time (3-10 seconds)
- Resource limits per workspace
- Workspace reuse vs. isolation
- Cost optimization (warm pool vs. on-demand)

**Related Requirements**: REQ-PERF-001, REQ-SEC-001

---

### Q5.2: Custom Tool Development [MEDIUM]
**Context**: OpenHands provides BashTool, FileEditorTool, BrowserToolSet. We may need custom tools (GitHub API, Jira API, Supabase).

**Question**: What custom tools do we need beyond OpenHands built-in tools? How do we package and distribute custom tools - as separate packages, in a shared tools package, or dynamically loaded? Do we use OpenHands' ToolDefinition pattern?

**Considerations**:
- GitHub integration (read files, create PRs)
- Ticket system integration (create tickets, update status)
- Database access (read schema, run migrations)
- Tool versioning and updates

**Related Requirements**: REQ-MCP-001, REQ-MCP-002

---

### Q5.3: MCP Server Integration Strategy [MEDIUM]
**Context**: OpenHands has basic tool system but no explicit MCP protocol support. Our design requires MCP server integration.

**Question**: Should we implement MCP server support by extending OpenHands' tool system to support MCP protocol, or create an MCP adapter layer that translates MCP tools to OpenHands ToolDefinitions? Where does the MCP server client live?

**Considerations**:
- MCP protocol: JSON-RPC 2.0 over stdio/HTTP
- Tool schema mapping (MCP → OpenHands)
- Authentication and authorization per MCP server
- MCP server lifecycle management

**Related Requirements**: REQ-MCP-001, REQ-MCP-002, REQ-MCP-003

---

### Q5.4: Tool Authorization Model [MEDIUM]
**Context**: Different agent types should have different tool access (e.g., ValidationAgent shouldn't write code).

**Question**: How do we enforce tool authorization - at agent registration (declare allowed tools), at tool invocation (check permissions), or both? Is authorization role-based (by agent_type/phase_id) or capability-based (by individual tool)?

**Considerations**:
- Principle of least privilege
- Tool allow-list vs. deny-list
- Dynamic tool permissions (grant/revoke)
- Audit logging of tool usage

**Related Requirements**: REQ-SEC-002, REQ-SEC-004

---

### Q5.5: Workspace State Preservation [LOW]
**Context**: When agents restart or tasks fail, we may need to preserve workspace state.

**Question**: Do we need workspace state preservation (filesystem snapshots, Git commits) or can we recreate workspace from ticket artifacts? If preserving, what is the mechanism (Docker volumes, S3 uploads, Git repository)?

**Considerations**:
- State preservation adds overhead
- Most workflows are reproducible
- Debugging may require state preservation
- Storage costs for snapshots

**Related Requirements**: REQ-ALM-003, REQ-REL-002

---

### Q5.6: Browser Automation Requirements [LOW]
**Context**: OpenHands includes BrowserToolSet with 10 actions. Our design doesn't explicitly require browser automation.

**Question**: Do any of our agent types need browser automation (e.g., for testing web UIs, scraping documentation)? If so, which phases and how do we provision browser environments (headless Chrome, Playwright)?

**Considerations**:
- Testing phase might need browser testing
- Analysis phase might scrape docs/dashboards
- Browser adds significant resource requirements
- VNC/screenshots for debugging

**Related Requirements**: REQ-PHS-001 (Testing phase)

---

## 6. Monitoring & Health Management

### Q6.1: Health Metrics Collection [HIGH]
**Context**: Monitor agents need health metrics (CPU, memory, latency, errors). OpenHands doesn't expose built-in metrics.

**Question**: How do we collect agent health metrics - by instrumenting OpenHands Agent class, using external monitoring (Prometheus client), or having agents report metrics in heartbeats? What metrics are critical vs. nice-to-have?

**Considerations**:
- Metrics must be efficient (low overhead)
- Need both gauge (current status) and counter (cumulative)
- Prometheus pull vs. push model
- Metric cardinality with 100+ agents

**Related Requirements**: REQ-MON-004, REQ-OBS-001

---

### Q6.2: Anomaly Detection Implementation [MEDIUM]
**Context**: Monitor agents calculate anomaly_score (0.0-1.0) based on latency, error rate, resource usage, completion rate.

**Question**: Do we implement anomaly detection as rule-based (threshold comparisons), statistical (z-score), or ML-based (isolation forest, autoencoder)? Where does the anomaly detector run (in Monitor agent, separate service)?

**Considerations**:
- Rule-based is simple but brittle
- Statistical requires baseline computation
- ML requires training data and infrastructure
- Real-time vs. batch detection

**Related Requirements**: REQ-MON-004, REQ-MON-005

---

### Q6.3: Alert Severity and Routing [MEDIUM]
**Context**: Alerts have severity (CRITICAL, HIGH, MEDIUM, LOW) and need routing to appropriate handlers.

**Question**: What is our alert routing strategy - do we send all alerts to a central AlertManager, route based on severity, or have different channels per alert type? How do humans get notified (Slack, PagerDuty, email)?

**Considerations**:
- Alert fatigue prevention (deduplication, throttling)
- Severity escalation over time
- On-call rotation integration
- Alert acknowledgment workflow

**Related Requirements**: REQ-MON-003, REQ-PERF-003

---

### Q6.4: Restart Protocol Timing [MEDIUM]
**Context**: Our design specifies graceful shutdown (10s timeout), force terminate, spawn replacement, task reassignment.

**Question**: What are the exact timeout values for each restart phase, and how do we handle partially completed tasks during restart? Should we checkpoint task progress before restarting agent?

**Considerations**:
- Graceful shutdown must save state
- Force terminate may lose work
- Task reassignment atomicity
- Restart count per agent (max 3/hour)

**Related Requirements**: REQ-MON-002, REQ-MON-003

---

### Q6.5: Quarantine Forensics [LOW]
**Context**: Quarantined agents are preserved for forensic analysis. OpenHands has no quarantine concept.

**Question**: What do we preserve when quarantining an agent - full conversation history, workspace filesystem, memory dump, log files? How long do we keep quarantined agents, and who analyzes them (Guardian agent, human)?

**Considerations**:
- Full state preservation is expensive
- Selective preservation needs criteria
- Automated analysis vs. manual review
- Storage and retention policies

**Related Requirements**: REQ-MON-006

---

### Q6.6: Observability Integration [MEDIUM]
**Context**: Our design requires metrics (Prometheus), logs (structured JSON), traces (distributed tracing), and dashboards (Grafana).

**Question**: How do we integrate observability into OpenHands agents - by wrapping Agent methods with decorators/middleware, using OpenTelemetry auto-instrumentation, or manual instrumentation? What is our tracing strategy (trace per conversation, per task, per action)?

**Considerations**:
- OpenTelemetry provides unified observability
- Manual instrumentation is more flexible
- Trace context propagation across services
- Dashboard design (agent status, task queue depth, error rates)

**Related Requirements**: REQ-OBS-001, REQ-OBS-002, REQ-OBS-004

---

## Question Priority Summary

### CRITICAL (Must decide before starting implementation):
- Q1.1: OpenHands Package Selection
- Q1.2: Agent Base Class Extension
- Q1.4: Event Bus Architecture
- Q1.5: State Store Selection
- Q1.8: Deployment Model Decision
- Q4.1: Task Queue Implementation

### HIGH (Needed for MVP functionality):
- Q1.3: LLM Configuration Strategy
- Q1.6: Workspace Isolation Strategy
- Q2.1: Worker Agent Implementation
- Q2.2: Monitor Agent Design
- Q2.3: Agent-to-Conversation Mapping
- Q2.4: Agent Registration Protocol
- Q2.5: Heartbeat Mechanism
- Q3.1: Event Type Hierarchy
- Q3.2: Event Delivery Guarantees
- Q4.2: Task-to-Action Mapping
- Q4.3: Discovery-Based Task Spawning
- Q4.4: Validation Feedback Loop
- Q4.5: Phase Gate Validation
- Q5.1: Workspace Provisioning
- Q6.1: Health Metrics Collection

### MEDIUM (Important for production readiness):
- Q1.7: OpenHands Server Integration
- Q2.6: Agent Status State Machine
- Q2.7: Guardian Agent Authority
- Q2.8: Agent Resurrection Logic
- Q3.3: Conversation Context Management
- Q3.4: Event Filtering and Routing
- Q3.5: Event Persistence Strategy
- Q3.6: WebSocket vs. REST for Events
- Q4.6: Parallel Task Execution
- Q5.2: Custom Tool Development
- Q5.3: MCP Server Integration Strategy
- Q5.4: Tool Authorization Model
- Q6.2: Anomaly Detection Implementation
- Q6.3: Alert Severity and Routing
- Q6.4: Restart Protocol Timing
- Q6.6: Observability Integration

### LOW (Nice-to-have or can be added later):
- Q5.5: Workspace State Preservation
- Q5.6: Browser Automation Requirements
- Q6.5: Quarantine Forensics

---

## Next Steps

1. **Review Questions**: Development team reviews all 40 questions and identifies additional questions or clarifications needed.

2. **Answer Critical Questions**: Focus on the 6 CRITICAL questions first as these are blocking for implementation start.

3. **Create Decision Records**: Document decisions in Architecture Decision Records (ADRs) in `docs/decisions/`.

4. **Update Design Documents**: Incorporate decisions into design documents with specific implementation details.

5. **Create Implementation Plan**: Based on answers, create phased implementation plan with milestones.

6. **Prototype Key Components**: Build prototypes for critical architectural decisions (Event Bus, Task Queue, Agent integration).

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial 40-question document aligned with OpenHands SDK |

