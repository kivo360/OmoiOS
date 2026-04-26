# 03 · Sessions API

The only endpoint that blocks is `GET /events` (it streams). Everything else returns immediately.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/organizations/{org}/sessions` | Create. Returns `{ id, status: "pending" }`. |
| `GET` | `/v1/organizations/{org}/sessions` | List. Filters: `status`, `created_by`, `workspace`, `since`. |
| `GET` | `/v1/organizations/{org}/sessions/{id}` | Full state + URLs + usage. |
| `POST` | `/v1/organizations/{org}/sessions/{id}/messages` | Send follow-up prompt mid-session. |
| `POST` | `/v1/organizations/{org}/sessions/{id}/cancel` | Cancel. Idempotent. Graceful shutdown. |
| `POST` | `/v1/organizations/{org}/sessions/{id}/fork` | Branch from event `{ seq }` with a new prompt. |
| `GET` | `/v1/organizations/{org}/sessions/{id}/events` | SSE. Supports `Last-Event-Id`. |
| `GET` | `/v1/organizations/{org}/sessions/{id}/artifacts` | List artifacts. |

## Create request

```json
POST /v1/organizations/org_2fJxKk9/sessions

{
  "workspace_id": "ws_aK3p",
  "environment_id": "env_Jk2p",
  "prompt": "fix the flaky test in payments/refund_spec.ts",
  "share_with": ["usr_1Nbp"],
  "webhook_subscription": "whsub_9fEa",
  "metadata": {
    "origin": "slack",
    "slack_thread_ts": "1713700000.000100"
  }
}
```

## Event envelope

Every event — SSE frame, WebSocket message, or webhook body — uses this shape:

```json
{
  "id": "evt_01HW…",
  "seq": 142,
  "type": "tool_call",
  "session_id": "sess_9Qw2",
  "actor": "agent",
  "timestamp": "2026-04-21T14:03:22.481Z",
  "data": {
    "tool": "bash",
    "args": { "cmd": "pnpm test payments/refund_spec.ts" }
  }
}
```

`seq` is monotonic per session and survives reconnect. `actor` is `"agent"`, `"user:<user_id>"`, or `"system"`.
