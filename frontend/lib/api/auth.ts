/**
 * Auth API functions
 * Wraps auth endpoints with proper typing
 */

import { api, setTokens, clearTokens } from "./client"
import type {
  User,
  UserCreate,
  UserUpdate,
  LoginRequest,
  TokenResponse,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  ChangePasswordRequest,
  APIKeyCreate,
  APIKey,
  APIKeyWithSecret,
  MessageResponse,
  WaitlistListResponse,
  WaitlistApproveResponse,
  WaitlistApproveAllResponse,
} from "./types"

// ============================================================================
// Authentication
// ============================================================================

/**
 * Register a new user
 */
export async function register(data: UserCreate): Promise<User> {
  return api.post<User>("/api/v1/auth/register", data, false)
}

/**
 * Login with email and password
 * Stores tokens automatically
 */
export async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/api/v1/auth/login", data, false)
  setTokens(response.access_token, response.refresh_token)
  return response
}

/**
 * Logout current user
 * Clears stored tokens
 */
export async function logout(): Promise<void> {
  try {
    await api.post<MessageResponse>("/api/v1/auth/logout")
  } finally {
    clearTokens()
  }
}

/**
 * Verify email with token
 */
export async function verifyEmail(token: string): Promise<MessageResponse> {
  return api.post<MessageResponse>("/api/v1/auth/verify-email", { token }, false)
}

/**
 * Resend verification email
 */
export async function resendVerification(email: string): Promise<MessageResponse> {
  return api.post<MessageResponse>("/api/v1/auth/resend-verification", { email }, false)
}

/**
 * Request password reset email
 */
export async function forgotPassword(data: ForgotPasswordRequest): Promise<MessageResponse> {
  return api.post<MessageResponse>("/api/v1/auth/forgot-password", data, false)
}

/**
 * Reset password with token
 */
export async function resetPassword(data: ResetPasswordRequest): Promise<MessageResponse> {
  return api.post<MessageResponse>("/api/v1/auth/reset-password", data, false)
}

/**
 * Change password (authenticated)
 */
export async function changePassword(data: ChangePasswordRequest): Promise<MessageResponse> {
  return api.post<MessageResponse>("/api/v1/auth/change-password", data)
}

// ============================================================================
// User Profile
// ============================================================================

/**
 * Get current authenticated user
 */
export async function getCurrentUser(): Promise<User> {
  return api.get<User>("/api/v1/auth/me")
}

/**
 * Update current user profile
 */
export async function updateCurrentUser(data: UserUpdate): Promise<User> {
  return api.patch<User>("/api/v1/auth/me", data)
}

// ============================================================================
// API Keys
// ============================================================================

/**
 * Create a new API key
 */
export async function createApiKey(data: APIKeyCreate): Promise<APIKeyWithSecret> {
  return api.post<APIKeyWithSecret>("/api/v1/auth/api-keys", data)
}

/**
 * List all API keys for current user
 */
export async function listApiKeys(): Promise<APIKey[]> {
  return api.get<APIKey[]>("/api/v1/auth/api-keys")
}

/**
 * Revoke an API key
 */
export async function revokeApiKey(keyId: string): Promise<MessageResponse> {
  return api.delete<MessageResponse>(`/api/v1/auth/api-keys/${keyId}`)
}

// ============================================================================
// Waitlist Management (Admin Only)
// ============================================================================

/**
 * List waitlist users (admin only)
 */
export async function listWaitlistUsers(
  statusFilter: "pending" | "approved" | "none" = "pending",
  limit = 100,
  offset = 0
): Promise<WaitlistListResponse> {
  return api.get<WaitlistListResponse>(
    `/api/v1/auth/waitlist?status_filter=${statusFilter}&limit=${limit}&offset=${offset}`
  )
}

/**
 * Approve a single waitlist user (admin only)
 */
export async function approveWaitlistUser(userId: string): Promise<WaitlistApproveResponse> {
  return api.post<WaitlistApproveResponse>(`/api/v1/auth/waitlist/${userId}/approve`)
}

/**
 * Approve all pending waitlist users (admin only)
 */
export async function approveAllWaitlistUsers(): Promise<WaitlistApproveAllResponse> {
  return api.post<WaitlistApproveAllResponse>("/api/v1/auth/waitlist/approve-all")
}

// ============================================================================
// Waitlist Registration (Public)
// ============================================================================

/**
 * Join the waitlist (register with pending status)
 * This is the same as register() but named for clarity on landing pages
 */
export async function joinWaitlist(data: {
  email: string
  password: string
  full_name?: string
  referral_source?: string
}): Promise<User> {
  return register(data)
}
