---
id: TSK-005
title: Update API Routes for Webhook Configuration
status: pending
parent_ticket: TKT-001
estimate: S
created: 2025-12-29
assignee: null
dependencies:
  depends_on:
    - TSK-002
  blocks:
    - TSK-006
---

# TSK-005: Update API Routes for Webhook Configuration

## Objective

Update project and ticket API routes to support reading and updating webhook_url field.

---

## Deliverables

- [ ] `backend/omoi_os/api/routes/projects.py` - Support webhook_url in PATCH
- [ ] `backend/omoi_os/api/routes/tickets.py` - Support webhook_url in PATCH
- [ ] `backend/omoi_os/api/schemas/project.py` - Add webhook_url to schema
- [ ] `backend/omoi_os/api/schemas/ticket.py` - Add webhook_url to schema

---

## Implementation Notes

### Approach

1. Update Pydantic schemas with webhook_url field
2. Update route handlers to accept webhook_url in PATCH
3. Ensure GET responses include webhook_url
4. Add URL validation

### Code Patterns

Add to Pydantic schemas:
```python
class ProjectUpdate(BaseModel):
    # ... existing fields ...
    webhook_url: Optional[str] = Field(None, max_length=2048)

class ProjectResponse(BaseModel):
    # ... existing fields ...
    webhook_url: Optional[str] = None

class TicketUpdate(BaseModel):
    # ... existing fields ...
    webhook_url: Optional[str] = Field(None, max_length=2048)

class TicketResponse(BaseModel):
    # ... existing fields ...
    webhook_url: Optional[str] = None
```

Optional: Add URL validation
```python
from pydantic import HttpUrl, field_validator

class ProjectUpdate(BaseModel):
    webhook_url: Optional[str] = Field(None, max_length=2048)

    @field_validator('webhook_url')
    @classmethod
    def validate_url(cls, v):
        if v is not None and not v.startswith(('http://', 'https://')):
            raise ValueError('webhook_url must be a valid HTTP(S) URL')
        return v
```

### References
- backend/omoi_os/api/routes/projects.py
- backend/omoi_os/api/routes/tickets.py
- Pydantic v2 documentation

---

## Acceptance Criteria

- [ ] PATCH /api/v1/projects/{id} accepts webhook_url
- [ ] PATCH /api/v1/tickets/{id} accepts webhook_url
- [ ] GET responses include webhook_url field
- [ ] Invalid URLs are rejected with 422 status

---

## Testing Requirements

### API Tests
```python
async def test_update_project_webhook_url(client):
    response = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"webhook_url": "https://example.com/webhook"}
    )
    assert response.status_code == 200
    assert response.json()["webhook_url"] == "https://example.com/webhook"

async def test_invalid_url_rejected(client):
    response = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"webhook_url": "not-a-valid-url"}
    )
    assert response.status_code == 422
```

### Edge Cases
- Setting webhook_url to null (should clear it)
- Very long URLs (near 2048 limit)
- URLs with query parameters and fragments

---

## Notes

Schema changes should be backward compatible - webhook_url is optional.
