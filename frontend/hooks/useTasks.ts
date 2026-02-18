/**
 * React Query hooks for Tasks API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listTasks,
  listSandboxTasks,
  getTask,
  getTaskDependencies,
  addTaskDependencies,
  setTaskDependencies,
  removeTaskDependency,
  cancelTask,
  failTask,
  getTaskTimeoutStatus,
  getTimedOutTasks,
  getCancellableTasks,
  cleanupTimedOutTasks,
  setTaskTimeout,
  type ListTasksParams,
} from "@/lib/api/tasks";
import type { Task, TaskListItem, TaskDependencies } from "@/lib/api/types";

// Query keys
export const taskKeys = {
  all: ["tasks"] as const,
  lists: () => [...taskKeys.all, "list"] as const,
  list: (params?: ListTasksParams) => [...taskKeys.lists(), params] as const,
  sandboxList: (params?: Omit<ListTasksParams, "has_sandbox">) =>
    [...taskKeys.lists(), "sandbox", params] as const,
  details: () => [...taskKeys.all, "detail"] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
  dependencies: (id: string) =>
    [...taskKeys.detail(id), "dependencies"] as const,
  timeout: (id: string) => [...taskKeys.detail(id), "timeout"] as const,
  timedOut: () => [...taskKeys.all, "timed-out"] as const,
  cancellable: (agentId?: string) =>
    [...taskKeys.all, "cancellable", agentId] as const,
};

/**
 * Hook to fetch list of tasks
 */
export function useTasks(params?: ListTasksParams) {
  return useQuery<TaskListItem[]>({
    queryKey: taskKeys.list(params),
    queryFn: () => listTasks(params),
  });
}

/**
 * Hook to fetch tasks that have sandboxes
 */
export function useSandboxTasks(params?: Omit<ListTasksParams, "has_sandbox">) {
  return useQuery<TaskListItem[]>({
    queryKey: taskKeys.sandboxList(params),
    queryFn: () => listSandboxTasks(params),
  });
}

/**
 * Hook to fetch a single task
 */
export function useTask(taskId: string | undefined) {
  return useQuery<Task>({
    queryKey: taskKeys.detail(taskId!),
    queryFn: () => getTask(taskId!),
    enabled: !!taskId,
  });
}

/**
 * Hook to fetch task dependencies
 */
export function useTaskDependencies(taskId: string | undefined) {
  return useQuery<TaskDependencies>({
    queryKey: taskKeys.dependencies(taskId!),
    queryFn: () => getTaskDependencies(taskId!),
    enabled: !!taskId,
  });
}

/**
 * Hook to fetch task timeout status
 */
export function useTaskTimeoutStatus(taskId: string | undefined) {
  return useQuery({
    queryKey: taskKeys.timeout(taskId!),
    queryFn: () => getTaskTimeoutStatus(taskId!),
    enabled: !!taskId,
    refetchInterval: 10000, // Check every 10 seconds
  });
}

/**
 * Hook to fetch timed-out tasks
 */
export function useTimedOutTasks() {
  return useQuery<TaskListItem[]>({
    queryKey: taskKeys.timedOut(),
    queryFn: getTimedOutTasks,
    refetchInterval: 30000,
  });
}

/**
 * Hook to fetch cancellable tasks
 */
export function useCancellableTasks(agentId?: string) {
  return useQuery<TaskListItem[]>({
    queryKey: taskKeys.cancellable(agentId),
    queryFn: () => getCancellableTasks(agentId),
  });
}

/**
 * Hook to add task dependencies
 */
export function useAddTaskDependencies() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      taskId,
      dependsOn,
    }: {
      taskId: string;
      dependsOn: string[];
    }) => addTaskDependencies(taskId, dependsOn),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({
        queryKey: taskKeys.dependencies(taskId),
      });
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
    },
  });
}

/**
 * Hook to set task dependencies (replace all)
 */
export function useSetTaskDependencies() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      taskId,
      dependsOn,
    }: {
      taskId: string;
      dependsOn: string[];
    }) => setTaskDependencies(taskId, dependsOn),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({
        queryKey: taskKeys.dependencies(taskId),
      });
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
    },
  });
}

/**
 * Hook to remove a task dependency
 */
export function useRemoveTaskDependency() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      taskId,
      dependsOnTaskId,
    }: {
      taskId: string;
      dependsOnTaskId: string;
    }) => removeTaskDependency(taskId, dependsOnTaskId),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({
        queryKey: taskKeys.dependencies(taskId),
      });
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
    },
  });
}

/**
 * Hook to cancel a task
 */
export function useCancelTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ taskId, reason }: { taskId: string; reason?: string }) =>
      cancelTask(taskId, reason),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.invalidateQueries({ queryKey: taskKeys.timedOut() });
      queryClient.invalidateQueries({ queryKey: taskKeys.cancellable() });
    },
  });
}

/**
 * Hook to mark a task as failed
 */
export function useFailTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ taskId, reason }: { taskId: string; reason?: string }) =>
      failTask(taskId, reason),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.invalidateQueries({ queryKey: taskKeys.timedOut() });
      queryClient.invalidateQueries({ queryKey: taskKeys.cancellable() });
    },
  });
}

/**
 * Hook to set task timeout
 */
export function useSetTaskTimeout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      taskId,
      timeoutSeconds,
    }: {
      taskId: string;
      timeoutSeconds: number;
    }) => setTaskTimeout(taskId, timeoutSeconds),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
      queryClient.invalidateQueries({ queryKey: taskKeys.timeout(taskId) });
    },
  });
}

/**
 * Hook to cleanup timed-out tasks
 */
export function useCleanupTimedOutTasks() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cleanupTimedOutTasks,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.invalidateQueries({ queryKey: taskKeys.timedOut() });
    },
  });
}
