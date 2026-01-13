/**
 * PostHog Analytics Client
 *
 * Initializes PostHog with session recording, autocapture, and heatmaps.
 * This module handles client-side initialization for Next.js App Router.
 */

import posthog from 'posthog-js'

// Environment variables
const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com'

// Use proxy to bypass ad blockers - routes through your own backend
// The proxy forwards requests to PostHog, but ad blockers can't detect it
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:18000'
const USE_PROXY = process.env.NEXT_PUBLIC_POSTHOG_USE_PROXY !== 'false'
const POSTHOG_API_HOST = USE_PROXY ? `${API_URL}/ingest` : POSTHOG_HOST

// Check if we're in the browser
const isBrowser = typeof window !== 'undefined'

// Track initialization state
let isInitialized = false

/**
 * Initialize PostHog client
 * Should be called once when the app loads
 */
export function initPostHog(): void {
  // Only initialize in browser and if key is provided
  if (!isBrowser || !POSTHOG_KEY) {
    if (!POSTHOG_KEY && isBrowser) {
      console.warn('[PostHog] NEXT_PUBLIC_POSTHOG_KEY is not set. Analytics disabled.')
    }
    return
  }

  // Prevent double initialization
  if (isInitialized) {
    return
  }

  try {
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_API_HOST,

      // UI host is where PostHog's toolbar/features are served from (not proxied)
      ui_host: POSTHOG_HOST,

      // Capture all clicks, form submissions automatically
      autocapture: true,

      // Track page views automatically
      capture_pageview: true,

      // Track when users leave pages
      capture_pageleave: true,

      // Session Recording configuration
      session_recording: {
        // Don't mask all inputs by default - we want to see user interactions
        maskAllInputs: false,
        // But DO mask sensitive inputs like passwords
        maskInputOptions: {
          password: true,
        },
        // Mask specific CSS selectors (credit cards, SSN fields, etc.)
        maskCapturedNetworkRequestFn: (request) => {
          // Mask authorization headers
          if (request.requestHeaders) {
            if (request.requestHeaders['Authorization']) {
              request.requestHeaders['Authorization'] = '***'
            }
          }
          return request
        },
      },

      // Enable heatmaps for click tracking visualization
      enable_heatmaps: true,

      // Disable in development if needed (can be toggled)
      loaded: (ph) => {
        // Enable debug mode in development
        if (process.env.NODE_ENV === 'development') {
          ph.debug()
        }
      },

      // Respect Do Not Track browser setting
      respect_dnt: true,

      // Persist user identity across sessions - use cookie as fallback when localStorage blocked
      persistence: 'localStorage+cookie',

      // Cross-subdomain cookie for tracking across subdomains
      cross_subdomain_cookie: true,

      // Disable automatic session recording start - we'll control this
      disable_session_recording: false,
    })

    isInitialized = true
  } catch (error) {
    // PostHog initialization failed - likely due to blocked storage
    // This can happen in private browsing, iframes, or with strict privacy settings
    console.warn('[PostHog] Failed to initialize:', error)
    // Continue without analytics rather than crashing the app
  }
}

/**
 * Check if PostHog is initialized and ready
 */
export function isPostHogReady(): boolean {
  return isInitialized && isBrowser && !!POSTHOG_KEY
}

/**
 * Get the PostHog instance for direct access
 * Returns undefined if not initialized
 */
export function getPostHog(): typeof posthog | undefined {
  if (!isPostHogReady()) {
    return undefined
  }
  return posthog
}

/**
 * Manually capture a page view
 * Useful for SPA navigation where automatic capture might not trigger
 */
export function capturePageView(url?: string): void {
  if (!isPostHogReady()) return

  posthog.capture('$pageview', {
    $current_url: url || window.location.href,
  })
}

/**
 * Capture a page leave event
 */
export function capturePageLeave(): void {
  if (!isPostHogReady()) return

  posthog.capture('$pageleave')
}

/**
 * Start session recording manually
 */
export function startSessionRecording(): void {
  if (!isPostHogReady()) return

  posthog.startSessionRecording()
}

/**
 * Stop session recording
 */
export function stopSessionRecording(): void {
  if (!isPostHogReady()) return

  posthog.stopSessionRecording()
}

/**
 * Check if session recording is active
 */
export function isSessionRecordingActive(): boolean {
  if (!isPostHogReady()) return false

  return posthog.sessionRecordingStarted() ?? false
}

/**
 * Get current session ID
 */
export function getSessionId(): string | undefined {
  if (!isPostHogReady()) return undefined

  return posthog.get_session_id()
}

/**
 * Get current distinct ID (user identifier)
 */
export function getDistinctId(): string | undefined {
  if (!isPostHogReady()) return undefined

  return posthog.get_distinct_id()
}

// Export the posthog instance for advanced usage
export { posthog }
