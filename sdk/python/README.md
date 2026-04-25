# OmoiOS Python SDK

Python SDK for the OmoiOS Agent Workspace Platform.

Resources: `sessions`, `environments`, `credentials`, `artifacts`,
`webhooks`, `workspaces`, `connections`, `usage` — covering spec §18 §2's
canonical seven plus workspace management.

## Spec §18 primitive patterns

```python
from omoios import AsyncOmoiOSClient

async with AsyncOmoiOSClient(base_url, api_key=key, telemetry=print) as c:
    # Pattern A — fire and forget
    s = await c.sessions.create(workspace_id=ws, prompt="build an endpoint")

    # Pattern B — sync wait on terminal event
    async for evt in c.sessions.events(s.id):
        if evt.type == "session.succeeded":
            break

    # Pattern C — live stream
    async for evt in c.sessions.events(s.id):
        render(evt)

    # Pattern D — multiplayer
    ch = c.sessions.connect(s.id, user_token=jwt)
    ch.on("cursor.moved", on_cursor)
    await ch.open()
```

## Telemetry

Pass a callback to observe every HTTP lifecycle event — emitted for
every `_request` call plus `stream_open` / `stream_close` for SSE and
WebSocket channels. Auth headers are never included.

```python
def on_event(e):
    print(f"{e['kind']} {e.get('method','')} {e['path']} "
          f"status={e.get('status')} dur={e.get('duration_ms',0):.0f}ms")

c = AsyncOmoiOSClient(base_url, api_key=key, telemetry=on_event)
```

## Cancellation

`asyncio.wait_for` already works — httpx cooperates with task
cancellation natively:

```python
import asyncio
await asyncio.wait_for(c.sessions.create(...), timeout=5.0)
```

For reusable cancel scopes that span multiple calls, pass an
`anyio.CancelScope` to any SDK method that forwards it:

```python
import anyio
scope = anyio.CancelScope()
# pass scope down into _request via kwargs in a resource layer you own
```

## Installation

```bash
pip install omoios-sdk
```

Or with uv:

```bash
uv add omoios-sdk
```

## Quick Start

```python
from omoios import MockOmoiOSClient

# Use mock client for development
client = MockOmoiOSClient()

# List credentials
credentials = client.list_credentials()
print(credentials)

# Create an environment
env = client.create_environment({"name": "staging", "description": "Staging environment"})
print(env)
```

## Development

```bash
cd sdk/python
uv sync
uv run pytest
```

## API Coverage

- Credentials (CRUD)
- Environments (versioned)
- Artifacts (upload/download)
- Webhooks (subscriptions & deliveries)
- Workspaces (settings)

## License

Apache License 2.0
