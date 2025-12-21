# Production Patterns

Best practices for deploying Claude Agent SDK applications in production.

## Session Management

### Session State Machine

```
┌──────────┐     ┌─────────┐     ┌──────────┐
│  IDLE    │────>│ RUNNING │────>│ COMPLETE │
└──────────┘     └─────────┘     └──────────┘
     │                │                │
     │                ▼                │
     │          ┌─────────┐           │
     └─────────>│  ERROR  │<──────────┘
                └─────────┘
```

### Tracking Sessions

```python
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class SessionState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"

@dataclass
class SessionInfo:
    session_id: str
    state: SessionState
    started_at: datetime
    completed_at: datetime | None = None
    total_cost_usd: float = 0.0
    num_turns: int = 0
    error: str | None = None

sessions: dict[str, SessionInfo] = {}

async def run_session(prompt: str) -> SessionInfo:
    session_info = SessionInfo(
        session_id="pending",
        state=SessionState.RUNNING,
        started_at=datetime.now(),
    )

    try:
        async with ClaudeSDKClient(options) as client:
            await client.query(prompt)

            async for msg in client.receive_response():
                if isinstance(msg, ResultMessage):
                    session_info.session_id = msg.session_id
                    session_info.state = SessionState.COMPLETE
                    session_info.completed_at = datetime.now()
                    session_info.total_cost_usd = msg.total_cost_usd or 0
                    session_info.num_turns = msg.num_turns

    except Exception as e:
        session_info.state = SessionState.ERROR
        session_info.error = str(e)

    sessions[session_info.session_id] = session_info
    return session_info
```

## Cost Control

### Budget Management

```python
from claude_agent_sdk import ClaudeAgentOptions

# Per-session budget
options = ClaudeAgentOptions(
    max_budget_usd=1.00,
    max_turns=20,
)

# Track cumulative costs
class CostTracker:
    def __init__(self, daily_limit: float):
        self.daily_limit = daily_limit
        self.daily_spent = 0.0
        self.last_reset = datetime.now().date()

    def can_spend(self, amount: float) -> bool:
        self._maybe_reset()
        return self.daily_spent + amount <= self.daily_limit

    def record_spend(self, amount: float):
        self._maybe_reset()
        self.daily_spent += amount

    def _maybe_reset(self):
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_spent = 0.0
            self.last_reset = today

cost_tracker = CostTracker(daily_limit=100.0)
```

### Pre-flight Cost Check

```python
async def run_with_budget_check(prompt: str, estimated_cost: float):
    if not cost_tracker.can_spend(estimated_cost):
        raise ValueError("Daily budget exceeded")

    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, ResultMessage):
            cost_tracker.record_spend(msg.total_cost_usd or 0)
            yield msg
        else:
            yield msg
```

## Error Handling

### Retry Logic

```python
import anyio
from claude_agent_sdk import ProcessError, CLIConnectionError

async def query_with_retry(
    prompt: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
):
    last_error = None

    for attempt in range(max_retries):
        try:
            async for msg in query(prompt=prompt, options=options):
                yield msg
            return
        except (ProcessError, CLIConnectionError) as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await anyio.sleep(delay)

    raise last_error
```

### Graceful Shutdown

```python
import signal
from contextlib import asynccontextmanager

class GracefulShutdown:
    def __init__(self):
        self.shutdown_requested = False
        self.active_clients: list[ClaudeSDKClient] = []

    def request_shutdown(self):
        self.shutdown_requested = True

    @asynccontextmanager
    async def managed_client(self, options: ClaudeAgentOptions):
        client = ClaudeSDKClient(options=options)
        self.active_clients.append(client)
        try:
            await client.connect()
            yield client
        finally:
            await client.disconnect()
            self.active_clients.remove(client)

    async def shutdown_all(self):
        for client in self.active_clients:
            try:
                await client.interrupt()
                await client.disconnect()
            except Exception:
                pass

shutdown_manager = GracefulShutdown()

# Signal handlers
def handle_sigterm(signum, frame):
    shutdown_manager.request_shutdown()

signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)
```

## Logging and Monitoring

### Structured Logging

```python
import logging
import json
from datetime import datetime

class AgentLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log_session_start(self, session_id: str, prompt: str):
        self.logger.info(json.dumps({
            "event": "session_start",
            "session_id": session_id,
            "prompt_length": len(prompt),
            "timestamp": datetime.now().isoformat(),
        }))

    def log_tool_use(self, session_id: str, tool_name: str, input_data: dict):
        self.logger.info(json.dumps({
            "event": "tool_use",
            "session_id": session_id,
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
        }))

    def log_session_complete(self, session_id: str, result: ResultMessage):
        self.logger.info(json.dumps({
            "event": "session_complete",
            "session_id": session_id,
            "num_turns": result.num_turns,
            "cost_usd": result.total_cost_usd,
            "duration_ms": result.duration_ms,
            "timestamp": datetime.now().isoformat(),
        }))
```

### Metrics Collection

```python
from dataclasses import dataclass, field

@dataclass
class AgentMetrics:
    total_sessions: int = 0
    successful_sessions: int = 0
    failed_sessions: int = 0
    total_cost_usd: float = 0.0
    total_turns: int = 0
    tool_usage: dict[str, int] = field(default_factory=dict)

    def record_session(self, result: ResultMessage, success: bool):
        self.total_sessions += 1
        if success:
            self.successful_sessions += 1
        else:
            self.failed_sessions += 1
        self.total_cost_usd += result.total_cost_usd or 0
        self.total_turns += result.num_turns

    def record_tool_use(self, tool_name: str):
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1

    def get_success_rate(self) -> float:
        if self.total_sessions == 0:
            return 0.0
        return self.successful_sessions / self.total_sessions

    def get_avg_cost(self) -> float:
        if self.total_sessions == 0:
            return 0.0
        return self.total_cost_usd / self.total_sessions
```

## Multi-Tenant Patterns

### Tenant Isolation

```python
from dataclasses import dataclass

@dataclass
class TenantConfig:
    tenant_id: str
    api_key: str
    max_budget_usd: float
    allowed_tools: list[str]
    system_prompt: str

def create_tenant_options(tenant: TenantConfig) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=tenant.system_prompt,
        allowed_tools=tenant.allowed_tools,
        max_budget_usd=tenant.max_budget_usd,
        env={"ANTHROPIC_API_KEY": tenant.api_key},
        user=tenant.tenant_id,
    )
```

### Per-Tenant Cost Tracking

```python
tenant_costs: dict[str, CostTracker] = {}

def get_tenant_tracker(tenant_id: str, daily_limit: float) -> CostTracker:
    if tenant_id not in tenant_costs:
        tenant_costs[tenant_id] = CostTracker(daily_limit=daily_limit)
    return tenant_costs[tenant_id]
```

## Health Checks

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage

async def health_check() -> dict:
    try:
        options = ClaudeAgentOptions(
            max_turns=1,
            max_budget_usd=0.01,
        )

        async with ClaudeSDKClient(options=options) as client:
            await client.query("Say 'ok'")

            async for msg in client.receive_response():
                if isinstance(msg, ResultMessage):
                    return {
                        "status": "healthy",
                        "latency_ms": msg.duration_ms,
                    }

        return {"status": "unhealthy", "error": "No result received"}

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```
