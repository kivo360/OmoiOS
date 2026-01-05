# Sentry Backend Setup

This document describes the Sentry integration for error tracking and performance monitoring in the OmoiOS backend.

## Overview

Sentry is integrated into the FastAPI backend to provide:

- **Exception Tracking**: Automatic capture of both sync and async exceptions
- **Performance Monitoring**: Distributed tracing with transaction and span tracking
- **PII Filtering**: Automatic redaction of sensitive data before sending to Sentry
- **Database Monitoring**: SQLAlchemy query tracking with timing information
- **External API Tracing**: HTTP client calls are automatically instrumented

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SENTRY_DSN` | Sentry project DSN (required for Sentry to work) | None |
| `SENTRY_ENVIRONMENT` | Environment name (development, staging, production) | development |
| `SENTRY_RELEASE` | Release version (auto-detected from git) | None |
| `SENTRY_TRACES_SAMPLE_RATE` | Transaction sampling rate (0.0-1.0) | 0.1 |
| `SENTRY_PROFILES_SAMPLE_RATE` | Profile sampling rate (0.0-1.0) | 0.1 |
| `SENTRY_DEBUG` | Enable debug logging | false |
| `SENTRY_SEND_DEFAULT_PII` | Allow PII in events (dev only) | false |

### Example Configuration

```bash
# Production
export SENTRY_DSN="https://xxx@sentry.io/123"
export SENTRY_ENVIRONMENT="production"
export SENTRY_TRACES_SAMPLE_RATE="0.1"

# Development (higher sample rate, debug enabled)
export SENTRY_DSN="https://xxx@sentry.io/123"
export SENTRY_ENVIRONMENT="development"
export SENTRY_TRACES_SAMPLE_RATE="1.0"
export SENTRY_DEBUG="true"
```

## Features

### Automatic Instrumentation

The following are automatically instrumented:

1. **FastAPI Routes**: All HTTP endpoints are traced
2. **SQLAlchemy Queries**: Database queries appear as spans with timing
3. **HTTPX Clients**: Outbound HTTP requests are traced
4. **Redis Operations**: Cache operations are traced

### PII Filtering

The `filter_pii` function automatically redacts sensitive data:

- **Sensitive Keys**: password, token, api_key, secret, authorization, etc.
- **PII Patterns**: Email addresses, credit cards, phone numbers, SSN
- **Request Data**: Headers, body, query strings are scrubbed
- **User Data**: Only user ID is kept, email/username are redacted
- **Exception Values**: PII patterns are removed from error messages

### Custom Tracing

Use the tracing decorators for custom instrumentation:

```python
from omoi_os.observability import trace_external_api, trace_operation

# Trace external API calls
@trace_external_api("github")
async def fetch_repo_info(repo: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/repos/{repo}")
        return response.json()

# Trace any operation
@trace_operation("db", "complex_aggregation")
async def get_monthly_stats(org_id: str) -> dict:
    # Complex database operation
    pass
```

### Manual Error Capture

```python
from omoi_os.observability import capture_exception, capture_message, set_user

# Capture an exception with context
try:
    risky_operation()
except Exception as e:
    capture_exception(e, user_id=user_id, operation="risky_operation")

# Capture a message
capture_message("Important event occurred", level="info", data={"key": "value"})

# Set user context for the current scope
set_user(user_id="123", email="user@example.com")
```

## Transaction Sampling

The custom sampler (`_traces_sampler`) filters out noisy transactions:

- **Always Skip**: Health checks, static files, internal endpoints
- **Higher Rate**: Webhook endpoints (2x configured rate)
- **Default**: All other endpoints use configured rate

## Troubleshooting

### Sentry Not Capturing Events

1. Verify `SENTRY_DSN` is set correctly
2. Check Sentry debug output with `SENTRY_DEBUG=true`
3. Ensure the DSN is for the correct project
4. Check network connectivity to Sentry

### Missing Stack Traces

1. Ensure `attach_stacktrace` is true (default)
2. Check if exceptions are being caught and re-raised properly
3. Verify the exception is not being swallowed

### Performance Issues

1. Reduce `traces_sample_rate` if capturing too many transactions
2. Check `profiles_sample_rate` for profiling overhead
3. Review custom spans for excessive instrumentation

### PII Leaking

1. Review `filter_pii` function for missing patterns
2. Add new sensitive keys to `SENSITIVE_KEYS` set
3. Ensure `SENTRY_SEND_DEFAULT_PII` is false in production

## Integration Points

### FastAPI Main

Sentry is initialized at module load time in `api/main.py`:

```python
from omoi_os.observability.sentry import init_sentry
init_sentry()
```

### Exception Handlers

The general exception handler captures unhandled exceptions:

```python
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    import sentry_sdk
    with sentry_sdk.push_scope() as scope:
        scope.set_context("request", {...})
        sentry_sdk.capture_exception(exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

## Best Practices

1. **Use structured context**: Add meaningful tags and context data
2. **Don't over-instrument**: Focus on critical paths and external calls
3. **Test PII filtering**: Verify sensitive data is redacted in Sentry events
4. **Set appropriate sample rates**: Balance visibility with cost/performance
5. **Use breadcrumbs**: Add breadcrumbs for debugging complex flows
