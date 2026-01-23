/**
 * React Query hooks for Resource Monitoring API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getResourceSummary,
  getWorkerResources,
  getWorkerResourceHistory,
  getWorkerResourceLimits,
  setWorkerResourceLimits,
  resetWorkerResourceLimits,
  getResourceAlerts,
} from "@/lib/api/resources"
import type {
  ResourceSummary,
  WorkerResourceStatus,
  ResourceHistory,
  ResourceLimits,
  ResourceAlert,
} from "@/lib/api/types"

// Query keys
export const resourceKeys = {
  all: ["resources"] as const,
  summary: () => [...resourceKeys.all, "summary"] as const,
  worker: (workerId: string) => [...resourceKeys.all, "worker", workerId] as const,
  history: (workerId: string, minutes?: number) =>
    [...resourceKeys.all, "history", workerId, minutes] as const,
  limits: (workerId: string) => [...resourceKeys.all, "limits", workerId] as const,
  alerts: () => [...resourceKeys.all, "alerts"] as const,
}

/**
 * Hook to fetch resource summary for all workers
 */
export function useResourceSummary() {
  return useQuery<ResourceSummary>({
    queryKey: resourceKeys.summary(),
    queryFn: getResourceSummary,
    refetchInterval: 15000, // Refresh every 15 seconds
  })
}

/**
 * Hook to fetch resource usage for a specific worker
 */
export function useWorkerResources(workerId: string) {
  return useQuery<WorkerResourceStatus>({
    queryKey: resourceKeys.worker(workerId),
    queryFn: () => getWorkerResources(workerId),
    refetchInterval: 10000, // Refresh every 10 seconds
    enabled: !!workerId,
  })
}

/**
 * Hook to fetch historical resource usage for a worker
 */
export function useWorkerResourceHistory(workerId: string, minutes: number = 30) {
  return useQuery<ResourceHistory>({
    queryKey: resourceKeys.history(workerId, minutes),
    queryFn: () => getWorkerResourceHistory(workerId, minutes),
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: !!workerId,
  })
}

/**
 * Hook to fetch current resource limits for a worker
 */
export function useWorkerResourceLimits(workerId: string) {
  return useQuery<ResourceLimits>({
    queryKey: resourceKeys.limits(workerId),
    queryFn: () => getWorkerResourceLimits(workerId),
    enabled: !!workerId,
  })
}

/**
 * Hook to set resource limits for a worker
 */
export function useSetWorkerResourceLimits() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ workerId, limits }: { workerId: string; limits: ResourceLimits }) =>
      setWorkerResourceLimits(workerId, limits),
    onSuccess: (data, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: resourceKeys.worker(variables.workerId) })
      queryClient.invalidateQueries({ queryKey: resourceKeys.limits(variables.workerId) })
      queryClient.invalidateQueries({ queryKey: resourceKeys.summary() })
    },
  })
}

/**
 * Hook to reset resource limits to defaults for a worker
 */
export function useResetWorkerResourceLimits() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (workerId: string) => resetWorkerResourceLimits(workerId),
    onSuccess: (data, workerId) => {
      queryClient.invalidateQueries({ queryKey: resourceKeys.worker(workerId) })
      queryClient.invalidateQueries({ queryKey: resourceKeys.limits(workerId) })
      queryClient.invalidateQueries({ queryKey: resourceKeys.summary() })
    },
  })
}

/**
 * Hook to fetch all active resource alerts
 */
export function useResourceAlerts() {
  return useQuery<ResourceAlert[]>({
    queryKey: resourceKeys.alerts(),
    queryFn: getResourceAlerts,
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}
