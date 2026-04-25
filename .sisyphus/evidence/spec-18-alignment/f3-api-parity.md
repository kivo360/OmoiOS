# F3 — OpenAPI + SDK parity

## New routes registered

- `/api/v1/connections` → ['get']
- `/api/v1/connections/{provider}` → ['delete']
- `/api/v1/connections/{provider}/start` → ['post']
- `/api/v1/usage` → ['get']
- `/api/v1/usage/sessions/{session_id}` → ['get']

## Session enrichment (live GET /sessions/{id})

Runtime probe returned `urls` and `usage` keys — see `f3-session-enriched.json`.

## Canonical resource count per SDK

Spec §18 §2 canonical 7 + workspaces = 8.
- Python `omoios.AsyncOmoiOSClient`: sessions, environments, credentials, artifacts, webhooks, workspaces, connections, usage (8)
- TypeScript `OmoiOSClient`: sessions, environments, credentials, artifacts, webhooks, workspaces, connections, usage (8)
