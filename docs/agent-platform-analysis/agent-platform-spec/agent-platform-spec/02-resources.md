# 02 · Resource Model

Five top-level resources, all org-scoped. Every other object is a child of one of these.

## Organization — `org_`

The tenant. Billing boundary, data partition, trust root.

```json
{
  "id": "org_2fJxKk9",
  "name": "Acme Corp",
  "plan": "team",
  "limits": {
    "concurrent_sessions": 20,
    "monthly_compute_seconds": 3600000,
    "monthly_tokens_input": 50000000,
    "monthly_tokens_output": 10000000
  },
  "created_at": "2026-04-01T12:00:00Z"
}
```

## Workspace — `ws_`

Optional grouping: a repo set, a product area, a customer project.

```json
{
  "id": "ws_aK3p",
  "org_id": "org_2fJxKk9",
  "name": "payments-service",
  "default_environment_id": "env_Jk2p",
  "connections": {
    "github": "conn_gh_9fEa",
    "linear": "conn_ln_1Axc"
  }
}
```

## Environment — `env_`

Immutable sandbox recipe: image + env + tools + egress + resources. Versioned.

```json
{
  "id": "env_Jk2p",
  "version": 7,
  "image": { "kind": "snapshot", "ref": "snap_payments_7" },
  "env": {
    "DATABASE_URL": { "$secret": "sec_db_prod_ro" },
    "NODE_ENV":     "development"
  },
  "tools": ["bash", "editor", "git", "browser"],
  "egress": {
    "allowed_hosts":  ["api.github.com", "*.internal.acme.com"],
    "allowed_ports":  [443, 5432]
  },
  "resources": { "cpu": 4, "memory_gb": 8, "timeout_sec": 3600 }
}
```

## Session — `sess_`

One agent execution. Has state, events, artifacts, participants.

```json
{
  "id": "sess_9Qw2",
  "org_id": "org_2fJxKk9",
  "workspace_id": "ws_aK3p",
  "environment_id": "env_Jk2p",
  "environment_version": 7,
  "status": "running",
  "initial_prompt": "fix the flaky test in payments/refund_spec.ts",
  "created_by": "usr_5kLm",
  "acl": {
    "owner":   "usr_5kLm",
    "editors": ["usr_1Nbp"],
    "viewers": []
  },
  "urls": {
    "events_sse":  "https://api.example.com/v1/…/events",
    "websocket":   "wss://api.example.com/v1/…/ws",
    "editor":      "https://ide.example.com/s/sess_9Qw2"
  },
  "usage": { "compute_seconds": 142, "tokens_input": 28400, "tokens_output": 3100 },
  "created_at": "2026-04-21T14:02:10Z",
  "ended_at":   null
}
```

## Artifact — `art_`

Output surface: PRs, patches, files, screenshots, logs.

```json
{
  "id": "art_7Yp3",
  "session_id": "sess_9Qw2",
  "kind": "pull_request",
  "external_url": "https://github.com/acme/payments-service/pull/482",
  "payload": {
    "branch": "agent/fix-flaky-refund-spec",
    "commits": 3,
    "files_changed": 2
  },
  "created_at": "2026-04-21T14:09:41Z"
}
```
