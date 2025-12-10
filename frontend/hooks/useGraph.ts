import { useQuery } from "@tanstack/react-query"
import {
  getProjectDependencyGraph,
  getTicketDependencyGraph,
  getBlockedTasks,
  getBlockingTasks,
} from "@/lib/api/graph"
import type {
  DependencyGraphResponse,
  BlockedTasksResponse,
  BlockingTasksResponse,
} from "@/lib/api/types"

export const graphKeys = {
  all: ["graph"] as const,
  project: (projectId: string) => [...graphKeys.all, "project", projectId] as const,
  ticket: (ticketId: string) => [...graphKeys.all, "ticket", ticketId] as const,
  blockedTasks: (taskId: string) => [...graphKeys.all, "blocked", taskId] as const,
  blockingTasks: (taskId: string) => [...graphKeys.all, "blocking", taskId] as const,
}

/**
 * Hook to get project dependency graph
 */
export function useProjectDependencyGraph(
  projectId: string | undefined,
  params?: { includeResolved?: boolean }
) {
  return useQuery<DependencyGraphResponse>({
    queryKey: graphKeys.project(projectId!),
    queryFn: () => getProjectDependencyGraph(projectId!, params),
    enabled: !!projectId,
  })
}

/**
 * Hook to get ticket dependency graph
 */
export function useTicketDependencyGraph(
  ticketId: string | undefined,
  params?: { includeResolved?: boolean; includeDiscoveries?: boolean }
) {
  return useQuery<DependencyGraphResponse>({
    queryKey: graphKeys.ticket(ticketId!),
    queryFn: () => getTicketDependencyGraph(ticketId!, params),
    enabled: !!ticketId,
  })
}

/**
 * Hook to get tasks blocked by a specific task
 */
export function useBlockedTasks(taskId: string | undefined) {
  return useQuery<BlockedTasksResponse>({
    queryKey: graphKeys.blockedTasks(taskId!),
    queryFn: () => getBlockedTasks(taskId!),
    enabled: !!taskId,
  })
}

/**
 * Hook to get tasks that block a specific task
 */
export function useBlockingTasks(taskId: string | undefined) {
  return useQuery<BlockingTasksResponse>({
    queryKey: graphKeys.blockingTasks(taskId!),
    queryFn: () => getBlockingTasks(taskId!),
    enabled: !!taskId,
  })
}
