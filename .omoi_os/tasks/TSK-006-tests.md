---
id: TSK-006
title: Add Unit and Integration Tests
status: pending
parent_ticket: TKT-001
estimate: M
created: 2025-12-29
assignee: null
dependencies:
  depends_on:
    - TSK-003
    - TSK-004
    - TSK-005
  blocks: []
---

# TSK-006: Add Unit and Integration Tests

## Objective

Add comprehensive tests for webhook notification functionality to ensure reliability.

---

## Deliverables

- [ ] `backend/tests/unit/services/test_webhook_delivery.py`
- [ ] `backend/tests/integration/services/test_webhook_notification.py`
- [ ] `backend/tests/integration/api/test_webhook_config.py`

---

## Implementation Notes

### Approach

1. Write unit tests for WebhookDeliveryService (mock HTTP)
2. Write integration tests for WebhookNotificationService (mock delivery)
3. Write API tests for webhook configuration endpoints
4. Ensure >80% coverage for new code

### Test Cases

#### Unit: WebhookDeliveryService

1. `test_successful_delivery` - 200 response returns True
2. `test_retry_on_5xx` - 500 response triggers retry, eventual success
3. `test_no_retry_on_4xx` - 400 response fails immediately
4. `test_timeout_handling` - Timeout triggers retry
5. `test_max_retries_exhausted` - Returns False after 3 failures

#### Integration: WebhookNotificationService

1. `test_task_completed_triggers_webhook` - Event → webhook delivery
2. `test_task_failed_triggers_webhook` - Event → webhook delivery
3. `test_agent_stuck_triggers_webhook` - Event → webhook delivery
4. `test_ticket_url_overrides_project` - Correct URL resolution
5. `test_no_webhook_configured` - No error when URL is None

#### Integration: API

1. `test_update_project_webhook_url` - PATCH project works
2. `test_update_ticket_webhook_url` - PATCH ticket works
3. `test_invalid_url_rejected` - Returns 422 for bad URL

### Code Patterns

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

@respx.mock
async def test_retry_on_5xx():
    route = respx.post("https://example.com/hook")
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(500),
        httpx.Response(200)
    ]
    service = WebhookDeliveryService()
    result = await service.deliver("https://example.com/hook", {"test": True})
    assert result is True
    assert route.call_count == 3
```

### References
- pytest-asyncio documentation
- respx documentation
- Existing test patterns in backend/tests/

---

## Acceptance Criteria

- [ ] All tests pass: `uv run pytest tests/ -k webhook`
- [ ] Coverage > 80% for new code
- [ ] Tests are fast (mock external HTTP)
- [ ] No flaky tests

---

## Testing Requirements

### Run Tests
```bash
cd backend
uv run pytest tests/ -k webhook -v
uv run pytest tests/ -k webhook --cov=omoi_os/services/webhook --cov-report=term-missing
```

### Edge Cases
- Concurrent webhook deliveries
- Large payloads
- Unicode in payloads

---

## Notes

This is the final task - all other webhook tasks must complete first.
