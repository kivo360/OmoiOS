// PostHog analytics module
// See frontend/docs/analytics-setup.md for documentation

export { posthog, initPostHog, isPostHogEnabled } from "./posthog"

export {
  // Event tracking
  trackEvent,
  identifyUser,
  resetUser,
  setUserProperties,
  incrementUserProperty,
  setGroup,

  // Feature flags
  isFeatureEnabled,
  getFeatureFlag,
  reloadFeatureFlags,

  // Privacy controls
  optOut,
  optIn,
  hasOptedOut,

  // Types
  type AnalyticsEvent,
  type UserEvent,
  type ProjectEvent,
  type SpecEvent,
  type AgentEvent,
  type BillingEvent,
  type NavigationEvent,
  type EventProperties,
} from "./events"
