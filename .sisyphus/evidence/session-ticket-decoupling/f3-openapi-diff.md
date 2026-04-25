# F3 — OpenAPI schema diff for POST /api/v1/sessions

Snapshot captured 2026-04-24 after Wave 3 landed.

## Before (pre-decoupling)
- required: ["ticket_id", "title", "description"]
- no workspace_id, no github_repo, no prompt

## After (post-decoupling)
- required: []  (all fields optional on the wire; backend enforces
               `prompt + (workspace_id | github_repo)` semantically)
- nullable ticket_id (legacy, ignored when present)
- prompt: string
- workspace_id: string (UUID)
- environment_id: string (UUID)
- github_repo: string (pattern "owner/repo")
- share_with: UUID list
- metadata: object

Verified via:

    uv run python -c "from fastapi.openapi.utils import get_openapi; ..."

- ticket_id removed from required ✓
- prompt / workspace_id / github_repo all present ✓
- ticket_id nullable (tolerates legacy clients) ✓
