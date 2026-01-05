"use client"

import { useEffect, Suspense, createContext, useContext, type ReactNode } from "react"
import { usePathname, useSearchParams } from "next/navigation"
import { initPostHog, capturePageView, isPostHogReady, posthog } from "@/lib/analytics/posthog"

// ============================================================================
// Context for PostHog
// ============================================================================

interface PostHogContextValue {
  isReady: boolean
  capture: typeof posthog.capture
  identify: typeof posthog.identify
  reset: typeof posthog.reset
  setPersonProperties: typeof posthog.setPersonProperties
  getFeatureFlag: typeof posthog.getFeatureFlag
  isFeatureEnabled: typeof posthog.isFeatureEnabled
  onFeatureFlags: typeof posthog.onFeatureFlags
}

const PostHogContext = createContext<PostHogContextValue | null>(null)

// ============================================================================
// Page View Tracker Component
// ============================================================================

/**
 * Tracks page views on route changes
 * Separated into its own component because useSearchParams requires Suspense
 */
function PageViewTracker(): null {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!isPostHogReady()) return

    // Construct full URL with search params
    const url = searchParams?.toString()
      ? `${pathname}?${searchParams.toString()}`
      : pathname

    // Capture pageview with full URL
    capturePageView(window.location.origin + url)
  }, [pathname, searchParams])

  return null
}

// ============================================================================
// PostHog Provider Component
// ============================================================================

interface PostHogProviderProps {
  children: ReactNode
}

export function PostHogProvider({ children }: PostHogProviderProps) {
  // Initialize PostHog on mount
  useEffect(() => {
    initPostHog()
  }, [])

  // Create context value with bound methods
  const contextValue: PostHogContextValue = {
    isReady: isPostHogReady(),
    capture: (...args) => {
      if (isPostHogReady()) {
        return posthog.capture(...args)
      }
    },
    identify: (...args) => {
      if (isPostHogReady()) {
        posthog.identify(...args)
      }
    },
    reset: (...args) => {
      if (isPostHogReady()) {
        posthog.reset(...args)
      }
    },
    setPersonProperties: (...args) => {
      if (isPostHogReady()) {
        posthog.setPersonProperties(...args)
      }
    },
    getFeatureFlag: (...args) => {
      if (isPostHogReady()) {
        return posthog.getFeatureFlag(...args)
      }
      return undefined
    },
    isFeatureEnabled: (...args) => {
      if (isPostHogReady()) {
        return posthog.isFeatureEnabled(...args)
      }
      return undefined
    },
    onFeatureFlags: (...args) => {
      if (isPostHogReady()) {
        return posthog.onFeatureFlags(...args)
      }
      return () => {}
    },
  }

  return (
    <PostHogContext.Provider value={contextValue}>
      {/* Wrap PageViewTracker in Suspense because useSearchParams requires it */}
      <Suspense fallback={null}>
        <PageViewTracker />
      </Suspense>
      {children}
    </PostHogContext.Provider>
  )
}

// ============================================================================
// Hook for accessing PostHog
// ============================================================================

/**
 * Hook to access PostHog context
 * Provides type-safe access to PostHog methods
 */
export function usePostHog(): PostHogContextValue {
  const context = useContext(PostHogContext)

  if (!context) {
    // Return a no-op context if used outside provider
    // This allows components to safely call analytics methods
    return {
      isReady: false,
      capture: () => undefined,
      identify: () => undefined,
      reset: () => undefined,
      setPersonProperties: () => undefined,
      getFeatureFlag: () => undefined,
      isFeatureEnabled: () => undefined,
      onFeatureFlags: () => () => {},
    }
  }

  return context
}
