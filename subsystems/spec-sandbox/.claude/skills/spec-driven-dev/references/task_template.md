# Task Template

Use this template for `.omoi_os/tasks/TSK-{NUM}.md` files.

**IMPORTANT**: All task files MUST include YAML frontmatter for programmatic parsing.

---

## Template

```markdown
---
id: TSK-{NUM}
title: {Task Title}
status: pending  # pending | in_progress | review | done | blocked
parent_ticket: TKT-{NUM}
estimate: M  # S | M | L
created: {YYYY-MM-DD}
assignee: null  # agent-id or null
dependencies:
  depends_on: []  # Task IDs that must complete first
  blocks: []      # Task IDs that cannot start until this completes
---

# TSK-{NUM}: {Task Title}

## Objective

{1-2 sentences describing what this task accomplishes}

---

## Deliverables

- [ ] `{path/to/file1.py}` - {What this file should contain/do}
- [ ] `{path/to/file2.py}` - {What this file should contain/do}
- [ ] `{path/to/test_file.py}` - {Test coverage}

---

## Implementation Notes

### Approach
{Step-by-step approach to implementing this task}

1. {Step 1}
2. {Step 2}
3. {Step 3}

### Code Patterns
{Specific patterns, libraries, or conventions to use}

```python
# Example code pattern
def example_pattern():
    pass
```

### References
- {Link to documentation}
- {Link to similar implementation}
- {Link to design section}

---

## Acceptance Criteria

- [ ] {Specific criterion 1}
- [ ] {Specific criterion 2}
- [ ] All tests pass
- [ ] No linting errors
- [ ] Type hints complete

---

## Testing Requirements

### Unit Tests
```python
# Expected test cases
def test_example():
    # Test {scenario}
    pass
```

### Edge Cases
- {Edge case 1 to handle}
- {Edge case 2 to handle}

---

## Notes

{Additional context, decisions, or warnings}
```

---

## Frontmatter Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique task ID (TSK-001, TSK-FEAT-001) |
| `title` | string | Yes | Human-readable task title |
| `status` | string | Yes | Current status (see Status Definitions) |
| `parent_ticket` | string | Yes | Parent ticket ID |
| `estimate` | string | Yes | T-shirt size (S/M/L) |
| `created` | date | Yes | Creation date (YYYY-MM-DD) |
| `assignee` | string | No | Agent ID or null if unassigned |
| `dependencies.depends_on` | list | No | Task IDs that must complete first |
| `dependencies.blocks` | list | No | Task IDs waiting on this |

---

## Task ID Conventions

### Format
```
TSK-{NUM}
TSK-{PREFIX}-{NUM}
```

### Numbering
- Start at 001
- Increment sequentially
- Can have prefix: `TSK-COLLAB-001`

---

## Status Definitions

| Status | Description |
|--------|-------------|
| `pending` | Not yet started |
| `in_progress` | Currently being worked on |
| `review` | Complete, awaiting review |
| `done` | Completed and verified |
| `blocked` | Cannot proceed |

---

## Estimate Definitions

| Size | Time | Description |
|------|------|-------------|
| `S` | < 2 hours | Simple, straightforward |
| `M` | 2-4 hours | Moderate complexity |
| `L` | 4-8 hours | Complex, may need splitting |

---

## Dependency Rules

1. **No Circular Dependencies**: A task cannot depend on itself or create a cycle
2. **Same Ticket Preferred**: Dependencies should ideally be within the same parent ticket
3. **Cross-Ticket Dependencies**: Use ticket-level `blocked_by` instead when possible
4. **Keep Chains Short**: Prefer max 3-4 levels of task dependency depth

### Example Dependency Graph

```
TSK-001 (Add model fields)
  └─ blocks: TSK-002

TSK-002 (Create migration)
  ├─ depends_on: TSK-001
  └─ blocks: TSK-003, TSK-004

TSK-003 (Implement service)
  ├─ depends_on: TSK-002
  └─ blocks: TSK-005

TSK-004 (Update API routes)
  ├─ depends_on: TSK-002
  └─ blocks: TSK-005

TSK-005 (Add tests)
  └─ depends_on: TSK-003, TSK-004
```

---

## Best Practices

1. **Atomic** - One clear deliverable per task
2. **Self-Contained** - All context needed is in the task
3. **Testable** - Clear acceptance criteria
4. **Time-Boxed** - Should complete in one session (< 8 hours)
5. **Linked** - Always reference parent ticket in frontmatter
6. **Explicit Dependencies** - List all dependencies in frontmatter, not just prose
