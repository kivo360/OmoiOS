# Part 10: GitHub Integration

> Summary doc — partially documented; this covers the key integration patterns.

## Overview

OmoiOS integrates with GitHub for **branch management**, **commit tracking**, **pull request workflows**, and **webhook processing**. The orchestrator creates branches before sandbox execution and tracks all code changes back to tickets.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GitHub Integration Flow                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DaytonaSpawner                                                      │
│       │                                                              │
│       ├─ Create branch (BEFORE sandbox)                              │
│       │   Branch naming: task/{task-id}/{short-description}          │
│       │                                                              │
│       ├─ Clone repo into sandbox                                     │
│       │                                                              │
│       └─ Configure git credentials (PAT)                             │
│                                                                      │
│  ClaudeSandboxWorker (in sandbox)                                    │
│       │                                                              │
│       ├─ Execute task (code changes)                                 │
│       ├─ Commit with ticket references                               │
│       └─ Push to branch                                              │
│                                                                      │
│  ContinuousSandboxWorker                                             │
│       │                                                              │
│       └─ Create PR when task completes                               │
│                                                                      │
│  GitHubIntegrationService (webhook receiver)                         │
│       │                                                              │
│       ├─ Verify webhook signature (HMAC-SHA256)                      │
│       ├─ Process push events → link commits to tickets               │
│       └─ Process PR events → link PRs to tickets                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Webhook Processing

### Supported Events

| Event | Processing |
|-------|-----------|
| `push` | Extract commits, match ticket IDs, create `ticket_commit` records |
| `pull_request` | Extract PR data, link to ticket, track status |

### Commit-to-Ticket Linking

Regex patterns match ticket IDs in commit messages:

```
#123           → links commit to ticket 123
closes #123    → links commit + marks ticket intent
fixes #123     → links commit + marks ticket intent
```

## Branch Naming Convention

```
task/{task-uuid-short}/{description-slug}
```

Branches are created by `DaytonaSpawner` **before** sandbox creation to ensure the sandbox clones the correct branch.

## Key Files

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/github_integration.py` | Webhook handling, commit linking, PR tracking |
| `backend/omoi_os/api/routes/github.py` | GitHub webhook endpoint |
| `backend/omoi_os/api/routes/github_repos.py` | Repository listing/management |
| `backend/omoi_os/services/daytona_spawner.py` | Branch creation before sandbox spawn |
| `backend/omoi_os/services/sandbox_git_operations.py` | Git operations inside sandboxes |
| `backend/omoi_os/models/ticket_commit.py` | Commit-to-ticket association model |
| `backend/omoi_os/models/ticket_pull_request.py` | PR-to-ticket association model |
| `backend/omoi_os/models/branch_workflow.py` | Branch lifecycle tracking |
| `backend/omoi_os/models/merge_attempt.py` | Merge attempt tracking |

## Security

- Webhook signature verification using HMAC-SHA256
- Personal Access Token (PAT) for API calls via `httpx` client
- Token stored in project settings (not hardcoded)

## Known TODOs

- `github.py:156` — Get webhook secret from project settings (currently hardcoded)
- `github.py:206` — Implement sync logic for initial repository import
- GitHub events (`GITHUB_*`) are published to EventBus but have no subscribers
