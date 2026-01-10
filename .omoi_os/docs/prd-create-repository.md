---
id: PRD-CREATE-REPO-001
title: Create Repository PRD
feature: create-repository
created: 2026-01-09
updated: 2026-01-09
status: draft
author: Claude
---

# Create Repository

## Executive Summary

Enable users to create new GitHub repositories directly from OmoiOS as part of the existing project onboarding flow. After creation, agents automatically scaffold the project based on the user's feature description. This unlocks the full "idea to shipped code" workflow for greenfield projects, removing the friction of requiring an existing repository.

The feature includes support for creating repos in both personal accounts and GitHub Organizations, optional starter templates (Next.js, FastAPI, etc.), and the ability to delete repos when needed.

## Problem Statement

### Current State
Users must have an existing GitHub repository before they can use OmoiOS. This creates friction for:
- New project ideas that don't have a repo yet
- Rapid prototyping where users want to describe and build in one flow
- Users who want OmoiOS to handle the full lifecycle from idea to code

### Desired State
Users can describe what they want to build, OmoiOS creates the repository, scaffolds the project structure, and agents begin implementing features—all in one seamless flow. Users can also clean up failed or unwanted projects by deleting repositories directly from OmoiOS.

### Impact of Not Building
- Lost users who want greenfield project support
- Competitive disadvantage vs tools that handle full project creation
- Friction in the "idea to shipped code" value proposition

## Goals & Success Metrics

### Primary Goals
1. Enable creation of new GitHub repos from within OmoiOS
2. Support both personal accounts and GitHub Organizations
3. Auto-scaffold projects after creation based on user's feature description
4. Provide repo deletion capability for cleanup

### Success Metrics
| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| Projects using "Create New Repo" | 0% | 30% of new projects | Analytics |
| Time from idea to first commit | N/A (manual) | < 5 minutes | Workflow timing |
| Project completion rate (greenfield) | N/A | > 60% | Project status tracking |
| Repo cleanup usage | N/A | Track usage | Delete action analytics |

## User Stories

### Primary User: Solo Developer / Startup Founder

1. **Create Repo and Start Building**
   As a solo developer, I want to create a new repository and describe what I want built so that OmoiOS can scaffold and implement my idea without me setting up the repo manually.

   Acceptance Criteria:
   - [ ] Can create repo in personal account or organization
   - [ ] Can provide repo name and description
   - [ ] Can choose public or private visibility
   - [ ] After creation, can immediately describe features to build
   - [ ] Agents auto-scaffold based on description

2. **Use Starter Template**
   As a developer, I want to select a starter template (Next.js, FastAPI, etc.) so that the project has a solid foundation before agents add my features.

   Acceptance Criteria:
   - [ ] Template selection is optional (default: empty)
   - [ ] Templates include common stacks (Next.js, FastAPI, React, Python package)
   - [ ] Template is applied as initial commit before feature work

3. **Delete Unwanted Repository**
   As a user, I want to delete repositories that are no longer needed so that I can clean up failed experiments or trash code.

   Acceptance Criteria:
   - [ ] Can delete repos created by OmoiOS
   - [ ] Confirmation required before deletion
   - [ ] Associated OmoiOS project is also cleaned up

### Secondary User: Team Lead

4. **Create Repo in Organization**
   As a team lead, I want to create new repositories in my GitHub Organization so that projects are properly organized under the team's account.

   Acceptance Criteria:
   - [ ] Can select from organizations I have create_repo permission in
   - [ ] Clear indication of which org/account will own the repo
   - [ ] Error handling if permissions are insufficient

## Scope

### In Scope
- Create repository (personal account or organization)
- Select visibility (public/private)
- Optional template selection
- Auto-scaffold after creation based on feature description
- Delete repository capability
- Integration into existing "Connect Repository" flow (as a tab/option)
- List organizations user can create repos in

### Out of Scope
- GitLab/Bitbucket support (future)
- Monorepo creation with multiple packages (future)
- Custom organization templates (future)
- Transfer repo ownership (future)

### Future Considerations
- Import from template repositories (user's own templates)
- Clone existing repo as starting point
- Local-first option (review before pushing to GitHub)

## Constraints

### Technical Constraints
- Requires GitHub OAuth token with `repo` and `delete_repo` scopes
- Rate limited by GitHub API (5000 requests/hour authenticated)
- Repo names must follow GitHub naming rules (alphanumeric, hyphens, underscores)

### Business Constraints
- Must not break existing "Connect Repository" flow
- Should feel seamless, not like a separate feature

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| User creates repo, scaffolding fails, left with empty repo | Medium | Medium | Clear error messaging, option to delete and retry |
| Token lacks delete_repo scope | Medium | Low | Check scopes on connect, prompt to re-auth if needed |
| Org permissions insufficient | Low | Low | Pre-check permissions, clear error messages |
| Name collision (repo already exists) | Medium | Low | Check availability before creation, suggest alternatives |

## Dependencies

- GitHub OAuth integration (exists)
- GitHub MCP tools for repo operations (exists)
- Agent scaffolding capability (exists)

## Open Questions

- [x] Include templates from start? **Yes**
- [x] Support organizations? **Yes**
- [x] Auto-scaffold after creation? **Yes**
- [x] Include delete capability? **Yes**
- [x] Separate flow or integrate into existing? **Integrate into existing**
