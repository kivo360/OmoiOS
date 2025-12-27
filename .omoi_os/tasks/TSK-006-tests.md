# TSK-006: Add Unit and Integration Tests

**Status**: pending
**Parent Ticket**: TKT-001
**Estimate**: M
**Assignee**: (unassigned)
**Depends On**: TSK-003, TSK-004, TSK-005

## Objective

Add comprehensive tests for webhook notification functionality.

## Deliverables

- [ ] `backend/tests/unit/services/test_webhook_delivery.py`
- [ ] `backend/tests/integration/services/test_webhook_notification.py`
- [ ] `backend/tests/integration/api/test_webhook_config.py`

## Test Cases

### Unit: WebhookDeliveryService

1. `test_successful_delivery` - 200 response returns True
2. `test_retry_on_5xx` - 500 response triggers retry, eventual success
3. `test_no_retry_on_4xx` - 400 response fails immediately
4. `test_timeout_handling` - Timeout triggers retry
5. `test_max_retries_exhausted` - Returns False after 3 failures

### Integration: WebhookNotificationService

1. `test_task_completed_triggers_webhook` - Event → webhook delivery
2. `test_task_failed_triggers_webhook` - Event → webhook delivery
3. `test_agent_stuck_triggers_webhook` - Event → webhook delivery
4. `test_ticket_url_overrides_project` - Correct URL resolution
5. `test_no_webhook_configured` - No error when URL is None

### Integration: API

1. `test_update_project_webhook_url` - PATCH project works
2. `test_update_ticket_webhook_url` - PATCH ticket works
3. `test_invalid_url_rejected` - Returns 422 for bad URL

## Implementation Notes

Use `respx` or `pytest-httpx` for mocking HTTP requests.

```python
import respx
import httpx

@respx.mock
async def test_successful_delivery():
    respx.post("https://example.com/hook").respond(200)
    service = WebhookDeliveryService()
    result = await service.deliver("https://example.com/hook", {"test": True})
    assert result is True
```

## Acceptance Criteria

- All tests pass: `uv run pytest tests/ -k webhook`
- Coverage > 80% for new code
- Tests are fast (mock external HTTP)
