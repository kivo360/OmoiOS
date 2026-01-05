# Performance Monitoring with Sentry

This document describes how performance monitoring is configured in the OmoiOS frontend application using Sentry.

## Overview

Sentry performance monitoring captures:
- **Page load transactions** - Automatic tracking of page loads and navigations
- **Custom transactions** - User flows like onboarding and checkout
- **Web Vitals** - Core Web Vitals (LCP, FID, CLS) and other metrics
- **API call timing** - Duration and success rate of API requests
- **Spans** - Individual operations within transactions

## Configuration

Performance monitoring is enabled in `sentry.client.config.ts`:

```typescript
Sentry.init({
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
  profilesSampleRate: 0.1,
})
```

### Sample Rates

| Environment | Transaction Rate | Profile Rate |
|-------------|-----------------|--------------|
| Development | 100% | 0% |
| Production | 10% | 10% |

Adjust these based on your traffic and Sentry plan.

## Automatic Instrumentation

Sentry automatically tracks:

1. **Page navigations** in Next.js App Router
2. **API calls** made via fetch
3. **Browser resources** (scripts, stylesheets, images)
4. **Web Vitals** (LCP, FID, CLS, TTFB, INP)

## Custom Transactions

### User Flow Tracking

Track multi-step user flows like onboarding or checkout:

```typescript
import { trackUserFlow } from "@/lib/sentry/performance"

function OnboardingPage() {
  const flow = trackUserFlow("onboarding", "New User Onboarding")

  const handleStepComplete = (step: string) => {
    flow.startStep(step)
    // ... perform step logic ...
    flow.completeStep()
  }

  const handleComplete = () => {
    flow.finish("ok")
  }

  const handleCancel = () => {
    flow.finish("cancelled")
  }

  return (
    // ... component JSX ...
  )
}
```

### Simple Transaction

For simpler cases:

```typescript
import { startTransaction } from "@/lib/sentry/performance"

async function complexOperation() {
  const transaction = startTransaction("data-import", "Import User Data")

  try {
    // ... perform operation ...
    transaction?.end()
  } catch (error) {
    transaction?.setStatus({ code: 2, message: "error" })
    transaction?.end()
    throw error
  }
}
```

### Measuring Operations

Measure specific operations with automatic timing:

```typescript
import { measureOperation } from "@/lib/sentry/performance"

const result = await measureOperation(
  {
    op: "db.query",
    description: "Fetch user posts",
    data: { userId: "123" },
  },
  async () => {
    return await fetchUserPosts(userId)
  }
)
```

### API Call Tracking

Track API calls with timing:

```typescript
import { trackAPICall } from "@/lib/sentry/performance"

const data = await trackAPICall("POST", "/api/orders", async () => {
  return await createOrder(orderData)
})
```

## Web Vitals

### Automatic Tracking

Sentry automatically captures Core Web Vitals:

| Metric | Description | Good | Needs Improvement | Poor |
|--------|-------------|------|-------------------|------|
| LCP | Largest Contentful Paint | ≤2.5s | ≤4s | >4s |
| FID | First Input Delay | ≤100ms | ≤300ms | >300ms |
| CLS | Cumulative Layout Shift | ≤0.1 | ≤0.25 | >0.25 |
| TTFB | Time to First Byte | ≤800ms | ≤1800ms | >1800ms |
| INP | Interaction to Next Paint | ≤200ms | ≤500ms | >500ms |

### Custom Reporting

Report additional metrics:

```typescript
import { reportWebVital } from "@/lib/sentry/performance"

reportWebVital({
  name: "LCP",
  value: 2100,
  rating: "good",
})
```

## Performance Budgets

### Default Budgets

```typescript
const DEFAULT_BUDGETS = {
  "page.load": { max: 3000, unit: "ms" },
  "api.call": { max: 500, unit: "ms" },
  "bundle.size": { max: 500000, unit: "bytes" },
  LCP: { max: 2500, unit: "ms" },
  FID: { max: 100, unit: "ms" },
  CLS: { max: 0.1, unit: "count" },
}
```

### Checking Budgets

```typescript
import { checkPerformanceBudget } from "@/lib/sentry/performance"

const pageLoadTime = 3500 // ms
const result = checkPerformanceBudget("page.load", pageLoadTime)

if (result.exceeded) {
  console.warn(`Page load exceeded budget: ${result.actual}ms > ${result.budget}ms`)
}
```

## React Integration

### Tracked Callbacks

Create performance-monitored callbacks:

```typescript
import { createTrackedCallback } from "@/lib/sentry/performance"

const handleSubmit = createTrackedCallback("form-submit", async (data) => {
  await submitForm(data)
})
```

## Best Practices

### 1. Track Critical User Flows

Always track flows that affect business metrics:
- Onboarding/signup
- Checkout/payment
- Core feature usage

### 2. Set Appropriate Sample Rates

Balance data granularity with cost:
- Start with 10% in production
- Increase for debugging specific issues
- Use custom sampling for critical flows

### 3. Use Descriptive Names

Transaction and span names should be clear:

```typescript
// Good
startTransaction("checkout-flow", "User Checkout Process")

// Bad
startTransaction("tx1", "")
```

### 4. Don't Over-Instrument

Only track operations that matter:
- API calls (automatic)
- Heavy computations
- Third-party service calls
- User-initiated actions

### 5. Set Performance Budgets

Define and monitor budgets for:
- Page load times
- API response times
- Bundle sizes
- Core Web Vitals

## Viewing Data in Sentry

### Transaction Dashboard

Navigate to **Performance** → **Transactions** to see:
- Transaction duration distribution
- Throughput (transactions per minute)
- Failure rate
- Apdex score

### Web Vitals Dashboard

Navigate to **Performance** → **Web Vitals** to see:
- Real user monitoring data
- Distribution by page
- Trends over time
- Impact analysis

### Trace View

Click on any transaction to see:
- Full trace with all spans
- Timeline visualization
- Associated errors
- User and browser context

## Alerts

Set up performance alerts in Sentry:

1. Go to **Alerts** → **Create Alert**
2. Select **Performance** alert type
3. Configure conditions:
   - Transaction duration exceeds threshold
   - Apdex drops below threshold
   - Error rate increases

Example alert configurations:
- Checkout takes > 5 seconds
- LCP > 4 seconds for more than 5% of users
- API error rate > 1%

## Troubleshooting

### Transactions Not Appearing

1. Verify `tracesSampleRate > 0`
2. Check DSN is configured
3. Ensure transactions are being finished
4. Check for `beforeSendTransaction` filtering

### Missing Spans

1. Verify span is started within an active transaction
2. Check span is properly ended
3. Ensure async operations complete before transaction ends

### High Cardinality Warnings

If seeing "high cardinality" warnings:
1. Normalize transaction names (remove IDs)
2. Use route patterns instead of full URLs
3. Group similar operations

## Resources

- [Sentry Performance Monitoring Docs](https://docs.sentry.io/product/performance/)
- [Web Vitals](https://web.dev/vitals/)
- [Next.js Performance](https://nextjs.org/docs/advanced-features/measuring-performance)
