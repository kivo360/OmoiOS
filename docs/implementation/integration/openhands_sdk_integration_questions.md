# OpenHands Agent SDK Integration Questions

**Created**: 2025-11-20
**Status**: Draft
**Purpose**: Collect critical integration questions for implementing OpenHands Agent SDK within the multi-agent orchestration system
**Related**: docs/design/agents/openhands_sdk_integration.md, docs/requirements/integration/agent_orchestration.md, docs/implementation/openhands_sdk_integration_log.md

---


## Document Overview

This document contains 40 critical questions for implementing the multi-agent orchestration system using OpenHands Agent SDK. These questions are specifically tailored to OpenHands SDK patterns, APIs, and integration points.

---

## Agent Lifecycle & Registration (Questions 1-8)

1. **Agent Registration via Conversation Creation**: Since OpenHands agents are registered when `Conversation` is initialized (via `ConversationState.create()`), how do we integrate this with our Agent Registry? Should we wrap `Conversation.create()` to register agents in our system, or create a post-initialization registration step?

2. **Agent Identity Mapping**: How do we map OpenHands `conversation_id` (from `ConversationState.id`) to our UUID-based `agent_id`? Should we store the mapping in `ConversationState.metadata`, inject via `AgentContext`, or maintain a separate registry mapping?

3. **Heartbeat via Event Callbacks**: How do we implement bidirectional heartbeats using OpenHands `conversation.callbacks` or `ConversationState.set_on_state_change()`? Should we emit heartbeat events through the PubSub system, or create a custom tool that agents call periodically?

4. **AgentExecutionStatus Integration**: How do we map OpenHands `AgentExecutionStatus` enum (IDLE, RUNNING, PAUSED, WAITING_FOR_CONFIRMATION, FINISHED, ERROR, STUCK) to our orchestration status states? Should we subscribe to `ConversationStateUpdateEvent` for status changes, or maintain parallel state tracking?

5. **Agent Capability Declaration**: How do we declare agent capabilities (phase_id, languages, tool proficiencies) using OpenHands SDK? Should we store capabilities in `AgentContext`, `ConversationState.metadata`, or extend the agent reconciliation process to include capability validation?

6. **Agent Type Classification**: How do we distinguish Worker/Monitor/Watchdog/Guardian agents? Should we use `AgentContext` metadata, different tool sets per agent type, or store agent type in `ConversationState.metadata` for reconciliation?

7. **Resource Budget Enforcement**: How do we enforce resource budgets (CPU, memory, token limits) for OpenHands agents? Should we wrap the `LLM` instance with rate limiters, use workspace isolation (Docker/Remote), or implement resource tracking via `ConversationStats`?

8. **Graceful Termination**: How do we implement graceful termination using `ConversationState` monitoring? Should we call `conversation.pause()` and then cleanup, monitor `AgentExecutionStatus.FINISHED`, or use persistence (`persistence_dir`) to checkpoint before termination?

---

## Task Queue & Assignment (Questions 9-16)

9. **Task Pull via Custom Tool**: How do we implement pull-first task assignment where agents request tasks? Should we create a custom `ToolDefinition` (e.g., `GetNextTaskTool`) that agents call when `AgentExecutionStatus.IDLE`, or use a different pattern?

10. **Task Assignment via send_message**: How do we assign tasks to OpenHands `Conversation` instances? Since tasks are assigned via `conversation.send_message()`, how do we format task descriptions, include priority/context, and handle task metadata?

11. **Task Result Extraction**: How do we extract task completion results from OpenHands conversations? Should we parse `ConversationState.events` (ActionEvent/ObservationEvent), use conversation callbacks to capture structured outputs, or create a custom tool for result reporting?

12. **Task Priority in AgentContext**: How do we expose task priority and scoring to agents? Should we inject priority into `AgentContext.skills`, include in the task message, or create a `GetTaskDetailsTool` that agents can query?

13. **Dependency Blocking**: How do we handle task dependencies where agents must wait? Should we block `conversation.send_message()` until dependencies complete, use `AgentExecutionStatus.PAUSED` to pause agents, or implement dependency-checking in task assignment logic?

14. **Discovery Capture from Events**: How do we capture discoveries from conversations and create new tasks? Should we parse `ActionEvent`/`ObservationEvent` for discovery patterns, use structured tool outputs, or analyze `ConversationState.events` for discovery indicators?

15. **Validation Feedback via Messages**: How do we deliver validation feedback to agents? Should we use `conversation.send_message()` with feedback, inject feedback into `AgentContext.skills`, or create a `ValidationFeedbackTool` for structured feedback delivery?

16. **Retry via New Conversations**: How do we handle task retries? Should we create new `Conversation` instances with the same `conversation_id` (leveraging persistence), reuse existing conversations, or use `ConversationState.create()` with retry metadata?

---

## MCP Server Integration (Questions 17-22)

17. **Orchestration Tools as MCP Tools**: How do we expose our orchestration tools (ticket management, task queue, validation) as MCP tools? Should we create an MCP server that exposes these tools and configure it via `Agent.mcp_config`, or use `register_tool()` to create custom `ToolDefinition` instances?

18. **Tool Authorization via filter_tools_regex**: How do we enforce tool authorization per agent type? Should we use `Agent.filter_tools_regex` to filter available tools, implement authorization checks in `ToolExecutor.__call__()`, or create agent-type-specific tool sets?

19. **MCP Server Lifecycle Management**: How do we manage lifecycle for our orchestration MCP servers? Should we use OpenHands `MCPClient` patterns (which spawn servers via `command`/`args`), or manage MCP servers separately and connect via standardio transport?

20. **MCP Tool Error Handling**: How do we handle MCP tool failures (`MCPToolExecutor.call_tool` errors)? Should we wrap `MCPToolExecutor` with retry logic, implement circuit breakers in tool executors, or handle failures at the orchestration layer via `ObservationEvent` error parsing?

21. **Context Injection in Tool Executors**: How do we pass orchestration context (agent_id, ticket_id, task_id) to tool executors? Since `ToolExecutor.__call__(action, conversation)` receives `conversation`, should we extract context from `ConversationState.metadata`, or pass context through `Action` parameters?

22. **Tool Usage via EventLog**: How do we track tool usage for memory integration? Should we parse `ConversationState.events` (specifically `ActionEvent` instances), use `conversation.callbacks` to capture tool calls, or implement tracking in `ToolExecutor` implementations?

---

## Validation System Integration (Questions 23-28)

23. **Validator Agent via New Conversations**: How do we spawn validator agents when tasks enter `under_review`? Should we create new `Conversation` instances with validator-specific `Agent` configurations and tools, or reuse conversation pools with different agent types?

24. **Review Submission via Custom Tool**: How do validator agents submit reviews (`give_review`)? Should we create a custom `ToolDefinition` (e.g., `SubmitValidationReviewTool`) that validators call, or parse structured outputs from `ConversationState.events`?

25. **Feedback via send_message**: How do we deliver validation feedback to worker agents? Should we use `conversation.send_message()` with feedback text, inject feedback into `AgentContext.skills` for the next conversation cycle, or create a `ReceiveValidationFeedbackTool`?

26. **Iteration in ConversationState.metadata**: How do we track validation iterations? Should we store `validation_iteration` in `ConversationState.metadata` (persisted via `persistence_dir`), or maintain iteration state externally and inject it into conversations?

27. **Workspace Commits via Workspace API**: How do we integrate workspace commits with OpenHands workspace management? Should we use `Workspace.execute_command()` to run git commands, leverage workspace persistence, or manage Git operations outside OpenHands workspace abstraction?

28. **Timeout via ConversationState Monitoring**: How do we detect validator timeouts? Should we monitor `ConversationState.agent_status` and conversation duration, use async timeouts around `conversation.run()`, or implement timeout detection via `StuckDetector` configuration?

---

## Memory System Integration (Questions 29-32)

29. **ACE Workflow via Callbacks**: How do we integrate ACE workflow with OpenHands task completion? Should we trigger ACE when `AgentExecutionStatus.FINISHED` is detected via `ConversationState.set_on_state_change()` callback, use conversation completion callbacks, or implement as post-processing after `conversation.run()` completes?

30. **Tool Usage from EventLog**: How do we extract tool usage for memory? Should we parse `ConversationState.events` (filtering `ActionEvent` and `ObservationEvent` instances), use `conversation.callbacks` to capture tool calls, or analyze `EventLog` after conversation completion?

31. **Memory Context via AgentContext.skills**: How do we load memories/playbook into agents? Should we use `AgentContext.skills` to inject memory entries as skills, include context in system messages during `Agent` initialization, or create a `LoadMemoryContextTool` that agents call?

32. **Memory Writing Post-Completion**: How do we write memories after task completion? Should we use `ConversationState.set_on_state_change()` to detect `FINISHED` and trigger memory writing, parse `ConversationState` after `conversation.run()` completes, or implement as a separate orchestration step that processes completed conversations?

---

## Monitoring & Fault Tolerance (Questions 33-36)

33. **Monitor Agents via RemoteConversation**: How do we implement monitor agents? Should monitors be separate processes that use `RemoteConversation` to query agent server state, or should monitors be OpenHands agents themselves that use custom tools to inspect other conversations?

34. **Heartbeat via Event Monitoring**: How do monitors detect missed heartbeats? Should we track `ConversationStateUpdateEvent` frequency, monitor `ActionEvent`/`ObservationEvent` activity in `EventLog`, or use `ConversationStats` to detect inactivity?

35. **Anomaly Detection via StuckDetector**: How do we calculate anomaly scores? Should we leverage OpenHands `StuckDetector` patterns (repeating action-error cycles, agent monologue), analyze `ConversationStats` (token usage, latency), or combine `EventLog` analysis with external metrics?

36. **Restart via Persistence**: How do we restart failed agents while preserving context? Should we use `ConversationState.create()` with `persistence_dir` to restore conversations, leverage agent reconciliation to resume state, or implement checkpointing via `ConversationState` serialization?

---

## Event Bus & Communication (Questions 37-40)

37. **Event Emission via PubSub**: How do we emit orchestration events from OpenHands conversations? Should we use `ConversationState.set_on_state_change()` callbacks to publish events via our PubSub system, emit events from `ToolExecutor` implementations, or bridge OpenHands `EventService` PubSub to our event bus?

38. **Event Subscription via WebSocket**: How do agents subscribe to orchestration events? Should we use `RemoteConversation` WebSocket streams (`/sockets/events/{conversation_id}`) to receive events, inject event context into `AgentContext.skills`, or create an `SubscribeToEventsTool`?

39. **WebSocket Bridge Integration**: How do we integrate OpenHands WebSocket events (`/sockets/events/{conversation_id}`) with our WebSocket gateway? Should we bridge `EventService` PubSub subscribers to our WebSocket gateway, aggregate events from multiple conversations, or use OpenHands Agent Server WebSocket as our primary event stream?

40. **Cross-Agent Communication via Event Bus**: How do agents communicate with each other? Should we use our event bus (subscribed via `RemoteConversation` WebSocket) to send messages between agents, create inter-agent tools that agents call, or use shared `AgentContext` injected into multiple conversations?

---

## Implementation Priorities

**Phase 1 (Core Integration)**:
- Questions 1-3: Agent registration and heartbeat
- Questions 9-11: Task assignment and result reporting
- Questions 17-18: MCP tool registration and authorization

**Phase 2 (Workflow Integration)**:
- Questions 4-6: Status management and capabilities
- Questions 12-15: Task dependencies and discoveries
- Questions 23-25: Validation system integration

**Phase 3 (Advanced Features)**:
- Questions 29-32: Memory system integration
- Questions 33-36: Monitoring and fault tolerance
- Questions 37-40: Event bus and communication

---

## Related Documents

- [Multi-Agent Orchestration Design](../design/multi_agent_orchestration.md)
- [Agent Lifecycle Management Design](../design/agent_lifecycle_management.md)
- [Task Queue Management Design](../design/task_queue_management.md)
- [Validation System Design](../design/validation_system.md)
- [OpenHands SDK Documentation](https://docs.openhands.dev)

---

## Notes

- All questions assume OpenHands SDK v1.1.0+ patterns based on DeepWiki documentation
- Questions reference actual SDK patterns: `ConversationState`, `AgentExecutionStatus`, `ToolDefinition`, `MCPToolDefinition`, `EventService`, `PubSub`, `StuckDetector`, `AgentContext`, `persistence_dir`
- Integration should maintain OpenHands SDK idioms (conversation-based lifecycle, event-driven architecture, tool registration) while satisfying orchestration requirements
- Key SDK concepts:
  - Agents are registered via `Conversation` initialization, not separately
  - State managed via `ConversationState` with persistence support
  - Events flow through PubSub pattern with WebSocket support
  - Tools use `ToolDefinition`/`Action`/`Observation` pattern with `register_tool()`
  - MCP tools dynamically created from `mcp_config`
  - Health monitoring via `StuckDetector` and `ConversationStats`

