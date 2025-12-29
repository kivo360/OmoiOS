# Ticket Template

Use this template for `.omoi_os/tickets/TKT-{NUM}.md` files.

**IMPORTANT**: All ticket files MUST include YAML frontmatter for programmatic parsing.

---

## Template

```markdown
---
id: TKT-{NUM}
title: {Ticket Title}
status: backlog  # backlog | analyzing | building | testing | done | blocked
priority: MEDIUM  # CRITICAL | HIGH | MEDIUM | LOW
estimate: M  # S | M | L | XL
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
feature: {feature-name}
requirements:
  - REQ-XXX-YYY
design_ref: designs/{feature-name}.md
tasks:
  - TSK-{NUM}
  - TSK-{NUM}
dependencies:
  blocked_by: []  # Tickets that must complete before this can start
  blocks: []      # Tickets that cannot start until this completes
  related: []     # Tickets that are related but not blocking
---

# TKT-{NUM}: {Ticket Title}

## Description

{2-3 paragraph description of what this ticket accomplishes}

### Context
{Why this work is needed, background information}

### Goals
- {Goal 1}
- {Goal 2}

### Non-Goals
- {What this ticket does NOT include}

---

## Acceptance Criteria

- [ ] {Specific, testable criterion 1}
- [ ] {Specific, testable criterion 2}
- [ ] {Specific, testable criterion 3}
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Documentation updated

---

## Technical Notes

### Implementation Approach
{High-level approach to implementing this ticket}

### Key Files
- `{path/to/file1.py}` - {Purpose}
- `{path/to/file2.py}` - {Purpose}

### API Changes
{Summary of API changes if any}

### Database Changes
{Summary of schema changes if any}

---

## Testing Strategy

### Unit Tests
- {What to test}

### Integration Tests
- {What to test}

### Manual Testing
- {Test scenarios}

---

## Rollback Plan

{How to revert changes if something goes wrong}

---

## Notes

{Additional notes, decisions, or context}
```

---

## Frontmatter Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique ticket ID (TKT-001, TKT-FEAT-001) |
| `title` | string | Yes | Human-readable ticket title |
| `status` | string | Yes | Current status (see Status Definitions) |
| `priority` | string | Yes | Priority level (CRITICAL/HIGH/MEDIUM/LOW) |
| `estimate` | string | Yes | T-shirt size (S/M/L/XL) |
| `created` | date | Yes | Creation date (YYYY-MM-DD) |
| `updated` | date | Yes | Last update date (YYYY-MM-DD) |
| `feature` | string | No | Feature name for grouping |
| `requirements` | list | No | Linked requirement IDs |
| `design_ref` | string | No | Path to design document |
| `tasks` | list | No | Child task IDs |
| `dependencies.blocked_by` | list | No | Ticket IDs that must complete first |
| `dependencies.blocks` | list | No | Ticket IDs waiting on this |
| `dependencies.related` | list | No | Related ticket IDs (non-blocking) |

---

## Ticket ID Conventions

### Format
```
TKT-{NUM}
TKT-{PREFIX}-{NUM}
```

### Numbering
- Start at 001 for new projects
- Increment sequentially
- Never reuse deleted numbers
- Can have feature prefix: `TKT-COLLAB-001`

---

## Status Definitions

| Status | Description |
|--------|-------------|
| `backlog` | Ticket created but not yet started |
| `analyzing` | Requirements/design analysis in progress |
| `building` | Implementation in progress |
| `testing` | Testing and validation in progress |
| `done` | Completed and verified |
| `blocked` | Cannot proceed due to dependency or issue |

---

## Priority Definitions

| Priority | Response Time | Description |
|----------|---------------|-------------|
| `CRITICAL` | Immediate | Production-breaking, security issues |
| `HIGH` | 1-2 days | Important feature, significant bug |
| `MEDIUM` | 1 week | Normal priority work |
| `LOW` | Backlog | Nice-to-have, minor improvements |

---

## Estimate Definitions

| Size | Time Range | Complexity |
|------|------------|------------|
| `S` | 1-4 hours | Simple, well-understood |
| `M` | 0.5-2 days | Moderate complexity |
| `L` | 3-5 days | Complex, multiple components |
| `XL` | 1-2 weeks | Very complex, should consider splitting |

---

## Dependency Rules

1. **No Circular Dependencies**: A ticket cannot be blocked by itself or create a cycle
2. **Explicit Over Implicit**: Always list dependencies in frontmatter, not just in prose
3. **Use `related` for Informational Links**: Non-blocking relationships go in `related`
4. **Keep Chains Short**: Prefer max 3-4 levels of dependency depth

### Example Dependency Graph

```
TKT-001 (Infrastructure)
  └─ blocks: TKT-002, TKT-003

TKT-002 (User Model)
  ├─ blocked_by: TKT-001
  └─ blocks: TKT-004

TKT-003 (API Framework)
  ├─ blocked_by: TKT-001
  └─ blocks: TKT-004

TKT-004 (User API)
  └─ blocked_by: TKT-002, TKT-003
```

---

## Best Practices

1. **One Component Per Ticket** - Scope to a single major component or feature slice
2. **Clear Acceptance Criteria** - Every criterion should be testable
3. **Explicit Dependencies** - Document all blockers in frontmatter
4. **Task Breakdown** - Every ticket should have associated tasks in `tasks` field
5. **Traceability** - Always link to requirements and design docs
