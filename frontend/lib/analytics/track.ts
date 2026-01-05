/**
 * Analytics Tracking Module
 *
 * Provides type-safe event tracking using PostHog.
 * Use this module for all analytics tracking in the application.
 */

import { posthog, isPostHogReady } from './posthog'
import {
  ANALYTICS_EVENTS,
  type AnalyticsEventName,
  type EventProperties,
  type BaseEventProperties,
} from './events'

/**
 * Track an analytics event with type-safe properties
 *
 * @param eventName - The name of the event to track
 * @param properties - Event-specific properties
 *
 * @example
 * ```ts
 * track(ANALYTICS_EVENTS.ONBOARDING_STEP_VIEWED, {
 *   step: 'welcome',
 *   step_number: 1,
 * })
 * ```
 */
export function track<E extends AnalyticsEventName>(
  eventName: E,
  properties?: EventProperties<E>
): void {
  // Add base properties
  const enrichedProperties = {
    page_path: typeof window !== 'undefined' ? window.location.pathname : undefined,
    page_title: typeof document !== 'undefined' ? document.title : undefined,
    ...properties,
  }

  // Log in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Analytics] ${eventName}`, enrichedProperties)
  }

  // Send to PostHog if ready
  if (isPostHogReady()) {
    posthog.capture(eventName, enrichedProperties)
  }
}

/**
 * Track an event with arbitrary properties (for backwards compatibility)
 * Prefer using the typed `track` function when possible.
 *
 * @param eventName - The name of the event
 * @param data - Arbitrary event data
 */
export function trackEvent(eventName: string, data?: Record<string, unknown>): void {
  const enrichedData = {
    page_path: typeof window !== 'undefined' ? window.location.pathname : undefined,
    page_title: typeof document !== 'undefined' ? document.title : undefined,
    ...data,
  }

  if (process.env.NODE_ENV === 'development') {
    console.log(`[Analytics] ${eventName}`, enrichedData)
  }

  if (isPostHogReady()) {
    posthog.capture(eventName, enrichedData)
  }
}

/**
 * Track a page view manually
 * Useful for single-page navigation
 */
export function trackPageView(pagePath?: string, pageTitle?: string): void {
  const properties = {
    page_path: pagePath || (typeof window !== 'undefined' ? window.location.pathname : undefined),
    page_title: pageTitle || (typeof document !== 'undefined' ? document.title : undefined),
    page_referrer: typeof document !== 'undefined' ? document.referrer : undefined,
  }

  if (isPostHogReady()) {
    posthog.capture('$pageview', {
      $current_url: typeof window !== 'undefined' ? window.location.href : undefined,
      ...properties,
    })
  }
}

/**
 * Track an error event
 *
 * @param error - The error object
 * @param context - Additional context about the error
 */
export function trackError(
  error: Error | unknown,
  context?: {
    error_type?: string
    api_endpoint?: string
    http_status?: number
  }
): void {
  const errorMessage = error instanceof Error ? error.message : String(error)
  const errorStack = error instanceof Error ? error.stack : undefined

  track(ANALYTICS_EVENTS.ERROR_OCCURRED, {
    error_type: context?.error_type || 'unknown',
    error_message: errorMessage,
    error_stack: errorStack,
    api_endpoint: context?.api_endpoint,
    http_status: context?.http_status,
  })
}

/**
 * Track an API error specifically
 *
 * @param endpoint - The API endpoint that failed
 * @param status - HTTP status code
 * @param message - Error message
 */
export function trackApiError(endpoint: string, status: number, message?: string): void {
  track(ANALYTICS_EVENTS.API_ERROR, {
    error_type: 'api_error',
    api_endpoint: endpoint,
    http_status: status,
    error_message: message,
  })
}

/**
 * Track feature usage
 *
 * @param featureName - Name of the feature used
 * @param action - Action performed (e.g., 'click', 'submit', 'view')
 * @param success - Whether the action was successful
 */
export function trackFeature(featureName: string, action?: string, success?: boolean): void {
  track(ANALYTICS_EVENTS.FEATURE_USED, {
    feature_name: featureName,
    action,
    success,
  })
}

// Re-export events for convenience
export { ANALYTICS_EVENTS } from './events'
