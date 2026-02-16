# OmoiOS SDK & CLI Design

> Design document for the OmoiOS Python SDK and CLI.
> These would give developers programmatic and terminal access to the full
> spec-driven orchestration pipeline.

## Motivation

The OmoiOS web UI works well for interactive use, but several workflows
benefit from programmatic or terminal access:

- **CI/CD integration** — trigger specs from a pipeline, gate deploys on
  spec completion.
- **Scripting & automation** — batch-create tasks, monitor agents from cron
  jobs, post Slack alerts on steering interventions.
- **Developer daily driver** — kick off work and tail agent logs without
  leaving the terminal.
- **Building on top of OmoiOS** — custom dashboards, Slack/Discord bots,
  IDE plugins that call the SDK.

---

## SDK (Python Package: `omoios`)

### Installation

```bash
pip install omoios
# or
uv add omoios
```

### Authentication

```python
import omoios

# API key (headless / CI)
client = omoios.Client(api_key="omoi_sk_...", base_url="https://api.omoios.dev")

# OAuth token (interactive)
client = omoios.Client.from_token(access_token="...")
```

### Spec Management

Create specs and drive them through the EXPLORE → PRD → REQUIREMENTS →
DESIGN → TASKS → SYNC → COMPLETE pipeline.

```python
# Create and start a spec
spec = client.specs.create(
    title="Add JWT refresh token rotation",
    description="Implement silent refresh with rotation and revocation...",
    org_id="org_abc",
)

# Check status
spec = client.specs.get(spec.id)
print(spec.phase)          # "REQUIREMENTS"
print(spec.evaluator_score) # 0.87

# List specs with filters
specs = client.specs.list(org_id="org_abc", phase="TASKS", limit=20)

# Phase control
client.specs.advance(spec.id)       # Manually advance to next phase
client.specs.retry_phase(spec.id)   # Re-run the current phase evaluator
client.specs.cancel(spec.id)        # Abort the spec
```

### Task & Ticket Operations

Traverse the Spec → Ticket → Task hierarchy and interact with work units.

```python
# List tickets under a spec
tickets = client.tickets.list(spec_id=spec.id)

# List tasks under a ticket
tasks = client.tasks.list(ticket_id=tickets[0].id)

# Get task details
task = client.tasks.get(task_id="TSK-042")
print(task.status)       # "running"
print(task.agent_id)     # "agent_7f3a..."
print(task.execution_mode)  # "implementation"

# Inject a task into the DAG
new_task = client.tasks.create(
    ticket_id=tickets[0].id,
    title="Add rate limiting middleware",
    description="...",
    depends_on=["TSK-041"],
)

# Retry / cancel
client.tasks.retry(task_id="TSK-042")
client.tasks.cancel(task_id="TSK-042")

# Get task output (diffs, test results, logs)
result = client.tasks.get_result(task_id="TSK-042")
print(result.diff)
print(result.test_summary)
```

### Agent Operations

Inspect running agents, view trajectories, and send steering interventions.

```python
# List active agents
agents = client.agents.list(status="active")
for a in agents:
    print(f"{a.id}  {a.status}  task={a.task_id}  health={a.health}")

# Get full trajectory (conversation + tool calls)
trajectory = client.agents.get_trajectory(agent_id="agent_7f3a")
for step in trajectory.steps:
    print(f"[{step.type}] {step.summary}")

# Steering interventions
client.agents.steer(
    agent_id="agent_7f3a",
    action="refocus",
    instruction="Focus on the API tests. Skip UI changes for now.",
)
client.agents.stop(agent_id="agent_7f3a")

# Spawn an agent manually
client.agents.spawn(
    task_id="TSK-042",
    mode="validation",  # "exploration" | "implementation" | "validation"
)
```

### DAG & Merge Coordination

Query the dependency graph and manage branch merges.

```python
# Get the full dependency graph
dag = client.dag.get(spec_id=spec.id)
print(dag.nodes)          # List of tasks with edges
print(dag.critical_path)  # Longest chain of dependencies

# Check merge readiness
merge = client.dag.merge_status(spec_id=spec.id)
for branch in merge.branches:
    print(f"{branch.name}  conflict_score={branch.conflict_score}")

# Trigger convergence merge
client.dag.trigger_merge(spec_id=spec.id)
```

### Discovery System

Interact with emergent work that agents found during execution.

```python
# List discoveries
discoveries = client.discoveries.list(spec_id=spec.id)
for d in discoveries:
    print(f"{d.id}  {d.title}  source_task={d.source_task_id}")

# Promote a discovery to a real task
client.discoveries.promote(discovery_id=d.id)

# Dismiss a discovery
client.discoveries.dismiss(discovery_id=d.id, reason="Out of scope")
```

### Memory Service

Search execution history and inject knowledge.

```python
# Hybrid search (semantic + keyword with RRF)
results = client.memory.search("redis connection pooling patterns")
for r in results:
    print(f"[{r.memory_type}] {r.content[:100]}...")

# Add a memory
client.memory.add(
    content="Always use get_async_session() in worker context, not the API session.",
    memory_type="LEARNING",  # ERROR_FIX | DECISION | LEARNING | WARNING | CODEBASE_KNOWLEDGE | DISCOVERY
)
```

### Event Streaming

Subscribe to real-time events from specs, tasks, and agents.

```python
# Async generator — streams events as they arrive
async for event in client.events.stream(spec_id=spec.id):
    print(f"[{event.type}] {event.data}")
    # Types: agent.started, agent.heartbeat, agent.completed,
    #        task.assigned, task.completed, task.failed,
    #        phase.advanced, phase.failed,
    #        discovery.created, steering.intervention,
    #        merge.started, merge.completed

# Callback-based subscription
def on_task_complete(event):
    print(f"Task {event.task_id} done — {event.summary}")

client.events.subscribe("task.completed", on_task_complete)
```

### Billing & Quotas

```python
usage = client.billing.get_usage()
print(f"Credits used: {usage.credits_used}/{usage.credits_total}")

can_run = client.billing.check_quota()
if not can_run:
    print("Quota exhausted — upgrade or purchase credits")
```

### Monitoring

```python
# System health
health = client.monitoring.status()
print(f"Guardian: {health.guardian}")
print(f"Conductor: {health.conductor}")

# Recent steering interventions
alerts = client.monitoring.alerts(limit=10)
for a in alerts:
    print(f"[{a.severity}] {a.agent_id}: {a.reason}")

# Coherence score for a spec
coherence = client.monitoring.coherence(spec_id=spec.id)
print(f"Score: {coherence.score}  issues: {coherence.issues}")
```

---

## CLI (`omoios`)

### Installation

```bash
pip install omoios[cli]
# or
uv tool install omoios
```

### Configuration

```bash
omoios login                              # Interactive OAuth / API key setup
omoios config set api-url https://api.omoios.dev
omoios config set org my-org
omoios config show
```

Config stored in `~/.config/omoios/config.toml`.

### Spec Lifecycle

```bash
# Create a spec
omoios spec create --title "Add auth" --description "Implement JWT..."

# List specs
omoios spec list
omoios spec list --phase TASKS --limit 10

# Check status
omoios spec status <spec-id>
#  Phase: REQUIREMENTS (3/7)
#  Evaluator: 0.87 (passed)
#  Tickets: 4  Tasks: 12 (8 done, 3 running, 1 pending)
#  Agents: 3 active

# Stream events (like kubectl logs -f)
omoios spec logs <spec-id> --follow
#  [14:02:03] phase.advanced      REQUIREMENTS → DESIGN
#  [14:02:15] task.assigned       TSK-041 → agent_7f3a (implementation)
#  [14:02:18] agent.started       agent_7f3a in sandbox daytona-abc
#  [14:03:45] discovery.created   "Missing rate limit config" from TSK-041
#  [14:05:12] task.completed      TSK-041 (3 files changed, 12 tests pass)

# Cancel
omoios spec cancel <spec-id>
```

### Task Commands

```bash
# List tasks
omoios task list --spec <id>
omoios task list --status running

# Show task details
omoios task show <task-id>
#  TSK-042: Add rate limiting middleware
#  Status: running
#  Agent: agent_7f3a (implementation mode)
#  Depends on: TSK-041 (done)
#  Blocks: TSK-043, TSK-044
#  Duration: 4m 32s

# Stream agent logs for a task
omoios task logs <task-id> --follow

# Retry / cancel
omoios task retry <task-id>
omoios task cancel <task-id>

# Show task output
omoios task result <task-id>
omoios task diff <task-id>          # Git diff of changes made
```

### Agent Commands

```bash
# List agents
omoios agent list
#  ID            STATUS   TASK      MODE            HEALTH   UPTIME
#  agent_7f3a    active   TSK-042   implementation  healthy  4m 32s
#  agent_b1c2    active   TSK-043   exploration     healthy  2m 10s
#  agent_d4e5    idle     —         —               healthy  12m 05s

# Inspect agent trajectory
omoios agent inspect <agent-id>
omoios agent inspect <agent-id> --format json

# Send steering intervention
omoios agent steer <agent-id> "Focus on API tests, skip UI"
omoios agent steer <agent-id> --action stop

# Stop agent
omoios agent stop <agent-id>
```

### DAG Visualization

```bash
# ASCII dependency graph
omoios dag show <spec-id>
#  TSK-040 ─┬─ TSK-041 ─── TSK-043 ─┬─ TSK-045
#            │                        │
#            └─ TSK-042 ─── TSK-044 ─┘
#
#  Critical path: TSK-040 → TSK-041 → TSK-043 → TSK-045

# Highlight critical path
omoios dag critical-path <spec-id>

# Show merge conflict scores
omoios dag conflicts <spec-id>
#  branch/TSK-041  ↔  branch/TSK-042   score: 0.12 (low)
#  branch/TSK-043  ↔  branch/TSK-044   score: 0.67 (medium)

# Trigger merge
omoios dag merge <spec-id>
```

### Discovery Commands

```bash
omoios discovery list --spec <id>
#  ID          TITLE                              SOURCE    STATUS
#  DSC-001     Missing rate limit config           TSK-041   pending
#  DSC-002     Needs DB index on user_sessions     TSK-043   promoted

omoios discovery promote <id>
omoios discovery dismiss <id> --reason "Out of scope"
```

### Monitoring

```bash
# System health
omoios monitor status
#  Guardian:   healthy (last run 12s ago, 60s interval)
#  Conductor:  healthy (last run 2m ago, 5m interval)
#  Health:     healthy (last run 8s ago, 30s interval)

# Recent alerts / steering interventions
omoios monitor alerts
#  TIME        SEVERITY   AGENT        REASON
#  14:05:12    warning    agent_7f3a   Trajectory drifting from goal (alignment: 0.42)
#  14:03:45    info       agent_b1c2   Spawned discovery branch task

# Coherence score
omoios monitor coherence <spec-id>
```

### Memory

```bash
# Search
omoios memory search "redis connection pooling"
#  [LEARNING]  Always use get_async_session() in worker context...
#  [ERROR_FIX] Redis connection timeout fix: increase pool_size to 20...

# Add
omoios memory add --type LEARNING "Use connection_for_boss() in workers"
```

### Organization Management

```bash
omoios org list
omoios org switch <name>
omoios org members
```

### Output Formats

All commands support output format flags:

```bash
omoios spec list --format table     # Default: human-readable table
omoios spec list --format json      # Machine-readable JSON
omoios spec list --format yaml      # YAML output
omoios task show TSK-042 --format json | jq '.status'
```

---

## Differentiators

These are the features that would set the OmoiOS SDK/CLI apart from generic
CI/CD or task-runner tools:

| Feature | Why It's Different |
|---------|--------------------|
| `spec create` as entry point | You describe *what* you want, not *how*. The pipeline handles decomposition. |
| `agent steer` | Mid-flight course correction. Most agent tools are fire-and-forget. |
| `dag show` (live ASCII) | See the parallel execution graph update in terminal. |
| `discovery promote/dismiss` | Interact with emergent work agents found — not just planned work. |
| `spec logs --follow` | Real-time streaming of agent thoughts, tool calls, phase transitions (like `kubectl logs -f` but for AI agents). |
| `monitor coherence` | System-wide coordination score — are agents stepping on each other? |
| Memory as a first-class resource | Search and inject execution history. Agents learn across runs. |

---

## Implementation Notes

### SDK Architecture

```
omoios/
├── __init__.py              # Client class, top-level exports
├── client.py                # HTTP client (httpx async + sync)
├── auth.py                  # API key / OAuth token management
├── resources/
│   ├── specs.py             # SpecResource (CRUD + phase control)
│   ├── tickets.py           # TicketResource
│   ├── tasks.py             # TaskResource
│   ├── agents.py            # AgentResource (inspect, steer, spawn)
│   ├── dag.py               # DAGResource (graph, merge, conflicts)
│   ├── discoveries.py       # DiscoveryResource
│   ├── memory.py            # MemoryResource
│   ├── monitoring.py        # MonitoringResource
│   ├── billing.py           # BillingResource
│   └── events.py            # EventStream (SSE / WebSocket)
├── models/
│   ├── spec.py              # Pydantic models for API responses
│   ├── task.py
│   ├── agent.py
│   └── ...
└── cli/
    ├── __init__.py
    ├── main.py              # Typer app entry point
    ├── commands/
    │   ├── spec.py
    │   ├── task.py
    │   ├── agent.py
    │   ├── dag.py
    │   ├── discovery.py
    │   ├── monitor.py
    │   ├── memory.py
    │   └── config.py
    └── formatters/
        ├── table.py         # Rich table output
        ├── json.py
        └── dag_ascii.py     # ASCII DAG renderer
```

### Key Dependencies

| Package | Purpose |
|---------|---------|
| `httpx` | Async + sync HTTP client |
| `pydantic` | Response models, validation |
| `typer` | CLI framework |
| `rich` | Terminal tables, progress bars, syntax highlighting |
| `websockets` | Event streaming |

### API Surface

The SDK would be a thin wrapper over the existing FastAPI routes
(see `backend/omoi_os/api/routes/`). No new backend logic is needed —
just a well-typed Python client and CLI presentation layer.

Endpoints the SDK maps to:

| SDK Method | HTTP Route |
|------------|------------|
| `specs.create()` | `POST /api/specs` |
| `specs.get()` | `GET /api/specs/{id}` |
| `specs.list()` | `GET /api/specs` |
| `specs.advance()` | `POST /api/specs/{id}/advance` |
| `tasks.list()` | `GET /api/tasks` |
| `tasks.get_result()` | `GET /api/tasks/{id}/result` |
| `agents.list()` | `GET /api/agents` |
| `agents.steer()` | `POST /api/agents/{id}/steer` |
| `agents.get_trajectory()` | `GET /api/agents/{id}/trajectory` |
| `dag.get()` | `GET /api/specs/{id}/dag` |
| `dag.merge_status()` | `GET /api/specs/{id}/merge-status` |
| `discoveries.list()` | `GET /api/specs/{id}/discoveries` |
| `memory.search()` | `POST /api/memory/search` |
| `events.stream()` | `GET /api/events/stream` (SSE) |
| `monitoring.status()` | `GET /api/monitoring/status` |
| `billing.get_usage()` | `GET /api/billing/usage` |

---

## Multi-Language SDK Generation

The Python SDK described above would be hand-crafted for the best developer
experience. For other languages (TypeScript, Go, Java, etc.), generating
clients from the OpenAPI spec is the fastest path. FastAPI produces the
OpenAPI schema automatically.

### Extracting the OpenAPI Spec

```bash
# From running server
curl http://localhost:18000/openapi.json > openapi.json

# Or without running the server
cd backend
uv run python -c \
  "from omoi_os.api.main import app; import json; print(json.dumps(app.openapi()))" \
  > ../openapi.json
```

### Open Source Code Generators

| Tool | Languages | License | Best For |
|------|-----------|---------|----------|
| [OpenAPI Generator](https://github.com/OpenAPITools/openapi-generator) | 40+ (Python, TS, Go, Java, Rust, C#, PHP, Ruby, etc.) | Apache 2.0 | Broadest language coverage, most battle-tested |
| [Kiota](https://github.com/microsoft/kiota) (Microsoft) | Python, TypeScript, Go, Java, C#, PHP, Ruby | MIT | Consistent cross-language patterns via language-agnostic code model |
| [Fern](https://github.com/fern-api/fern) | Python, TypeScript, Go, Java, C#, PHP, Ruby, Swift, Rust | MIT (CLI) | Best output quality — idiomatic, type-safe, feels hand-written |
| [oapi-codegen](https://github.com/oapi-codegen/oapi-codegen) | Go only | Apache 2.0 | Best Go output, purpose-built and idiomatic |
| [openapi-typescript](https://github.com/openapi-ts/openapi-typescript) / [Hey API](https://github.com/hey-api/openapi-ts) | TypeScript only | MIT | Lightweight typed TS client, recommended by FastAPI docs |
| [AutoRest](https://github.com/Azure/autorest) (Microsoft) | TypeScript, Python, Go, Java, C# | MIT | Mature, powers the Azure SDKs |
| [Swagger Codegen](https://github.com/swagger-api/swagger-codegen) | Many | Apache 2.0 | The original (OpenAPI Generator was forked from this) |

### Commercial Generators (for comparison)

| Tool | Languages | Notable Users | Pricing |
|------|-----------|---------------|---------|
| [Stainless](https://www.stainless.com/) | Python, TS, Go, Java, Kotlin, Ruby, PHP, C# | Anthropic, OpenAI, Cloudflare | Paid SaaS |
| [Speakeasy](https://www.speakeasy.com/) | 10+ | Vercel, Airbyte | Free tier (1 lang), paid from $250/mo |
| [APIMatic](https://www.apimatic.io/) | 10+ | Enterprise-focused | Paid SaaS |
| [LibLab](https://liblab.com/) | Several | — | Paid SaaS |

### Recommended Per-Language Strategy

| Language | Tool | Rationale |
|----------|------|-----------|
| **Python** | Hand-crafted SDK (this doc) | First-class experience with streaming, steering, CLI |
| **TypeScript** | openapi-typescript + openapi-fetch | Tiny, fully typed, no bloat |
| **Go** | oapi-codegen | Idiomatic Go, purpose-built |
| **Java / C# / others** | Fern or OpenAPI Generator | Fern for quality, OAG for breadth |

### Generation Commands

```bash
# Install OpenAPI Generator
brew install openapi-generator

# Python (if not hand-crafting)
openapi-generator generate \
  -i openapi.json -g python -o sdks/python \
  --package-name omoios --additional-properties=packageVersion=0.1.0

# TypeScript
openapi-generator generate \
  -i openapi.json -g typescript-fetch -o sdks/typescript \
  --additional-properties=npmName=omoios,npmVersion=0.1.0

# Go
openapi-generator generate \
  -i openapi.json -g go -o sdks/go --package-name omoios

# Or use language-specific generators for better output:

# TypeScript (higher quality)
npx openapi-typescript openapi.json -o sdks/typescript/schema.d.ts

# Go (higher quality)
go install github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen@latest
oapi-codegen -package omoios -generate types,client openapi.json > sdks/go/client.go
```

### Automating Generation (Justfile recipe)

```just
generate-sdks:
    cd backend && uv run python -c \
      "from omoi_os.api.main import app; import json; print(json.dumps(app.openapi()))" \
      > ../openapi.json
    openapi-generator generate -i openapi.json -g python -o sdks/python --package-name omoios
    openapi-generator generate -i openapi.json -g typescript-fetch -o sdks/typescript
    openapi-generator generate -i openapi.json -g go -o sdks/go --package-name omoios
```

### What You Get vs. What You Add

**Generated automatically:**
- Typed request/response models in every language
- HTTP client with all endpoints wired up
- Auth header injection
- Serialization/deserialization

**Added manually (thin layer on top):**
- Event streaming (SSE/WebSocket — OpenAPI doesn't model these well)
- The CLI itself (Typer/Click wrapping the Python SDK)
- Convenience methods (`spec.logs(follow=True)` combining polling)
- Retry/backoff policies
- The ASCII DAG renderer

The generated code gets ~70-80% of the way. The remaining 20% is the
developer experience polish that makes it feel like a first-class SDK
rather than auto-generated bindings
