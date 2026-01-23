/**
 * React Query hooks for Resource Monitor API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  listResources,
  getResourceSummary,
  getResourceLimits,
  getResourceStatus,
  updateResourceAllocation,
  terminateResource,
} from "@/lib/api/resources"
import type {
  ResourceStatus,
  ResourceSummary,
  ResourceLimits,
  UpdateAllocationRequest,
} from "@/lib/api/resources"

// Query keys
export const resourceKeys = {
  all: ["resources"] as const,
  list: (status?: string) => [...resourceKeys.all, "list", status] as const,
  summary: () => [...resourceKeys.all, "summary"] as const,
  limits: () => [...resourceKeys.all, "limits"] as const,
  detail: (sandboxId: string) =>
    [...resourceKeys.all, "detail", sandboxId] as const,
}

/**
 * Hook to fetch all resource statuses
 */
export function useResources(status: string = "active") {
  return useQuery<ResourceStatus[]>({
    queryKey: resourceKeys.list(status),
    queryFn: () => listResources(status),
    refetchInterval: 5000, // Refresh every 5 seconds for real-time monitoring
  })
}

/**
 * Hook to fetch resource summary statistics
 */
export function useResourceSummary() {
  return useQuery<ResourceSummary>({
    queryKey: resourceKeys.summary(),
    queryFn: getResourceSummary,
    refetchInterval: 10000, // Refresh every 10 seconds
  })
}

/**
 * Hook to fetch resource limits
 */
export function useResourceLimits() {
  return useQuery<ResourceLimits>({
    queryKey: resourceKeys.limits(),
    queryFn: getResourceLimits,
    staleTime: Infinity, // Limits don't change
  })
}

/**
 * Hook to fetch resource status for a specific sandbox
 */
export function useResourceStatus(sandboxId: string) {
  return useQuery<ResourceStatus>({
    queryKey: resourceKeys.detail(sandboxId),
    queryFn: () => getResourceStatus(sandboxId),
    enabled: !!sandboxId,
    refetchInterval: 5000,
  })
}

/**
 * Hook to update resource allocation
 */
export function useUpdateAllocation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      sandboxId,
      allocation,
    }: {
      sandboxId: string
      allocation: UpdateAllocationRequest
    }) => updateResourceAllocation(sandboxId, allocation),
    onSuccess: (data, variables) => {
      // Update the specific resource in cache
      queryClient.setQueryData(resourceKeys.detail(variables.sandboxId), data)
      // Invalidate list to refresh
      queryClient.invalidateQueries({ queryKey: resourceKeys.list() })
      queryClient.invalidateQueries({ queryKey: resourceKeys.summary() })
    },
  })
}

/**
 * Hook to terminate a resource
 */
export function useTerminateResource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sandboxId: string) => terminateResource(sandboxId),
    onSuccess: (_, sandboxId) => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: resourceKeys.list() })
      queryClient.invalidateQueries({ queryKey: resourceKeys.summary() })
      queryClient.removeQueries({ queryKey: resourceKeys.detail(sandboxId) })
    },
  })
}
