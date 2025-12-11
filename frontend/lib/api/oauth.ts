/**
 * OAuth API functions
 * Handles OAuth authentication flows and provider management
 */

import { api } from "./client"
import type {
  OAuthProvidersResponse,
  OAuthAuthUrlResponse,
  ConnectedProvidersResponse,
  DisconnectResponse,
} from "./types"

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"

// ============================================================================
// Provider Management
// ============================================================================

/**
 * Get list of available OAuth providers
 */
export async function getOAuthProviders(): Promise<OAuthProvidersResponse> {
  return api.get<OAuthProvidersResponse>("/api/v1/auth/oauth/providers", false)
}

/**
 * Get OAuth authorization URL for a provider
 * Returns the URL to redirect the user to
 */
export async function getOAuthUrl(provider: string): Promise<OAuthAuthUrlResponse> {
  return api.get<OAuthAuthUrlResponse>(`/api/v1/auth/oauth/${provider}/url`, false)
}

/**
 * Start OAuth flow by redirecting to the provider
 * This is the simplest way to start OAuth - just redirect the browser
 */
export function startOAuthFlow(provider: string): void {
  window.location.href = `${API_BASE_URL}/api/v1/auth/oauth/${provider}`
}

/**
 * Start OAuth flow with state tracking
 * Stores state in sessionStorage for verification
 */
export async function startOAuthFlowWithState(provider: string): Promise<void> {
  const { auth_url, state } = await getOAuthUrl(provider)
  sessionStorage.setItem("oauth_state", state)
  sessionStorage.setItem("oauth_provider", provider)
  window.location.href = auth_url
}

// ============================================================================
// Connected Providers (Authenticated)
// ============================================================================

/**
 * Get list of OAuth providers connected to the current user's account
 */
export async function getConnectedProviders(): Promise<ConnectedProvidersResponse> {
  return api.get<ConnectedProvidersResponse>("/api/v1/auth/oauth/connected")
}

/**
 * Connect a new OAuth provider to the current account
 * Returns the authorization URL - redirect the user there
 */
export async function connectProvider(provider: string): Promise<OAuthAuthUrlResponse> {
  return api.post<OAuthAuthUrlResponse>(`/api/v1/auth/oauth/${provider}/connect`)
}

/**
 * Disconnect an OAuth provider from the current account
 */
export async function disconnectProvider(provider: string): Promise<DisconnectResponse> {
  return api.delete<DisconnectResponse>(`/api/v1/auth/oauth/${provider}/disconnect`)
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Check if a specific provider is connected for the current user
 */
export async function isProviderConnected(provider: string): Promise<boolean> {
  try {
    const { providers } = await getConnectedProviders()
    return providers.some((p) => p.provider === provider && p.connected)
  } catch {
    return false
  }
}

/**
 * Get the username for a connected provider
 */
export async function getProviderUsername(provider: string): Promise<string | null> {
  try {
    const { providers } = await getConnectedProviders()
    const found = providers.find((p) => p.provider === provider)
    return found?.username ?? null
  } catch {
    return null
  }
}

/**
 * Get provider display info
 */
export function getProviderInfo(provider: string): {
  name: string
  icon: string
  color: string
} {
  const providers: Record<string, { name: string; icon: string; color: string }> = {
    github: {
      name: "GitHub",
      icon: "github",
      color: "#24292f",
    },
    google: {
      name: "Google",
      icon: "mail",
      color: "#4285f4",
    },
    gitlab: {
      name: "GitLab",
      icon: "gitlab",
      color: "#fc6d26",
    },
  }

  return (
    providers[provider.toLowerCase()] || {
      name: provider,
      icon: "link",
      color: "#666",
    }
  )
}
