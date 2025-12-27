# TSK-005: Update API Routes for Webhook Configuration

**Status**: pending
**Parent Ticket**: TKT-001
**Estimate**: S
**Assignee**: (unassigned)
**Depends On**: TSK-001, TSK-002

## Objective

Update project and ticket API routes to support webhook_url field.

## Deliverables

- [ ] `backend/omoi_os/api/routes/projects.py` - Support webhook_url in PATCH
- [ ] `backend/omoi_os/api/routes/tickets.py` - Support webhook_url in PATCH
- [ ] `backend/omoi_os/api/schemas/project.py` - Add webhook_url to schema
- [ ] `backend/omoi_os/api/schemas/ticket.py` - Add webhook_url to schema

## Implementation Notes

Add to Pydantic schemas:
```python
class ProjectUpdate(BaseModel):
    # ... existing fields ...
    webhook_url: Optional[str] = Field(None, max_length=2048)

class TicketUpdate(BaseModel):
    # ... existing fields ...
    webhook_url: Optional[str] = Field(None, max_length=2048)
```

Optional: Add URL validation
```python
from pydantic import HttpUrl

webhook_url: Optional[HttpUrl] = None
```

## Acceptance Criteria

- PATCH /api/v1/projects/{id} accepts webhook_url
- PATCH /api/v1/tickets/{id} accepts webhook_url
- GET responses include webhook_url field
- Invalid URLs are rejected with 422
