# PostHog Analytics Setup

This document describes how to use PostHog analytics in the OmoiOS frontend.

## Features

- **Session Recording** - Watch full user sessions to see exactly what users click and how they navigate
- **Autocapture** - Automatically tracks all clicks, form submissions, and page views
- **Custom Events** - Track business-specific events with typed definitions
- **User Identification** - Link sessions to authenticated users
- **Feature Flags** - A/B test features and pricing
- **Heatmaps** - See where users click most (requires session recording)

## Environment Variables

Add these to your `.env.local`:

```bash
# Required - Get from https://app.posthog.com/project/settings
NEXT_PUBLIC_POSTHOG_KEY=phc_your_project_key

# Optional - defaults to US cloud
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com

# Optional - enable session recording in development
NEXT_PUBLIC_POSTHOG_RECORD_DEV=true
```

## Quick Start

### Tracking Events

```typescript
import { trackEvent } from "@/lib/analytics"

// Track a custom event
trackEvent("project_created", {
  project_id: "123",
  project_name: "My Project",
})

// Track with typed events
trackEvent("billing_checkout_started", {
  plan_name: "Pro",
  billing_period: "monthly",
})
```

### Identifying Users

Call after login to link sessions to users:

```typescript
import { identifyUser, resetUser } from "@/lib/analytics"

// After login
identifyUser(user.id, {
  email: user.email,
  name: user.name,
  plan: user.subscription?.plan,
})

// After logout
resetUser()
```

### Feature Flags

```typescript
import { isFeatureEnabled, getFeatureFlag } from "@/lib/analytics"

// Boolean flag
if (isFeatureEnabled("new-pricing-page")) {
  // Show new pricing
}

// Multivariate flag
const variant = getFeatureFlag("pricing-experiment")
if (variant === "variant-a") {
  // Show variant A
}
```

## Event Types

All events are typed in `lib/analytics/events.ts`:

| Category | Events |
|----------|--------|
| User | `user_signed_up`, `user_logged_in`, `user_logged_out`, `user_onboarding_started`, `user_onboarding_completed` |
| Project | `project_created`, `project_updated`, `project_deleted`, `project_github_connected` |
| Spec | `spec_created`, `spec_updated`, `spec_submitted`, `spec_approved`, `spec_rejected` |
| Agent | `agent_spawned`, `agent_task_started`, `agent_task_completed`, `agent_task_failed` |
| Billing | `billing_checkout_started`, `billing_checkout_completed`, `billing_subscription_created`, `billing_subscription_cancelled` |
| Navigation | `page_viewed`, `feature_used`, `cta_clicked`, `modal_opened` |

## Adding New Events

1. Add the event type to `lib/analytics/events.ts`:

```typescript
export type MyNewEvent = "my_new_event" | "another_event"

// Add to AnalyticsEvent union
export type AnalyticsEvent = ... | MyNewEvent
```

2. Optionally add typed properties:

```typescript
export interface MyNewEventProperties extends BaseEventProperties {
  custom_field: string
  count: number
}
```

3. Use in your component:

```typescript
trackEvent("my_new_event", { custom_field: "value", count: 42 })
```

## Session Recording Configuration

Session recording is configured in `lib/analytics/posthog.ts`:

```typescript
session_recording: {
  // Show input values (helps understand user intent)
  maskAllInputs: false,

  // Always mask passwords
  maskInputOptions: { password: true },

  // Mask elements with data-ph-no-capture attribute
  maskTextSelector: "[data-ph-no-capture]",
}
```

### Masking Sensitive Data

Add the `data-ph-no-capture` attribute to mask content in recordings:

```tsx
<div data-ph-no-capture>
  Credit Card: **** **** **** 1234
</div>
```

Passwords are automatically masked. Other sensitive inputs can be masked:

```tsx
<input type="text" data-ph-no-capture placeholder="SSN" />
```

## Watching Session Recordings

1. Go to [PostHog Dashboard](https://app.posthog.com)
2. Navigate to **Recordings** in the sidebar
3. Filter by user, date, or specific events
4. Click a session to watch the full replay

Tips for debugging:
- Use filters to find sessions with specific errors
- Look at the event timeline to see what actions led to issues
- Check console errors visible in recordings

## Privacy & GDPR

### Opt-out Users

```typescript
import { optOut, optIn, hasOptedOut } from "@/lib/analytics"

// Opt user out of all tracking
optOut()

// Opt user back in
optIn()

// Check status
if (hasOptedOut()) {
  // User has opted out
}
```

### Do Not Track

PostHog respects the browser's DNT setting:

```typescript
// In posthog.ts config
respect_dnt: true
```

## Development

### Debug Mode

In development, PostHog runs in debug mode. Check browser console for:
- `[PostHog] Initialized` - confirms initialization
- `[Analytics] event_name` - logs all tracked events

### Testing Feature Flags

Add `?__posthog_debug=true` to any URL to open the PostHog toolbar and test feature flags.

### Disable Recording in Dev

Session recording is disabled in development by default. Enable with:

```bash
NEXT_PUBLIC_POSTHOG_RECORD_DEV=true
```

## Architecture

```
frontend/
├── lib/analytics/
│   ├── index.ts       # Public exports
│   ├── posthog.ts     # PostHog initialization
│   └── events.ts      # Event types and tracking functions
├── providers/
│   └── PostHogProvider.tsx  # React provider with pageview tracking
└── app/layout.tsx     # Provider integration
```

## Troubleshooting

### Events not appearing in dashboard

1. Check `NEXT_PUBLIC_POSTHOG_KEY` is set correctly
2. Check browser console for initialization message
3. Wait a few seconds - events batch before sending
4. Check browser network tab for `posthog.com/capture` requests

### Session recordings not working

1. Ensure `NEXT_PUBLIC_POSTHOG_KEY` is set
2. In dev, set `NEXT_PUBLIC_POSTHOG_RECORD_DEV=true`
3. Check PostHog dashboard Recordings settings
4. Session recording requires a valid PostHog plan

### Autocapture not tracking button clicks

1. Ensure buttons have text content or aria-labels
2. Check the element isn't inside a `data-ph-no-capture` container
3. Try adding `data-ph-capture-attribute-action="my-action"` to the element

## Resources

- [PostHog Docs](https://posthog.com/docs)
- [Next.js Integration Guide](https://posthog.com/docs/libraries/next-js)
- [Session Recording](https://posthog.com/docs/session-replay)
- [Feature Flags](https://posthog.com/docs/feature-flags)
