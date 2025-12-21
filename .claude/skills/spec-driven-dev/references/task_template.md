# Task Template

Use this template for `.omoi_os/tasks/TSK-{NUM}.md` files.

---

```markdown
# TSK-{NUM}: {Task Title}

**Status**: pending | in_progress | review | done | blocked
**Parent Ticket**: TKT-{NUM}
**Estimate**: S | M | L
**Created**: {YYYY-MM-DD}
**Assignee**: {agent-id | unassigned}

---

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

## Dependencies

**Requires**:
- {TSK-XXX complete}
- {File/module exists}

**Provides**:
- {What other tasks need from this}

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

---

## History

| Date | Action | By |
|------|--------|-----|
| {YYYY-MM-DD} | Created | {Author} |
```

---

## Task ID Conventions

### Format
```
TSK-{NUM}
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

## Best Practices

1. **Atomic** - One clear deliverable per task
2. **Self-Contained** - All context needed is in the task
3. **Testable** - Clear acceptance criteria
4. **Time-Boxed** - Should complete in one session (< 8 hours)
5. **Linked** - Always reference parent ticket
