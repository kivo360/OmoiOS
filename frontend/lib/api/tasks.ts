/**
 * Tasks API functions
 */

import { apiRequest } from "./client"
import type {
  Task,
  TaskListItem,
  TaskDependencies,
} from "./types"

export interface ListTasksParams {
  status?: string
  phase_id?: string
  has_sandbox?: boolean
  limit?: number
}

/**
 * List tasks with optional filtering
 */
export async function listTasks(params?: ListTasksParams): Promise<TaskListItem[]> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set("status", params.status)
  if (params?.phase_id) searchParams.set("phase_id", params.phase_id)
  if (params?.has_sandbox !== undefined) searchParams.set("has_sandbox", String(params.has_sandbox))
  if (params?.limit) searchParams.set("limit", String(params.limit))

  const query = searchParams.toString()
  const url = query ? `/api/v1/tasks?${query}` : "/api/v1/tasks"

  return apiRequest<TaskListItem[]>(url)
}

/**
 * List tasks that have sandboxes (convenience function)
 */
export async function listSandboxTasks(params?: Omit<ListTasksParams, "has_sandbox">): Promise<TaskListItem[]> {
  return listTasks({ ...params, has_sandbox: true })
}

/**
 * Get a specific task by ID
 */
export async function getTask(taskId: string): Promise<Task> {
  return apiRequest<Task>(`/api/v1/tasks/${taskId}`)
}

/**
 * Get task dependencies information
 */
export async function getTaskDependencies(taskId: string): Promise<TaskDependencies> {
  return apiRequest<TaskDependencies>(`/api/v1/tasks/${taskId}/dependencies`)
}

/**
 * Add dependencies to a task
 */
export async function addTaskDependencies(
  taskId: string,
  dependsOn: string[]
): Promise<TaskDependencies> {
  return apiRequest<TaskDependencies>(`/api/v1/tasks/${taskId}/dependencies`, {
    method: "POST",
    body: { depends_on: dependsOn },
  })
}

/**
 * Set all dependencies for a task (replace)
 */
export async function setTaskDependencies(
  taskId: string,
  dependsOn: string[]
): Promise<TaskDependencies> {
  return apiRequest<TaskDependencies>(`/api/v1/tasks/${taskId}/dependencies`, {
    method: "PUT",
    body: { depends_on: dependsOn },
  })
}

/**
 * Remove a specific dependency from a task
 */
export async function removeTaskDependency(
  taskId: string,
  dependsOnTaskId: string
): Promise<TaskDependencies> {
  return apiRequest<TaskDependencies>(
    `/api/v1/tasks/${taskId}/dependencies/${dependsOnTaskId}`,
    { method: "DELETE" }
  )
}

/**
 * Check for circular dependencies
 */
export async function checkCircularDependencies(
  taskId: string,
  dependsOn: string[]
): Promise<{ has_circular_dependency: boolean; cycle: string[] | null }> {
  return apiRequest<{ has_circular_dependency: boolean; cycle: string[] | null }>(
    `/api/v1/tasks/${taskId}/check-circular`,
    {
      method: "POST",
      body: dependsOn,
    }
  )
}

/**
 * Cancel a running task
 */
export async function cancelTask(
  taskId: string,
  reason = "cancelled_by_request"
): Promise<{ task_id: string; cancelled: boolean; reason: string }> {
  return apiRequest<{ task_id: string; cancelled: boolean; reason: string }>(
    `/api/v1/tasks/${taskId}/cancel`,
    {
      method: "POST",
      body: { reason },
    }
  )
}

/**
 * Get timeout status for a task
 */
export async function getTaskTimeoutStatus(taskId: string): Promise<{
  exists: boolean
  task_id?: string
  timeout_seconds?: number
  started_at?: string
  elapsed_time?: number
  is_timed_out?: boolean
}> {
  return apiRequest(`/api/v1/tasks/${taskId}/timeout-status`)
}

/**
 * Get all timed-out tasks
 */
export async function getTimedOutTasks(): Promise<TaskListItem[]> {
  return apiRequest<TaskListItem[]>("/api/v1/tasks/timed-out")
}

/**
 * Get cancellable tasks
 */
export async function getCancellableTasks(agentId?: string): Promise<TaskListItem[]> {
  const url = agentId
    ? `/api/v1/tasks/cancellable?agent_id=${agentId}`
    : "/api/v1/tasks/cancellable"
  return apiRequest<TaskListItem[]>(url)
}

/**
 * Cleanup timed-out tasks
 */
export async function cleanupTimedOutTasks(): Promise<{
  cleaned_count: number
  total_timed_out: number
}> {
  return apiRequest<{ cleaned_count: number; total_timed_out: number }>(
    "/api/v1/tasks/cleanup-timed-out",
    { method: "POST" }
  )
}

/**
 * Set timeout for a task
 */
export async function setTaskTimeout(
  taskId: string,
  timeoutSeconds: number
): Promise<{ task_id: string; timeout_seconds: number; status: string }> {
  return apiRequest<{ task_id: string; timeout_seconds: number; status: string }>(
    `/api/v1/tasks/${taskId}/set-timeout`,
    {
      method: "POST",
      body: { timeout_seconds: timeoutSeconds },
    }
  )
}

/**
 * Register conversation from sandbox
 */
export async function registerConversation(
  taskId: string,
  conversationId: string,
  sandboxId?: string,
  persistenceDir?: string
): Promise<{ success: boolean; task_id: string; conversation_id: string }> {
  return apiRequest<{ success: boolean; task_id: string; conversation_id: string }>(
    `/api/v1/tasks/${taskId}/register-conversation`,
    {
      method: "POST",
      body: {
        conversation_id: conversationId,
        sandbox_id: sandboxId || "",
        persistence_dir: persistenceDir || "",
      },
    }
  )
}
