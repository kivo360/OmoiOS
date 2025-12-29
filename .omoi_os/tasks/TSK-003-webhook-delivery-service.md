---
id: TSK-003
title: Implement WebhookDeliveryService
status: pending
parent_ticket: TKT-001
estimate: M
created: 2025-12-29
assignee: null
dependencies:
  depends_on:
    - TSK-002
  blocks:
    - TSK-004
    - TSK-006
---

# TSK-003: Implement WebhookDeliveryService

## Objective

Create a reusable HTTP webhook delivery service with retry logic and structured logging.

---

## Deliverables

- [ ] `backend/omoi_os/services/webhook_delivery.py`
- [ ] `backend/tests/unit/services/test_webhook_delivery.py`

---

## Implementation Notes

### Approach

1. Create WebhookDeliveryService class
2. Implement async deliver method with httpx
3. Add retry logic with exponential backoff
4. Add structured logging for all attempts
5. Write unit tests with mocked HTTP

### Code Patterns

Key features:
- HTTP POST with `application/json` content type
- 10 second timeout
- Retry on 5xx errors: 3 attempts with exponential backoff (1s, 2s, 4s)
- No retry on 4xx errors (client error)
- Structured logging for all attempts

Use `httpx.AsyncClient` for async HTTP requests.

```python
class WebhookDeliveryService:
    TIMEOUT_SECONDS = 10.0
    MAX_RETRIES = 3
    RETRY_DELAYS = [1.0, 2.0, 4.0]

    async def deliver(self, url: str, payload: dict) -> bool:
        """Deliver webhook with retry logic.

        Returns True on success, False on failure.
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json=payload)
                    if response.status_code < 400:
                        return True
                    if 400 <= response.status_code < 500:
                        # Client error - don't retry
                        return False
                    # Server error - retry
            except httpx.TimeoutException:
                pass

            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAYS[attempt])

        return False
```

### References
- httpx documentation
- designs/webhook-notifications.md#webhook-delivery

---

## Acceptance Criteria

- [ ] Successful delivery returns True
- [ ] Failed delivery (after retries) returns False
- [ ] All attempts are logged with structured data
- [ ] Timeout is enforced at 10 seconds
- [ ] 5xx errors trigger retry, 4xx do not
- [ ] Exponential backoff: 1s, 2s, 4s between retries

---

## Testing Requirements

### Unit Tests
```python
@respx.mock
async def test_successful_delivery():
    respx.post("https://example.com/hook").respond(200)
    service = WebhookDeliveryService()
    result = await service.deliver("https://example.com/hook", {"test": True})
    assert result is True

@respx.mock
async def test_retry_on_5xx():
    route = respx.post("https://example.com/hook")
    route.side_effect = [httpx.Response(500), httpx.Response(500), httpx.Response(200)]
    # ... verify 3 attempts made
```

### Edge Cases
- Connection refused
- DNS resolution failure
- Very slow responses (timeout)
- Empty payloads

---

## Notes

Use `respx` or `pytest-httpx` for mocking HTTP in tests.
