/**
 * Sentry Edge Runtime Configuration
 *
 * This file configures Sentry for Edge runtime (middleware, edge API routes).
 * Edge runtime has different constraints than Node.js runtime.
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

    // Performance monitoring for edge functions
    // Edge functions are lightweight, so we can sample more
    tracesSampleRate: IS_PRODUCTION ? 0.2 : 1.0,

    // Filter errors before sending
    beforeSend(event, hint) {
      // Don't send in development unless explicitly enabled
      if (!IS_PRODUCTION && !process.env.SENTRY_DEBUG) {
        console.log("[Sentry Edge] Error captured (dev mode):", hint.originalException)
        return null
      }

      return event
    },

    // Transaction name normalization
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
