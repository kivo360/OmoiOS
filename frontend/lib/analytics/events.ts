import { posthog, isPostHogEnabled } from "./posthog"

// ============================================================================
// Event Type Definitions
// ============================================================================

// User lifecycle events
export type UserEvent =
  | "user_signed_up"
  | "user_logged_in"
  | "user_logged_out"
  | "user_profile_updated"
  | "user_onboarding_started"
  | "user_onboarding_completed"
  | "user_onboarding_step_completed"

// Project events
export type ProjectEvent =
  | "project_created"
  | "project_updated"
  | "project_deleted"
  | "project_github_connected"
  | "project_settings_changed"

// Spec events
export type SpecEvent =
  | "spec_created"
  | "spec_updated"
  | "spec_submitted"
  | "spec_approved"
  | "spec_rejected"

// Agent events
export type AgentEvent =
  | "agent_spawned"
  | "agent_task_started"
  | "agent_task_completed"
  | "agent_task_failed"
  | "agent_intervention_required"

// Billing events
export type BillingEvent =
  | "billing_checkout_started"
  | "billing_checkout_completed"
  | "billing_subscription_created"
  | "billing_subscription_cancelled"
  | "billing_payment_failed"
  | "billing_plan_upgraded"
  | "billing_plan_downgraded"

// Navigation events
export type NavigationEvent =
  | "page_viewed"
  | "feature_used"
  | "cta_clicked"
  | "modal_opened"
  | "modal_closed"

// All event types
export type AnalyticsEvent =
  | UserEvent
  | ProjectEvent
  | SpecEvent
  | AgentEvent
  | BillingEvent
  | NavigationEvent

// ============================================================================
// Event Properties Types
// ============================================================================

export interface BaseEventProperties {
  timestamp?: string
  source?: "web" | "api" | "webhook"
}

export interface UserEventProperties extends BaseEventProperties {
  user_id?: string
  email?: string
  plan?: string
}

export interface ProjectEventProperties extends BaseEventProperties {
  project_id?: string
  project_name?: string
  has_github?: boolean
}

export interface SpecEventProperties extends BaseEventProperties {
  spec_id?: string
  project_id?: string
  spec_type?: string
}

export interface AgentEventProperties extends BaseEventProperties {
  agent_id?: string
  task_type?: string
  duration_ms?: number
  error_message?: string
}

export interface BillingEventProperties extends BaseEventProperties {
  plan_name?: string
  plan_id?: string
  amount?: number
  currency?: string
  billing_period?: "monthly" | "yearly"
}

export interface NavigationEventProperties extends BaseEventProperties {
  page_path?: string
  feature_name?: string
  cta_name?: string
  modal_name?: string
}

export type EventProperties =
  | UserEventProperties
  | ProjectEventProperties
  | SpecEventProperties
  | AgentEventProperties
  | BillingEventProperties
  | NavigationEventProperties
  | Record<string, unknown>

// ============================================================================
// Analytics Functions
// ============================================================================

/**
 * Track a custom analytics event
 *
 * @example
 * trackEvent("project_created", { project_id: "123", project_name: "My App" })
 */
export function trackEvent(
  eventName: AnalyticsEvent | string,
  properties?: EventProperties
): void {
  // Console log in development regardless of PostHog status
  if (process.env.NODE_ENV === "development") {
    console.log(`[Analytics] ${eventName}`, properties)
  }

  if (!isPostHogEnabled()) return

  posthog.capture(eventName, {
    ...properties,
    timestamp: properties?.timestamp || new Date().toISOString(),
  })
}

/**
 * Identify a user for tracking
 * Call this after login or when user data is available
 *
 * @example
 * identifyUser("user_123", { email: "user@example.com", plan: "pro" })
 */
export function identifyUser(
  userId: string,
  properties?: Record<string, unknown>
): void {
  if (!isPostHogEnabled()) return

  posthog.identify(userId, {
    ...properties,
    identified_at: new Date().toISOString(),
  })
}

/**
 * Reset user identification (call on logout)
 */
export function resetUser(): void {
  if (!isPostHogEnabled()) return

  posthog.reset()
}

/**
 * Set user properties without identifying
 *
 * @example
 * setUserProperties({ subscription_tier: "pro", team_size: 5 })
 */
export function setUserProperties(properties: Record<string, unknown>): void {
  if (!isPostHogEnabled()) return

  posthog.people.set(properties)
}

/**
 * Increment a numeric user property by tracking an event
 * PostHog handles increments through event aggregation in Insights
 *
 * @example
 * incrementUserProperty("projects_created", 1)
 */
export function incrementUserProperty(
  property: string,
  value: number = 1
): void {
  if (!isPostHogEnabled()) return

  // Track as an event - PostHog aggregates these in Insights
  posthog.capture(`$increment_${property}`, {
    $set: { [property]: value },
    increment_value: value,
  })
}

/**
 * Check if a feature flag is enabled
 *
 * @example
 * const showNewPricing = isFeatureEnabled("new-pricing-page")
 */
export function isFeatureEnabled(flagKey: string): boolean {
  if (!isPostHogEnabled()) return false

  return posthog.isFeatureEnabled(flagKey) ?? false
}

/**
 * Get feature flag value (for multivariate flags)
 *
 * @example
 * const variant = getFeatureFlag("pricing-experiment") // "control" | "variant-a" | "variant-b"
 */
export function getFeatureFlag(
  flagKey: string
): string | boolean | undefined {
  if (!isPostHogEnabled()) return undefined

  return posthog.getFeatureFlag(flagKey)
}

/**
 * Reload feature flags (useful after user identification)
 */
export function reloadFeatureFlags(): void {
  if (!isPostHogEnabled()) return

  posthog.reloadFeatureFlags()
}

/**
 * Associate current user with a group (e.g., organization)
 *
 * @example
 * setGroup("organization", "org_123", { name: "Acme Corp", plan: "enterprise" })
 */
export function setGroup(
  groupType: string,
  groupKey: string,
  properties?: Record<string, unknown>
): void {
  if (!isPostHogEnabled()) return

  posthog.group(groupType, groupKey, properties)
}

/**
 * Opt user out of tracking (for GDPR compliance)
 */
export function optOut(): void {
  if (!isPostHogEnabled()) return

  posthog.opt_out_capturing()
}

/**
 * Opt user back into tracking
 */
export function optIn(): void {
  if (!isPostHogEnabled()) return

  posthog.opt_in_capturing()
}

/**
 * Check if user has opted out
 */
export function hasOptedOut(): boolean {
  if (!isPostHogEnabled()) return true

  return posthog.has_opted_out_capturing()
}
