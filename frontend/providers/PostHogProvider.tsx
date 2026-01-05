"use client"

import { Suspense, useEffect, useRef, type ReactNode } from "react"
import { usePathname, useSearchParams } from "next/navigation"
import { initPostHog, posthog, isPostHogEnabled } from "@/lib/analytics/posthog"

interface PostHogProviderProps {
  children: ReactNode
}

/**
 * Internal component that tracks page views
 * Separated to handle Suspense boundary for useSearchParams
 */
function PostHogPageView() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!isPostHogEnabled()) return

    // Build the full URL for the pageview
    const url = window.origin + pathname
    const search = searchParams?.toString()
    const fullUrl = search ? `${url}?${search}` : url

    // Capture pageview event
    posthog.capture("$pageview", {
      $current_url: fullUrl,
    })
  }, [pathname, searchParams])

  return null
}

/**
 * PostHog Analytics Provider
 *
 * Initializes PostHog on mount and tracks page views on route changes.
 * Handles Next.js App Router integration with session recording.
 *
 * Features:
 * - Session recording (watch full user sessions)
 * - Autocapture (automatic click, form, and page tracking)
 * - Custom event tracking via trackEvent()
 * - User identification via identifyUser()
 * - Feature flags via isFeatureEnabled() / getFeatureFlag()
 * - Heatmaps
 *
 * @see frontend/docs/analytics-setup.md for configuration
 */
export function PostHogProvider({ children }: PostHogProviderProps) {
  const isInitializedRef = useRef(false)

  // Initialize PostHog on mount
  useEffect(() => {
    if (isInitializedRef.current) return
    isInitializedRef.current = true

    initPostHog()
  }, [])

  return (
    <>
      <Suspense fallback={null}>
        <PostHogPageView />
      </Suspense>
      {children}
    </>
  )
}

/**
 * Hook to access PostHog analytics functions
 * Import from @/lib/analytics instead for better typing
 */
export function usePostHog() {
  return {
    posthog,
    isEnabled: isPostHogEnabled(),
  }
}
