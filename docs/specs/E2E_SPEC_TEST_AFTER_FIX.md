# E2E Spec Test After Fix - Specification

**Spec ID**: e2e-spec-test-after-fix
**Date**: 2026-01-18
**Status**: Requirements
**Phase**: Requirements
**Project**: OmoiOS

---

## 1. Overview

### 1.1 Purpose
This specification defines the end-to-end testing requirements for the Specification Workflow system after the critical fix (f3bab41) that resolved the Next.js 15 routing conflict preventing frontend deployment.

### 1.2 Context
The recent fix removed a duplicate `(dashboard)` route group that was causing Vercel deployment failures. With the frontend now deployable, comprehensive E2E testing is needed to validate that:
1. The spec workflow system functions correctly end-to-end
2. Frontend spec management pages are accessible and functional
3. Backend spec API endpoints work as expected
4. The complete user journey through spec creation, requirements, design, and execution phases works

### 1.3 Scope
- **In Scope**: E2E tests for spec workflow, frontend spec pages, backend spec API
- **Out of Scope**: Unit tests (already covered), non-spec related E2E tests

---

## 2. Requirements (EARS Format)

### REQ-001: Spec Creation
**Title**: Create New Specification
**WHEN** a user navigates to a project's specs page and clicks "Create Spec"
**THE SYSTEM SHALL** display a spec creation form and save the spec to the database upon submission

**Acceptance Criteria**:
- AC-001.1: The specs page loads within 3 seconds
- AC-001.2: The "Create Spec" button is visible and clickable
- AC-001.3: The form accepts title and description inputs
- AC-001.4: Upon submission, the new spec appears in the specs list
- AC-001.5: The spec is created with status "draft" and phase "Requirements"

---

### REQ-002: Spec List Display
**Title**: Display Project Specifications
**WHEN** a user navigates to a project's specs page
**THE SYSTEM SHALL** display a list of all specifications for that project with their status and progress

**Acceptance Criteria**:
- AC-002.1: The page displays spec title, status, phase, and progress
- AC-002.2: Specs are sorted by creation date (newest first)
- AC-002.3: Clicking a spec navigates to the spec detail page
- AC-002.4: Empty state is shown when no specs exist

---

### REQ-003: Spec Detail View
**Title**: View Specification Details
**WHEN** a user clicks on a specification from the list
**THE SYSTEM SHALL** display the complete spec detail page with requirements, design, and tasks

**Acceptance Criteria**:
- AC-003.1: The spec detail page loads successfully
- AC-003.2: Requirements section is visible and lists all requirements
- AC-003.3: Design section shows architecture, data model, and API spec
- AC-003.4: Tasks section lists all spec tasks with status
- AC-003.5: Phase progression indicator shows current phase

---

### REQ-004: Add Requirements
**Title**: Add EARS-Format Requirements
**WHEN** a user is on a spec detail page in Requirements phase and adds a requirement
**THE SYSTEM SHALL** accept EARS-format requirements with condition and action fields

**Acceptance Criteria**:
- AC-004.1: "Add Requirement" button is visible in Requirements phase
- AC-004.2: Requirement form has title, condition (WHEN), and action (SHALL) fields
- AC-004.3: New requirement appears in the requirements list immediately
- AC-004.4: Requirement can be edited after creation
- AC-004.5: Requirement can be deleted

---

### REQ-005: Add Acceptance Criteria
**Title**: Add Acceptance Criteria to Requirements
**WHEN** a user has a requirement and adds acceptance criteria
**THE SYSTEM SHALL** save and display the criteria linked to that requirement

**Acceptance Criteria**:
- AC-005.1: "Add Criterion" option is available for each requirement
- AC-005.2: Criterion text field accepts input
- AC-005.3: Criterion can be marked as completed
- AC-005.4: Criteria count is displayed on the requirement

---

### REQ-006: Approve Requirements
**Title**: Approve Requirements and Transition to Design
**WHEN** a user clicks "Approve Requirements" on a spec with requirements
**THE SYSTEM SHALL** mark requirements as approved and transition the spec to Design phase

**Acceptance Criteria**:
- AC-006.1: "Approve Requirements" button is visible when requirements exist
- AC-006.2: Clicking approve changes spec status to "design"
- AC-006.3: Spec phase changes to "Design"
- AC-006.4: Requirements become read-only after approval
- AC-006.5: Approval timestamp is recorded

---

### REQ-007: Update Design Artifacts
**Title**: Update Specification Design
**WHEN** a user is in the Design phase and updates design artifacts
**THE SYSTEM SHALL** save architecture, data model, and API spec content

**Acceptance Criteria**:
- AC-007.1: Design section is editable in Design phase
- AC-007.2: Architecture field accepts markdown content
- AC-007.3: Data model field accepts markdown content
- AC-007.4: API spec can define multiple endpoints
- AC-007.5: Changes are persisted to database

---

### REQ-008: Approve Design
**Title**: Approve Design and Transition to Implementation
**WHEN** a user clicks "Approve Design" on a spec in Design phase
**THE SYSTEM SHALL** mark design as approved and transition to Implementation phase

**Acceptance Criteria**:
- AC-008.1: "Approve Design" button is visible in Design phase
- AC-008.2: Clicking approve changes spec status to "executing"
- AC-008.3: Spec phase changes to "Implementation"
- AC-008.4: Design becomes read-only after approval
- AC-008.5: Approval timestamp is recorded

---

### REQ-009: Add Tasks
**Title**: Add Implementation Tasks
**WHEN** a user adds a task to a specification
**THE SYSTEM SHALL** create the task with phase, priority, and status tracking

**Acceptance Criteria**:
- AC-009.1: "Add Task" option is available
- AC-009.2: Task form includes title, description, phase, and priority
- AC-009.3: New task appears in the tasks list
- AC-009.4: Task status can be updated
- AC-009.5: Tasks can have dependencies defined

---

### REQ-010: Spec API CRUD Operations
**Title**: Backend Spec API Functionality
**WHEN** the frontend makes API requests to spec endpoints
**THE SYSTEM SHALL** correctly handle all CRUD operations for specs, requirements, criteria, and tasks

**Acceptance Criteria**:
- AC-010.1: POST /api/v1/specs creates new spec
- AC-010.2: GET /api/v1/specs/{id} returns spec with all relationships
- AC-010.3: PATCH /api/v1/specs/{id} updates spec fields
- AC-010.4: DELETE /api/v1/specs/{id} removes spec and related data
- AC-010.5: All endpoints return proper error responses for invalid requests

---

### REQ-011: Navigation After Fix
**Title**: Frontend Navigation Works After Route Fix
**WHEN** a user navigates between pages in the application
**THE SYSTEM SHALL** correctly route to all pages without conflicts or errors

**Acceptance Criteria**:
- AC-011.1: /login page loads correctly
- AC-011.2: /command page loads after authentication
- AC-011.3: /projects/{id}/specs page loads correctly
- AC-011.4: /projects/{id}/specs/{specId} page loads correctly
- AC-011.5: No duplicate route conflicts occur

---

## 3. Test Scenarios

### 3.1 Frontend E2E Tests (Playwright)

| Test File | Test Name | Requirements Covered |
|-----------|-----------|---------------------|
| `specs.spec.ts` | `displays specs list page` | REQ-002 |
| `specs.spec.ts` | `creates new specification` | REQ-001 |
| `specs.spec.ts` | `views spec detail page` | REQ-003 |
| `specs.spec.ts` | `adds requirement with EARS format` | REQ-004 |
| `specs.spec.ts` | `adds acceptance criterion` | REQ-005 |
| `specs.spec.ts` | `approves requirements` | REQ-006 |
| `specs.spec.ts` | `updates design artifacts` | REQ-007 |
| `specs.spec.ts` | `approves design` | REQ-008 |
| `specs.spec.ts` | `adds implementation task` | REQ-009 |
| `navigation.spec.ts` | `navigates without route conflicts` | REQ-011 |

### 3.2 Backend E2E Tests (pytest)

| Test File | Test Name | Requirements Covered |
|-----------|-----------|---------------------|
| `test_e2e_specs.py` | `test_create_spec` | REQ-010 |
| `test_e2e_specs.py` | `test_get_spec_with_relationships` | REQ-010 |
| `test_e2e_specs.py` | `test_add_requirement` | REQ-004, REQ-010 |
| `test_e2e_specs.py` | `test_add_acceptance_criterion` | REQ-005, REQ-010 |
| `test_e2e_specs.py` | `test_approve_requirements` | REQ-006, REQ-010 |
| `test_e2e_specs.py` | `test_update_design` | REQ-007, REQ-010 |
| `test_e2e_specs.py` | `test_approve_design` | REQ-008, REQ-010 |
| `test_e2e_specs.py` | `test_add_task` | REQ-009, REQ-010 |
| `test_e2e_specs.py` | `test_full_spec_lifecycle` | All |

### 3.3 Integration Tests

| Test File | Test Name | Requirements Covered |
|-----------|-----------|---------------------|
| `specs.test.tsx` | `renders specs list with API data` | REQ-002 |
| `specs.test.tsx` | `creates spec via API` | REQ-001 |
| `specs.test.tsx` | `displays spec details` | REQ-003 |

---

## 4. Design Artifacts

### 4.1 Architecture

The spec workflow system follows a layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Specs List     │  │  Spec Detail    │              │
│  │  Page           │  │  Page           │              │
│  └────────┬────────┘  └────────┬────────┘              │
│           │                     │                       │
│  ┌────────┴─────────────────────┴────────┐             │
│  │        React Query + Hooks            │             │
│  │  (useProjectSpecs, useCreateSpec)     │             │
│  └────────────────────┬──────────────────┘             │
│                       │                                 │
│  ┌────────────────────┴──────────────────┐             │
│  │           API Client (specs.ts)       │             │
│  └────────────────────┬──────────────────┘             │
└───────────────────────┼─────────────────────────────────┘
                        │ HTTP/REST
┌───────────────────────┼─────────────────────────────────┐
│                    Backend (FastAPI)                     │
│  ┌────────────────────┴──────────────────┐             │
│  │         Specs API Router              │             │
│  │    (/api/v1/specs/*)                  │             │
│  └────────────────────┬──────────────────┘             │
│                       │                                 │
│  ┌────────────────────┴──────────────────┐             │
│  │         Database Service              │             │
│  └────────────────────┬──────────────────┘             │
│                       │                                 │
│  ┌────────────────────┴──────────────────┐             │
│  │      SQLAlchemy Models (spec.py)      │             │
│  │  Spec, SpecRequirement, SpecCriterion │             │
│  └────────────────────┬──────────────────┘             │
└───────────────────────┼─────────────────────────────────┘
                        │
┌───────────────────────┼─────────────────────────────────┐
│                   PostgreSQL                             │
│  ┌────────────────────┴──────────────────┐             │
│  │  specs, spec_requirements,            │             │
│  │  spec_acceptance_criteria, spec_tasks │             │
│  └───────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Data Model

**Spec (Main Entity)**
- id: UUID (PK)
- project_id: UUID (FK)
- title: String(500)
- description: Text
- status: Enum [draft, requirements, design, executing, completed]
- phase: Enum [Requirements, Design, Implementation, Testing, Done]
- progress: Float
- test_coverage: Float
- design: JSONB
- execution: JSONB
- requirements_approved: Boolean
- design_approved: Boolean

**SpecRequirement**
- id: UUID (PK)
- spec_id: UUID (FK)
- title: String
- condition: Text (WHEN clause)
- action: Text (SHALL clause)
- status: Enum [pending, in_progress, completed]

**SpecAcceptanceCriterion**
- id: UUID (PK)
- requirement_id: UUID (FK)
- text: Text
- completed: Boolean

**SpecTask**
- id: UUID (PK)
- spec_id: UUID (FK)
- title: String
- description: Text
- phase: String
- priority: Enum [low, medium, high, critical]
- status: Enum [pending, in_progress, completed]
- dependencies: JSONB

### 4.3 API Spec

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/specs/project/{project_id} | List specs for project |
| POST | /api/v1/specs | Create new spec |
| GET | /api/v1/specs/{spec_id} | Get spec details |
| PATCH | /api/v1/specs/{spec_id} | Update spec |
| DELETE | /api/v1/specs/{spec_id} | Delete spec |
| POST | /api/v1/specs/{spec_id}/requirements | Add requirement |
| PATCH | /api/v1/specs/{spec_id}/requirements/{req_id} | Update requirement |
| DELETE | /api/v1/specs/{spec_id}/requirements/{req_id} | Delete requirement |
| POST | /api/v1/specs/{spec_id}/requirements/{req_id}/criteria | Add criterion |
| PATCH | /api/v1/specs/{spec_id}/requirements/{req_id}/criteria/{id} | Update criterion |
| PUT | /api/v1/specs/{spec_id}/design | Update design |
| POST | /api/v1/specs/{spec_id}/tasks | Add task |
| GET | /api/v1/specs/{spec_id}/tasks | List tasks |
| POST | /api/v1/specs/{spec_id}/approve-requirements | Approve requirements |
| POST | /api/v1/specs/{spec_id}/approve-design | Approve design |

---

## 5. Implementation Tasks

### Phase 1: Test Infrastructure Setup
| Task | Priority | Status |
|------|----------|--------|
| Create specs E2E test file (Playwright) | High | Pending |
| Create MSW handlers for spec API | High | Pending |
| Add spec fixtures to test data | Medium | Pending |

### Phase 2: Frontend E2E Tests
| Task | Priority | Status |
|------|----------|--------|
| Implement specs list page tests | High | Pending |
| Implement spec creation tests | High | Pending |
| Implement spec detail page tests | High | Pending |
| Implement requirements workflow tests | High | Pending |
| Implement design workflow tests | Medium | Pending |
| Implement tasks workflow tests | Medium | Pending |

### Phase 3: Backend E2E Tests
| Task | Priority | Status |
|------|----------|--------|
| Create test_e2e_specs.py | High | Pending |
| Implement CRUD operation tests | High | Pending |
| Implement lifecycle transition tests | High | Pending |
| Implement error handling tests | Medium | Pending |

### Phase 4: Integration Tests
| Task | Priority | Status |
|------|----------|--------|
| Create specs.test.tsx | Medium | Pending |
| Test React Query integration | Medium | Pending |
| Test error boundary handling | Low | Pending |

---

## 6. Success Criteria

The E2E Spec Test After Fix is complete when:

1. **All E2E tests pass**: 100% pass rate on Playwright and pytest E2E tests
2. **Coverage targets met**:
   - Frontend: >80% of spec components covered
   - Backend: >90% of spec API endpoints covered
3. **No route conflicts**: Navigation tests confirm the fix resolved routing issues
4. **Full lifecycle tested**: Complete spec workflow from creation to completion verified
5. **CI/CD integration**: Tests run automatically on PR

---

## 7. Dependencies

- **Frontend Testing Framework**: Playwright (already installed)
- **Backend Testing Framework**: pytest (already configured)
- **Mock Service**: MSW (already configured)
- **Database**: PostgreSQL test database
- **CI/CD**: GitHub Actions (existing)

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Database state pollution | Tests interfere with each other | Use transaction rollback, isolated test databases |
| Flaky tests | CI failures, developer frustration | Implement retry logic, use stable selectors |
| API changes break tests | False negatives | Use MSW mocks consistently, version API contracts |
| Route conflicts reoccur | Deployment failures | Add specific navigation tests as regression guard |

---

## 9. References

- [Frontend Testing Infrastructure Commit](https://github.com/kivo360/omoi-os/commit/0a27af9)
- [Route Fix Commit](https://github.com/kivo360/omoi-os/commit/f3bab41)
- [Backend E2E Testing Plan](/workspace/backend/docs/E2E_TESTING_PLAN.md)
- [Spec API Implementation](/workspace/backend/omoi_os/api/routes/specs.py)
- [Frontend Spec Client](/workspace/frontend/lib/api/specs.ts)
