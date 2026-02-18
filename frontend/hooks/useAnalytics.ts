/**
 * React Hook for Analytics
 *
 * Provides convenient access to analytics functions in React components.
 * Includes utilities for tracking events, identifying users, and feature flags.
 */

"use client";

import { useCallback } from "react";
import { usePostHog } from "@/providers/PostHogProvider";
import {
  track,
  trackEvent,
  trackError,
  trackApiError,
  trackFeature,
  identify,
  identifyUser,
  resetUser,
  setUserProperties,
  ANALYTICS_EVENTS,
  type AnalyticsEventName,
  type EventProperties,
  type UserProperties,
} from "@/lib/analytics";
import type { User } from "@/lib/api/types";

/**
 * Hook return type
 */
export interface UseAnalyticsReturn {
  /** Whether PostHog is ready to track events */
  isReady: boolean;

  /**
   * Track a typed event with type-safe properties
   * @example track(ANALYTICS_EVENTS.CHECKOUT_STARTED, { plan_type: 'pro' })
   */
  track: <E extends AnalyticsEventName>(
    eventName: E,
    properties?: EventProperties<E>,
  ) => void;

  /**
   * Track an event with arbitrary properties (for flexibility)
   * @example trackEvent('custom_event', { foo: 'bar' })
   */
  trackEvent: (eventName: string, data?: Record<string, unknown>) => void;

  /**
   * Track an error event
   * @example trackError(new Error('Something went wrong'), { error_type: 'validation' })
   */
  trackError: (
    error: Error | unknown,
    context?: {
      error_type?: string;
      api_endpoint?: string;
      http_status?: number;
    },
  ) => void;

  /**
   * Track an API error
   * @example trackApiError('/api/users', 500, 'Internal server error')
   */
  trackApiError: (endpoint: string, status: number, message?: string) => void;

  /**
   * Track feature usage
   * @example trackFeature('dark_mode', 'toggle', true)
   */
  trackFeature: (
    featureName: string,
    action?: string,
    success?: boolean,
  ) => void;

  /**
   * Identify a user with their properties
   * @example identify(userId, { email: 'user@example.com', plan_type: 'pro' })
   */
  identify: (userId: string, properties?: UserProperties) => void;

  /**
   * Identify a user from a User object
   * @example identifyUser(user, { github_connected: true })
   */
  identifyUser: (user: User, additionalProperties?: UserProperties) => void;

  /**
   * Reset user identity (call on logout)
   */
  resetUser: () => void;

  /**
   * Set or update user properties
   * @example setUserProperties({ plan_type: 'pro', onboarding_completed: true })
   */
  setUserProperties: (properties: UserProperties) => void;

  /**
   * Check if a feature flag is enabled
   * @example isFeatureEnabled('new_checkout_flow')
   */
  isFeatureEnabled: (key: string) => boolean | undefined;

  /**
   * Get a feature flag value (for multivariate flags)
   * @example getFeatureFlag('pricing_experiment')
   */
  getFeatureFlag: (key: string) => string | boolean | undefined;

  /**
   * Register a callback for when feature flags load
   * @example onFeatureFlags((flags) => console.log('Flags loaded', flags))
   */
  onFeatureFlags: (callback: (flags: string[]) => void) => () => void;

  /** All event names for convenience */
  ANALYTICS_EVENTS: typeof ANALYTICS_EVENTS;
}

/**
 * React hook for analytics
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { track, ANALYTICS_EVENTS, isFeatureEnabled } = useAnalytics()
 *
 *   const handleClick = () => {
 *     track(ANALYTICS_EVENTS.FEATURE_USED, { feature_name: 'button_click' })
 *   }
 *
 *   return (
 *     <button onClick={handleClick}>
 *       {isFeatureEnabled('new_button_text') ? 'New Text' : 'Click Me'}
 *     </button>
 *   )
 * }
 * ```
 */
export function useAnalytics(): UseAnalyticsReturn {
  const posthog = usePostHog();

  // Wrap functions in useCallback for stable references
  const wrappedTrack = useCallback(
    <E extends AnalyticsEventName>(
      eventName: E,
      properties?: EventProperties<E>,
    ) => {
      track(eventName, properties);
    },
    [],
  );

  const wrappedTrackEvent = useCallback(
    (eventName: string, data?: Record<string, unknown>) => {
      trackEvent(eventName, data);
    },
    [],
  );

  const wrappedTrackError = useCallback(
    (
      error: Error | unknown,
      context?: {
        error_type?: string;
        api_endpoint?: string;
        http_status?: number;
      },
    ) => {
      trackError(error, context);
    },
    [],
  );

  const wrappedTrackApiError = useCallback(
    (endpoint: string, status: number, message?: string) => {
      trackApiError(endpoint, status, message);
    },
    [],
  );

  const wrappedTrackFeature = useCallback(
    (featureName: string, action?: string, success?: boolean) => {
      trackFeature(featureName, action, success);
    },
    [],
  );

  const wrappedIdentify = useCallback(
    (userId: string, properties?: UserProperties) => {
      identify(userId, properties);
    },
    [],
  );

  const wrappedIdentifyUser = useCallback(
    (user: User, additionalProperties?: UserProperties) => {
      identifyUser(user, additionalProperties);
    },
    [],
  );

  const wrappedResetUser = useCallback(() => {
    resetUser();
  }, []);

  const wrappedSetUserProperties = useCallback((properties: UserProperties) => {
    setUserProperties(properties);
  }, []);

  return {
    isReady: posthog.isReady,
    track: wrappedTrack,
    trackEvent: wrappedTrackEvent,
    trackError: wrappedTrackError,
    trackApiError: wrappedTrackApiError,
    trackFeature: wrappedTrackFeature,
    identify: wrappedIdentify,
    identifyUser: wrappedIdentifyUser,
    resetUser: wrappedResetUser,
    setUserProperties: wrappedSetUserProperties,
    isFeatureEnabled: posthog.isFeatureEnabled,
    getFeatureFlag: posthog.getFeatureFlag,
    onFeatureFlags: posthog.onFeatureFlags,
    ANALYTICS_EVENTS,
  };
}

// Re-export event types for convenience
export type { AnalyticsEventName, EventProperties, UserProperties };
export { ANALYTICS_EVENTS };
