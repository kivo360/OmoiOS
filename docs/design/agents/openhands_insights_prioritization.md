# OpenHands SDK Insights & Question Prioritization

**Document Purpose**: This document synthesizes key insights from OpenHands SDK documentation research and proposes a revised prioritization strategy for implementation questions, optimized for spec-driven development (tests-first approach).

**Created**: 2025-11-16  
**Related Documents**:
- [OpenHands SDK Documentation Findings](./openhands_sdk_doc_findings.md)
- [Implementation Questions](./implementation_questions.md)
- [Multi-Agent Orchestration Design](./design/multi_agent_orchestration.md)

---

## Key Insights from Documentation Research

### 1. **OpenHands is Conversation-Scoped, Not System-Scoped**

**Finding**: OpenHands events (`MessageEvent`, `ActionEvent`, `ObservationEvent`) are tied to individual `Conversation` instances. The `EventService` manages events per conversation, not system-wide.

**Technical Details**:
- All events inherit from the base `Event` class (immutable with `frozen=True` in `model_config`)
- Event types include: `SystemPromptEvent`, `MessageEvent`, `ActionEvent`, `ObservationEvent`, `AgentErrorEvent`, `Condensation`, `PauseEvent`, `ConversationStateUpdateEvent`
- Events have common fields: `id` (unique), `timestamp`, `source` (agent/user/environment)
- `LLMConvertibleEvent` subset can be converted to LLM `Message` objects for context construction
- `EventService` uses `PubSub[Event]` class with `subscribe(subscriber)`, `unsubscribe(subscriber_id)`, and async `__call__(event)` methods
- Each subscriber receives events independently; failures in one subscriber don't affect others
- `ConversationState._state.set_on_state_change(callback)` enables state change hooks

**Implication**: Our orchestration layer must build a separate system-wide event bus (Redis Pub/Sub, RabbitMQ, Kafka) for cross-agent communication, monitoring alerts, and workflow coordination. OpenHands provides the raw event data via callbacks/APIs, but we own the routing and persistence.

**Affects Questions**: Q1.4, Q3.1, Q3.2, Q3.6

**SDK Reference**: 
- Source: `openhands-sdk/openhands/sdk/event/`
- Event Service: `openhands-agent-server/openhands/agent_server/event_service.py`
- [DeepWiki – Event System](https://deepwiki.com/OpenHands/software-agent-sdk#5.3)

---

### 2. **File-Based Persistence by Default**

**Finding**: OpenHands uses `FileStore` (local filesystem) for conversation persistence. `base_state.json` + `events/` directory per conversation. No built-in SQLite/PostgreSQL support.

**Technical Details**:
- `ConversationState` is a Pydantic model with fields: `id`, `agent`, `workspace`, `persistence_dir`, `max_iterations`, `agent_status`, `confirmation_policy`, `stats`, `secret_registry`
- Private attributes: `_fs` (FileStore), `_events` (EventLog), `_autosave_enabled`, `_on_state_change`, `_lock`
- Key methods:
  - `ConversationState.create(...)` - Factory method to resume existing or create new conversation
  - `_save_base_state(fs)` - Persists base state snapshot (excluding events)
  - `__setattr__(name, value)` - Auto-persists public field changes if autosave enabled
- `FileStore` abstract interface with methods: `write(path, contents)`, `read(path)`, `list(path)`, `delete(path)`
- Implementations: `LocalFileStore` (disk), `InMemoryFileStore` (non-persistent)
- Events stored separately in `EventLog` using same `FileStore`
- Custom persistence: Implement `FileStore` interface and inject into `ConversationState.create()`

**Implication**: We need a separate PostgreSQL database for tickets, tasks, agent registry, and workflow state. OpenHands conversation files can coexist, but our orchestration metadata lives in PostgreSQL. To integrate custom persistence, we'd implement the `FileStore` interface or sync conversation artifacts to PostgreSQL.

**Affects Questions**: Q1.5, Q2.8, Q3.5

**SDK Reference**:
- Source: `openhands-sdk/openhands/sdk/conversation/state.py`
- FileStore: `openhands-sdk/openhands/sdk/filestore/`
- [DeepWiki – State Persistence](https://deepwiki.com/OpenHands/software-agent-sdk#5.5)

---

### 3. **No Built-In Task Queue**

**Finding**: OpenHands automation workflows rely on external orchestration (GitHub Actions). The SDK has no internal task queue or scheduling mechanism. Agents have a `task_tracker` tool for internal task decomposition, but this is conversation-scoped.

**Technical Details**:
- GitHub Actions orchestration examples use:
  - Scheduled triggers: `cron: "0 2 * * *"` for daily runs
  - Event-based triggers: `pull_request_target`, `label_added`, etc.
  - Manual triggers: `workflow_dispatch` for on-demand execution
  - Matrix strategy: `matrix.query` for parallel job execution with `max-parallel: 1` for conflict avoidance
- `TaskTrackerTool` (included in `get_default_agent()`) helps agents decompose work internally within a single conversation
- No agent-to-agent task delegation or priority queue
- No retry logic or task dependency management at SDK level

**Implication**: We must implement our own priority queue (Redis sorted sets, PostgreSQL with indexes, or Celery/RQ) for task assignment, retries, and phase transitions. OpenHands agents are invoked as workers by our orchestration layer. The SDK provides conversation-level task tracking but not system-level orchestration.

**Affects Questions**: Q4.1, Q4.2, Q4.3, Q4.4, Q4.5

**SDK Reference**:
- Examples: `examples/03_github_workflows/`
- TaskTrackerTool: `openhands-tools/openhands/tools/task_tracker/`
- [DeepWiki – Automation Workflows](https://deepwiki.com/OpenHands/software-agent-sdk#9.4)

---

### 4. **Workspace Modes Are Well-Defined**

**Finding**: Three clear workspace types: `LocalWorkspace` (no isolation), `DockerWorkspace` (container isolation), `RemoteWorkspace` (HTTP API to agent server). Documentation provides clear use case guidance.

**Technical Details**:
- `LocalWorkspace`: Direct filesystem and shell access on host machine (no isolation)
  - Use case: Local development, trusted scripts, direct system access acceptable
  - Created via: `Conversation(workspace="/path/to/project")` or `Workspace(host=None)`
- `DockerWorkspace`: Container-level isolation with reproducible snapshots
  - Use case: Untrusted code execution, CI environments, reproducible builds
  - Inherits from `RemoteWorkspace`
  - Requires Docker daemon running
- `RemoteWorkspace` / `AsyncRemoteWorkspace`: HTTP/WebSocket API to remote agent server
  - Use case: Multi-tenant deployments, cloud execution, API-based control
  - Created via: `Workspace(host="http://localhost:8000")`
  - Methods: `execute_command(cmd)` returns `{exit_code, stdout, stderr}`
  - `AsyncRemoteWorkspace` uses `httpx.AsyncClient` for non-blocking operations
- Workspace interface provides: `execute_command()`, `read_file()`, `write_file()`, `list_files()`

**Implication**: Decision is straightforward based on security/isolation requirements. Docker recommended for untrusted workloads; Remote for multi-tenant deployments. Container startup overhead (3-10 seconds) affects workspace provisioning strategy.

**Affects Questions**: Q1.6, Q1.8, Q5.1

**SDK Reference**:
- Source: `openhands-workspace/openhands/workspace/`
- Remote: `openhands-sdk/openhands/sdk/workspace/remote/`
- [DeepWiki – Workspace Environments](https://deepwiki.com/OpenHands/software-agent-sdk#7)

---

### 5. **LLM Configuration is Highly Flexible**

**Finding**: Each agent can have its own `LLM` instance with provider-specific config, retry policies, and routing strategies (`MultimodalRouter`, `RandomRouter`). Supports per-agent model selection and rate limiting.

**Technical Details**:
- `LLM` is a Pydantic `BaseModel` with fields:
  - Core: `model` (provider-prefixed like `"openai/gpt-4o"`, `"anthropic/claude-sonnet-4"`), `api_key`, `base_url`
  - Provider-specific: `aws_access_key_id`, `aws_region_name`, `openrouter_site_url`, etc.
  - Inference params: `temperature`, `top_p`, `top_k`, `max_input_tokens`, `max_output_tokens`
  - Retry config: `num_retries`, `retry_multiplier`, `retry_min_wait`, `retry_max_wait`
  - Telemetry: `usage_id` for tracking, auto-tracked token usage and costs
- Special handling:
  - `"openhands/*"` models rewritten to `"litellm_proxy/*"` with specific base URL
  - Azure models get automatic `api_version` setting
- Router implementations:
  - `MultimodalRouter`: Routes based on multimodal content (images) or token limits
  - `RandomRouter`: Randomly selects from predefined LLM list
- `AgentBase` has `llm` field accepting `LLM` instance
- `LocalConversation` initializes `LLMRegistry` to track multiple LLM instances
- Automatic retry on `RateLimitError` and other transient failures

**Implication**: We can implement phase-specific LLM strategies (e.g., Claude for implementation, GPT-4 for analysis) without framework limitations. Each agent type can have dedicated LLM config with independent rate limits and cost tracking.

**Affects Questions**: Q1.3, Q6.1

**SDK Reference**:
- Source: `openhands-sdk/openhands/sdk/llm/`
- Routers: `openhands-sdk/openhands/sdk/llm/router/`
- [DeepWiki – LLM Configuration](https://deepwiki.com/OpenHands/software-agent-sdk#4.1)

---

### 6. **Agent Server is Optional**

**Finding**: OpenHands supports both embedded SDK mode (direct Python imports) and server mode (REST/WebSocket API). The server provides isolation and API boundaries but adds network overhead.

**Technical Details**:
- **Embedded SDK Mode**:
  - Direct imports: `from openhands.sdk import Agent, Conversation, LLM`
  - In-process execution, no network overhead
  - Full control over agent lifecycle
  - Example: `conversation = Conversation(agent=agent, workspace=os.getcwd())`
- **Server Mode** (`openhands-agent-server`):
  - Start server: `python -m openhands.agent_server --port 8000 --host 127.0.0.1`
  - REST API endpoints:
    - `POST /api/conversations` - Create conversation with agent config
    - `POST /api/conversations/{id}/run` - Execute agent
    - `GET /api/conversations/{id}/events` - Retrieve events
    - `GET /api/conversations/{id}/events/search` - Filter events with pagination
    - `DELETE /conversations/{id}` - Delete conversation and workspace files
  - WebSocket: `/conversations/{id}/events/socket` - Real-time event streaming
  - Client: `workspace = Workspace(host="http://localhost:8000")`
  - Storage: `workspace/conversations` directory (configurable via `conversations_path`)
- Server components:
  - `ConversationService`: CRUD operations, message handling, state persistence
  - `EventService`: Event streaming, WebSocket subscribers, buffering
  - Database: SQLite with alembic migrations (for server metadata)
  - `ManagedAPIServer`: Programmatic server control for testing

**Implication**: We can choose based on deployment architecture: embed SDK for monolithic services, use server for microservices or remote execution. Server mode enables better isolation, independent scaling, and API-driven orchestration.

**Affects Questions**: Q1.7, Q1.8

**SDK Reference**:
- Server: `openhands-agent-server/openhands/agent_server/`
- REST API: `openhands-agent-server/openhands/agent_server/README.md`
- [DeepWiki – Agent Server](https://deepwiki.com/OpenHands/software-agent-sdk#8)

---

### 7. **Event Callbacks Enable Observability**

**Finding**: Conversations accept callback hooks that receive every `Event`, allowing orchestration layers to capture telemetry, metrics, and health data. SDK tracks LLM token usage and costs.

**Technical Details**:
- Callback registration: `Conversation(agent=agent, workspace=workspace, callbacks=[event_callback])`
- Callback signature: `def event_callback(event: Event) -> None`
- Callback receives all events: `MessageEvent`, `ActionEvent`, `ObservationEvent`, `AgentErrorEvent`, etc.
- `LLMConvertibleEvent` subset can be filtered: `if isinstance(event, LLMConvertibleEvent): llm_messages.append(event.to_llm_message())`
- Metrics access:
  - `llm.metrics.accumulated_cost` - Total API cost
  - `llm.metrics.accumulated_tokens` - Total tokens used
  - `conversation.conversation_stats.get_combined_metrics()` - Aggregated metrics
- Multiple callbacks supported: callbacks receive events independently
- No built-in heartbeat or health monitoring; must implement via callbacks
- Example pattern:
  ```python
  all_events = []
  def event_callback(event: Event):
      all_events.append(event)
      logger.info(f"Event: {type(event).__name__}")
  ```

**Implication**: We can implement heartbeat emission, health metrics collection, and anomaly detection by instrumenting OpenHands callbacks, even though the SDK doesn't provide these features natively. Callbacks provide the raw data stream for building custom monitoring and observability layers.

**Affects Questions**: Q2.5, Q6.1, Q6.6

**SDK Reference**:
- Source: `openhands-sdk/openhands/sdk/conversation/`
- Event types: `openhands-sdk/openhands/sdk/event/`
- [Context7 – Event Callback Example](https://context7.com/openhands/software-agent-sdk/llms.txt)

---

### 8. **Agent Extension and Tool System**

**Finding**: OpenHands `Agent` class provides a clean tool-based extension model. Agents are configured with LLM, tools, and optional context/skills.

**Technical Details**:
- **Agent Configuration**:
  - `Agent(llm=llm, tools=[Tool(name="TerminalTool"), Tool(name="FileEditorTool")])`
  - `AgentBase` has fields: `llm`, `tools`, `agent_context`, `confirmation_policy`
  - Preset agent: `get_default_agent(llm=llm, cli_mode=True)` includes TerminalTool, FileEditorTool, TaskTrackerTool, built-in tools (Finish, Think)
- **Tool Registration**:
  - `register_tool(name, tool_class)` - Register custom tools globally
  - `Tool(name="MyTool")` - Reference tool by name in agent config
  - Tools follow Action/Observation pattern with `ToolDefinition` binding
- **Agent Context & Skills**:
  - `AgentContext(skills=[...], system_message_suffix="...")` - Add dynamic context
  - `Skill(name="...", content="...", trigger=None)` - Always-active skills
  - `Skill(name="...", content="...", trigger=KeywordTrigger(keywords=["deploy"]))` - Conditional skills
  - Skills inject instructions/knowledge into agent behavior
- **Conversation Persistence**:
  - `Conversation(persistence_dir="/path", conversation_id="session-001")` - Enable state persistence
  - Same `conversation_id` resumes previous session with full event history
  - `ConversationState.create()` handles agent reconciliation on resume
- **No Built-In Lifecycle Hooks**:
  - No registration protocol, heartbeat mechanism, or status management hooks
  - Agent lifecycle managed externally through conversation creation/closure
  - Extension points limited to: tools, callbacks, agent context, custom persistence backends

**Implication**: We must wrap or compose OpenHands `Agent` to add lifecycle management (registration, heartbeat, status transitions). The tool system is extensible for adding GitHub/Jira/Supabase integrations. Agent context/skills can inject phase-specific instructions.

**Affects Questions**: Q1.2, Q2.1, Q2.4, Q2.5, Q2.6, Q5.2

**SDK Reference**:
- Agent: `openhands-sdk/openhands/sdk/agent/`
- Tools: `openhands-tools/openhands/tools/`
- Context: `openhands-sdk/openhands/sdk/context/`
- [DeepWiki – Agent Configuration](https://deepwiki.com/OpenHands/software-agent-sdk#3.1)
- [DeepWiki – Tool System Architecture](https://deepwiki.com/OpenHands/software-agent-sdk#6.1)

---

## Revised Question Prioritization Strategy

### **TIER 0: Foundation Architecture (Must Answer Before Any Code)**

These questions define the fundamental architecture and data models. They block writing interface contracts, database schemas, and test specifications.

#### **0.1: State Store Selection** (Q1.5)
- **Why Critical**: Blocks database schema design, migration strategy, and all persistence tests.
- **OpenHands Insight**: File-based only; we need PostgreSQL for tickets/tasks/agents.
- **Decision Needed**: PostgreSQL schema design, conversation-to-ticket mapping strategy.
- **Blocks**: Q2.3, Q2.8, Q3.5, Q4.1 (task queue persistence)

#### **0.2: Event Bus Architecture** (Q1.4)
- **Why Critical**: Blocks event type definitions, pub/sub contracts, and all inter-agent communication tests.
- **OpenHands Insight**: Conversation-scoped events; we need system-wide bus.
- **Decision Needed**: Redis vs. RabbitMQ vs. Kafka; event schema design.
- **Blocks**: Q3.1, Q3.2, Q3.4, Q3.6

#### **0.3: Task Queue Implementation** (Q4.1)
- **Why Critical**: Blocks task assignment logic, priority handling, and workflow orchestration tests.
- **OpenHands Insight**: No built-in queue; external orchestration required.
- **Decision Needed**: Redis sorted sets vs. PostgreSQL vs. Celery; queue schema.
- **Blocks**: Q4.2, Q4.3, Q4.4, Q4.5, Q4.6

#### **0.4: Agent-to-Conversation Mapping** (Q2.3)
- **Why Critical**: Blocks agent lifecycle tests, conversation persistence strategy, and task execution contracts.
- **OpenHands Insight**: One conversation per agent instance is typical; we need to map to tickets/tasks.
- **Decision Needed**: One conversation per task vs. per ticket vs. per agent; conversation reuse strategy.
- **Blocks**: Q2.1, Q2.4, Q2.8

---

### **TIER 1: Core Component Design (Blocks MVP Implementation)**

These questions define how core components work. They block writing component interfaces and integration tests.

#### **1.1: OpenHands Package Selection** (Q1.1)
- **Why High**: Determines dependencies, deployment model, and agent implementation approach.
- **OpenHands Insight**: Layered packages (SDK, Tools, Workspace, Server); choose based on agent type.
- **Decision Needed**: Which packages per agent type; server vs. embedded SDK.
- **Blocks**: Q1.2, Q1.7, Q1.8, Q2.1, Q2.2

#### **1.2: Agent Base Class Extension** (Q1.2)
- **Why High**: Defines agent interface contracts and lifecycle hooks.
- **OpenHands Insight**: `openhands.sdk.agent.Agent` handles LLM/tools/events; we need lifecycle management.
- **Decision Needed**: Extend vs. wrap vs. compose; registration/heartbeat hooks.
- **Blocks**: Q2.1, Q2.4, Q2.5, Q2.6

#### **1.3: Worker Agent Implementation** (Q2.1)
- **Why High**: Defines how worker agents execute tasks and interact with OpenHands.
- **OpenHands Insight**: Generic `Agent` class; we need phase-specific configurations.
- **Decision Needed**: Single `WorkerAgent` with config vs. 5 separate classes.
- **Blocks**: Q2.3, Q4.2, Q5.1

#### **1.4: Deployment Model Decision** (Q1.8)
- **Why High**: Determines service boundaries, scaling strategy, and deployment tests.
- **OpenHands Insight**: Standalone SDK, managed server, Docker, or remote API modes available.
- **Decision Needed**: Monolith vs. microservices vs. hybrid; container orchestration.
- **Blocks**: Q1.6, Q1.7, Q5.1

#### **1.5: Workspace Isolation Strategy** (Q1.6)
- **Why High**: Defines execution environment and security boundaries.
- **OpenHands Insight**: Local/Docker/Remote modes with clear use cases.
- **Decision Needed**: Docker for isolation vs. Local for performance; workspace pooling strategy.
- **Blocks**: Q5.1, Q5.5

---

### **TIER 2: Integration & Lifecycle (Needed for MVP Functionality)**

These questions define how components integrate and manage lifecycle. They block end-to-end workflow tests.

#### **2.1: Agent Registration Protocol** (Q2.4)
- **Why High**: Defines how agents join the system and become eligible for tasks.
- **OpenHands Insight**: No built-in registration; we must implement.
- **Decision Needed**: Registration hooks, validation checks, crypto identity.
- **Blocks**: Q2.5, Q2.6

#### **2.2: Heartbeat Mechanism** (Q2.5)
- **Why High**: Enables health monitoring and fault detection.
- **OpenHands Insight**: No built-in heartbeat; use event callbacks.
- **Decision Needed**: Background thread vs. async task; heartbeat manager location.
- **Blocks**: Q6.1, Q6.4

#### **2.3: Event Type Hierarchy** (Q3.1)
- **Why High**: Defines event contracts and routing rules.
- **OpenHands Insight**: OpenHands events are conversation-scoped; we need system events.
- **Decision Needed**: Extend OpenHands events vs. parallel systems; event schema.
- **Blocks**: Q3.2, Q3.4

#### **2.4: Task-to-Action Mapping** (Q4.2)
- **Why High**: Defines how domain tasks map to OpenHands conversations/actions.
- **OpenHands Insight**: Tasks are high-level; Actions are tool invocations.
- **Decision Needed**: One task = one conversation vs. multiple actions; progress tracking.
- **Blocks**: Q4.3, Q4.4

#### **2.5: LLM Configuration Strategy** (Q1.3)
- **Why High**: Determines cost, performance, and model selection per agent type.
- **OpenHands Insight**: Flexible per-agent LLM config with routing support.
- **Decision Needed**: Shared vs. per-agent config; model routing policies.
- **Blocks**: Q6.1

#### **2.6: Monitor Agent Design** (Q2.2)
- **Why High**: Defines monitoring architecture and anomaly detection approach.
- **OpenHands Insight**: Monitors don't need LLM/tools; pure Python services possible.
- **Decision Needed**: Use OpenHands SDK vs. custom implementation.
- **Blocks**: Q6.1, Q6.2

#### **2.7: Workspace Provisioning** (Q5.1)
- **Why High**: Defines workspace lifecycle and resource management.
- **OpenHands Insight**: DockerWorkspace requires Docker daemon; container startup overhead.
- **Decision Needed**: Pre-create pool vs. on-demand; workspace reuse strategy.
- **Blocks**: Q5.5

---

### **TIER 3: Workflow & Validation (Important for Production)**

These questions define workflow logic and validation patterns. They block workflow integration tests.

#### **3.1: Event Delivery Guarantees** (Q3.2)
- **Why Medium**: Defines reliability requirements and retry strategies.
- **OpenHands Insight**: In-process events; we need external bus guarantees.
- **Decision Needed**: At-most-once vs. at-least-once vs. exactly-once; idempotency.
- **Blocks**: Q3.4, Q3.5

#### **3.2: Discovery-Based Task Spawning** (Q4.3)
- **Why Medium**: Enables dynamic workflow expansion.
- **OpenHands Insight**: Agents can discover issues; we need task creation protocol.
- **Decision Needed**: Parsing observations vs. explicit tools; discovery validation.
- **Blocks**: Q4.4

#### **3.3: Validation Feedback Loop** (Q4.4)
- **Why Medium**: Enables iterative improvement and retry logic.
- **OpenHands Insight**: Validation agents return structured results; we create fix tasks.
- **Decision Needed**: Validation result format; fix task creation protocol.
- **Blocks**: Q4.5

#### **3.4: Phase Gate Validation** (Q4.5)
- **Why Medium**: Enforces workflow progression and artifact requirements.
- **OpenHands Insight**: No built-in phase gates; we implement validation orchestrator.
- **Decision Needed**: Gate validation triggers; artifact checking logic.
- **Blocks**: None (end of workflow chain)

#### **3.5: Agent Status State Machine** (Q2.6)
- **Why Medium**: Defines agent lifecycle and eligibility rules.
- **OpenHands Insight**: No built-in status management; we implement.
- **Decision Needed**: State machine enforcement location; status transition atomicity.
- **Blocks**: Q2.7, Q2.8

---

### **TIER 4: Advanced Features (Production Readiness)**

These questions define advanced monitoring, security, and observability features.

#### **4.1: Health Metrics Collection** (Q6.1)
- **Why Medium**: Enables monitoring dashboards and alerting.
- **OpenHands Insight**: Event callbacks + LLM metrics available; we add system metrics.
- **Decision Needed**: Prometheus vs. custom metrics; metric cardinality.

#### **4.2: Event Filtering and Routing** (Q3.4)
- **Why Medium**: Optimizes performance with 100+ agents.
- **OpenHands Insight**: Server-side vs. client-side filtering tradeoffs.
- **Decision Needed**: Topic-based subscriptions; subscription management.

#### **4.3: Custom Tool Development** (Q5.2)
- **Why Medium**: Enables GitHub, Jira, Supabase integrations.
- **OpenHands Insight**: ToolDefinition pattern available; package distribution strategy.
- **Decision Needed**: Tool packaging; dynamic loading strategy.

#### **4.4: MCP Server Integration Strategy** (Q5.3)
- **Why Medium**: Enables external tool integration via MCP protocol.
- **OpenHands Insight**: No explicit MCP support; adapter layer needed.
- **Decision Needed**: MCP adapter implementation; tool schema mapping.

#### **4.5: Tool Authorization Model** (Q5.4)
- **Why Medium**: Enforces security boundaries per agent type.
- **OpenHands Insight**: No built-in authorization; we implement.
- **Decision Needed**: Role-based vs. capability-based; allow-list vs. deny-list.

#### **4.6: Observability Integration** (Q6.6)
- **Why Medium**: Enables production debugging and performance analysis.
- **OpenHands Insight**: Event callbacks available; OpenTelemetry integration possible.
- **Decision Needed**: Manual instrumentation vs. auto-instrumentation; tracing strategy.

#### **4.7: Guardian Agent Authority** (Q2.7)
- **Why Medium**: Enables emergency intervention and resource reallocation.
- **OpenHands Insight**: No privilege model; we implement override mechanisms.
- **Decision Needed**: Authentication tokens; audit logging; rate limiting.

#### **4.8: Agent Resurrection Logic** (Q2.8)
- **Why Medium**: Enables fault tolerance and task continuity.
- **OpenHands Insight**: Conversation persistence available; we add agent state reconstruction.
- **Decision Needed**: State preservation strategy; checkpoint frequency.

#### **4.9: Anomaly Detection Implementation** (Q6.2)
- **Why Medium**: Enables proactive monitoring and alerting.
- **OpenHands Insight**: No built-in anomaly detection; we implement.
- **Decision Needed**: Rule-based vs. statistical vs. ML-based; baseline computation.

#### **4.10: Alert Severity and Routing** (Q6.3)
- **Why Medium**: Enables human notification and escalation workflows.
- **OpenHands Insight**: No built-in alerting; we implement.
- **Decision Needed**: Alert routing channels; deduplication strategy.

#### **4.11: Restart Protocol Timing** (Q6.4)
- **Why Medium**: Defines fault recovery behavior.
- **OpenHands Insight**: No built-in restart protocol; we implement.
- **Decision Needed**: Timeout values; task checkpointing strategy.

#### **4.12: WebSocket vs. REST for Events** (Q3.6)
- **Why Medium**: Optimizes real-time event propagation.
- **OpenHands Insight**: Both APIs available; choose based on scale.
- **Decision Needed**: WebSocket for all vs. REST polling fallback.

#### **4.13: Conversation Context Management** (Q3.3)
- **Why Medium**: Optimizes token usage and maintains context across phases.
- **OpenHands Insight**: Context condensation available; we manage cross-phase context.
- **Decision Needed**: Context passing strategy; summarization approach.

#### **4.14: Parallel Task Execution** (Q4.6)
- **Why Medium**: Enables concurrent ticket processing.
- **OpenHands Insight**: No built-in dependency management; we implement.
- **Decision Needed**: Dependency graph implementation; cycle detection.

#### **4.15: OpenHands Server Integration** (Q1.7)
- **Why Medium**: Determines service boundaries and API contracts.
- **OpenHands Insight**: Server mode available; embed vs. call decision.
- **Decision Needed**: Conversation-to-ticket mapping; API integration pattern.

---

### **TIER 5: Nice-to-Have (Can Defer)**

These questions define optional features that can be added post-MVP.

#### **5.1: Workspace State Preservation** (Q5.5)
- **Why Low**: Debugging convenience; most workflows are reproducible.
- **OpenHands Insight**: Workspace cleanup is standard; preservation adds overhead.

#### **5.2: Browser Automation Requirements** (Q5.6)
- **Why Low**: Not explicitly required; may be needed for testing phase.
- **OpenHands Insight**: BrowserToolSet available; resource-intensive.

#### **5.3: Quarantine Forensics** (Q6.5)
- **Why Low**: Advanced debugging feature; can be added post-MVP.
- **OpenHands Insight**: No built-in quarantine; we implement preservation logic.

#### **5.4: Event Persistence Strategy** (Q3.5)
- **Why Low**: Can use OpenHands file-based persistence initially; optimize later.
- **OpenHands Insight**: Events stored per conversation; we may need system-wide history.

---

## Prioritization Summary Table

| Tier | Priority | Questions | Rationale |
|------|----------|-----------|-----------|
| **0** | **CRITICAL** | Q1.5, Q1.4, Q4.1, Q2.3 | Blocks interface contracts, schemas, and test specifications |
| **1** | **HIGH** | Q1.1, Q1.2, Q2.1, Q1.8, Q1.6 | Blocks component interfaces and integration tests |
| **2** | **HIGH** | Q2.4, Q2.5, Q3.1, Q4.2, Q1.3, Q2.2, Q5.1 | Blocks end-to-end workflow tests |
| **3** | **MEDIUM** | Q3.2, Q4.3, Q4.4, Q4.5, Q2.6 | Blocks workflow integration tests |
| **4** | **MEDIUM** | Q6.1, Q3.4, Q5.2, Q5.3, Q5.4, Q6.6, Q2.7, Q2.8, Q6.2, Q6.3, Q6.4, Q3.6, Q3.3, Q4.6, Q1.7 | Production readiness features |
| **5** | **LOW** | Q5.5, Q5.6, Q6.5, Q3.5 | Nice-to-have; can defer |

---

## Recommended Implementation Order

### **Phase 1: Foundation (Tier 0)**
1. Answer Q1.5 (State Store) → Design PostgreSQL schema
2. Answer Q1.4 (Event Bus) → Design event types and pub/sub contracts
3. Answer Q4.1 (Task Queue) → Design queue schema and assignment logic
4. Answer Q2.3 (Agent-Conversation Mapping) → Design conversation lifecycle

**Deliverable**: Database schemas, event type definitions, queue contracts, conversation mapping strategy

### **Phase 2: Core Components (Tier 1)**
5. Answer Q1.1 (Package Selection) → Choose packages per agent type
6. Answer Q1.2 (Agent Extension) → Design agent base class/interfaces
7. Answer Q2.1 (Worker Implementation) → Implement worker agent classes
8. Answer Q1.8 (Deployment Model) → Choose architecture (monolith vs. microservices)
9. Answer Q1.6 (Workspace Strategy) → Choose isolation mode

**Deliverable**: Agent interfaces, worker implementations, deployment architecture

### **Phase 3: Integration (Tier 2)**
10. Answer Q2.4 (Registration) → Implement agent registry
11. Answer Q2.5 (Heartbeat) → Implement health monitoring
12. Answer Q3.1 (Event Hierarchy) → Extend event types
13. Answer Q4.2 (Task Mapping) → Implement task-to-conversation mapping
14. Answer Q1.3 (LLM Config) → Configure per-agent LLMs
15. Answer Q2.2 (Monitor Design) → Implement monitor agents
16. Answer Q5.1 (Workspace Provisioning) → Implement workspace manager

**Deliverable**: End-to-end workflow (ticket → task → agent → completion)

### **Phase 4: Workflow Logic (Tier 3)**
17. Answer Q3.2 (Event Delivery) → Implement retry/idempotency
18. Answer Q4.3 (Discovery) → Implement task spawning
19. Answer Q4.4 (Validation Loop) → Implement fix task creation
20. Answer Q4.5 (Phase Gates) → Implement gate validation
21. Answer Q2.6 (Status Machine) → Implement agent lifecycle

**Deliverable**: Complete workflow with validation and retries

### **Phase 5: Production Features (Tier 4)**
22-36. Answer remaining Tier 4 questions (monitoring, security, observability)

**Deliverable**: Production-ready system with monitoring, alerts, and observability

### **Phase 6: Polish (Tier 5)**
37-40. Answer Tier 5 questions (optional features)

**Deliverable**: Enhanced system with debugging and optimization features

---

## Next Steps for Spec-Driven Development

1. **Answer Tier 0 Questions** → Create ADRs (Architecture Decision Records)
2. **Design Interfaces** → Write interface contracts based on Tier 0/1 decisions
3. **Write Tests** → Create test specifications for interfaces (before implementation)
4. **Implement Components** → Build components to pass tests
5. **Iterate** → Move to next tier, repeat process

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Assistant | Initial insights and prioritization based on OpenHands SDK documentation research |

