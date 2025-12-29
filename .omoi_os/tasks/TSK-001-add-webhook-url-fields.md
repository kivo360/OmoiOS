---
id: TSK-001
title: Add webhook_url to Project and Ticket Models
status: pending
parent_ticket: TKT-001
estimate: S
created: 2025-12-29
assignee: null
dependencies:
  depends_on: []
  blocks:
    - TSK-002
---

# TSK-001: Add webhook_url to Project and Ticket Models

## Objective

Add `webhook_url` field to both Project and Ticket models to enable webhook configuration.

---

## Deliverables

- [ ] `backend/omoi_os/models/project.py` - Add webhook_url field
- [ ] `backend/omoi_os/models/ticket.py` - Add webhook_url field

---

## Implementation Notes

### Approach

1. Add webhook_url field to Project model
2. Add webhook_url field to Ticket model
3. Verify models import correctly

### Code Patterns

Add to Project model (after line 68 in project.py):
```python
webhook_url: Mapped[Optional[str]] = mapped_column(
    String(2048),
    nullable=True,
    comment="Webhook URL for project-level notifications"
)
```

Add to Ticket model (after context_summary field):
```python
webhook_url: Mapped[Optional[str]] = mapped_column(
    String(2048),
    nullable=True,
    comment="Webhook URL override (takes precedence over project webhook)"
)
```

### References
- designs/webhook-notifications.md#data-model

---

## Acceptance Criteria

- [ ] Fields are nullable strings (max 2048 chars for URLs)
- [ ] Include SQLAlchemy comments for documentation
- [ ] No breaking changes to existing functionality
- [ ] Models import without errors

---

## Testing Requirements

### Unit Tests
```python
def test_project_webhook_url_field():
    project = Project(name="test")
    project.webhook_url = "https://example.com/webhook"
    assert project.webhook_url == "https://example.com/webhook"
```

### Edge Cases
- None/null values should be allowed
- Long URLs (up to 2048 chars) should work

---

## Notes

This is a model-only change. Database migration is handled in TSK-002.
