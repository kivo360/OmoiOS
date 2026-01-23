/**
 * Resource monitoring API functions
 */

import { apiRequest } from "./client"

// Types for resource monitoring
export interface ResourceAllocation {
  cpu_cores: number
  memory_gb: number
  disk_gb: number
}

export interface ResourceUsage {
  cpu_usage_percent: number
  memory_usage_percent: number
  memory_used_mb: number
  disk_usage_percent: number
  disk_used_gb: number
}

export interface SandboxResource {
  sandbox_id: string
  task_id: string | null
  agent_id: string | null
  allocation: ResourceAllocation
  usage: ResourceUsage
  status: string
  last_updated: string
  created_at: string
}

export interface ResourceMetricsHistory {
  cpu_usage_percent: number
  memory_usage_percent: number
  memory_used_mb: number
  disk_usage_percent: number
  disk_used_gb: number
  recorded_at: string
}

export interface ResourceSummary {
  total_sandboxes: number
  total_cpu_allocated: number
  total_memory_allocated_gb: number
  total_disk_allocated_gb: number
  avg_cpu_usage_percent: number
  avg_memory_usage_percent: number
  avg_disk_usage_percent: number
}

export interface UpdateAllocationRequest {
  cpu_cores?: number
  memory_gb?: number
  disk_gb?: number
}

export interface UpdateAllocationResponse {
  success: boolean
  sandbox_id: string
  message: string
  allocation: ResourceAllocation | null
}

/**
 * Get all sandbox resources
 */
export async function getSandboxResources(status?: string): Promise<SandboxResource[]> {
  const url = status
    ? `/api/v1/resources/sandboxes?status=${status}`
    : "/api/v1/resources/sandboxes"
  return apiRequest<SandboxResource[]>(url)
}

/**
 * Get specific sandbox resource
 */
export async function getSandboxResource(sandboxId: string): Promise<SandboxResource> {
  return apiRequest<SandboxResource>(`/api/v1/resources/sandboxes/${sandboxId}`)
}

/**
 * Update resource allocation for a sandbox
 */
export async function updateSandboxAllocation(
  sandboxId: string,
  allocation: UpdateAllocationRequest
): Promise<UpdateAllocationResponse> {
  return apiRequest<UpdateAllocationResponse>(
    `/api/v1/resources/sandboxes/${sandboxId}/allocate`,
    {
      method: "POST",
      body: allocation,
    }
  )
}

/**
 * Get historical metrics for a sandbox
 */
export async function getSandboxMetricsHistory(
  sandboxId: string,
  hours: number = 1,
  limit: number = 100
): Promise<ResourceMetricsHistory[]> {
  return apiRequest<ResourceMetricsHistory[]>(
    `/api/v1/resources/sandboxes/${sandboxId}/history?hours=${hours}&limit=${limit}`
  )
}

/**
 * Get resource summary across all sandboxes
 */
export async function getResourceSummary(): Promise<ResourceSummary> {
  return apiRequest<ResourceSummary>("/api/v1/resources/summary")
}
