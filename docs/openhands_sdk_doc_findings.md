# OpenHands SDK Documentation Findings

This document summarizes authoritative references from the OpenHands SDK documentation (DeepWiki + upstream repository) and maps them onto the open questions tracked in `docs/implementation_questions.md`.

## 1. Package & Agent Foundations (Q1.1, Q1.2, Q2.1)

- **Layered packages** – `openhands-sdk` supplies core `Agent`, `Conversation`, and `LLM` orchestration; `openhands-tools` adds executable tool definitions (bash, file editor, browser); `openhands-workspace` provides Local/Docker/Remote workspace abstractions; `openhands-agent-server` bundles the stack behind REST/WebSocket APIs for deployment. This hierarchy supports composing custom worker, monitor, and watchdog agents by mixing only the layers they require (e.g., monitors may rely on SDK alone, while workers need SDK + tools + workspace).  
  Source: [DeepWiki – Core Architecture](https://deepwiki.com/OpenHands/software-agent-sdk#2)

- **Deployment considerations** – The doc explicitly calls out choosing between embedding the SDK (standalone) versus using the agent server microservice for orchestration, aligning with the decision in Q1.7/Q1.8 about whether to run workers locally or behind a managed service boundary.  
  Source: [DeepWiki – Overview → Deployment Modes](https://deepwiki.com/OpenHands/software-agent-sdk#1.2)

## 2. Event & Conversation System (Q1.4, Q3.1, Q3.2, Q3.6)

- **Event scope** – `EventService` instances are conversation-scoped pub/sub hubs tied to a `StoredConversation`. Events such as `MessageEvent`, `ActionEvent`, and `ObservationEvent` live within that conversation boundary; the server forwards them over REST, WebSocket streams, or optional webhook subscribers rather than an external broker. Thus, a system-wide event bus (AGENT_REGISTERED, HEARTBEAT_MISSED, etc.) must be layered on top if required.  
  Source: [DeepWiki – Agent Reconciliation](https://deepwiki.com/OpenHands/software-agent-sdk#3.3)

- **APIs for streaming** – The agent server exposes `/conversations/{conversation_id}/events` (REST), `/events/search` (filtered history), and `/events/socket` (WebSocket) so orchestration layers can mirror or augment OpenHands events when building richer monitoring or routing logic.  
  Source: [OpenHands Agent Server README](https://github.com/openhands/software-agent-sdk/blob/main/openhands-agent-server/openhands/agent_server/README.md)

## 3. Persistence & State Store (Q1.5, Q2.8, Q3.5)

- **File-based default** – Conversations persist to a `FileStore` (`LocalFileStore` by default) that writes `base_state.json` plus an `events/` log per conversation. If `persistence_dir` is `None`, the conversation is in-memory only. There is no built-in SQLite/PostgreSQL layer, so migrating to PostgreSQL for tickets/tasks requires implementing a new store or syncing conversation artifacts into an external database.  
  Source: [DeepWiki – Conversation Management → State Persistence](https://deepwiki.com/OpenHands/software-agent-sdk#5.5)

- **Server storage pathing** – `openhands-agent-server` stores conversations and workspace data under `workspace/conversations` (configurable via `conversations_path`). Deleting a conversation via the API removes its events and workspace files, reinforcing that persistence is filesystem-based unless an alternative backing store is added.  
  Source: [OpenHands Agent Server README](https://github.com/openhands/software-agent-sdk/blob/main/openhands-agent-server/openhands/agent_server/README.md)

## 4. Workspace Isolation & Deployment Modes (Q1.6, Q1.8, Q5.1)

- **Local vs. Docker vs. Remote** – `LocalWorkspace` runs commands directly on the host (no isolation); `DockerWorkspace` provides container-level isolation with reproducible snapshots; `RemoteWorkspace`/`AsyncRemoteWorkspace` forward all actions to a remote agent server via HTTP/WebSocket. The documentation recommends choosing Docker for untrusted workloads and Remote for multi-tenant or centralized deployment scenarios, matching the ticket-per-workspace vs. pooled workspace questions.  
  Source: [DeepWiki – Workspace Environments](https://deepwiki.com/OpenHands/software-agent-sdk#7)

- **Remote agent orchestration** – The SDK example demonstrates spinning up the agent server, connecting through `Workspace(host="http://localhost:8000")`, and streaming events, showing how worker agents can run remotely while orchestration services manage them through the REST/WebSocket endpoints.  
  Source: [Context7 – Deploy Remote Agent Server](https://context7.com/openhands/software-agent-sdk/llms.txt)

## 5. Task Queue & Automation (Q4.1, Q4.2, Q4.4)

- **No internal task queue** – The Automation Workflows guide shows OpenHands agents triggered by GitHub Actions (scheduled, event-based, or manual) where Actions orchestrate job sequencing (including matrix jobs for TODO processing). This confirms that task queuing/priority logic must be implemented externally (e.g., Redis/PostgreSQL queue) and integrated with agent invocations.  
  Source: [DeepWiki – CI/CD and Automation → Automation Workflows](https://deepwiki.com/OpenHands/software-agent-sdk#9.4)

- **Agent-side task tracker** – While agents have a `task_tracker` tool for decomposing work internally, it does not replace a system-level queue; it merely structures tasks within a single conversation, aligning with the need to map our domain tasks to OpenHands conversations/actions (Q4.2).  
  Source: [DeepWiki – Tools and Capabilities → Tool System Architecture](https://deepwiki.com/OpenHands/software-agent-sdk#6.1)

## 6. LLM Configuration & Routing (Q1.3, Q6.1)

- **Per-agent LLM profiles** – The `LLM` Pydantic model supports specifying provider-prefixed models (`openai/*`, `anthropic/*`, `openhands/*`), API keys, base URLs, max tokens, and inference parameters. Each agent configuration embeds its own LLM instance, enabling phase-specific model choices or rate-limit partitions.  
  Source: [DeepWiki – LLM Integration → LLM Configuration](https://deepwiki.com/OpenHands/software-agent-sdk#4.1)

- **Retries & routing** – Built-in retry controls (`num_retries`, `retry_multiplier`, etc.) handle provider rate limits, while router implementations (`MultimodalRouter`, `RandomRouter`) demonstrate policy-based model selection (e.g., switch to a different provider when messages contain images or exceed token windows). This aligns with Q1.3’s requirement for differentiated LLM strategies per agent type.  
  Source: [DeepWiki – LLM Integration → Model Features and Routing](https://deepwiki.com/OpenHands/software-agent-sdk#4.2)

## 7. Observability & Event Capture (Q3.2, Q6.1, Q6.6)

- **Callback instrumentation** – Conversations accept callback hooks that receive every `Event`, allowing orchestration layers to capture telemetry (latency, errors, LLM token usage) as agents run. The SDK sample shows collecting all events plus LLM-convertible events for downstream logging/metrics, providing a pattern for heartbeat-style health reporting even though the base SDK does not emit heartbeats out of the box.  
  Source: [Context7 – Event Callback Example](https://context7.com/openhands/software-agent-sdk/llms.txt)

## 8. Implications for Outstanding Questions

- **Event Bus (Q1.4, Q3.1)** – Because OpenHands confines events to conversation scope, a separate system-wide bus (Redis, Kafka, etc.) is required for cross-agent alerts and monitoring. The provided APIs and callbacks supply the raw data needed to publish into that bus.

- **State Store (Q1.5, Q2.8)** – With only filesystem persistence available, integrating PostgreSQL (or another HA database) for ticket/task metadata entails syncing conversation files or re-implementing the persistence interface, reinforcing the need for a dedicated state service.

- **Task Queue (Q4.1)** – GitHub Actions-based automation illustrates that OpenHands expects external scheduling. Therefore, our orchestration layer must own priority queues, retries, and phase transitions, invoking OpenHands agents as workers.

- **LLM Strategy (Q1.3)** – The flexibility of the `LLM` model plus router patterns supports configuring dedicated providers/models per agent role, enabling the adaptive strategy described in the implementation questions.

These grounded references should be used when drafting ADRs or resolving each question block in `docs/implementation_questions.md`.

