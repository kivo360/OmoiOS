# Analytics Setup Guide

This document describes the PostHog analytics integration for the OmoiOS frontend.

## Overview

We use [PostHog](https://posthog.com) for product analytics with the following features enabled:

- **Session Recording** - Watch full user sessions to understand navigation patterns
- **Autocapture** - Automatically track clicks, form submissions, page views
- **Event Tracking** - Custom events for business logic
- **User Identification** - Link sessions to authenticated users
- **Feature Flags** - A/B testing for pricing and features
- **Heatmaps** - Visual click tracking (requires session recording)

## Environment Variables

Add these to your `.env.local` file:

```bash
# Required: Your PostHog project API key
NEXT_PUBLIC_POSTHOG_KEY=phc_your_project_key_here

# Optional: PostHog host (defaults to US cloud)
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com
```

Get your API key from: https://app.posthog.com/project/settings

## File Structure

```
frontend/
├── lib/analytics/
│   ├── index.ts        # Central export for all analytics
│   ├── posthog.ts      # PostHog client initialization
│   ├── events.ts       # Typed event definitions
│   ├── track.ts        # Tracking functions
│   └── identify.ts     # User identification
├── providers/
│   └── PostHogProvider.tsx  # React provider for analytics
└── docs/
    └── analytics-setup.md   # This documentation
```

## Quick Start

### Track an Event

```typescript
import { track, ANALYTICS_EVENTS } from '@/lib/analytics'

// With type-safe properties
track(ANALYTICS_EVENTS.CHECKOUT_STARTED, {
  plan_type: 'pro',
  price_amount: 50,
})

// Or with the flexible trackEvent function
import { trackEvent } from '@/lib/analytics'

trackEvent('custom_event', {
  custom_property: 'value',
})
```

### Identify a User

```typescript
import { identify, identifyUser } from '@/lib/analytics'

// With user ID and properties
identify(user.id, {
  email: user.email,
  plan_type: 'pro',
})

// Or from a User object
import type { User } from '@/lib/api/types'
identifyUser(user, { github_connected: true })
```

### Reset on Logout

```typescript
import { resetUser } from '@/lib/analytics'

// Call on logout to clear user identity
resetUser()
```

## Event Catalog

### Onboarding Events

| Event Name | Description | Properties |
|------------|-------------|------------|
| `onboarding_step_viewed` | User views an onboarding step | `step`, `step_number` |
| `onboarding_step_completed` | User completes an onboarding step | `step`, `step_number` |
| `onboarding_completed` | User finishes onboarding flow | `selected_plan`, `has_first_spec` |
| `first_spec_submitted` | User submits their first spec | `spec_length`, `project_id` |

### Authentication Events

| Event Name | Description | Properties |
|------------|-------------|------------|
| `user_signed_up` | New user registration | `auth_method` |
| `user_logged_in` | User login | `auth_method` |
| `user_logged_out` | User logout | - |
| `github_connected` | GitHub OAuth connected | `username` |

### Billing Events

| Event Name | Description | Properties |
|------------|-------------|------------|
| `checkout_started` | User initiates checkout | `plan_type`, `price_amount` |
| `checkout_completed` | Successful checkout | `plan_type`, `payment_method_type` |
| `checkout_failed` | Failed checkout | `plan_type`, `error_code` |
| `subscription_created` | New subscription | `plan_type` |
| `subscription_cancelled` | Subscription cancelled | `plan_type` |
| `lifetime_purchased` | Lifetime plan purchased | `price_amount` |

### Feature Usage Events

| Event Name | Description | Properties |
|------------|-------------|------------|
| `spec_created` | New spec created | `project_id`, `spec_length` |
| `project_created` | New project created | `project_id`, `github_connected` |
| `sandbox_started` | Sandbox execution started | `sandbox_id`, `project_id` |
| `feature_used` | Generic feature usage | `feature_name`, `action` |

### Error Events

| Event Name | Description | Properties |
|------------|-------------|------------|
| `error_occurred` | Generic error | `error_type`, `error_message` |
| `api_error` | API request failed | `api_endpoint`, `http_status` |

## Adding New Events

1. **Define the event** in `lib/analytics/events.ts`:

```typescript
export const ANALYTICS_EVENTS = {
  // ... existing events
  MY_NEW_EVENT: 'my_new_event',
} as const

// Add property types
export interface MyNewEventProperties extends BaseEventProperties {
  custom_field: string
  optional_field?: number
}

// Add to EventPropertiesMap
export interface EventPropertiesMap {
  // ... existing mappings
  [ANALYTICS_EVENTS.MY_NEW_EVENT]: MyNewEventProperties
}
```

2. **Track the event** in your component:

```typescript
import { track, ANALYTICS_EVENTS } from '@/lib/analytics'

track(ANALYTICS_EVENTS.MY_NEW_EVENT, {
  custom_field: 'value',
  optional_field: 123,
})
```

## User Identification

### Automatic Identification

User identification is handled automatically in `AuthProvider.tsx`:

1. **On Login** - `identifyUser(user)` is called with user properties
2. **On Session Restore** - User is re-identified when session is validated
3. **On Logout** - `resetUser()` and `clearOrganization()` are called

### Manual Identification

```typescript
import { identify, identifyUser } from '@/lib/analytics'

// Identify with user ID and properties
identify(userId, {
  email: 'user@example.com',
  name: 'John Doe',
  plan_type: 'pro',
  github_connected: true,
})

// Or use the User object directly
identifyUser(user, {
  onboarding_completed: true,
})
```

### User Properties

The following properties are tracked for users:

| Property | Type | Description |
|----------|------|-------------|
| `email` | string | User's email address |
| `name` | string | User's display name |
| `plan_type` | string | Subscription tier (free, pro, team, etc.) |
| `github_connected` | boolean | Whether GitHub is connected |
| `is_verified` | boolean | Email verification status |
| `created_at` | string | Account creation timestamp |
| `onboarding_completed` | boolean | Onboarding completion status |

### Organization Context (B2B)

For multi-tenant B2B analytics, set the organization context:

```typescript
import { setOrganization, clearOrganization } from '@/lib/analytics'

// Set organization when user selects/switches org
setOrganization(organizationId, {
  name: 'Acme Corp',
  plan_type: 'team',
  member_count: 10,
})

// Clear on logout or org switch
clearOrganization()
```

Organization context:
- Groups users by organization in PostHog
- Adds `organization_id` and `organization_name` to all events
- Enables B2B analytics dashboards

### Anonymous to Identified User Flow

When an anonymous user signs up:

1. Pre-signup events are tracked with an anonymous ID
2. On signup/login, `identify()` links anonymous events to the user
3. PostHog automatically merges the anonymous and identified profiles

```typescript
// PostHog handles this automatically when you call identify()
// No need to manually call alias()
```

## Session Recording

### Privacy Configuration

Session recording is configured in `lib/analytics/posthog.ts`:

```typescript
session_recording: {
  // Show inputs (except passwords)
  maskAllInputs: false,

  // Always mask password fields
  maskInputOptions: { password: true },
}
```

### Masking Sensitive Elements

Add `data-ph-no-capture` attribute to mask elements:

```html
<input type="text" data-ph-no-capture placeholder="SSN" />
<div data-ph-no-capture>Sensitive content</div>
```

### Watching Recordings

1. Go to PostHog Dashboard → Session Recordings
2. Filter by user, page, or events
3. Click a recording to watch

## Feature Flags

### Checking Feature Flags

```typescript
import { usePostHog } from '@/providers/PostHogProvider'

function MyComponent() {
  const { isFeatureEnabled, getFeatureFlag } = usePostHog()

  // Boolean flag
  if (isFeatureEnabled('new-checkout-flow')) {
    return <NewCheckout />
  }

  // Multivariate flag
  const variant = getFeatureFlag('pricing-test')
  if (variant === 'discount-10') {
    return <DiscountedPricing discount={10} />
  }
}
```

### React Hook for Feature Flags

```typescript
import { useFeatureFlag, useFeatureFlagEnabled } from 'posthog-js/react'

function MyComponent() {
  const isEnabled = useFeatureFlagEnabled('feature-name')
  const variant = useFeatureFlag('experiment-name')
}
```

## Debugging

### Development Mode

In development, PostHog runs in debug mode with console logging:

```
[Analytics] onboarding_step_viewed { step: 'welcome', page_path: '/onboarding' }
```

### PostHog Toolbar

In development, the PostHog toolbar is enabled for:
- Testing feature flags
- Viewing events in real-time
- Inspecting autocapture elements

Access via the PostHog floating button in bottom-right corner.

## Best Practices

1. **Use typed events** - Always use `ANALYTICS_EVENTS` constants
2. **Include context** - Add relevant properties for filtering
3. **Don't track PII** - Avoid tracking passwords, SSNs, credit cards
4. **Test in development** - Verify events appear in console
5. **Identify early** - Call `identify` as soon as user logs in
6. **Reset on logout** - Call `resetUser` to clear session

## Troubleshooting

### Events not appearing

1. Check `NEXT_PUBLIC_POSTHOG_KEY` is set
2. Verify PostHog console logs in browser DevTools
3. Check PostHog dashboard for delayed ingestion

### Session recording not working

1. Ensure session recording is enabled in PostHog project settings
2. Check for browser ad-blockers blocking PostHog
3. Verify the `session_recording` config in `posthog.ts`

### Feature flags not loading

1. Check `onFeatureFlags` callback is registered
2. Verify flags are enabled in PostHog dashboard
3. Check for correct targeting rules

## Resources

- [PostHog Documentation](https://posthog.com/docs)
- [PostHog JS SDK](https://posthog.com/docs/libraries/js)
- [Session Recording Docs](https://posthog.com/docs/session-recording)
- [Feature Flags Docs](https://posthog.com/docs/feature-flags)
