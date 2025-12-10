/**
 * React Query hooks for GitHub Integration API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  connectRepository,
  listConnectedRepositories,
  syncRepository,
} from "@/lib/api/github"
import type {
  ConnectRepositoryRequest,
  RepositoryInfo,
} from "@/lib/api/types"
import { projectKeys } from "./useProjects"

// Query keys
export const githubKeys = {
  all: ["github"] as const,
  repos: () => [...githubKeys.all, "repos"] as const,
}

/**
 * Hook to fetch connected repositories
 */
export function useConnectedRepositories() {
  return useQuery<RepositoryInfo[]>({
    queryKey: githubKeys.repos(),
    queryFn: listConnectedRepositories,
  })
}

/**
 * Hook to connect a repository
 */
export function useConnectRepository() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectId,
      data,
    }: {
      projectId: string
      data: ConnectRepositoryRequest
    }) => connectRepository(projectId, data),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: githubKeys.repos() })
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

/**
 * Hook to sync a repository
 */
export function useSyncRepository() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectId: string) => syncRepository(projectId),
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}
