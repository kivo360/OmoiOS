# Spec-Driven Development Command Panel Features

> **Purpose**: Demo-ready feature list for the spec-driven development command panel. These are toggleable settings that can be configured to customize the autonomous development workflow.

---

## Quick Summary

| Category | Features | Demo Priority |
|----------|----------|---------------|
| [Phase Control](#1-phase-control) | 8 | ⭐⭐⭐ High |
| [Agent Monitoring](#2-agent-monitoring) | 7 | ⭐⭐⭐ High |
| [Task Queue](#3-task-queue-configuration) | 10 | ⭐⭐ Medium |
| [Worker Settings](#4-worker--sandbox-configuration) | 8 | ⭐⭐ Medium |
| [LLM Configuration](#5-llm-configuration) | 6 | ⭐⭐⭐ High |
| [Integrations](#6-integrations) | 4 | ⭐ Low |
| [Observability](#7-observability) | 5 | ⭐⭐ Medium |
| [Demo/Testing](#8-demotesting-mode) | 4 | ⭐⭐⭐ High |

---

## 1. Phase Control

Manage the spec-driven workflow phases: BACKLOG → REQUIREMENTS → DESIGN → IMPLEMENTATION → TESTING → DEPLOYMENT → DONE

### 1.1 Auto-Advance Phases
- **Type**: Toggle (Boolean)
- **Default**: `true`
- **Description**: Automatically progress to the next phase when all gate criteria are met
- **Demo Value**: Show manual vs automatic phase progression

### 1.2 Phase Gate Enforcement
- **Type**: Dropdown (Strict / Lenient / Disabled)
- **Default**: `Strict`
- **Description**: Control how strictly phase gate criteria are enforced
- **Options**:
  - `Strict`: All criteria must pass (production)
  - `Lenient`: Warnings only, allows progression
  - `Disabled`: No gates enforced (demo/testing)

### 1.3 Skip Requirements Phase
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Allow bypassing the requirements analysis phase
- **Demo Value**: Fast-track to implementation for quick iterations

### 1.4 Skip Design Phase
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Allow bypassing the design phase
- **Demo Value**: Jump directly to implementation for simple features

### 1.5 Minimum Test Coverage
- **Type**: Slider (0-100%)
- **Default**: `80%`
- **Description**: Required test coverage percentage before IMPLEMENTATION → TESTING transition
- **Demo Value**: Show how coverage gates affect workflow

### 1.6 Fast-Track to Implementation
- **Type**: Action Button
- **Description**: Immediately advance from any early phase to IMPLEMENTATION
- **Demo Value**: Quick start for demos when context is already established

### 1.7 Require Human Approval
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Require manual approval before each phase transition
- **Demo Value**: Show human-in-the-loop workflow

### 1.8 Blocked State Auto-Recovery
- **Type**: Toggle (Boolean)
- **Default**: `true`
- **Description**: Automatically attempt to recover from BLOCKED state
- **Demo Value**: Resilience demonstration

---

## 2. Agent Monitoring

Control the Intelligent Guardian and Conductor monitoring systems.

### 2.1 Guardian Analysis
- **Type**: Toggle (Boolean)
- **Default**: `true`
- **Description**: Enable per-agent trajectory analysis using LLM
- **Demo Value**: Show real-time agent behavior monitoring
- **Location**: `backend/omoi_os/services/intelligent_guardian.py`

### 2.2 Auto-Steering
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Allow Guardian to automatically correct agent trajectory
- **Steering Types**: `refocus`, `throttle`, `terminate`, `escalate`
- **Demo Value**: Show autonomous correction of wayward agents

### 2.3 Guardian Interval
- **Type**: Slider (30s - 300s)
- **Default**: `60s`
- **Description**: How often Guardian analyzes each agent
- **Demo Value**: Faster intervals show more responsive monitoring

### 2.4 Conductor Analysis
- **Type**: Toggle (Boolean)
- **Default**: `true`
- **Description**: Enable system-wide coherence analysis
- **Demo Value**: Show multi-agent coordination monitoring

### 2.5 Conductor Interval
- **Type**: Slider (60s - 600s)
- **Default**: `300s`
- **Description**: How often Conductor performs system-wide analysis
- **Demo Value**: Shorter intervals for demos

### 2.6 Duplicate Detection Threshold
- **Type**: Slider (0.5 - 1.0)
- **Default**: `0.8`
- **Description**: Similarity threshold for detecting redundant work across agents
- **Demo Value**: Show how system prevents duplicate effort

### 2.7 Agent Health Check Interval
- **Type**: Slider (10s - 60s)
- **Default**: `30s`
- **Description**: Heartbeat frequency for agent health monitoring
- **Demo Value**: Show stale agent detection

---

## 3. Task Queue Configuration

Tune the priority-based task assignment algorithm.

### 3.1 Priority Weight: Phase Importance (w_p)
- **Type**: Slider (0.0 - 1.0)
- **Default**: `0.45`
- **Description**: Weight given to task phase alignment in priority calculation
- **Demo Value**: Show how phase-aware scoring works

### 3.2 Priority Weight: Age (w_a)
- **Type**: Slider (0.0 - 1.0)
- **Default**: `0.20`
- **Description**: Weight given to task age in priority calculation
- **Demo Value**: Show task aging and urgency escalation

### 3.3 Priority Weight: Dependencies (w_d)
- **Type**: Slider (0.0 - 1.0)
- **Default**: `0.15`
- **Description**: Weight given to blocking other tasks
- **Demo Value**: Show dependency-aware prioritization

### 3.4 Priority Weight: Blockers (w_b)
- **Type**: Slider (0.0 - 1.0)
- **Default**: `0.15`
- **Description**: Weight given to tasks that unblock others
- **Demo Value**: Show critical path optimization

### 3.5 Priority Weight: Rarity (w_r)
- **Type**: Slider (0.0 - 1.0)
- **Default**: `0.05`
- **Description**: Weight given to rare/unique task types
- **Demo Value**: Show specialized task handling

### 3.6 SLA Urgency Window
- **Type**: Slider (5min - 30min)
- **Default**: `15min`
- **Description**: Time window before SLA boost kicks in
- **Demo Value**: Show urgency escalation

### 3.7 SLA Boost Multiplier
- **Type**: Slider (1.0 - 2.0)
- **Default**: `1.25`
- **Description**: Score multiplier when SLA urgency is triggered
- **Demo Value**: Show prioritization boost

### 3.8 Starvation Limit
- **Type**: Slider (30min - 4hr)
- **Default**: `2hr`
- **Description**: Max time before task gets starvation priority floor
- **Demo Value**: Show how no task gets left behind

### 3.9 Age Ceiling
- **Type**: Slider (10min - 2hr)
- **Default**: `1hr`
- **Description**: Age at which urgency scoring maxes out
- **Demo Value**: Show aging normalization

### 3.10 Blocker Ceiling
- **Type**: Slider (3 - 20)
- **Default**: `10`
- **Description**: Maximum blocking tasks counted for scoring
- **Demo Value**: Show dependency depth limiting

---

## 4. Worker & Sandbox Configuration

Control compute resources for agent execution.

### 4.1 Worker Concurrency
- **Type**: Slider (1 - 8)
- **Default**: `2`
- **Description**: Number of parallel task workers
- **Demo Value**: Show parallelization scaling

### 4.2 Worker Heartbeat Interval
- **Type**: Slider (10s - 60s)
- **Default**: `30s`
- **Description**: How often workers report status
- **Demo Value**: Show worker health monitoring

### 4.3 Task Timeout
- **Type**: Slider (1min - 10min)
- **Default**: `5min`
- **Description**: Maximum execution time per task
- **Demo Value**: Show timeout handling

### 4.4 Sandbox Memory
- **Type**: Dropdown (2GB / 4GB / 8GB)
- **Default**: `4GB`
- **Description**: Memory allocated per Daytona sandbox
- **Demo Value**: Show resource scaling

### 4.5 Sandbox CPU
- **Type**: Dropdown (1 / 2 / 4 cores)
- **Default**: `2 cores`
- **Description**: CPU cores per Daytona sandbox
- **Demo Value**: Show compute allocation

### 4.6 Sandbox Disk
- **Type**: Dropdown (4GB / 8GB / 16GB)
- **Default**: `8GB`
- **Description**: Disk space per Daytona sandbox
- **Demo Value**: Show storage allocation

### 4.7 Daytona Region
- **Type**: Dropdown (US / EU / Asia)
- **Default**: `US`
- **Description**: Cloud region for sandbox deployment
- **Demo Value**: Show geographic distribution

### 4.8 Agent Stale Threshold
- **Type**: Slider (30s - 180s)
- **Default**: `90s`
- **Description**: Time without heartbeat before agent marked stale
- **Demo Value**: Show unresponsive agent detection

---

## 5. LLM Configuration

Configure AI model selection and parameters.

### 5.1 Primary LLM Model
- **Type**: Dropdown
- **Default**: `claude-3-5-sonnet-20241022`
- **Options**:
  - `claude-3-5-sonnet-20241022` (Balanced)
  - `claude-3-opus-20240229` (Highest quality)
  - `gpt-4-turbo` (OpenAI alternative)
  - `openai/glm-4.7` (Custom)
- **Demo Value**: Show model switching impact

### 5.2 Embedding Provider
- **Type**: Dropdown
- **Default**: `fireworks`
- **Options**: `fireworks`, `openai`, `cohere`
- **Demo Value**: Show embedding flexibility

### 5.3 Embedding Model
- **Type**: Dropdown
- **Default**: `fireworks/qwen3-embedding-8b`
- **Description**: Model used for semantic search and memory
- **Demo Value**: Show embedding quality differences

### 5.4 Embedding Dimensions
- **Type**: Dropdown (512 / 1024 / 1536 / 2048)
- **Default**: `1536`
- **Description**: Vector dimension size for embeddings
- **Demo Value**: Show quality vs performance tradeoff

### 5.5 Lazy Load Embeddings
- **Type**: Toggle (Boolean)
- **Default**: `true`
- **Description**: Defer embedding model initialization until needed
- **Demo Value**: Show startup optimization

### 5.6 Title Generation Model
- **Type**: Dropdown
- **Default**: `gpt-oss-20b`
- **Description**: Model used for generating task titles
- **Demo Value**: Show title quality variations

---

## 6. Integrations

External service connections.

### 6.1 Enable MCP Tools
- **Type**: Toggle (Boolean)
- **Default**: `true`
- **Description**: Enable Claude Model Context Protocol tools
- **Demo Value**: Show extended tool capabilities

### 6.2 Enable GitHub Sync
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Synchronize specs with GitHub issues/PRs
- **Demo Value**: Show GitHub integration

### 6.3 Enable Webhooks
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Enable webhook notifications for events
- **Demo Value**: Show external notification capabilities

### 6.4 Memory System
- **Type**: Toggle (Boolean)
- **Default**: `true`
- **Description**: Enable RAG-based memory and context retrieval
- **Demo Value**: Show memory-augmented agents

---

## 7. Observability

Logging, tracing, and monitoring configuration.

### 7.1 Enable Tracing
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Enable OpenTelemetry distributed tracing
- **Demo Value**: Show request flow visualization

### 7.2 Log Level
- **Type**: Dropdown
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **Demo Value**: Show verbose debugging

### 7.3 Guardian Analysis Logging
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Log detailed Guardian analysis results
- **Demo Value**: Show trajectory analysis details

### 7.4 Logfire Integration
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Enable Logfire observability platform
- **Demo Value**: Show production monitoring

### 7.5 Sentry Integration
- **Type**: Toggle (Boolean)
- **Default**: `true`
- **Description**: Enable Sentry error tracking
- **Demo Value**: Show error capture and reporting

---

## 8. Demo/Testing Mode

Special settings for demonstrations and testing.

### 8.1 Mock External APIs
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Use mock responses for external API calls
- **Demo Value**: Run demos without real API costs

### 8.2 Mock LLM Calls
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Use cached/mocked LLM responses
- **Demo Value**: Deterministic demo behavior

### 8.3 Mock Stripe
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Use Stripe test mode
- **Demo Value**: Show billing without real charges

### 8.4 Fail Fast Mode
- **Type**: Toggle (Boolean)
- **Default**: `false`
- **Description**: Immediately fail on any error (vs retry)
- **Demo Value**: Quick debugging during demos

---

## Feature Implementation Status

| Feature | Backend Config | Frontend UI | API Endpoint |
|---------|---------------|-------------|--------------|
| Phase Control | ✅ `phase_manager.py` | 🔲 Pending | 🔲 Pending |
| Agent Monitoring | ✅ `intelligent_guardian.py` | 🔲 Pending | 🔲 Pending |
| Task Queue | ✅ `task_scorer.py` | 🔲 Pending | 🔲 Pending |
| Worker Settings | ✅ `config/*.yaml` | 🔲 Pending | 🔲 Pending |
| LLM Config | ✅ `llm_service.py` | 🔲 Pending | 🔲 Pending |
| Integrations | ✅ `config/*.yaml` | 🔲 Pending | 🔲 Pending |
| Observability | ✅ `config/*.yaml` | 🔲 Pending | 🔲 Pending |
| Demo Mode | ✅ `test.yaml` | 🔲 Pending | 🔲 Pending |

---

## Configuration File Locations

```
backend/config/
├── base.yaml        # Base configuration (all environments)
├── local.yaml       # Local development overrides
├── test.yaml        # Test environment (all flags visible)
└── production.yaml  # Production settings

backend/omoi_os/
├── services/
│   ├── phase_manager.py      # Phase definitions & transitions
│   ├── intelligent_guardian.py # Guardian & Conductor
│   ├── task_scorer.py         # Priority algorithm
│   ├── agent_health.py        # Health monitoring
│   └── llm_service.py         # LLM configuration
└── config.py                  # Configuration loading
```

---

## UI Component Reference

The command panel can leverage existing patterns from:

- **CommandPalette**: `/frontend/components/command/CommandPalette.tsx`
- **SettingsPanel**: `/frontend/components/panels/SettingsPanel.tsx`

### Suggested Panel Structure

```
┌─────────────────────────────────────────────┐
│ Spec Configuration                      [X] │
├─────────────────────────────────────────────┤
│ ▼ Phase Control                             │
│   ○ Auto-Advance Phases          [ON ]      │
│   ○ Gate Enforcement      [Strict    ▼]     │
│   ○ Min Test Coverage     [====80%====]     │
│                                             │
│ ▼ Agent Monitoring                          │
│   ○ Guardian Analysis            [ON ]      │
│   ○ Auto-Steering                [OFF]      │
│   ○ Guardian Interval     [====60s===]      │
│                                             │
│ ▼ Task Queue                                │
│   ○ Priority: Phase (w_p) [====0.45==]      │
│   ○ Priority: Age (w_a)   [====0.20==]      │
│   ○ SLA Urgency Window    [===15min==]      │
│                                             │
│ ▼ Demo Mode                                 │
│   ○ Mock External APIs           [OFF]      │
│   ○ Mock LLM Calls               [OFF]      │
│                                             │
│ [Reset to Defaults]    [Apply Changes]      │
└─────────────────────────────────────────────┘
```

---

## Demo Scenarios

### Scenario 1: Fast Iteration Demo
1. Enable "Skip Requirements Phase"
2. Enable "Skip Design Phase"
3. Set "Min Test Coverage" to 0%
4. Disable "Phase Gate Enforcement"
5. Show rapid feature implementation

### Scenario 2: Production Simulation
1. Enable "Require Human Approval"
2. Set "Phase Gate Enforcement" to Strict
3. Set "Min Test Coverage" to 80%
4. Enable "Guardian Analysis"
5. Enable "Auto-Steering"
6. Show enterprise-grade workflow

### Scenario 3: Multi-Agent Coordination
1. Set "Worker Concurrency" to 4
2. Enable "Conductor Analysis"
3. Set "Duplicate Detection Threshold" to 0.7
4. Enable "Guardian Analysis"
5. Show parallel agent orchestration

### Scenario 4: Cost-Conscious Demo
1. Enable "Mock LLM Calls"
2. Enable "Mock External APIs"
3. Set "Worker Concurrency" to 1
4. Show workflow without API costs

---

*Last Updated: January 2026*
*Source: OmoiOS codebase analysis*
