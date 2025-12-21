# Ticket Template

Use this template for `.omoi_os/tickets/TKT-{NUM}.md` files.

---

```markdown
# TKT-{NUM}: {Ticket Title}

**Status**: backlog | analyzing | building | testing | done | blocked
**Priority**: CRITICAL | HIGH | MEDIUM | LOW
**Estimate**: S | M | L | XL
**Created**: {YYYY-MM-DD}
**Updated**: {YYYY-MM-DD}

## Traceability

**Requirements**: {REQ-XXX-YYY, REQ-XXX-YYY}
**Design Reference**: {designs/feature-name.md#section}
**Feature**: {feature-name}

---

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

## Dependencies

### Blocks
{Tickets that cannot start until this completes}
- {TKT-XXX: Reason}

### Blocked By
{Tickets that must complete before this can start}
- {TKT-XXX: Reason}

### Related
{Tickets that are related but not blocking}
- {TKT-XXX: Relationship}

---

## Tasks

| Task ID | Description | Status | Assignee |
|---------|-------------|--------|----------|
| TSK-{NUM} | {Task description} | pending | - |
| TSK-{NUM} | {Task description} | pending | - |
| TSK-{NUM} | {Task description} | pending | - |

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

---

## History

| Date | Action | By |
|------|--------|-----|
| {YYYY-MM-DD} | Created | {Author} |
| {YYYY-MM-DD} | {Action} | {Author} |
```

---

## Ticket ID Conventions

### Format
```
TKT-{NUM}
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

## Best Practices

1. **One Component Per Ticket** - Scope to a single major component or feature slice
2. **Clear Acceptance Criteria** - Every criterion should be testable
3. **Explicit Dependencies** - Document all blockers and blocked tickets
4. **Task Breakdown** - Every ticket should have associated tasks
5. **Traceability** - Always link to requirements and design docs
