---
id: TKT-007
title: Create Repository Backend Service
created: 2026-01-09
updated: 2026-01-09
status: backlog
priority: CRITICAL
type: feature
feature: create-repository
estimate: L
requirements:
  - REQ-CREATE-REPO-FUNC-001
  - REQ-CREATE-REPO-FUNC-002
  - REQ-CREATE-REPO-FUNC-003
  - REQ-CREATE-REPO-FUNC-007
dependencies:
  blocked_by: []
  blocks:
    - TKT-008
    - TKT-009
    - TKT-010
---

# TKT-007: Create Repository Backend Service

## Objective

Implement the core backend service for creating GitHub repositories, including listing available owners (personal account + organizations), checking name availability, and creating repos via the GitHub API.

## Scope

### In Scope
- `RepositoryService` class with GitHub API integration
- List owners (personal + orgs with create_repo permission)
- Check repo name availability with suggestions
- Create repository in personal account or organization
- OAuth scope validation
- API routes for all operations

### Out of Scope
- Template application (TKT-008)
- Delete functionality (TKT-009)
- Frontend components (TKT-010)

## Acceptance Criteria

- [ ] `RepositoryService` implemented with httpx async client
- [ ] `GET /api/v1/github/owners` returns user + authorized orgs
- [ ] `GET /api/v1/github/repos/{owner}/{repo}/available` checks availability
- [ ] `POST /api/v1/github/repos` creates repository
- [ ] Proper error handling for permission issues
- [ ] OAuth scope validation for `repo` scope
- [ ] Unit tests for all service methods
- [ ] Integration tests for API routes

## Technical Notes

- Use httpx AsyncClient for GitHub API calls
- GitHub API version: 2022-11-28
- Cache org list for 5 minutes
- Implement retry logic (3 retries, exponential backoff)

## Tasks

- TSK-009: Implement RepositoryService class
- TSK-010: Add GitHub owner listing API route
- TSK-011: Add repo availability check API route
- TSK-012: Add create repository API route
- TSK-013: Write unit tests for RepositoryService
- TSK-014: Write integration tests for API routes

## Estimate

**Size**: L (4-8 hours)
**Rationale**: Multiple API endpoints, GitHub API integration, comprehensive testing
