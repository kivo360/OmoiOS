---
id: TKT-009
title: Delete Repository Functionality
created: 2026-01-09
updated: 2026-01-09
status: backlog
priority: HIGH
type: feature
feature: create-repository
estimate: M
requirements:
  - REQ-CREATE-REPO-FUNC-006
  - REQ-CREATE-REPO-SEC-001
  - REQ-CREATE-REPO-SEC-002
dependencies:
  blocked_by:
    - TKT-007
  blocks:
    - TKT-010
---

# TKT-009: Delete Repository Functionality

## Objective

Implement the ability to delete GitHub repositories directly from OmoiOS, with proper confirmation and cleanup of associated project data.

## Scope

### In Scope
- Delete repository via GitHub API
- OAuth scope validation for `delete_repo`
- Confirmation flow (type repo name to confirm)
- Archive/delete associated OmoiOS project
- Clean up related specs, tickets, tasks
- Re-authorization flow if scope missing

### Out of Scope
- Soft-delete with recovery period (future)
- Bulk delete (future)

## Acceptance Criteria

- [ ] `DELETE /api/v1/github/repos/{owner}/{repo}` endpoint
- [ ] Requires `confirm_name` matching repo name
- [ ] Checks for `delete_repo` OAuth scope before attempting
- [ ] Returns re-auth URL if scope is missing
- [ ] Deletes GitHub repository via API
- [ ] Archives or deletes OmoiOS project
- [ ] Cleans up specs, tickets, tasks in `.omoi_os/`
- [ ] Clear success/error messaging
- [ ] Unit and integration tests

## Technical Notes

- GitHub delete requires `delete_repo` scope (not included in basic `repo` scope)
- Check scopes via `X-OAuth-Scopes` header on any GitHub API response
- Provide re-authorization URL: `/auth/github/reauthorize?scope=delete_repo`
- Consider soft-delete for project (set `archived=true`) vs hard delete

## Tasks

- TSK-019: Add delete method to RepositoryService
- TSK-020: Implement OAuth scope checking
- TSK-021: Add delete repository API route
- TSK-022: Implement project cleanup on delete
- TSK-023: Write tests for delete flow

## Estimate

**Size**: M (2-4 hours)
**Rationale**: Single endpoint with scope validation and cleanup logic
