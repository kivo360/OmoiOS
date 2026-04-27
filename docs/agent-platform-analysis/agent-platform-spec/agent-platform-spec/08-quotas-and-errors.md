# 08 · Quotas & Errors

Multi-tenant means noisy neighbors. Every resource has a quota; every breach has a predictable error code. Codes are stable; messages are not.

## Limit dimensions

| Limit | Enforcement |
|---|---|
| `concurrent_sessions` | hard; 429 on exceed |
| `sessions_per_minute` | token-bucket; 429 w/ `Retry-After` |
| `monthly_compute_seconds` | soft warn at 80 %, hard 429 at 100 % |
| `monthly_tokens_(in/out)` | same |
| `sandbox_egress_mb_per_session` | hard; session fails with `reason: egress_limit` |
| `environment_image_size_gb` | hard; build fails |

## Error envelope

```json
{
  "error": {
    "code":    "quota_exceeded",
    "type":    "rate_limit",
    "message": "concurrent session limit (20) exceeded for org_2fJxKk9",
    "param":   "concurrent_sessions",
    "retry_after_seconds": 12,
    "request_id": "req_01HW…",
    "docs_url":   "https://docs.example.com/errors/quota_exceeded"
  }
}
```

## Stable error codes

| Code | HTTP | Meaning |
|---|---|---|
| `invalid_request` | 400 | Schema violation; `param` is the field. |
| `unauthenticated` | 401 | Missing/bad token. |
| `forbidden` | 403 | Valid token, wrong tenant or missing scope. |
| `not_found` | 404 | Resource doesn't exist in this tenant. |
| `conflict` | 409 | Idempotency-key collision or state conflict. |
| `quota_exceeded` | 429 | See `retry_after_seconds`. |
| `environment_build_failed` | 422 | Dockerfile build error; details in `data`. |
| `egress_denied` | 451 | Sandbox tried to reach a non-allowlisted host. |
| `sandbox_timeout` | 408 | Session hit `resources.timeout_sec`. |
| `internal_error` | 500 | We're paged. |
