# Usage Monitoring & Billing Architecture

**Created**: 2025-12-23
**Status**: Design Document
**Purpose**: Define how OmoiOS tracks usage and where billing code integrates with the existing sandbox-based architecture

---

## Overview

OmoiOS needs to track usage for a **pay-per-workflow** billing model where users pay $5-15 per successful workflow completion. This document explains what we monitor, where the code lives, and how it integrates with the **Daytona sandbox execution model**.

### What's Already Built vs What's Needed

| Component | Status | Details |
|-----------|--------|---------|
| **Sandbox token extraction** | ✅ Done | `claude_sandbox_worker.py` extracts from Claude SDK |
| **Token data storage** | ✅ Done | Stored in `sandbox_events` and `session_metadata` |
| **CostRecord model** | ✅ Done | `cost_record.py` ready for per-call tracking |
| **CostTrackingService** | ✅ Done | `record_llm_cost()`, aggregation, forecasting |
| **Cost API endpoints** | ✅ Done | `/api/costs/*` routes exist |
| **Budget enforcement** | ✅ Done | `budget_enforcer.py` with limits and alerts |
| **Connect events → CostRecords** | ❌ TODO | Wire `agent.completed` to `record_llm_cost()` |
| **Backend LLM tracking** | ❌ TODO | Guardian, Conductor, PydanticAI calls |
| **Usage aggregation per ticket** | ❌ TODO | New `UsageAggregatorService` |
| **Billing accounts & invoices** | ❌ TODO | New models and service |
| **Stripe integration** | ❌ TODO | Payment processing |
| **Free tier tracking** | ❌ TODO | 5 workflows/month |

---

## Gaps to Fill (Detailed)

### Gap 1: Connect Sandbox Token Data to CostRecords

**Problem**: Token usage is captured in `agent.completed` events and stored in `claude_session_transcripts.session_metadata`, but NOT written to `cost_records` table where `CostTrackingService` can aggregate it.

**Location**: `omoi_os/api/routes/sandbox.py` → `persist_sandbox_event_async()` (line ~336)

**Data Available in Event**:
```python
event_data = {
    "input_tokens": 15000,        # ✅ Available
    "output_tokens": 3500,        # ✅ Available
    "cache_read_tokens": 5000,    # ✅ Available
    "cache_write_tokens": 2000,   # ✅ Available
    "cost_usd": 0.0825,           # ✅ SDK's calculation
    "task_id": "uuid",            # ✅ Available
    "session_id": "session-123",  # ✅ Available
    "turns": 15,                  # ✅ Available
}
```

**What's Missing**: Call to `CostTrackingService.record_llm_cost()` after extracting this data.

**Fix**: See "Specific Code Change Required" section below.

---

### Gap 2: Backend LLM Calls Not Tracked

**Problem**: The monitoring services make LLM calls to Fireworks.ai but don't record costs.

**Services Making Untracked Calls**:

| Service | File | Method | Frequency |
|---------|------|--------|-----------|
| `IntelligentGuardian` | `intelligent_guardian.py` | `analyze_trajectory()` | Every 60s per active sandbox |
| `ConductorService` | `conductor.py` | `analyze_coherence()` | Every 300s |
| `PydanticAIService` | `pydantic_ai_service.py` | `structured_output()` | Various |
| `LLMService` | `llm_service.py` | `complete()`, `structured_output()` | Various |

**Fix Options**:

**Option A**: Instrument `LLMService` wrapper (recommended)
```python
# In llm_service.py
async def complete(self, prompt: str, ...) -> str:
    response = await self._pydantic_ai.complete(prompt, ...)

    # Record cost
    if self.cost_tracking:
        self.cost_tracking.record_llm_cost(
            task_id=None,  # Backend calls not tied to tasks
            agent_id="system:guardian",  # Or appropriate identifier
            provider="fireworks",
            model=self.model,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            metadata={"service": "guardian", "type": "trajectory_analysis"},
        )

    return response.content
```

**Option B**: Track as "platform overhead" separately
- Create `platform_costs` table for non-task-related LLM usage
- Useful for understanding operational costs vs customer costs

---

### Gap 3: Model Name Not Passed from Sandbox

**Problem**: The `agent.completed` event doesn't include the model name used, so we default to `claude-sonnet-4-5-20250929`.

**Location**: `claude_sandbox_worker.py` → where `agent.completed` event is built

**Fix**: Add model name to the event payload:
```python
# In claude_sandbox_worker.py, around line 1095
event_data = {
    ...
    "model": os.environ.get("MODEL", "claude-sonnet-4-5-20250929"),  # ADD THIS
    "input_tokens": result.usage.input_tokens,
    ...
}
```

---

### Gap 4: No ticket_id in CostRecord Model

**Problem**: `CostRecord` has `task_id` and `agent_id` but no `ticket_id` field, making aggregation by ticket require a join.

**Current Schema** (`cost_record.py`):
```python
class CostRecord(Base):
    task_id: Mapped[Optional[str]]
    agent_id: Mapped[Optional[str]]
    # No ticket_id!
```

**Fix Options**:

**Option A**: Add `ticket_id` column to `CostRecord`
```python
ticket_id: Mapped[Optional[str]] = mapped_column(
    String(255), nullable=True, index=True
)
```

**Option B**: Use metadata JSONB field (already exists)
- Store `ticket_id` in metadata, query with JSONB operators
- Less efficient but no migration needed

**Option C**: Create `UsageRecord` model that aggregates by ticket (planned for Phase 3)

---

### Gap 5: Fireworks.ai Pricing Not in cost_models.yaml

**Problem**: Backend LLM calls use Fireworks.ai, but pricing may not be configured.

**Check**: `config/cost_models.yaml` for Fireworks.ai pricing entries.

**Fix**: Add if missing:
```yaml
fireworks:
  models:
    accounts/fireworks/models/gpt-oss-120b:
      input_cost_per_1k: 0.0005   # Example - verify actual pricing
      output_cost_per_1k: 0.0015
```

---

### Gap 6: No Real-Time Cost Alerts

**Problem**: `BudgetEnforcerService` exists but may not be hooked into sandbox events.

**Desired Behavior**:
- Alert when a single sandbox exceeds $X in costs
- Alert when ticket total exceeds threshold
- Block new sandboxes if org budget exhausted

**Fix**: After recording cost in Gap 1 fix, add budget check:
```python
# After record_llm_cost()
budget_enforcer = BudgetEnforcerService(db)
budget_status = budget_enforcer.check_budget(
    scope="ticket",
    scope_id=str(ticket_id),
)
if budget_status.exceeded:
    # Publish alert event
    event_bus.publish(SystemEvent(
        event_type="budget.exceeded",
        entity_type="ticket",
        entity_id=str(ticket_id),
        payload={"current": budget_status.spent, "limit": budget_status.limit},
    ))
```

---

## Current Execution Architecture

OmoiOS uses **sandbox-based execution**, not traditional agent polling:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Orchestrator    │────▶│ Daytona Spawner  │────▶│ Isolated Sandbox    │
│ Worker          │     │                  │     │ (Claude/OpenHands)  │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                                                  │
        │ polls TaskQueue                                  │ sends events
        │                                                  ▼
        │                                         ┌─────────────────────┐
        └────────────────────────────────────────▶│ SandboxEvent Table  │
                                                  │ (all activity)      │
                                                  └─────────────────────┘
```

**Key components**:
- **Orchestrator Worker** (`orchestrator_worker.py`): Polls for pending tasks, spawns sandboxes
- **Daytona Spawner** (`daytona_spawner.py`): Creates isolated sandbox environments
- **Sandbox Workers** (`claude_sandbox_worker.py`): Run inside sandboxes, execute tasks
- **SandboxEvent Model**: Stores all events from sandboxes (heartbeats, file edits, completions)

---

## Billing Model Summary

| Component | Pricing | Notes |
|-----------|---------|-------|
| **Workflow Completion** | $5-15 per merged PR | Primary billing unit |
| **Free Tier** | 5 workflows/month | Remove friction for new users |
| **Prepaid Credits** | $50 → 60 credits | Optional, provides cash flow |

We absorb costs for failed/stuck workflows—users only pay for value delivered.

---

## What We Need to Monitor

### 1. LLM Token Usage (Cost Driver #1)

**Why**: LLM calls are the biggest variable cost. We need to track them to:
- Understand our cost-per-workflow
- Set profitable pricing
- Detect runaway sandboxes burning tokens

**What to Track**:
| Field | Description |
|-------|-------------|
| `provider` | anthropic, openai, etc. |
| `model` | claude-sonnet-4-5-20250929, etc. |
| `prompt_tokens` | Input tokens |
| `completion_tokens` | Output tokens |
| `total_cost` | Calculated cost in USD |
| `task_id` | Which task triggered this |
| `sandbox_id` | Which sandbox made the call |
| `ticket_id` | Parent ticket for aggregation |

**Existing Code**: `omoi_os/services/cost_tracking.py` and `omoi_os/models/cost_record.py` already handle this!

### 2. Sandbox Runtime (Cost Driver #2)

**Why**: Daytona sandboxes have compute costs. Track time to understand resource usage.

**What to Track**:
| Field | Description |
|-------|-------------|
| `sandbox_id` | Daytona sandbox identifier |
| `task_id` | Task being executed |
| `start_time` | First `agent.started` event |
| `end_time` | `agent.completed` or termination |
| `runtime_seconds` | Calculated duration |
| `status` | completed, failed, idle_terminated |

**Where**: SandboxEvents already track `agent.started` and `agent.completed`. We can derive runtime from event timestamps.

### 3. Ticket/Workflow Completions (Billing Trigger)

**Why**: This is what we actually bill for—successful workflow completions.

**What to Track**:
| Field | Description |
|-------|-------------|
| `ticket_id` | Ticket identifier |
| `user_id` / `org_id` | Who to bill |
| `started_at` | When ticket created |
| `completed_at` | When all tasks done / PR merged |
| `total_llm_cost` | Sum of all LLM costs |
| `total_runtime_seconds` | Sum of sandbox runtime |
| `tasks_completed` | Number of tasks |
| `billable` | Whether to charge (true for success) |

### 4. Storage Usage (Cost Driver #3)

**Why**: Vector embeddings and memory storage have costs.

**What to Track**:
| Field | Description |
|-------|-------------|
| `org_id` | Organization |
| `memory_count` | Number of stored memories |
| `embedding_bytes` | Storage size |
| `repo_cache_bytes` | Cached repository data |

---

## Where Code Lives

### Existing Code (Already Built)

```
omoi_os/
├── models/
│   ├── cost_record.py      # ✅ LLM cost tracking model
│   ├── budget.py           # ✅ Budget limits model
│   ├── sandbox_event.py    # ✅ All sandbox activity events
│   └── task.py             # ✅ Has sandbox_id field
├── services/
│   ├── cost_tracking.py    # ✅ Records LLM costs, aggregates
│   ├── budget_enforcer.py  # ✅ Enforces budget limits
│   ├── daytona_spawner.py  # ✅ Spawns sandboxes
│   └── idle_sandbox_monitor.py  # ✅ Monitors sandbox activity
├── workers/
│   ├── orchestrator_worker.py   # ✅ Spawns sandboxes for tasks
│   └── monitoring_worker.py     # ✅ Runs monitoring loops
└── api/routes/
    └── costs.py            # ✅ Cost & budget API endpoints
```

### New Code to Add

```
omoi_os/
├── models/
│   ├── usage_record.py     # NEW: Unified usage per ticket
│   ├── billing_account.py  # NEW: Customer billing info
│   └── invoice.py          # NEW: Generated invoices
├── services/
│   ├── usage_aggregator.py # NEW: Aggregates usage per ticket
│   ├── billing_service.py  # NEW: Generates invoices, handles payments
│   └── stripe_service.py   # NEW: Stripe API integration
└── api/routes/
    └── billing.py          # NEW: Billing API endpoints

config/
└── billing.yaml            # NEW: Pricing configuration
```

---

## Integration Points

### 1. LLM Call Tracking (Inside Sandboxes)

**Good News**: This is already implemented! The Claude Agent SDK reports token usage.

**Current Flow** (already working):
```
Claude Agent SDK → ResultMessage.usage → claude_sandbox_worker.py extracts tokens
                                                    ↓
                                         POST /api/v1/sandboxes/{sandbox_id}/events
                                                    ↓
                                         sandbox.py: persist_sandbox_event()
                                                    ↓
                                         Stored in claude_session_transcripts.session_metadata
```

**Data Already Captured** (in `agent.completed` event):
- `input_tokens` - prompt tokens
- `output_tokens` - completion tokens
- `cache_read_tokens` - tokens read from prompt cache
- `cache_write_tokens` - tokens written to prompt cache
- `cost_usd` - SDK's calculated cost
- `turns` - number of conversation turns

**Where It's Stored**:
- `sandbox_events` table (JSONB payload)
- `claude_session_transcripts.session_metadata` (extracted on completion)

**Existing Infrastructure**:
- `CostRecord` model (`omoi_os/models/cost_record.py`)
- `CostTrackingService` (`omoi_os/services/cost_tracking.py`)
- `cost_models.yaml` - pricing per model
- `/api/costs/*` endpoints already exist

**Gap to Fill**: Connect `agent.completed` events to `CostTrackingService.record_llm_cost()` so costs appear in `cost_records` table for aggregation.

**Specific Code Change Required** in `omoi_os/api/routes/sandbox.py`:

In the `persist_sandbox_event_async()` function (around line 336), after saving the session transcript, add cost recording:

```python
# Around line 352, after save_session_transcript_async() call:

# Save session transcript for cross-sandbox resumption (outside session)
if event_type == "agent.completed" and event_data.get("session_id"):
    await save_session_transcript_async(
        db=db,
        session_id=event_data["session_id"],
        sandbox_id=sandbox_id,
        task_id=event_data.get("task_id"),
        transcript_b64=event_data.get("transcript_b64"),
        metadata={
            "turns": event_data.get("turns"),
            "cost_usd": event_data.get("cost_usd"),
            "stop_reason": event_data.get("stop_reason"),
            "input_tokens": event_data.get("input_tokens"),
            "output_tokens": event_data.get("output_tokens"),
            "cache_read_tokens": event_data.get("cache_read_tokens"),
            "cache_write_tokens": event_data.get("cache_write_tokens"),
        },
    )

    # ========== NEW: Record LLM cost for billing aggregation ==========
    if event_data.get("input_tokens") or event_data.get("output_tokens"):
        try:
            from omoi_os.services.cost_tracking import CostTrackingService

            cost_service = CostTrackingService(db)
            task_id = event_data.get("task_id")

            # Get ticket_id from task for proper aggregation
            ticket_id = None
            if task_id:
                from omoi_os.models.task import Task
                async with db.get_async_session() as session:
                    from sqlalchemy import select
                    result = await session.execute(
                        select(Task.ticket_id).where(Task.id == task_id)
                    )
                    ticket_id = result.scalar_one_or_none()

            cost_service.record_llm_cost(
                task_id=task_id,
                agent_id=sandbox_id,  # Use sandbox_id as agent identifier
                provider="anthropic",  # Or extract from env/config
                model=event_data.get("model", "claude-sonnet-4-5-20250929"),
                prompt_tokens=event_data.get("input_tokens", 0),
                completion_tokens=event_data.get("output_tokens", 0),
                # Include ticket_id in metadata for aggregation
                metadata={
                    "ticket_id": str(ticket_id) if ticket_id else None,
                    "sandbox_id": sandbox_id,
                    "session_id": event_data.get("session_id"),
                    "turns": event_data.get("turns"),
                    "cache_read_tokens": event_data.get("cache_read_tokens"),
                    "cache_write_tokens": event_data.get("cache_write_tokens"),
                    "sdk_cost_usd": event_data.get("cost_usd"),  # SDK's calculation
                },
            )
            logger.info(f"Recorded LLM cost for sandbox {sandbox_id}: {event_data.get('input_tokens', 0)} in / {event_data.get('output_tokens', 0)} out")
        except Exception as e:
            # Cost recording is optional - don't fail event processing
            logger.warning(f"Failed to record LLM cost for sandbox {sandbox_id}: {e}")
    # ========== END NEW ==========
```

**Note**: The `CostTrackingService.record_llm_cost()` method may need an async version or the call wrapped appropriately.

### 1b. Backend LLM Usage (Monitoring Services)

**Additional LLM calls happen in the backend** for monitoring and analysis:

| Service | Purpose | Currently Tracked? |
|---------|---------|-------------------|
| `IntelligentGuardian` | Trajectory analysis every 60s | ❌ No |
| `ConductorService` | System coherence analysis | ❌ No |
| `PydanticAIService` | Structured outputs (task classification, memory analysis) | ❌ No |
| `LLMService` | General completions | ❌ No |

**These use Fireworks.ai** (not Anthropic) via `PydanticAIService`:
- Base URL: `https://api.fireworks.ai/inference/v1`
- Model: `accounts/fireworks/models/gpt-oss-120b` (or configured)

**Gap to Fill**: Instrument `LLMService` and `PydanticAIService` to call `CostTrackingService.record_llm_cost()` after each call.

**Note**: Monitoring LLM usage can be disabled via `llm_analysis_enabled: false` in `MonitoringConfig` to save costs during development.

### 2. Sandbox Runtime Tracking

**Location**: Derive from `SandboxEvent` timestamps

**Current Data Available**:
- `agent.started` event with timestamp
- `agent.completed` event with timestamp
- `agent.heartbeat` events every 30 seconds
- Idle termination events from `idle_sandbox_monitor.py`

**Implementation**:
```python
# In usage_aggregator.py
def calculate_sandbox_runtime(self, sandbox_id: str) -> int:
    """Calculate runtime in seconds from sandbox events."""
    with self.db.get_session() as session:
        # Get first started event
        start_event = session.execute(
            select(SandboxEvent)
            .where(SandboxEvent.sandbox_id == sandbox_id)
            .where(SandboxEvent.event_type == "agent.started")
            .order_by(SandboxEvent.created_at.asc())
            .limit(1)
        ).scalar_one_or_none()

        # Get completion or last event
        end_event = session.execute(
            select(SandboxEvent)
            .where(SandboxEvent.sandbox_id == sandbox_id)
            .where(SandboxEvent.event_type.in_(["agent.completed", "agent.terminated"]))
            .order_by(SandboxEvent.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if start_event and end_event:
            return int((end_event.created_at - start_event.created_at).total_seconds())
        return 0
```

### 3. Ticket Completion → Billing

**Location**: Hook into ticket status changes

**Trigger Points**:
- Ticket status changes to `"done"` or `"completed"`
- All tasks for ticket completed
- PR merged (if GitHub integration)

**Flow**:
```
Ticket Completed → TicketService.complete_ticket()
                          ↓
              UsageAggregator.finalize_ticket(ticket_id)
                          ↓
              BillingService.create_invoice(ticket_id)
                          ↓
              StripeService.charge_customer() [if auto-billing]
                          ↓
              EventBus.publish("billing.invoice_created")
```

**Implementation Hook** (in existing ticket service):
```python
# When ticket marked complete
async def complete_ticket(self, ticket_id: str):
    ticket.status = "done"
    ticket.completed_at = utc_now()

    # Trigger billing
    if self.billing_service:
        await self.billing_service.process_ticket_completion(ticket_id)
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     SANDBOX EXECUTION LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           Daytona Sandbox (Isolated)                  │       │
│  │                                                       │       │
│  │  claude_sandbox_worker.py runs inside sandbox         │       │
│  │                                                       │       │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │       │
│  │  │ LLM Calls   │  │ File Edits  │  │ Tool Calls  │   │       │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │       │
│  │         │                │                │          │       │
│  │         └────────────────┼────────────────┘          │       │
│  │                          ▼                           │       │
│  │              POST to CALLBACK_URL                     │       │
│  └──────────────────────────┬───────────────────────────┘       │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │ Events sent to backend
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        EVENT COLLECTION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              SandboxEvent Table                       │       │
│  │                                                       │       │
│  │  • agent.started, agent.completed                    │       │
│  │  • agent.file_edited, agent.tool_completed           │       │
│  │  • agent.heartbeat (every 30s)                       │       │
│  │  • agent.usage (NEW: token counts per LLM call)      │       │
│  └──────────────────────────┬───────────────────────────┘       │
│                             │                                    │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              CostTrackingService                      │       │
│  │                                                       │       │
│  │  • Records LLM costs from usage events               │       │
│  │  • Links to sandbox_id and task_id                   │       │
│  │  • Publishes "cost.recorded" events                  │       │
│  └──────────────────────────┬───────────────────────────┘       │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       USAGE AGGREGATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              UsageAggregatorService                   │       │
│  │                                                       │       │
│  │  • Aggregates costs by ticket_id                     │       │
│  │  • Calculates sandbox runtime from events            │       │
│  │  • Finalizes totals on ticket completion             │       │
│  │  • Stores in usage_records table                     │       │
│  └──────────────────────────┬───────────────────────────┘       │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          BILLING                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                BillingService                         │       │
│  │                                                       │       │
│  │  • Checks free tier allowance                        │       │
│  │  • Calculates invoice amount ($5-15 per ticket)      │       │
│  │  • Creates invoice records                           │       │
│  │  • Handles credit deduction                          │       │
│  └──────────────────────────┬───────────────────────────┘       │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                StripeService                          │       │
│  │                                                       │       │
│  │  • Creates Stripe customers                          │       │
│  │  • Processes charges                                 │       │
│  │  • Handles webhooks                                  │       │
│  │  • Manages payment methods                           │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### New Tables

```sql
-- Usage aggregation per workflow
CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    workflow_id UUID NOT NULL REFERENCES workflows(id),

    -- Aggregated metrics
    total_llm_cost DECIMAL(10, 6) NOT NULL DEFAULT 0,
    total_prompt_tokens INTEGER NOT NULL DEFAULT 0,
    total_completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_runtime_seconds INTEGER NOT NULL DEFAULT 0,
    tasks_completed INTEGER NOT NULL DEFAULT 0,
    tasks_failed INTEGER NOT NULL DEFAULT 0,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',  -- in_progress, completed, failed
    finalized_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Customer billing accounts
CREATE TABLE billing_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL UNIQUE REFERENCES organizations(id),

    -- Stripe integration
    stripe_customer_id VARCHAR(255),
    stripe_payment_method_id VARCHAR(255),

    -- Free tier tracking
    free_workflows_remaining INTEGER NOT NULL DEFAULT 5,
    free_tier_reset_at TIMESTAMP WITH TIME ZONE,

    -- Credits
    credit_balance DECIMAL(10, 2) NOT NULL DEFAULT 0,

    -- Settings
    auto_billing_enabled BOOLEAN NOT NULL DEFAULT false,
    billing_email VARCHAR(255),

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Invoices
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    workflow_id UUID REFERENCES workflows(id),

    -- Amounts
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, paid, failed, waived
    paid_at TIMESTAMP WITH TIME ZONE,

    -- Payment info
    stripe_payment_intent_id VARCHAR(255),
    payment_method VARCHAR(50),  -- card, credits, free_tier

    -- Details
    line_items JSONB NOT NULL DEFAULT '[]',

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_usage_records_org ON usage_records(org_id);
CREATE INDEX idx_usage_records_workflow ON usage_records(workflow_id);
CREATE INDEX idx_invoices_org ON invoices(org_id);
CREATE INDEX idx_invoices_status ON invoices(status);
```

---

## API Endpoints

### New Routes (`/api/v1/billing/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/account` | Get billing account for current org |
| `POST` | `/account/setup` | Initialize Stripe customer |
| `POST` | `/account/payment-method` | Add payment method |
| `GET` | `/usage` | Get usage for current billing period |
| `GET` | `/usage/{workflow_id}` | Get usage for specific workflow |
| `GET` | `/invoices` | List invoices |
| `GET` | `/invoices/{id}` | Get invoice details |
| `POST` | `/invoices/{id}/pay` | Pay an invoice |
| `POST` | `/credits/purchase` | Purchase credits |
| `GET` | `/credits/balance` | Get credit balance |

---

## Configuration

### `config/billing.yaml`

```yaml
billing:
  # Pricing
  workflow_price_usd: 10.00      # Base price per workflow

  # Free tier
  free_workflows_per_month: 5
  free_tier_reset_day: 1          # Day of month to reset

  # Credits
  credit_bonus_percentage: 20     # $50 → $60 in credits
  min_credit_purchase_usd: 10

  # Cost tracking
  llm_cost_markup_percentage: 0   # Pass-through for now

  # Alerts
  high_cost_workflow_threshold_usd: 50  # Alert if workflow costs this much

stripe:
  # Secrets in .env
  # STRIPE_SECRET_KEY=sk_...
  # STRIPE_WEBHOOK_SECRET=whsec_...

  # Settings in yaml
  currency: usd
  payment_method_types:
    - card
```

---

## Event Types

New events published to EventBus:

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `usage.recorded` | Any usage tracked | `{workflow_id, type, amount}` |
| `usage.finalized` | Workflow completed | `{workflow_id, totals}` |
| `billing.invoice_created` | Invoice generated | `{invoice_id, amount}` |
| `billing.payment_succeeded` | Payment processed | `{invoice_id, payment_id}` |
| `billing.payment_failed` | Payment failed | `{invoice_id, error}` |
| `billing.free_tier_exhausted` | No free workflows left | `{org_id}` |
| `billing.credits_low` | Credits below threshold | `{org_id, balance}` |

---

## Implementation Order

### Phase 1: Connect Existing Token Tracking to CostRecords
**Status**: Partial - data captured but not connected

1. ✅ Token usage already extracted in `claude_sandbox_worker.py` (lines 1070-1092)
2. ✅ Data already POSTed to `/api/v1/sandboxes/{sandbox_id}/events`
3. ✅ Data stored in `sandbox_events` and `claude_session_transcripts`
4. ❌ **TODO**: In `sandbox.py:persist_sandbox_event()`, call `CostTrackingService.record_llm_cost()` when event_type is `agent.completed`
5. ❌ **TODO**: Map sandbox_id → task_id → ticket_id for proper aggregation

### Phase 2: Track Backend LLM Usage
**Status**: Not implemented

1. ❌ Add cost tracking to `LLMService.complete()` and `LLMService.structured_output()`
2. ❌ Add cost tracking to `PydanticAIService` calls
3. ❌ Add Fireworks.ai pricing to `cost_models.yaml`
4. ❌ Decide: attribute backend LLM costs to specific tasks or track separately as "platform overhead"

### Phase 3: Usage Aggregation
1. Create `usage_records` table and model
2. Create `UsageAggregatorService`
3. Calculate sandbox runtime from `SandboxEvent` timestamps
4. Aggregate costs by ticket_id on ticket completion
5. Use existing `/api/costs/summary` as starting point

### Phase 4: Billing Core
1. Create `billing_accounts` and `invoices` tables
2. Create `BillingService`
3. Implement free tier tracking (5 tickets/month)
4. Hook into ticket completion to trigger billing
5. Create billing API routes

### Phase 5: Stripe Integration
1. Create `StripeService`
2. Implement customer creation
3. Implement payment processing
4. Set up webhooks for payment events

### Phase 6: Credits System (Optional)
1. Implement credit purchase flow
2. Implement credit deduction on invoice
3. Add credit balance API

---

## Monitoring Dashboard (Future)

Admin dashboard should show:
- Real-time usage across all workflows
- Cost per workflow trends
- Revenue metrics (MRR, invoices paid)
- Free tier conversion rates
- High-cost workflow alerts

---

## Related Documents

- [Product Vision](../../product_vision.md) - Overall product direction
- [Cost Tracking Service](../../../omoi_os/services/cost_tracking.py) - Existing implementation
- [Budget Enforcer Service](../../../omoi_os/services/budget_enforcer.py) - Existing implementation
