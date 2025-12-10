/**
 * Centralized API client with authentication handling
 * Automatically includes auth tokens and handles token refresh
 */

import type { APIError } from "./types"

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"

// ============================================================================
// Token Storage
// ============================================================================

const TOKEN_KEYS = {
  ACCESS: "omoios_access_token",
  REFRESH: "omoios_refresh_token",
} as const

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(TOKEN_KEYS.ACCESS)
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(TOKEN_KEYS.REFRESH)
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(TOKEN_KEYS.ACCESS, accessToken)
  localStorage.setItem(TOKEN_KEYS.REFRESH, refreshToken)
}

export function clearTokens(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(TOKEN_KEYS.ACCESS)
  localStorage.removeItem(TOKEN_KEYS.REFRESH)
}

// ============================================================================
// API Error Handling
// ============================================================================

export class ApiError extends Error {
  status: number
  code?: string
  errors?: { loc: (string | number)[]; msg: string; type: string }[]

  constructor(message: string, status: number, code?: string, errors?: ApiError["errors"]) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
    this.errors = errors
  }
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  try {
    const data: APIError = await response.json()

    if (typeof data.detail === "string") {
      return new ApiError(data.detail, response.status, data.code)
    }

    // Validation errors
    if (Array.isArray(data.detail)) {
      const message = data.detail.map((e) => e.msg).join(", ")
      return new ApiError(message, response.status, "VALIDATION_ERROR", data.detail)
    }

    return new ApiError("An error occurred", response.status)
  } catch {
    return new ApiError(response.statusText || "An error occurred", response.status)
  }
}

// ============================================================================
// Token Refresh Logic
// ============================================================================

let isRefreshing = false
let refreshPromise: Promise<boolean> | null = null

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    if (!response.ok) {
      clearTokens()
      return false
    }

    const data = await response.json()
    setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    clearTokens()
    return false
  }
}

async function ensureValidToken(): Promise<boolean> {
  if (isRefreshing) {
    return refreshPromise || Promise.resolve(false)
  }

  const accessToken = getAccessToken()
  if (!accessToken) return false

  // Token exists, assume valid (server will reject if not)
  return true
}

// ============================================================================
// Core Fetch Function
// ============================================================================

type RequestMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"

interface RequestOptions {
  method?: RequestMethod
  body?: unknown
  headers?: Record<string, string>
  requireAuth?: boolean
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, headers = {}, requireAuth = true } = options

  // Build headers
  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  }

  // Add auth header if required
  if (requireAuth) {
    const token = getAccessToken()
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`
    }
  }

  // Build request
  const requestInit: RequestInit = {
    method,
    headers: requestHeaders,
  }

  if (body && method !== "GET") {
    requestInit.body = JSON.stringify(body)
  }

  // Make request
  let response = await fetch(`${API_BASE_URL}${endpoint}`, requestInit)

  // Handle 401 - try token refresh
  if (response.status === 401 && requireAuth) {
    // Prevent multiple simultaneous refresh attempts
    if (!isRefreshing) {
      isRefreshing = true
      refreshPromise = refreshAccessToken()
    }

    const refreshed = await refreshPromise
    isRefreshing = false
    refreshPromise = null

    if (refreshed) {
      // Retry request with new token
      const newToken = getAccessToken()
      if (newToken) {
        requestHeaders["Authorization"] = `Bearer ${newToken}`
        response = await fetch(`${API_BASE_URL}${endpoint}`, {
          ...requestInit,
          headers: requestHeaders,
        })
      }
    }
  }

  // Handle errors
  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  // Handle empty responses
  if (response.status === 204) {
    return {} as T
  }

  return response.json()
}

// ============================================================================
// Convenience Methods
// ============================================================================

export const api = {
  get: <T>(endpoint: string, requireAuth = true) =>
    apiRequest<T>(endpoint, { method: "GET", requireAuth }),

  post: <T>(endpoint: string, body?: unknown, requireAuth = true) =>
    apiRequest<T>(endpoint, { method: "POST", body, requireAuth }),

  put: <T>(endpoint: string, body?: unknown, requireAuth = true) =>
    apiRequest<T>(endpoint, { method: "PUT", body, requireAuth }),

  patch: <T>(endpoint: string, body?: unknown, requireAuth = true) =>
    apiRequest<T>(endpoint, { method: "PATCH", body, requireAuth }),

  delete: <T>(endpoint: string, requireAuth = true) =>
    apiRequest<T>(endpoint, { method: "DELETE", requireAuth }),
}
