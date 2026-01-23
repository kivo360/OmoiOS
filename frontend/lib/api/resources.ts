/**
 * Resource Monitoring API functions
 */

import { apiRequest } from "./client"
import type {
  ResourceSummary,
  WorkerResourceStatus,
  ResourceHistory,
  ResourceLimits,
  ResourceAllocation,
  ResourceAlert,
} from "./types"

/**
 * Get resource usage summary for all workers
 */
export async function getResourceSummary(): Promise<ResourceSummary> {
  return apiRequest<ResourceSummary>("/api/v1/resources/workers")
}

/**
 * Get resource usage for a specific worker
 */
export async function getWorkerResources(workerId: string): Promise<WorkerResourceStatus> {
  return apiRequest<WorkerResourceStatus>(`/api/v1/resources/workers/${workerId}`)
}

/**
 * Get historical resource usage for a worker
 */
export async function getWorkerResourceHistory(
  workerId: string,
  minutes: number = 30
): Promise<ResourceHistory> {
  return apiRequest<ResourceHistory>(
    `/api/v1/resources/workers/${workerId}/history?minutes=${minutes}`
  )
}

/**
 * Get current resource limits for a worker
 */
export async function getWorkerResourceLimits(workerId: string): Promise<ResourceLimits> {
  return apiRequest<ResourceLimits>(`/api/v1/resources/workers/${workerId}/limits`)
}

/**
 * Set resource limits for a worker
 */
export async function setWorkerResourceLimits(
  workerId: string,
  limits: ResourceLimits
): Promise<ResourceAllocation> {
  return apiRequest<ResourceAllocation>(`/api/v1/resources/workers/${workerId}/limits`, {
    method: "PUT",
    body: limits,
  })
}

/**
 * Reset resource limits to defaults for a worker
 */
export async function resetWorkerResourceLimits(workerId: string): Promise<ResourceAllocation> {
  return apiRequest<ResourceAllocation>(`/api/v1/resources/workers/${workerId}/reset-limits`, {
    method: "POST",
  })
}

/**
 * Get all active resource alerts
 */
export async function getResourceAlerts(): Promise<ResourceAlert[]> {
  return apiRequest<ResourceAlert[]>("/api/v1/resources/alerts")
}
