# TSK-003: Implement WebhookDeliveryService

**Status**: pending
**Parent Ticket**: TKT-001
**Estimate**: M
**Assignee**: (unassigned)

## Objective

Create a reusable HTTP webhook delivery service with retry logic.

## Deliverables

- [ ] `backend/omoi_os/services/webhook_delivery.py`
- [ ] `backend/tests/unit/services/test_webhook_delivery.py`

## Implementation Notes

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
        # Implementation per design doc
```

## Acceptance Criteria

- Successful delivery returns True
- Failed delivery (after retries) returns False
- All attempts are logged with structured data
- Timeout is enforced at 10 seconds
- 5xx errors trigger retry, 4xx do not
