/**
 * Sentry Client-side Configuration
 *
 * This file configures Sentry for the browser environment.
 * It initializes error tracking, performance monitoring, and session replay.
 */

import * as Sentry from "@sentry/nextjs"

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN
const IS_PRODUCTION = process.env.NODE_ENV === "production"

// Only initialize Sentry if DSN is configured
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,

    // Environment configuration
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV,

    // Enable debug mode in development for troubleshooting
    debug: !IS_PRODUCTION,

    // Performance Monitoring
    // Sample rate for transactions (page loads, navigations)
    // 100% in development, 10% in production to balance data vs cost
    tracesSampleRate: IS_PRODUCTION ? 0.1 : 1.0,

    // Session Replay Configuration
    // Capture 10% of all sessions, 100% of sessions with errors
    replaysSessionSampleRate: IS_PRODUCTION ? 0.1 : 0.0,
    replaysOnErrorSampleRate: IS_PRODUCTION ? 1.0 : 0.0,

    // Integrations
    integrations: [
      // Session replay - see user actions leading to errors
      Sentry.replayIntegration({
        // Mask all text content and block all media
        maskAllText: true,
        blockAllMedia: true,
        // Mask input values for privacy
        maskAllInputs: true,
      }),

      // Browser tracing for automatic performance monitoring
      Sentry.browserTracingIntegration({
        // Trace interactions (clicks, etc.)
        enableInp: true,
      }),

      // Capture console errors as breadcrumbs
      Sentry.captureConsoleIntegration({
        levels: ["error", "warn"],
      }),

      // HTTP client instrumentation
      Sentry.httpClientIntegration(),
    ],

    // Filter sensitive data from errors
    beforeSend(event, hint) {
      // Don't send errors in development unless explicitly enabled
      if (!IS_PRODUCTION && !process.env.NEXT_PUBLIC_SENTRY_DEBUG) {
        console.log("[Sentry] Error captured (dev mode):", hint.originalException)
        return null
      }

      // Filter out noisy errors that don't provide value
      const error = hint.originalException
      if (error instanceof Error) {
        // Ignore cancelled requests
        if (error.name === "AbortError") {
          return null
        }

        // Ignore network errors from browser extensions
        if (error.message?.includes("chrome-extension://")) {
          return null
        }

        // Ignore ResizeObserver loop errors (benign)
        if (error.message?.includes("ResizeObserver loop")) {
          return null
        }
      }

      return event
    },

    // Filter breadcrumbs for privacy
    beforeBreadcrumb(breadcrumb) {
      // Don't log full URLs for sensitive routes
      if (breadcrumb.category === "navigation") {
        const sensitiveRoutes = ["/settings", "/billing", "/api-keys"]
        const url = breadcrumb.data?.to || breadcrumb.data?.from || ""

        if (sensitiveRoutes.some((route) => url.includes(route))) {
          breadcrumb.data = {
            ...breadcrumb.data,
            to: breadcrumb.data?.to ? "[REDACTED]" : undefined,
            from: breadcrumb.data?.from ? "[REDACTED]" : undefined,
          }
        }
      }

      return breadcrumb
    },

    // Ignore specific errors by message pattern
    ignoreErrors: [
      // Browser extension errors
      "top.GLOBALS",
      "canvas.contentDocument",
      "MyApp_RemoveAllHighlights",
      "atomicFindClose",
      // Network errors that are expected
      "Failed to fetch",
      "Load failed",
      "NetworkError",
      // Third-party script errors
      "Script error.",
      // React hydration warnings (handled separately)
      "Hydration failed",
      "There was an error while hydrating",
    ],

    // Transaction name normalization
    // Replace dynamic IDs with placeholders for better grouping
    beforeSendTransaction(event) {
      if (event.transaction) {
        // Normalize UUIDs
        event.transaction = event.transaction.replace(
          /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi,
          "[id]"
        )
        // Normalize numeric IDs
        event.transaction = event.transaction.replace(
          /\/\d+(?=\/|$)/g,
          "/[id]"
        )
      }
      return event
    },
  })
}
