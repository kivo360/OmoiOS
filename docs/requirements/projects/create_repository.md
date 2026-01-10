# Create New Repository Feature Requirements

**Status**: Draft
**Created**: 2026-01-09
**Updated**: 2026-01-09

## Executive Summary

Enable users to create new GitHub repositories directly from OmoiOS, allowing greenfield projects to be scaffolded and built from scratch by AI agents. This removes the requirement to connect an existing repository and opens up a powerful "idea to shipped code" workflow.

## Problem Statement

Currently OmoiOS requires users to connect an **existing** GitHub repository. This creates friction for:
- New projects that don't exist yet
- Users who want to prototype ideas quickly
- "Describe it and build it" workflows where the repo shouldn't exist until the user commits to the idea

## Core Requirements

### REQ-PROJ-001: Create Repository from Dashboard

**Priority**: P1 (High)

**Description**: Users can create a new GitHub repository directly from the OmoiOS dashboard as part of project onboarding.

**Acceptance Criteria**:
- User can choose "Create New Repository" instead of "Connect Existing Repository"
- User provides: repository name, description, visibility (public/private)
- Repository is created in user's GitHub account (or selected organization)
- Repository is automatically initialized with README
- Repository is immediately linked to the new OmoiOS project
- User receives confirmation with link to new repo

**User Flow**:
1. User clicks "New Project" in dashboard
2. User selects "Create New Repository" option
3. User enters: repo name, description, public/private toggle
4. User selects GitHub account or organization (if multiple available)
5. System creates repo via GitHub API
6. System links repo to new OmoiOS project
7. User proceeds to describe what they want built

**API Endpoints**:
- `POST /api/v1/projects/create-with-repo` - Create project + new GitHub repo

**Dependencies**:
- GitHub OAuth token with `repo` scope (already required for existing flow)
- User must have GitHub account connected

---

### REQ-PROJ-002: Repository Template Selection

**Priority**: P2 (Medium)

**Description**: Users can optionally select a starter template when creating a new repository.

**Acceptance Criteria**:
- User can choose from common templates: Empty, Next.js, FastAPI, React, Python Package, etc.
- Templates are applied after repo creation (initial commit with boilerplate)
- Custom organization templates can be added (future enhancement)
- "Empty" is the default (just README)

**Templates to Support (MVP)**:
- Empty (README only)
- Next.js App Router
- FastAPI + PostgreSQL
- React + Vite
- Python Package (pyproject.toml + src layout)

**API Endpoints**:
- `GET /api/v1/templates` - List available templates
- Template application happens via agent execution after repo creation

---

### REQ-PROJ-003: Organization Repository Creation

**Priority**: P2 (Medium)

**Description**: Users can create repositories under GitHub organizations they have access to, not just their personal account.

**Acceptance Criteria**:
- System fetches list of organizations user can create repos in
- User can select organization from dropdown
- Repo is created under selected organization
- Proper permissions checked before creation attempt
- Clear error messaging if user lacks permission

**API Endpoints**:
- `GET /api/v1/github/organizations` - List user's GitHub organizations with create_repo permission

---

### REQ-PROJ-004: Full Greenfield Workflow

**Priority**: P1 (High)

**Description**: Complete end-to-end flow from "I have an idea" to "code is in a repo with PRs".

**Acceptance Criteria**:
- User creates new repo from OmoiOS
- User describes feature/app in natural language
- OmoiOS generates spec (Requirements → Design → Tasks)
- User approves spec
- Agents scaffold project structure
- Agents implement features
- Agents create PR(s) with completed work
- User reviews and merges

**Example Flow**:
```
User: "Create a new repo called 'invoice-api'"
System: Creates github.com/user/invoice-api

User: "Build a REST API for managing invoices with
       Stripe integration, PostgreSQL, and email notifications"
System: Generates spec with phases
User: Approves spec
Agents: Scaffold FastAPI project, implement endpoints,
        add Stripe webhook handling, create PR
User: Reviews PR, merges
```

---

## Technical Implementation

### GitHub API Integration

Uses existing GitHub MCP tools:
- `mcp__github__create_repository` - Create the repo
- `mcp__github__push_files` - Push initial template files
- `mcp__github__create_branch` - Create feature branches
- `mcp__github__create_pull_request` - Create PRs

### Database Changes

Extend `Project` model:
```python
class Project(Base):
    # Existing fields...

    # New fields
    repo_created_by_omoios: Mapped[bool] = mapped_column(default=False)
    repo_template_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
```

### Frontend Components

- `CreateProjectModal` - Extended with "Create New Repo" tab
- `RepoNameInput` - Validates repo name availability
- `TemplateSelector` - Grid of template cards
- `OrgSelector` - Dropdown for organization selection

---

## Success Metrics

- % of new projects that use "Create New Repo" vs "Connect Existing"
- Time from project creation to first PR
- Completion rate of greenfield projects
- User satisfaction with onboarding flow

---

## Future Enhancements

- **Monorepo support**: Create repo with multiple packages/apps
- **GitHub template repos**: Use user's own template repositories
- **GitLab/Bitbucket support**: Extend to other git providers
- **Local-first option**: Clone to local, push later (for users who want to review before GitHub)

---

## Related Documents

- [Auth System](../auth/auth_system.md) - GitHub OAuth integration
- [Product Vision](../../product_vision.md) - Core workflow description
