/**
 * Analytics Module
 *
 * Central export for all analytics functionality.
 *
 * @example
 * ```ts
 * import { track, ANALYTICS_EVENTS, identify } from '@/lib/analytics'
 *
 * // Track an event
 * track(ANALYTICS_EVENTS.CHECKOUT_STARTED, { plan_type: 'pro' })
 *
 * // Identify a user
 * identify(userId, { email: 'user@example.com' })
 * ```
 */

// Core PostHog functionality
export {
  initPostHog,
  isPostHogReady,
  getPostHog,
  posthog,
  capturePageView,
  capturePageLeave,
  startSessionRecording,
  stopSessionRecording,
  isSessionRecordingActive,
  getSessionId,
  getDistinctId,
} from "./posthog";

// Event tracking
export {
  track,
  trackEvent,
  trackPageView,
  trackError,
  trackApiError,
  trackFeature,
} from "./track";

// Event definitions
export {
  ANALYTICS_EVENTS,
  type AnalyticsEventName,
  type EventProperties,
  type BaseEventProperties,
  type OnboardingStepProperties,
  type OnboardingCompletedProperties,
  type ChecklistItemProperties,
  type FirstSpecProperties,
  type CheckoutProperties,
  type CheckoutCompletedProperties,
  type CheckoutFailedProperties,
  type GitHubConnectionProperties,
  type GitHubRepoSelectedProperties,
  type ProjectEventProperties,
  type SpecEventProperties,
  type FeatureUsageProperties,
  type ErrorEventProperties,
  type AuthEventProperties,
  type NavigationEventProperties,
  type OrganizationEventProperties,
} from "./events";

// User identification
export {
  identify,
  identifyUser,
  resetUser,
  setUserProperties,
  setSuperProperties,
  unsetSuperProperties,
  aliasUser,
  setGroup,
  setOrganization,
  clearOrganization,
  type UserProperties,
  type OrganizationProperties,
} from "./identify";
