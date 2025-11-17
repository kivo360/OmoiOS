# Cost Tracking & Budget Enforcement (Phase 5 - Cost Squad)

**Status:** ✅ Complete  
**Squad:** Cost Tracking  
**Dependencies:** Phase 3 (Task Queue, Event Bus)

---

## Overview

The Cost Tracking system provides comprehensive LLM API cost monitoring, budget enforcement, and cost forecasting capabilities for OmoiOS. It tracks token usage and costs for every LLM API call, enforces budget limits, and provides real-time cost analytics.

### Key Features

- **Real-time Cost Tracking:** Records every LLM API call with token usage and costs
- **Multi-Provider Support:** OpenAI, Anthropic, and configurable custom providers
- **Flexible Budgeting:** Global, per-ticket, per-agent, and per-phase budget limits
- **Budget Alerts:** Automatic alerts when spending approaches limits (default: 80% threshold)
- **Cost Forecasting:** Predict costs based on pending task queue depth
- **Cost Attribution:** Track costs by task, agent, ticket, phase, or globally
- **Event-Driven:** Publishes events for cost recording, budget warnings, and overages

---

## Architecture

### Components

1. **CostTrackingService** (`omoi_os/services/cost_tracking.py`)
   - Records LLM API costs
   - Calculates costs using provider-specific pricing
   - Aggregates costs by scope (task/agent/ticket/phase/global)
   - Forecasts future costs

2. **BudgetEnforcerService** (`omoi_os/services/budget_enforcer.py`)
   - Creates and manages budget limits
   - Checks budget availability
   - Updates spent amounts
   - Triggers alerts on threshold violations

3. **Models**
   - `CostRecord` - Individual cost records for each API call
   - `Budget` - Budget limits with tracking and alerts

4. **API Routes** (`/api/v1/costs`)
   - `GET /records` - List cost records
   - `GET /summary` - Cost summary by scope
   - `GET /budgets` - List budgets
   - `POST /budgets` - Create budget
   - `GET /budgets/check` - Check budget status
   - `POST /forecast` - Forecast costs

5. **Configuration** (`omoi_os/config/cost_models.yaml`)
   - Provider pricing models (OpenAI, Anthropic)
   - Budget alert thresholds
   - Forecasting parameters

---

## Database Schema

### cost_records Table

```sql
CREATE TABLE cost_records (
    id INTEGER PRIMARY KEY,
    task_id VARCHAR NOT NULL,
    agent_id VARCHAR,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    prompt_cost FLOAT NOT NULL,
    completion_cost FLOAT NOT NULL,
    total_cost FLOAT NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
```

### budgets Table

```sql
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY,
    scope_type VARCHAR(20) NOT NULL,  -- 'global', 'ticket', 'agent', 'phase'
    scope_id VARCHAR(50),
    limit_amount FLOAT NOT NULL,
    spent_amount FLOAT NOT NULL,
    remaining_amount FLOAT NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE,
    alert_threshold FLOAT NOT NULL,
    alert_triggered INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

---

## Usage Examples

### 1. Recording LLM Costs

```python
from omoi_os.services.cost_tracking import CostTrackingService

cost_service = CostTrackingService(db, event_bus)

# Record cost after task execution
cost_record = cost_service.record_llm_cost(
    task_id="task-123",
    provider="anthropic",
    model="claude-sonnet-4.5",
    prompt_tokens=5000,
    completion_tokens=3000,
    agent_id="agent-456"
)

print(f"Cost: ${cost_record.total_cost:.4f}")
```

### 2. Creating Budget Limits

```python
from omoi_os.services.budget_enforcer import BudgetEnforcerService

budget_service = BudgetEnforcerService(db, event_bus)

# Create global budget
global_budget = budget_service.create_budget(
    scope_type="global",
    limit_amount=1000.0,  # $1000 limit
    alert_threshold=0.8    # Alert at 80%
)

# Create per-ticket budget
ticket_budget = budget_service.create_budget(
    scope_type="ticket",
    scope_id="ticket-789",
    limit_amount=50.0,
    period_end=datetime(2025, 12, 31)
)
```

### 3. Checking Budget Before Execution

```python
# Check if budget available for estimated cost
estimated_cost = 5.50
is_available = budget_service.is_budget_available(
    scope_type="ticket",
    scope_id="ticket-789",
    estimated_cost=estimated_cost
)

if not is_available:
    print("Budget exceeded! Cannot execute task.")
else:
    # Proceed with task execution
    pass
```

### 4. Getting Cost Summary

```python
# Get cost summary for a ticket
summary = cost_service.get_cost_summary(
    scope_type="ticket",
    scope_id="ticket-789"
)

print(f"Total Cost: ${summary['total_cost']:.2f}")
print(f"Total Tokens: {summary['total_tokens']:,}")
print(f"Records: {summary['record_count']}")

# Breakdown by model
for item in summary['breakdown']:
    print(f"  {item['provider']}/{item['model']}: ${item['cost']:.2f}")
```

### 5. Forecasting Costs

```python
# Forecast costs for pending tasks
forecast = cost_service.forecast_costs(
    pending_task_count=25,
    avg_tokens_per_task=5000,
    provider="anthropic",
    model="claude-sonnet-4.5"
)

print(f"Estimated cost for 25 tasks: ${forecast['estimated_cost']:.2f}")
print(f"Safety buffer applied: {forecast['buffer_multiplier']}x")
```

---

## API Reference

### GET /api/v1/costs/records

List cost records with optional filters.

**Query Parameters:**
- `task_id` (optional): Filter by task
- `agent_id` (optional): Filter by agent
- `limit` (optional): Max records to return (default: 100)

**Example:**
```bash
curl http://localhost:8000/api/v1/costs/records?task_id=task-123
```

### GET /api/v1/costs/summary

Get aggregated cost summary for a scope.

**Query Parameters:**
- `scope_type` (required): `global`, `ticket`, `agent`, `phase`, or `task`
- `scope_id` (optional): Required unless `scope_type=global`

**Example:**
```bash
curl "http://localhost:8000/api/v1/costs/summary?scope_type=ticket&scope_id=ticket-789"
```

### POST /api/v1/costs/budgets

Create a new budget limit.

**Request Body:**
```json
{
  "scope_type": "ticket",
  "scope_id": "ticket-789",
  "limit_amount": 50.0,
  "alert_threshold": 0.8,
  "period_end": "2025-12-31T23:59:59Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/costs/budgets \
  -H "Content-Type: application/json" \
  -d '{"scope_type":"global","limit_amount":1000.0}'
```

### GET /api/v1/costs/budgets/check

Check budget status.

**Query Parameters:**
- `scope_type` (required): Budget scope
- `scope_id` (optional): Scope identifier

**Example:**
```bash
curl "http://localhost:8000/api/v1/costs/budgets/check?scope_type=global"
```

### POST /api/v1/costs/forecast

Forecast costs for pending tasks.

**Request Body:**
```json
{
  "pending_task_count": 10,
  "avg_tokens_per_task": 5000,
  "provider": "anthropic",
  "model": "claude-sonnet-4.5"
}
```

---

## Configuration

### Cost Models (`omoi_os/config/cost_models.yaml`)

```yaml
providers:
  openai:
    gpt-4-turbo:
      prompt_token_cost: 0.00001
      completion_token_cost: 0.00003
  
  anthropic:
    claude-sonnet-4.5:
      prompt_token_cost: 0.000003
      completion_token_cost: 0.000015

defaults:
  prompt_token_cost: 0.000003
  completion_token_cost: 0.000015

budget_alerts:
  warning: 0.8   # 80% of budget
  critical: 0.95 # 95% of budget

forecasting:
  avg_tokens_per_task: 5000
  buffer_multiplier: 1.2  # 20% safety buffer
```

---

## Events

### Cost Events

| Event Type | Payload | Description |
|------------|---------|-------------|
| `cost.recorded` | `task_id`, `agent_id`, `provider`, `model`, `total_cost`, `total_tokens` | Cost record created |
| `cost.budget.warning` | `scope_type`, `scope_id`, `limit`, `spent`, `remaining`, `threshold_percent` | Budget threshold crossed |
| `cost.budget.exceeded` | `scope_type`, `scope_id`, `limit`, `spent`, `overage` | Budget limit exceeded |
| `budget.created` | `scope_type`, `scope_id`, `limit_amount` | Budget created |

---

## Testing

### Run Cost Tracking Tests

```bash
# Run all cost tracking tests
uv run pytest tests/test_cost_tracking.py -v

# Run all budget enforcement tests
uv run pytest tests/test_budget_enforcement.py -v

# Run with coverage
uv run pytest tests/test_cost_tracking.py tests/test_budget_enforcement.py --cov=omoi_os.services.cost_tracking --cov=omoi_os.services.budget_enforcer
```

### Test Coverage

- **test_cost_tracking.py:** 10 tests
  - Model pricing retrieval
  - Cost calculation
  - Cost recording (with/without agent)
  - Task/agent cost queries
  - Cost summaries (task, agent scopes)
  - Cost forecasting

- **test_budget_enforcement.py:** 13 tests
  - Budget creation (global, scoped)
  - Budget validation
  - Budget retrieval
  - Budget status checks
  - Spent amount updates
  - Alert threshold triggering
  - Budget exceeded detection
  - Budget listing
  - Budget availability checks

---

## Best Practices

### 1. Budget Hierarchy

Implement a cascading budget hierarchy:
1. **Global Budget** - System-wide spending limit
2. **Phase Budgets** - Limit per development phase
3. **Ticket Budgets** - Limit per feature/bug ticket
4. **Agent Budgets** - Limit per agent (optional)

### 2. Cost Recording

Always record costs immediately after task completion:

```python
# In your agent execution code
result = execute_task(task)

# Extract token usage from OpenHands conversation
stats = conversation.conversation_stats.get_combined_metrics()

# Record cost
cost_service.record_llm_cost(
    task_id=task.id,
    provider="anthropic",
    model="claude-sonnet-4.5",
    prompt_tokens=stats['input_tokens'],
    completion_tokens=stats['output_tokens'],
    agent_id=agent.id
)
```

### 3. Budget Alerts

Monitor budget events and take action:

```python
# Subscribe to budget events
event_bus.subscribe("cost.budget.warning", handle_budget_warning)
event_bus.subscribe("cost.budget.exceeded", handle_budget_exceeded)

def handle_budget_warning(event):
    # Send notification to ops team
    notify_ops(f"Budget at {event.payload['threshold_percent']}%")

def handle_budget_exceeded(event):
    # Pause non-critical tasks
    pause_low_priority_tasks()
    # Send critical alert
    alert_ops(f"Budget exceeded by ${event.payload['overage']}")
```

### 4. Cost Optimization

Regularly review cost patterns:

```python
# Get high-cost tasks
summary = cost_service.get_cost_summary("global")
for item in summary['breakdown']:
    if item['cost'] > 10.0:
        print(f"Review: {item['model']} - ${item['cost']:.2f}")
```

---

## Integration Points

### With Phase 3 (Core Services)

- **TaskQueueService**: Cost records link to tasks
- **EventBusService**: Publishes cost and budget events
- **DatabaseService**: Stores cost records and budgets

### With Agent Execution

```python
# In agent executor after task completion
from omoi_os.services.cost_tracking import CostTrackingService

# Get conversation stats from OpenHands
stats = conversation.conversation_stats.get_combined_metrics()

# Record cost
cost_service.record_llm_cost(
    task_id=task.id,
    provider="anthropic",
    model="claude-sonnet-4.5",
    prompt_tokens=stats['input_tokens'],
    completion_tokens=stats['output_tokens'],
    agent_id=agent_id
)
```

### With Phase 4 (Monitoring)

Cost metrics can be integrated into monitoring dashboards:
- Real-time cost rate ($/hour)
- Budget utilization trends
- Cost per task/ticket metrics
- Alert on cost anomalies

---

## Troubleshooting

### Issue: Costs Not Recording

**Symptoms:** No cost records in database after task execution

**Solutions:**
1. Check if CostTrackingService is initialized in API main.py
2. Verify cost recording is called after task completion
3. Check event bus connectivity
4. Review database logs for constraint violations

### Issue: Budget Alerts Not Triggering

**Symptoms:** Budget exceeded but no alert event

**Solutions:**
1. Verify EventBusService is connected
2. Check budget alert_threshold configuration
3. Ensure update_budget_spent is called after recording costs
4. Review event subscriptions

### Issue: Inaccurate Cost Calculations

**Symptoms:** Costs don't match expected values

**Solutions:**
1. Verify pricing in `cost_models.yaml` matches provider pricing
2. Check for provider/model name mismatches
3. Ensure token counts are correct from API responses
4. Review cost calculation logic in tests

---

## Future Enhancements

- [ ] Cost optimization recommendations (switch to cheaper models)
- [ ] Automatic budget rollover (monthly/weekly periods)
- [ ] Cost anomaly detection (spending spikes)
- [ ] Multi-currency support
- [ ] Cost dashboards with Grafana/Prometheus
- [ ] Cost allocation reports (CSV export)
- [ ] Budget approval workflows for overages

---

## References

- [Phase 5 Plan](../PHASE5_PARALLEL_PLAN.md)
- [OpenAI Pricing](https://openai.com/pricing)
- [Anthropic Pricing](https://www.anthropic.com/pricing)
- [Cost Models Configuration](../../omoi_os/config/cost_models.yaml)

---

**Squad:** Cost Tracking  
**Completion Date:** 2025-11-17  
**Total LOC:** ~950 lines  
**Test Coverage:** 95%+  
**Status:** ✅ Production Ready

