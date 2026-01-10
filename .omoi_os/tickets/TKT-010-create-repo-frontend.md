---
id: TKT-010
title: Create Repository Frontend Components
created: 2026-01-09
updated: 2026-01-09
status: backlog
priority: HIGH
type: feature
feature: create-repository
estimate: L
requirements:
  - REQ-CREATE-REPO-FUNC-008
  - REQ-CREATE-REPO-FUNC-001
  - REQ-CREATE-REPO-FUNC-002
  - REQ-CREATE-REPO-FUNC-004
dependencies:
  blocked_by:
    - TKT-007
    - TKT-008
    - TKT-009
  blocks:
    - TKT-011
---

# TKT-010: Create Repository Frontend Components

## Objective

Build the frontend UI for creating and deleting repositories, integrated into the existing project connection flow as a tabbed interface.

## Scope

### In Scope
- `ProjectCreationModal` with tabs (Create New / Connect Existing)
- `CreateRepoForm` component with all fields
- Owner selector (personal + orgs)
- Repo name input with availability indicator
- Template selector
- Visibility toggle
- Feature description textarea
- Delete confirmation dialog
- API integration hooks

### Out of Scope
- Bulk operations
- Advanced org management

## Acceptance Criteria

- [ ] Project creation modal has two tabs: "Create New" and "Connect Existing"
- [ ] Owner dropdown shows personal account + organizations
- [ ] Repo name input validates in real-time with availability check
- [ ] Green check when available, red X when taken, with suggestion
- [ ] Template selection as radio buttons or card grid
- [ ] Private/Public toggle
- [ ] Feature description textarea for auto-scaffold
- [ ] Submit button disabled until valid
- [ ] Loading states during creation
- [ ] Error handling with clear messages
- [ ] Delete button in project settings with confirmation dialog
- [ ] Responsive design

## Technical Notes

- Use ShadCN UI components (Dialog, Tabs, Select, Input, RadioGroup)
- Debounce availability check (300ms)
- Use React Query for API calls
- Show toast notifications for success/error

## Tasks

- TSK-024: Create ProjectCreationModal with tabs
- TSK-025: Implement CreateRepoForm component
- TSK-026: Build owner selector with avatars
- TSK-027: Build repo name input with availability
- TSK-028: Build template selector component
- TSK-029: Implement delete confirmation dialog
- TSK-030: Add API hooks for repo operations
- TSK-031: Write component tests

## Estimate

**Size**: L (4-8 hours)
**Rationale**: Multiple components, form validation, API integration
