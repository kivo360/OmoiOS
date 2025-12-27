# TSK-001: Add webhook_url to Project and Ticket Models

**Status**: pending
**Parent Ticket**: TKT-001
**Estimate**: S
**Assignee**: (unassigned)

## Objective

Add `webhook_url` field to both Project and Ticket models.

## Deliverables

- [ ] `backend/omoi_os/models/project.py` - Add webhook_url field
- [ ] `backend/omoi_os/models/ticket.py` - Add webhook_url field

## Implementation Notes

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

## Acceptance Criteria

- Fields are nullable strings (max 2048 chars for URLs)
- Include SQLAlchemy comments for documentation
- No breaking changes to existing functionality
