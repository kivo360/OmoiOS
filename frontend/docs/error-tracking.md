# Error Tracking with Sentry

This document describes how error tracking is configured in the OmoiOS frontend application using Sentry.

## Overview

Sentry is configured to capture:
- **JavaScript errors** - Uncaught exceptions and unhandled promise rejections
- **React errors** - Errors caught by error boundaries
- **API errors** - Failed HTTP requests with context
- **Performance data** - Page loads, navigations, Web Vitals
- **Session replays** - Video-like recordings of user sessions (production only)

## Configuration Files

| File | Purpose |
|------|---------|
| `sentry.client.config.ts` | Browser-side error tracking and performance monitoring |
| `sentry.server.config.ts` | Node.js server-side error tracking (SSR, API routes) |
| `sentry.edge.config.ts` | Edge runtime error tracking (middleware) |
| `instrumentation.ts` | Next.js instrumentation for automatic Sentry initialization |
| `next.config.js` | Sentry webpack plugin for source maps |

## Environment Variables

Required for production:

```bash
# Public DSN (safe to expose)
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/yyy

# Environment identifier
NEXT_PUBLIC_SENTRY_ENVIRONMENT=production

# For source map uploads (keep secret)
SENTRY_AUTH_TOKEN=sntrys_xxx
SENTRY_ORG=your-org
SENTRY_PROJECT=your-project
```

## How Errors Are Captured

### Automatic Capturing

Sentry automatically captures:

1. **Uncaught exceptions** - Any unhandled JavaScript errors
2. **Unhandled promise rejections** - Promises that reject without a `.catch()`
3. **Console errors** - `console.error()` calls become breadcrumbs
4. **Network errors** - Failed fetch requests

### React Error Boundaries

Use the `ErrorBoundary` component to catch React errors:

```tsx
import { ErrorBoundary } from "@/components/error-boundary"

function MyPage() {
  return (
    <ErrorBoundary
      category="dashboard"
      context={{ dashboardId: "123" }}
    >
      <Dashboard />
    </ErrorBoundary>
  )
}
```

The global error boundary (`app/global-error.tsx`) catches errors that escape all other boundaries.

### Manual Error Reporting

Report errors manually with additional context:

```tsx
import * as Sentry from "@sentry/nextjs"

try {
  await riskyOperation()
} catch (error) {
  Sentry.captureException(error, {
    tags: {
      "error.category": "payment",
      "error.severity": "critical",
    },
    extra: {
      userId: user.id,
      amount: paymentAmount,
    },
  })
}
```

### User Context

Set user context on login for better error tracking:

```tsx
import * as Sentry from "@sentry/nextjs"

// On successful login
Sentry.setUser({
  id: user.id,
  email: hashEmail(user.email), // Hash for privacy
  username: user.name,
})

// On logout
Sentry.setUser(null)
```

## Adding Breadcrumbs

Breadcrumbs are events that happened before an error:

```tsx
import * as Sentry from "@sentry/nextjs"

// Navigation breadcrumb
Sentry.addBreadcrumb({
  category: "navigation",
  message: "User navigated to checkout",
  level: "info",
})

// API breadcrumb
Sentry.addBreadcrumb({
  category: "api",
  message: "POST /api/orders",
  level: "info",
  data: {
    status: 200,
    duration: 150,
  },
})

// User action breadcrumb
Sentry.addBreadcrumb({
  category: "user",
  message: "Clicked submit button",
  level: "info",
})
```

## Source Maps

Source maps are automatically uploaded during production builds when `SENTRY_AUTH_TOKEN` is configured. This allows Sentry to show the original TypeScript code in stack traces instead of minified JavaScript.

### Build Process

1. During `next build`, Sentry webpack plugin generates source maps
2. Source maps are uploaded to Sentry with the release version
3. Source maps are deleted from the build output (security)

### Verifying Source Maps

1. Go to Sentry → Releases → [your release]
2. Check "Source Maps" tab for uploaded files
3. Trigger a test error and verify stack trace shows TypeScript

## Testing Error Capture Locally

### 1. Enable Development Mode

```bash
# In .env.local
NEXT_PUBLIC_SENTRY_DSN=your-dsn
NEXT_PUBLIC_SENTRY_DEBUG=true
```

### 2. Trigger a Test Error

```tsx
// Add a button to any page
<button onClick={() => {
  throw new Error("Test error from button click")
}}>
  Trigger Test Error
</button>
```

### 3. Check Console Output

In development, errors are logged to the console instead of sent to Sentry. Look for `[Sentry] Error captured (dev mode):`.

### 4. Send to Sentry (Development)

To actually send errors in development:

```bash
# Force production mode
NODE_ENV=production npm run build && npm run start
```

## Error Categories

Use these standard categories for filtering in Sentry:

| Category | Description |
|----------|-------------|
| `api` | API/network errors |
| `validation` | Form/input validation errors |
| `auth` | Authentication/authorization errors |
| `network` | Network connectivity issues |
| `render` | React rendering errors |
| `user` | User-initiated actions that failed |

## Filtering Errors

### In Sentry UI

Use these search queries:

- All API errors: `error.category:api`
- All auth errors: `error.category:auth`
- Critical errors: `error.severity:fatal`
- Specific user: `user.id:xxx`

### Ignoring Errors

Common errors are ignored in `sentry.client.config.ts`:

- Browser extension errors
- Network errors (handled gracefully)
- Third-party script errors
- React hydration warnings

## Performance Monitoring

See `docs/performance-monitoring.md` for details on:
- Transaction sampling rates
- Custom transactions for user flows
- Web Vitals tracking
- Performance alerts

## Troubleshooting

### Errors Not Appearing in Sentry

1. Check `NEXT_PUBLIC_SENTRY_DSN` is set correctly
2. Verify `beforeSend` isn't filtering your error
3. Check browser console for Sentry initialization errors
4. In development, errors are only logged (not sent)

### Source Maps Not Working

1. Verify `SENTRY_AUTH_TOKEN` has correct permissions
2. Check `SENTRY_ORG` and `SENTRY_PROJECT` match Sentry settings
3. Ensure release version matches between build and Sentry

### High Error Volume

1. Review `ignoreErrors` list in config
2. Add sampling for high-frequency errors
3. Set up Sentry rate limits in project settings

## Best Practices

1. **Always add context** - Include user ID, feature flags, relevant state
2. **Use categories** - Makes filtering much easier
3. **Don't catch and silence** - Catch, report, then handle gracefully
4. **Test locally first** - Verify errors are captured before deploying
5. **Monitor trends** - Set up alerts for error rate spikes
