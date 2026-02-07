/**
 * Resource Monitor API functions
 */

import { apiRequest } from "./client"

// ---------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------

export interface ResourceAllocation {
  cpu_cores: number
  memory_mb: number
  disk_gb: number
}

export interface ResourceUsage {
  cpu_percent: number
  memory_mb: number
  disk_gb: number
}

export interface ResourceStatus {
  sandbox_id: string
  task_id: string | null
  agent_id: string | null
  status: "active" | "paused" | "terminated"
  allocation: ResourceAllocation
  usage: ResourceUsage
  updated_at: string
}

export interface ResourceSummary {
  total_sandboxes: number
  total_cpu_allocated: number
  total_memory_allocated_mb: number
  total_disk_allocated_gb: number
  avg_cpu_usage_percent: number
  avg_memory_usage_percent: number
  avg_disk_usage_percent: number
  high_cpu_count: number
  high_memory_count: number
}

export interface ResourceLimits {
  max_cpu_cores: number
  max_memory_mb: number
  max_disk_gb: number
}

export interface UpdateAllocationRequest {
  cpu_cores?: number
  memory_mb?: number
  disk_gb?: number
}

// ---------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------

/**
 * Get resource status for all sandboxes
 */
export async function listResources(
  status: string = "active"
): Promise<ResourceStatus[]> {
  const url =
    status && status !== "all"
      ? `/api/v1/resources?status=${status}`
      : "/api/v1/resources?status=all"
  return apiRequest<ResourceStatus[]>(url)
}

/**
 * Get resource summary statistics
 */
export async function getResourceSummary(): Promise<ResourceSummary> {
  return apiRequest<ResourceSummary>("/api/v1/resources/summary")
}

/**
 * Get maximum resource limits
 */
export async function getResourceLimits(): Promise<ResourceLimits> {
  return apiRequest<ResourceLimits>("/api/v1/resources/limits")
}

/**
 * Get resource status for a specific sandbox
 */
export async function getResourceStatus(
  sandboxId: string
): Promise<ResourceStatus> {
  return apiRequest<ResourceStatus>(`/api/v1/resources/${sandboxId}`)
}

/**
 * Update resource allocation for a sandbox
 */
export async function updateResourceAllocation(
  sandboxId: string,
  allocation: UpdateAllocationRequest
): Promise<ResourceStatus> {
  return apiRequest<ResourceStatus>(`/api/v1/resources/${sandboxId}/allocation`, {
    method: "PATCH",
    body: allocation,
  })
}

/**
 * Terminate a sandbox resource
 */
export async function terminateResource(
  sandboxId: string
): Promise<{ status: string; sandbox_id: string; terminated: boolean }> {
  return apiRequest<{ status: string; sandbox_id: string; terminated: boolean }>(
    `/api/v1/resources/${sandboxId}`,
    { method: "DELETE" }
  )
}
