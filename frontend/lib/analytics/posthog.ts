import posthog from "posthog-js"

// PostHog client initialization for Next.js App Router
// Documentation: https://posthog.com/docs/libraries/next-js

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com"

// Check if PostHog should be enabled
export const isPostHogEnabled = (): boolean => {
  // Disable in SSR
  if (typeof window === "undefined") return false

  // Disable if no key configured
  if (!POSTHOG_KEY) {
    if (process.env.NODE_ENV === "development") {
      console.warn("[PostHog] NEXT_PUBLIC_POSTHOG_KEY is not set. Analytics disabled.")
    }
    return false
  }

  return true
}

// Initialize PostHog - call this once on app mount
export const initPostHog = (): void => {
  if (!isPostHogEnabled()) return

  // Prevent re-initialization
  if (posthog.__loaded) return

  posthog.init(POSTHOG_KEY!, {
    api_host: POSTHOG_HOST,

    // Autocapture: Automatically track clicks, form submissions, page views
    autocapture: true,

    // Page view tracking
    capture_pageview: true,
    capture_pageleave: true,

    // Session recording configuration
    session_recording: {
      // Show input values (except passwords) for better session understanding
      maskAllInputs: false,
      maskInputOptions: {
        password: true,
      },
      // Mask text content in elements with [data-ph-no-capture] attribute
      maskTextSelector: "[data-ph-no-capture]",
    },

    // Enable heatmaps (requires session recording)
    enable_heatmaps: true,

    // Enable toolbar for development testing
    // Access via: ?__posthog_debug=true in URL
    debug: process.env.NODE_ENV === "development",

    // Respect Do Not Track browser setting
    respect_dnt: true,

    // Capture performance metrics
    capture_performance: true,

    // Cookie settings
    persistence: "localStorage+cookie",

    // Disable automatic session recording in development by default
    // Enable with NEXT_PUBLIC_POSTHOG_RECORD_DEV=true
    disable_session_recording:
      process.env.NODE_ENV === "development" &&
      process.env.NEXT_PUBLIC_POSTHOG_RECORD_DEV !== "true",

    // Loaded callback
    loaded: (posthog) => {
      if (process.env.NODE_ENV === "development") {
        console.log("[PostHog] Initialized", {
          distinctId: posthog.get_distinct_id(),
          sessionRecording: !posthog.config.disable_session_recording,
        })
      }
    },
  })
}

// Export PostHog instance for direct access
export { posthog }
