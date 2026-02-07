/**
 * React Query hooks for Resource Monitoring API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getSandboxResources,
  getSandboxResource,
  updateSandboxAllocation,
  getSandboxMetricsHistory,
  getResourceSummary,
  type SandboxResource,
  type ResourceMetricsHistory,
  type ResourceSummary,
  type UpdateAllocationRequest,
  type UpdateAllocationResponse,
} from "@/lib/api/resources"

// Query keys
export const resourceKeys = {
  all: ["resources"] as const,
  sandboxes: (status?: string) => [...resourceKeys.all, "sandboxes", status] as const,
  sandbox: (sandboxId: string) => [...resourceKeys.all, "sandbox", sandboxId] as const,
  history: (sandboxId: string, hours?: number) =>
    [...resourceKeys.all, "history", sandboxId, hours] as const,
  summary: () => [...resourceKeys.all, "summary"] as const,
}

/**
 * Hook to fetch all sandbox resources
 */
export function useSandboxResources(status?: string) {
  return useQuery<SandboxResource[]>({
    queryKey: resourceKeys.sandboxes(status),
    queryFn: () => getSandboxResources(status),
    refetchInterval: 10000, // Refresh every 10 seconds for real-time monitoring
  })
}

/**
 * Hook to fetch a specific sandbox resource
 */
export function useSandboxResource(sandboxId: string, enabled = true) {
  return useQuery<SandboxResource>({
    queryKey: resourceKeys.sandbox(sandboxId),
    queryFn: () => getSandboxResource(sandboxId),
    enabled: enabled && !!sandboxId,
    refetchInterval: 5000, // Refresh every 5 seconds for real-time updates
  })
}

/**
 * Hook to fetch historical metrics for a sandbox
 */
export function useSandboxMetricsHistory(
  sandboxId: string,
  hours: number = 1,
  enabled = true
) {
  return useQuery<ResourceMetricsHistory[]>({
    queryKey: resourceKeys.history(sandboxId, hours),
    queryFn: () => getSandboxMetricsHistory(sandboxId, hours),
    enabled: enabled && !!sandboxId,
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

/**
 * Hook to fetch resource summary
 */
export function useResourceSummary() {
  return useQuery<ResourceSummary>({
    queryKey: resourceKeys.summary(),
    queryFn: getResourceSummary,
    refetchInterval: 15000, // Refresh every 15 seconds
  })
}

/**
 * Hook to update sandbox allocation
 */
export function useUpdateSandboxAllocation() {
  const queryClient = useQueryClient()

  return useMutation<
    UpdateAllocationResponse,
    Error,
    { sandboxId: string; allocation: UpdateAllocationRequest }
  >({
    mutationFn: ({ sandboxId, allocation }) =>
      updateSandboxAllocation(sandboxId, allocation),
    onSuccess: (data, variables) => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: resourceKeys.sandboxes() })
      queryClient.invalidateQueries({
        queryKey: resourceKeys.sandbox(variables.sandboxId),
      })
      queryClient.invalidateQueries({ queryKey: resourceKeys.summary() })
    },
  })
}
