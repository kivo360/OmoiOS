"use client"

import { createContext, useContext, useEffect, useCallback, useRef, type ReactNode } from "react"
import { create } from "zustand"
import { persist } from "zustand/middleware"
import { useRouter, usePathname } from "next/navigation"
import type { User } from "@/lib/api/types"
import { getCurrentUser, logout as apiLogout } from "@/lib/api/auth"
import {
  getAccessToken,
  clearTokens,
  isAccessTokenValid,
  needsRevalidation,
  shouldRefreshToken,
  setLastValidated,
} from "@/lib/api/client"
import { identifyUser, resetUser, clearOrganization, track, ANALYTICS_EVENTS } from "@/lib/analytics"

// ============================================================================
// Auth Store (Zustand)
// ============================================================================

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  error: string | null
  lastValidatedAt: number | null

  // Actions
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setLastValidatedAt: (timestamp: number | null) => void
  reset: () => void
}

const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: true,
      isAuthenticated: false,
      error: null,
      lastValidatedAt: null,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
          error: null,
        }),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error, isLoading: false }),

      setLastValidatedAt: (lastValidatedAt) => set({ lastValidatedAt }),

      reset: () =>
        set({
          user: null,
          isLoading: false,
          isAuthenticated: false,
          error: null,
          lastValidatedAt: null,
        }),
    }),
    {
      name: "omoios-auth",
      // Persist user data and validation timestamp
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        lastValidatedAt: state.lastValidatedAt,
      }),
    }
  )
)

// ============================================================================
// Auth Context
// ============================================================================

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  error: string | null
  login: (user: User) => void
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

// ============================================================================
// Auth Provider Component
// ============================================================================

// Routes that don't require authentication
const PUBLIC_ROUTES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/callback",
]

// Routes that should redirect to main app if already authenticated
const AUTH_ROUTES = ["/login", "/register"]

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter()
  const pathname = usePathname()
  const isValidatingRef = useRef(false)
  const hasRedirectedRef = useRef(false)

  const {
    user,
    isLoading,
    isAuthenticated,
    error,
    setUser,
    setLoading,
    setError,
    setLastValidatedAt,
    reset,
  } = useAuthStore()

  // Check if current route is public
  const isPublicRoute = PUBLIC_ROUTES.some((route) => pathname?.startsWith(route))
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname?.startsWith(route))

  // Background validation - doesn't block UI
  const validateInBackground = useCallback(async () => {
    if (isValidatingRef.current) return
    isValidatingRef.current = true

    try {
      const userData = await getCurrentUser()
      setUser(userData)
      setLastValidatedAt(Date.now())
      setLastValidated() // Also update localStorage

      // Re-identify user in PostHog (in case session was restored)
      identifyUser(userData)
    } catch (err) {
      console.error("Background validation failed:", err)
      // Token is invalid - clear everything and redirect
      reset()
      clearTokens()
      if (!isPublicRoute && pathname !== "/") {
        router.push("/login")
      }
    } finally {
      isValidatingRef.current = false
    }
  }, [setUser, setLastValidatedAt, reset, isPublicRoute, pathname, router])

  // Refresh user data from API (blocking)
  const refreshUser = useCallback(async () => {
    const token = getAccessToken()

    if (!token) {
      reset()
      return
    }

    try {
      setLoading(true)
      const userData = await getCurrentUser()
      setUser(userData)
      setLastValidatedAt(Date.now())
      setLastValidated()

      // Re-identify user in PostHog (in case session was restored)
      identifyUser(userData)
    } catch (err) {
      console.error("Failed to refresh user:", err)
      reset()
      clearTokens()
    } finally {
      setLoading(false)
    }
  }, [setUser, setLoading, setLastValidatedAt, reset])

  // Login handler - called after successful login API call
  const login = useCallback(
    (userData: User) => {
      setUser(userData)
      setLastValidatedAt(Date.now())

      // Identify user in PostHog for analytics
      identifyUser(userData)
      track(ANALYTICS_EVENTS.USER_LOGGED_IN, {
        auth_method: 'email',
      })
    },
    [setUser, setLastValidatedAt]
  )

  // Logout handler
  const logout = useCallback(async () => {
    try {
      // Track logout event before resetting
      track(ANALYTICS_EVENTS.USER_LOGGED_OUT, {})
      await apiLogout()
    } catch (err) {
      console.error("Logout error:", err)
    } finally {
      // Reset PostHog user identity and organization context
      clearOrganization()
      resetUser()
      reset()
      router.push("/login")
    }
  }, [reset, router])

  // Initial auth check on mount - OPTIMIZED for instant redirects
  useEffect(() => {
    const token = getAccessToken()
    const hasPersistedAuth = isAuthenticated && user

    // Case 1: No token at all - not authenticated
    if (!token) {
      setLoading(false)
      return
    }

    // Case 2: Have token AND persisted auth state AND token is still valid
    // -> Trust the cache, skip blocking API call, validate in background
    if (hasPersistedAuth && isAccessTokenValid()) {
      setLoading(false) // Immediately ready

      // Only validate in background if enough time has passed
      if (needsRevalidation()) {
        validateInBackground()
      }
      return
    }

    // Case 3: Have token but no persisted state, or token expired
    // -> Need to validate (blocking)
    if (token && !hasPersistedAuth) {
      refreshUser()
      return
    }

    // Case 4: Have persisted state but token is expired
    // -> Try to refresh token, if fails then logout
    if (hasPersistedAuth && !isAccessTokenValid()) {
      // Token expired but we have refresh token - attempt silent refresh
      refreshUser()
      return
    }

    setLoading(false)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle route protection - FALLBACK for cases middleware misses
  // Primary redirects happen in middleware.ts at the edge (faster)
  // This is a safety net for edge cases (e.g., cookie/localStorage mismatch)
  useEffect(() => {
    // Wait for loading to complete before making redirect decisions
    if (isLoading) return

    // Reset redirect flag when pathname changes
    hasRedirectedRef.current = false

    // If not authenticated and trying to access protected route
    if (!isAuthenticated && !isPublicRoute && pathname !== "/") {
      router.replace("/login")
      return
    }

    // If authenticated and trying to access auth routes (login/register)
    // Note: Middleware should catch this first, but this is a fallback
    if (isAuthenticated && isAuthRoute && !hasRedirectedRef.current) {
      hasRedirectedRef.current = true
      router.replace("/command")
      return
    }
  }, [isLoading, isAuthenticated, isPublicRoute, isAuthRoute, pathname, router])

  // Background token refresh before expiry
  useEffect(() => {
    if (!isAuthenticated) return

    const checkTokenRefresh = () => {
      if (shouldRefreshToken()) {
        validateInBackground()
      }
    }

    // Check immediately and then every minute
    checkTokenRefresh()
    const interval = setInterval(checkTokenRefresh, 60 * 1000)

    return () => clearInterval(interval)
  }, [isAuthenticated, validateInBackground])

  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated,
    error,
    login,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// ============================================================================
// Hook
// ============================================================================

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  
  return context
}

// Export store for direct access if needed
export { useAuthStore }
