"use client"

import { createContext, useContext, useEffect, useCallback, type ReactNode } from "react"
import { create } from "zustand"
import { persist } from "zustand/middleware"
import { useRouter, usePathname } from "next/navigation"
import type { User } from "@/lib/api/types"
import { getCurrentUser, logout as apiLogout } from "@/lib/api/auth"
import { getAccessToken, clearTokens } from "@/lib/api/client"

// ============================================================================
// Auth Store (Zustand)
// ============================================================================

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  error: string | null
  
  // Actions
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
}

const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: true,
      isAuthenticated: false,
      error: null,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
          error: null,
        }),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error, isLoading: false }),

      reset: () =>
        set({
          user: null,
          isLoading: false,
          isAuthenticated: false,
          error: null,
        }),
    }),
    {
      name: "omoios-auth",
      // Only persist user data, not loading states
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
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
]

// Routes that should redirect to main app if already authenticated
const AUTH_ROUTES = ["/login", "/register"]

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter()
  const pathname = usePathname()
  
  const { user, isLoading, isAuthenticated, error, setUser, setLoading, setError, reset } =
    useAuthStore()

  // Check if current route is public
  const isPublicRoute = PUBLIC_ROUTES.some((route) => pathname?.startsWith(route))
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname?.startsWith(route))

  // Refresh user data from API
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
    } catch (err) {
      console.error("Failed to refresh user:", err)
      reset()
      clearTokens()
    } finally {
      setLoading(false)
    }
  }, [setUser, setLoading, reset])

  // Login handler - called after successful login API call
  const login = useCallback(
    (userData: User) => {
      setUser(userData)
    },
    [setUser]
  )

  // Logout handler
  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } catch (err) {
      console.error("Logout error:", err)
    } finally {
      reset()
      router.push("/login")
    }
  }, [reset, router])

  // Initial auth check on mount
  useEffect(() => {
    const token = getAccessToken()
    
    if (token && !user) {
      refreshUser()
    } else if (!token) {
      setLoading(false)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle route protection
  useEffect(() => {
    if (isLoading) return

    // If not authenticated and trying to access protected route
    if (!isAuthenticated && !isPublicRoute && pathname !== "/") {
      router.push("/login")
      return
    }

    // If authenticated and trying to access auth routes (login/register)
    if (isAuthenticated && isAuthRoute) {
      router.push("/command")
      return
    }
  }, [isLoading, isAuthenticated, isPublicRoute, isAuthRoute, pathname, router])

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
