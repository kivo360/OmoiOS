import { apiRequest } from "./client"
import type {
  DependencyGraphResponse,
  BlockedTasksResponse,
  BlockingTasksResponse,
} from "./types"

/**
 * Get dependency graph for a project
 */
export async function getProjectDependencyGraph(
  projectId: string,
  params?: { includeResolved?: boolean }
): Promise<DependencyGraphResponse> {
  const searchParams = new URLSearchParams()
  if (params?.includeResolved !== undefined) {
    searchParams.set("include_resolved", String(params.includeResolved))
  }
  const query = searchParams.toString()
  return apiRequest<DependencyGraphResponse>(
    `/dependency-graph/project/${projectId}${query ? `?${query}` : ""}`
  )
}

/**
 * Get dependency graph for a ticket
 */
export async function getTicketDependencyGraph(
  ticketId: string,
  params?: { includeResolved?: boolean; includeDiscoveries?: boolean }
): Promise<DependencyGraphResponse> {
  const searchParams = new URLSearchParams()
  if (params?.includeResolved !== undefined) {
    searchParams.set("include_resolved", String(params.includeResolved))
  }
  if (params?.includeDiscoveries !== undefined) {
    searchParams.set("include_discoveries", String(params.includeDiscoveries))
  }
  const query = searchParams.toString()
  return apiRequest<DependencyGraphResponse>(
    `/dependency-graph/ticket/${ticketId}${query ? `?${query}` : ""}`
  )
}

/**
 * Get tasks blocked by a specific task
 */
export async function getBlockedTasks(taskId: string): Promise<BlockedTasksResponse> {
  return apiRequest<BlockedTasksResponse>(`/dependency-graph/task/${taskId}/blocked`)
}

/**
 * Get tasks that block a specific task
 */
export async function getBlockingTasks(taskId: string): Promise<BlockingTasksResponse> {
  return apiRequest<BlockingTasksResponse>(`/dependency-graph/task/${taskId}/blocking`)
}
