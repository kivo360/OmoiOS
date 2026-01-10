---
id: REQ-CREATE-REPO-001
title: Create Repository Requirements
feature: create-repository
created: 2026-01-09
updated: 2026-01-09
status: draft
category: functional
priority: HIGH
prd_ref: docs/prd-create-repository.md
design_ref: designs/create-repository.md
---

# Create Repository Requirements

## Overview

Requirements for enabling users to create new GitHub repositories directly from OmoiOS, with auto-scaffolding, template support, and deletion capability.

## Functional Requirements

### REQ-CREATE-REPO-FUNC-001: Create Repository in Personal Account

**Priority**: CRITICAL
**Category**: Functional

WHEN a user submits a valid repository name and selects their personal GitHub account, THE SYSTEM SHALL create the repository in their personal account and return the repository URL within 10 seconds.

**Acceptance Criteria**:
- [ ] User can enter repository name (validated against GitHub naming rules)
- [ ] User can enter optional description
- [ ] User can select public or private visibility
- [ ] Repository is created with README.md initialized
- [ ] Repository URL is returned and displayed to user
- [ ] Repository is automatically linked to new OmoiOS project

**Notes**: Uses GitHub API `POST /user/repos` endpoint.

---

### REQ-CREATE-REPO-FUNC-002: Create Repository in Organization

**Priority**: HIGH
**Category**: Functional

WHEN a user selects a GitHub Organization they have create_repo permission in and submits a valid repository name, THE SYSTEM SHALL create the repository in that organization.

**Acceptance Criteria**:
- [ ] System fetches list of organizations user can create repos in
- [ ] User can select organization from dropdown
- [ ] Repository is created under selected organization
- [ ] Proper error handling if permissions are insufficient
- [ ] Clear indication of which account/org will own the repo

**Notes**: Uses GitHub API `POST /orgs/{org}/repos` endpoint. Requires checking user's org memberships and permissions first.

---

### REQ-CREATE-REPO-FUNC-003: List Available Organizations

**Priority**: HIGH
**Category**: Functional

WHEN a user opens the repository creation form, THE SYSTEM SHALL display a list of GitHub organizations they can create repositories in, plus their personal account.

**Acceptance Criteria**:
- [ ] Personal account is always listed first
- [ ] Only organizations with create_repo permission are shown
- [ ] Organization avatars/icons displayed for recognition
- [ ] Graceful handling if user belongs to no organizations

**Notes**: Uses GitHub API `GET /user/orgs` and checks permissions.

---

### REQ-CREATE-REPO-FUNC-004: Template Selection

**Priority**: MEDIUM
**Category**: Functional

WHEN a user creates a new repository, THE SYSTEM SHALL optionally allow them to select a starter template to initialize the project structure.

**Acceptance Criteria**:
- [ ] Template selection is optional (default: empty/README only)
- [ ] Available templates: Next.js App Router, FastAPI + PostgreSQL, React + Vite, Python Package
- [ ] Selected template is pushed as initial commit after repo creation
- [ ] Template files include standard boilerplate (.gitignore, config files, etc.)

**Notes**: Templates are pushed via GitHub API `PUT /repos/{owner}/{repo}/contents/{path}` or via agent execution.

---

### REQ-CREATE-REPO-FUNC-005: Auto-Scaffold After Creation

**Priority**: CRITICAL
**Category**: Functional

WHEN a repository is created and the user provides a feature description, THE SYSTEM SHALL automatically trigger agent scaffolding to set up the project structure based on the description.

**Acceptance Criteria**:
- [ ] After repo creation, user can immediately describe what they want to build
- [ ] System generates spec (Requirements → Design → Tasks) from description
- [ ] Agents scaffold project structure based on spec
- [ ] User can monitor scaffolding progress in real-time
- [ ] Scaffolding failures are clearly reported with retry option

**Notes**: This connects repo creation to the existing spec-driven workflow.

---

### REQ-CREATE-REPO-FUNC-006: Delete Repository

**Priority**: HIGH
**Category**: Functional

WHEN a user requests to delete a repository created by OmoiOS, THE SYSTEM SHALL delete the GitHub repository and clean up the associated OmoiOS project.

**Acceptance Criteria**:
- [ ] User can delete repos from project settings
- [ ] Confirmation dialog required ("Type repo name to confirm")
- [ ] GitHub repository is deleted via API
- [ ] Associated OmoiOS project is archived/deleted
- [ ] All related specs, tickets, tasks are cleaned up
- [ ] Clear success/error messaging

**Notes**: Requires `delete_repo` OAuth scope. If scope is missing, prompt user to re-authorize.

---

### REQ-CREATE-REPO-FUNC-007: Validate Repository Name

**Priority**: HIGH
**Category**: Functional

WHEN a user enters a repository name, THE SYSTEM SHALL validate the name against GitHub's naming rules and check for availability.

**Acceptance Criteria**:
- [ ] Name must be 1-100 characters
- [ ] Only alphanumeric, hyphens, underscores, and periods allowed
- [ ] Cannot start with a period
- [ ] Check if name already exists in target account/org
- [ ] Real-time validation feedback as user types
- [ ] Suggest alternatives if name is taken

**Notes**: Availability check via GitHub API `GET /repos/{owner}/{repo}` (404 = available).

---

### REQ-CREATE-REPO-FUNC-008: Integrate Into Existing Flow

**Priority**: HIGH
**Category**: Functional

WHEN a user initiates "Connect Repository" or "New Project", THE SYSTEM SHALL present both options: connect existing repo OR create new repo, as tabs or toggle within the same modal.

**Acceptance Criteria**:
- [ ] Single modal with two options/tabs
- [ ] "Connect Existing" shows current repo connection flow
- [ ] "Create New" shows repo creation form
- [ ] Smooth transition between options
- [ ] Consistent styling and UX

---

## Non-Functional Requirements

### REQ-CREATE-REPO-PERF-001: Repository Creation Latency

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL complete repository creation within 10 seconds under normal conditions.

**Metrics**:
- P50 latency: < 3 seconds
- P99 latency: < 10 seconds
- Timeout: 30 seconds with clear error message

---

### REQ-CREATE-REPO-SEC-001: OAuth Scope Validation

**Priority**: HIGH
**Category**: Security

THE SYSTEM SHALL verify the user's GitHub token has required scopes (`repo`, `delete_repo`) before attempting operations that require them.

**Acceptance Criteria**:
- [ ] Check scopes on initial GitHub connection
- [ ] If delete_repo scope missing, prompt re-authorization when delete is attempted
- [ ] Never expose token or scopes to frontend beyond what's necessary
- [ ] Log scope-related errors for debugging

---

### REQ-CREATE-REPO-SEC-002: Delete Confirmation

**Priority**: HIGH
**Category**: Security

THE SYSTEM SHALL require explicit confirmation before deleting a repository to prevent accidental data loss.

**Acceptance Criteria**:
- [ ] User must type repository name to confirm deletion
- [ ] Warning message clearly states deletion is permanent
- [ ] Cannot delete via single click or accidental action

---

## Traceability

| Requirement ID | PRD Section | Design Section | Ticket |
|----------------|-------------|----------------|--------|
| REQ-CREATE-REPO-FUNC-001 | User Story #1 | API Endpoints | TKT-010 |
| REQ-CREATE-REPO-FUNC-002 | User Story #4 | API Endpoints | TKT-010 |
| REQ-CREATE-REPO-FUNC-003 | User Story #4 | API Endpoints | TKT-010 |
| REQ-CREATE-REPO-FUNC-004 | User Story #2 | Templates | TKT-011 |
| REQ-CREATE-REPO-FUNC-005 | User Story #1 | Auto-Scaffold | TKT-012 |
| REQ-CREATE-REPO-FUNC-006 | User Story #3 | Delete Flow | TKT-013 |
| REQ-CREATE-REPO-FUNC-007 | Constraints | Validation | TKT-010 |
| REQ-CREATE-REPO-FUNC-008 | Scope | Frontend | TKT-014 |
