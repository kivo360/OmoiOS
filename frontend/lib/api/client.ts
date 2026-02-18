/**
 * Centralized API client with authentication handling
 * Automatically includes auth tokens and handles token refresh
 */

import type { APIError } from "./types";
import { addAPIBreadcrumb, captureAPIError } from "@/lib/sentry/context";

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000";

// ============================================================================
// Token Storage
// ============================================================================

const TOKEN_KEYS = {
  ACCESS: "omoios_access_token",
  REFRESH: "omoios_refresh_token",
  ACCESS_EXPIRES_AT: "omoios_access_expires_at",
  LAST_VALIDATED: "omoios_last_validated",
} as const;

// Cookie name for middleware auth detection (must match middleware.ts)
const AUTH_COOKIE_NAME = "omoios_auth_state";

// How long to trust cached auth state before revalidating (in ms)
// Set to 23 hours - just under typical session length for smooth UX
const VALIDATION_CACHE_DURATION = 23 * 60 * 60 * 1000;

// How much buffer before token expiry to trigger refresh (in ms)
// Refresh 2 minutes before expiry to avoid race conditions
const TOKEN_REFRESH_BUFFER = 2 * 60 * 1000;

// Cookie expiry - 30 days (matches session duration)
const AUTH_COOKIE_MAX_AGE = 30 * 24 * 60 * 60;

/**
 * Set auth state cookie for middleware detection
 * This enables instant redirects at the edge before React hydrates
 */
function setAuthCookie(authenticated: boolean): void {
  if (typeof document === "undefined") return;

  if (authenticated) {
    document.cookie = `${AUTH_COOKIE_NAME}=true; path=/; max-age=${AUTH_COOKIE_MAX_AGE}; SameSite=Lax`;
  } else {
    // Clear cookie by setting expired date
    document.cookie = `${AUTH_COOKIE_NAME}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEYS.ACCESS);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEYS.REFRESH);
}

export function getAccessTokenExpiresAt(): number | null {
  if (typeof window === "undefined") return null;
  const expiry = localStorage.getItem(TOKEN_KEYS.ACCESS_EXPIRES_AT);
  return expiry ? parseInt(expiry, 10) : null;
}

export function getLastValidated(): number | null {
  if (typeof window === "undefined") return null;
  const timestamp = localStorage.getItem(TOKEN_KEYS.LAST_VALIDATED);
  return timestamp ? parseInt(timestamp, 10) : null;
}

export function setLastValidated(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEYS.LAST_VALIDATED, Date.now().toString());
}

/**
 * Decode JWT to extract expiration time
 * Returns expiry timestamp in milliseconds, or null if invalid
 */
function decodeJwtExpiry(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const payload = JSON.parse(atob(parts[1]));
    if (payload.exp) {
      // JWT exp is in seconds, convert to milliseconds
      return payload.exp * 1000;
    }
    return null;
  } catch {
    return null;
  }
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEYS.ACCESS, accessToken);
  localStorage.setItem(TOKEN_KEYS.REFRESH, refreshToken);

  // Extract and store expiry from JWT
  const expiresAt = decodeJwtExpiry(accessToken);
  if (expiresAt) {
    localStorage.setItem(TOKEN_KEYS.ACCESS_EXPIRES_AT, expiresAt.toString());
  }

  // Mark as just validated
  setLastValidated();

  // Set auth cookie for middleware edge redirects
  setAuthCookie(true);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEYS.ACCESS);
  localStorage.removeItem(TOKEN_KEYS.REFRESH);
  localStorage.removeItem(TOKEN_KEYS.ACCESS_EXPIRES_AT);
  localStorage.removeItem(TOKEN_KEYS.LAST_VALIDATED);

  // Clear auth cookie
  setAuthCookie(false);
}

/**
 * Check if the access token is still valid (not expired)
 * Returns true if token exists and hasn't expired yet
 */
export function isAccessTokenValid(): boolean {
  const token = getAccessToken();
  if (!token) return false;

  const expiresAt = getAccessTokenExpiresAt();
  if (!expiresAt) return true; // If no expiry stored, assume valid (server will reject if not)

  // Valid if not expired yet (with buffer for network latency)
  return Date.now() < expiresAt - TOKEN_REFRESH_BUFFER;
}

/**
 * Check if we need to revalidate with the server
 * Returns false if recently validated and token is still valid
 */
export function needsRevalidation(): boolean {
  const lastValidated = getLastValidated();
  if (!lastValidated) return true;

  // If validated within cache duration and token is still valid, no need to revalidate
  const timeSinceValidation = Date.now() - lastValidated;
  return (
    timeSinceValidation > VALIDATION_CACHE_DURATION || !isAccessTokenValid()
  );
}

/**
 * Check if we should attempt a background token refresh
 * Returns true if token is approaching expiry but refresh token might still be valid
 */
export function shouldRefreshToken(): boolean {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  const expiresAt = getAccessTokenExpiresAt();
  if (!expiresAt) return false;

  // Refresh if within buffer window of expiry
  const timeUntilExpiry = expiresAt - Date.now();
  return timeUntilExpiry > 0 && timeUntilExpiry < TOKEN_REFRESH_BUFFER;
}

// ============================================================================
// API Error Handling
// ============================================================================

export class ApiError extends Error {
  status: number;
  code?: string;
  errors?: { loc: (string | number)[]; msg: string; type: string }[];

  constructor(
    message: string,
    status: number,
    code?: string,
    errors?: ApiError["errors"],
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.errors = errors;
  }
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  try {
    const data: APIError = await response.json();

    if (typeof data.detail === "string") {
      return new ApiError(data.detail, response.status, data.code);
    }

    // Validation errors
    if (Array.isArray(data.detail)) {
      const message = data.detail.map((e) => e.msg).join(", ");
      return new ApiError(
        message,
        response.status,
        "VALIDATION_ERROR",
        data.detail,
      );
    }

    return new ApiError("An error occurred", response.status);
  } catch {
    return new ApiError(
      response.statusText || "An error occurred",
      response.status,
    );
  }
}

// ============================================================================
// Token Refresh Logic
// ============================================================================

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearTokens();
      return false;
    }

    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

async function ensureValidToken(): Promise<boolean> {
  if (isRefreshing) {
    return refreshPromise || Promise.resolve(false);
  }

  const accessToken = getAccessToken();
  if (!accessToken) return false;

  // Token exists, assume valid (server will reject if not)
  return true;
}

// ============================================================================
// Core Fetch Function
// ============================================================================

type RequestMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

interface RequestOptions {
  method?: RequestMethod;
  body?: unknown;
  headers?: Record<string, string>;
  requireAuth?: boolean;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, headers = {}, requireAuth = true } = options;

  // Track request timing for breadcrumbs
  const startTime = Date.now();

  // Build headers
  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  };

  // Add auth header if required
  if (requireAuth) {
    const token = getAccessToken();
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
    }
  }

  // Build request
  const requestInit: RequestInit = {
    method,
    headers: requestHeaders,
  };

  if (body && method !== "GET") {
    requestInit.body = JSON.stringify(body);
  }

  try {
    // Make request
    let response = await fetch(`${API_BASE_URL}${endpoint}`, requestInit);

    // Handle 401 - try token refresh
    if (response.status === 401 && requireAuth) {
      // Prevent multiple simultaneous refresh attempts
      if (!isRefreshing) {
        isRefreshing = true;
        refreshPromise = refreshAccessToken();
      }

      const refreshed = await refreshPromise;
      isRefreshing = false;
      refreshPromise = null;

      if (refreshed) {
        // Retry request with new token
        const newToken = getAccessToken();
        if (newToken) {
          requestHeaders["Authorization"] = `Bearer ${newToken}`;
          response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...requestInit,
            headers: requestHeaders,
          });
        }
      }
    }

    // Calculate request duration
    const duration = Date.now() - startTime;

    // Handle errors
    if (!response.ok) {
      // Handle rate limiting (429) with Retry-After header
      if (response.status === 429) {
        const retryAfter = response.headers.get("Retry-After");
        const retrySeconds = retryAfter ? parseInt(retryAfter, 10) : 60;
        const error = new ApiError(
          `Too many requests. Please try again in ${retrySeconds} seconds.`,
          429,
          "rate_limited",
        );
        throw error;
      }

      const error = await parseErrorResponse(response);

      // Add breadcrumb for failed request
      addAPIBreadcrumb({
        method,
        url: endpoint,
        status: response.status,
        duration,
        error: error.message,
      });

      // Capture error in Sentry (non-blocking)
      captureAPIError(error, {
        method,
        url: endpoint,
        status: response.status,
      });

      throw error;
    }

    // Add breadcrumb for successful request
    addAPIBreadcrumb({
      method,
      url: endpoint,
      status: response.status,
      duration,
    });

    // Handle empty responses
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  } catch (error) {
    // Handle network errors (not API errors)
    if (error instanceof ApiError) {
      throw error;
    }

    const duration = Date.now() - startTime;
    const networkError =
      error instanceof Error ? error : new Error("Network request failed");

    // Add breadcrumb for network failure
    addAPIBreadcrumb({
      method,
      url: endpoint,
      duration,
      error: networkError.message,
    });

    // Capture network error
    captureAPIError(networkError, {
      method,
      url: endpoint,
    });

    throw networkError;
  }
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
};
