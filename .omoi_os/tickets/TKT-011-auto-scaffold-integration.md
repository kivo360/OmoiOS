---
id: TKT-011
title: Auto-Scaffold Integration
created: 2026-01-09
updated: 2026-01-09
status: backlog
priority: CRITICAL
type: feature
feature: create-repository
estimate: M
requirements:
  - REQ-CREATE-REPO-FUNC-005
dependencies:
  blocked_by:
    - TKT-010
  blocks: []
---

# TKT-011: Auto-Scaffold Integration

## Objective

Connect the repository creation flow to the existing spec-driven workflow so that after a repo is created, agents automatically scaffold the project based on the user's feature description.

## Scope

### In Scope
- Trigger scaffolding after repo creation
- Pass feature description to spec generation
- Generate Requirements → Design → Tasks from description
- Start agent execution on generated tasks
- Real-time progress updates to user

### Out of Scope
- Changes to existing spec-driven workflow (use as-is)
- New agent types

## Acceptance Criteria

- [ ] After repo creation, if feature_description provided, scaffolding starts
- [ ] System generates spec from feature description
- [ ] Spec follows existing Requirements → Design → Tasks format
- [ ] Tasks are created and assigned to agents
- [ ] User can monitor progress in real-time
- [ ] Scaffolding failures are reported with retry option
- [ ] Progress shown in dashboard immediately after creation

## Technical Notes

- Leverage existing `ProjectService` and spec generation
- Use existing agent orchestration
- Trigger scaffolding as background task (don't block repo creation response)
- WebSocket updates for real-time progress

## Tasks

- TSK-032: Add scaffold trigger to project creation flow
- TSK-033: Connect to existing spec generation
- TSK-034: Implement progress tracking
- TSK-035: Add error handling and retry logic
- TSK-036: Write integration tests

## Estimate

**Size**: M (2-4 hours)
**Rationale**: Mostly integration with existing systems, minimal new code
