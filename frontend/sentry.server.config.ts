/**
 * Sentry Server-side Configuration
 *
 * This file configures Sentry for the Node.js server environment.
 * It handles server-side errors, API route errors, and SSR errors.
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

    // Enable debug mode in development
    debug: !IS_PRODUCTION,

    // Performance monitoring sample rate
    // Lower on server to reduce overhead
    tracesSampleRate: IS_PRODUCTION ? 0.1 : 1.0,

    // Profiling for performance analysis
    profilesSampleRate: IS_PRODUCTION ? 0.1 : 0.0,

    // Server-specific integrations
    integrations: [
      // Capture unhandled promise rejections
      Sentry.onUnhandledRejectionIntegration(),
    ],

    // Filter errors before sending
    beforeSend(event, hint) {
      // Don't send in development unless explicitly enabled
      if (!IS_PRODUCTION && !process.env.SENTRY_DEBUG) {
        console.log("[Sentry Server] Error captured (dev mode):", hint.originalException)
        return null
      }

      const error = hint.originalException

      // Filter out expected errors
      if (error instanceof Error) {
        // Ignore 404 errors (normal behavior)
        if (error.message?.includes("NEXT_NOT_FOUND")) {
          return null
        }

        // Ignore redirect errors (normal behavior)
        if (error.message?.includes("NEXT_REDIRECT")) {
          return null
        }
      }

      return event
    },

    // Transaction name normalization for server routes
    beforeSendTransaction(event) {
      if (event.transaction) {
        // Normalize UUIDs in route paths
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
