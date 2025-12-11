/**
 * React Query hooks for OAuth management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getOAuthProviders,
  getConnectedProviders,
  disconnectProvider,
  getOAuthUrl,
  startOAuthFlow,
} from "@/lib/api/oauth"
import type { OAuthProvidersResponse, ConnectedProvidersResponse, OAuthAuthUrlResponse } from "@/lib/api/types"

// Query keys
export const oauthKeys = {
  all: ["oauth"] as const,
  providers: () => [...oauthKeys.all, "providers"] as const,
  connected: () => [...oauthKeys.all, "connected"] as const,
}

/**
 * Hook to fetch available OAuth providers
 */
export function useOAuthProviders() {
  return useQuery<OAuthProvidersResponse>({
    queryKey: oauthKeys.providers(),
    queryFn: getOAuthProviders,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to fetch connected OAuth providers for current user
 */
export function useConnectedProviders() {
  return useQuery<ConnectedProvidersResponse>({
    queryKey: oauthKeys.connected(),
    queryFn: getConnectedProviders,
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

/**
 * Hook to get OAuth URL for a provider
 */
export function useOAuthUrl() {
  return useMutation<OAuthAuthUrlResponse, Error, string>({
    mutationFn: (provider: string) => getOAuthUrl(provider),
  })
}

/**
 * Hook to start OAuth flow (redirect to provider)
 */
export function useStartOAuth() {
  return useMutation<void, Error, string>({
    mutationFn: async (provider: string) => {
      startOAuthFlow(provider)
    },
  })
}

/**
 * Hook to disconnect an OAuth provider
 */
export function useDisconnectProvider() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (provider: string) => disconnectProvider(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: oauthKeys.connected() })
    },
  })
}

/**
 * Hook to check if a specific provider is connected
 */
export function useIsProviderConnected(provider: string) {
  const { data, isLoading } = useConnectedProviders()

  const isConnected = data?.providers.some(
    (p) => p.provider === provider && p.connected
  ) ?? false

  return {
    isConnected,
    isLoading,
    username: data?.providers.find((p) => p.provider === provider)?.username ?? null,
  }
}
