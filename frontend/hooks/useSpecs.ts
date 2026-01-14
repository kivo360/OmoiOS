import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  listProjectSpecs,
  createSpec,
  getSpec,
  updateSpec,
  deleteSpec,
  addRequirement,
  updateRequirement,
  deleteRequirement,
  addCriterion,
  updateCriterion,
  deleteCriterion,
  updateDesign,
  addTask,
  updateTask,
  deleteTask,
  approveRequirements,
  approveDesign,
  listSpecVersions,
  executeSpecTasks,
  getExecutionStatus,
  getCriteriaStatus,
  createSpecBranch,
  createSpecPR,
  launchSpec,
  getSpecEvents,
} from "@/lib/api/specs"
import type {
  Spec,
  SpecListResponse,
  SpecCreate,
  SpecUpdate,
  RequirementCreate,
  RequirementUpdate,
  CriterionCreate,
  CriterionUpdate,
  DesignArtifact,
  Requirement,
  AcceptanceCriterion,
  SpecTask,
  TaskCreate,
  TaskUpdate,
  SpecVersionListResponse,
  ExecuteTasksRequest,
  ExecuteTasksResponse,
  ExecutionStatusResponse,
  CriteriaStatusResponse,
  CreateBranchResponse,
  CreatePRResponse,
  SpecLaunchRequest,
  SpecLaunchResponse,
  SpecEventsResponse,
  GetSpecEventsParams,
} from "@/lib/api/specs"

export const specsKeys = {
  all: ["specs"] as const,
  project: (projectId: string) => [...specsKeys.all, "project", projectId] as const,
  detail: (specId: string) => [...specsKeys.all, "detail", specId] as const,
  versions: (specId: string) => [...specsKeys.all, "versions", specId] as const,
  executionStatus: (specId: string) => [...specsKeys.all, "execution", specId] as const,
  criteriaStatus: (specId: string) => [...specsKeys.all, "criteria", specId] as const,
  events: (specId: string) => [...specsKeys.all, "events", specId] as const,
}

/**
 * Hook to list specs for a project
 *
 * @param projectId - The project ID
 * @param options.status - Optional status filter
 * @param options.refetchInterval - Polling interval in ms (default: false)
 *
 * @example
 * // Poll every 5s when any spec is executing
 * const { data } = useProjectSpecs(projectId, {
 *   refetchInterval: (query) => {
 *     const hasExecuting = query.state.data?.specs.some(s => s.status === "executing")
 *     return hasExecuting ? 5000 : false
 *   }
 * })
 */
export function useProjectSpecs(
  projectId: string | undefined,
  options?: {
    status?: string
    refetchInterval?: number | false | ((query: { state: { data: SpecListResponse | undefined } }) => number | false)
  }
) {
  const { status, refetchInterval } = options || {}
  return useQuery<SpecListResponse>({
    queryKey: specsKeys.project(projectId!),
    queryFn: () => listProjectSpecs(projectId!, { status }),
    enabled: !!projectId,
    refetchInterval: refetchInterval as any, // TanStack Query supports function callback
  })
}

/**
 * Hook to get a single spec
 *
 * @param specId - The spec ID to get
 * @param options.enabled - Whether to enable the query (default: true if specId provided)
 * @param options.refetchInterval - Polling interval in ms, or function that receives query and returns interval (default: false)
 *
 * @example
 * // Poll every 5s when spec is executing to see task status updates
 * const { data: spec } = useSpec(specId, {
 *   refetchInterval: (query) => {
 *     return query.state.data?.status === "executing" ? 5000 : false
 *   },
 * })
 */
export function useSpec(
  specId: string | undefined,
  options?: {
    enabled?: boolean
    refetchInterval?: number | false | ((query: { state: { data: Spec | undefined } }) => number | false)
  }
) {
  return useQuery<Spec>({
    queryKey: specsKeys.detail(specId!),
    queryFn: () => getSpec(specId!),
    enabled: options?.enabled ?? !!specId,
    refetchInterval: options?.refetchInterval as any, // TanStack Query supports function callback
  })
}

/**
 * Hook to create a spec
 */
export function useCreateSpec() {
  const queryClient = useQueryClient()

  return useMutation<Spec, Error, SpecCreate>({
    mutationFn: createSpec,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: specsKeys.project(data.project_id) })
    },
  })
}

/**
 * Hook to update a spec
 */
export function useUpdateSpec(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<Spec, Error, SpecUpdate>({
    mutationFn: (data) => updateSpec(specId, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
      queryClient.invalidateQueries({ queryKey: specsKeys.project(data.project_id) })
    },
  })
}

/**
 * Hook to delete a spec
 */
export function useDeleteSpec() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, { specId: string; projectId: string }>({
    mutationFn: ({ specId }) => deleteSpec(specId),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: specsKeys.project(projectId) })
    },
  })
}

/**
 * Hook to add a requirement
 */
export function useAddRequirement(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<Requirement, Error, RequirementCreate>({
    mutationFn: (data) => addRequirement(specId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to update a requirement
 */
export function useUpdateRequirement(specId: string, reqId: string) {
  const queryClient = useQueryClient()

  return useMutation<Requirement, Error, RequirementUpdate>({
    mutationFn: (data) => updateRequirement(specId, reqId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to delete a requirement
 */
export function useDeleteRequirement(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (reqId) => deleteRequirement(specId, reqId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to add a criterion
 */
export function useAddCriterion(specId: string, reqId: string) {
  const queryClient = useQueryClient()

  return useMutation<AcceptanceCriterion, Error, CriterionCreate>({
    mutationFn: (data) => addCriterion(specId, reqId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to update a criterion
 */
export function useUpdateCriterion(specId: string, reqId: string) {
  const queryClient = useQueryClient()

  return useMutation<AcceptanceCriterion, Error, { criterionId: string; data: CriterionUpdate }>({
    mutationFn: ({ criterionId, data }) => updateCriterion(specId, reqId, criterionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to update design
 */
export function useUpdateDesign(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<DesignArtifact, Error, DesignArtifact>({
    mutationFn: (design) => updateDesign(specId, design),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to approve requirements
 */
export function useApproveRequirements(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<{ message: string }, Error, void>({
    mutationFn: () => approveRequirements(specId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to approve design
 */
export function useApproveDesign(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<{ message: string }, Error, void>({
    mutationFn: () => approveDesign(specId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to add a task
 */
export function useAddTask(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<SpecTask, Error, TaskCreate>({
    mutationFn: (data) => addTask(specId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to update a task
 */
export function useUpdateTask(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<SpecTask, Error, { taskId: string; data: TaskUpdate }>({
    mutationFn: ({ taskId, data }) => updateTask(specId, taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to delete a task
 */
export function useDeleteTask(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (taskId) => deleteTask(specId, taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to delete a criterion
 */
export function useDeleteCriterion(specId: string, reqId: string) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (criterionId) => deleteCriterion(specId, reqId, criterionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to list version history for a spec
 */
export function useSpecVersions(specId: string | undefined, limit?: number) {
  return useQuery<SpecVersionListResponse>({
    queryKey: specsKeys.versions(specId!),
    queryFn: () => listSpecVersions(specId!, limit),
    enabled: !!specId,
  })
}

// ============================================================================
// Spec Execution Hooks
// ============================================================================

/**
 * Hook to execute spec tasks via sandbox system.
 * Converts pending SpecTasks to executable Tasks and queues them for Daytona sandboxes.
 */
export function useExecuteSpecTasks(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<ExecuteTasksResponse, Error, ExecuteTasksRequest | undefined>({
    mutationFn: (request) => executeSpecTasks(specId, request),
    onSuccess: () => {
      // Invalidate spec detail to refresh task statuses
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
      // Invalidate execution status
      queryClient.invalidateQueries({ queryKey: specsKeys.executionStatus(specId) })
    },
  })
}

/**
 * Hook to get execution status for a spec's tasks.
 * Returns task counts by status and overall progress percentage.
 *
 * @param specId - The spec ID to get execution status for
 * @param options.enabled - Whether to enable the query (default: true if specId provided)
 * @param options.refetchInterval - Polling interval in ms (default: disabled)
 */
export function useExecutionStatus(
  specId: string | undefined,
  options?: {
    enabled?: boolean
    refetchInterval?: number | false
  }
) {
  return useQuery<ExecutionStatusResponse>({
    queryKey: specsKeys.executionStatus(specId!),
    queryFn: () => getExecutionStatus(specId!),
    enabled: options?.enabled ?? !!specId,
    refetchInterval: options?.refetchInterval,
  })
}

/**
 * Hook to get acceptance criteria status for a spec.
 * Returns completion status for all criteria organized by requirement.
 *
 * @param specId - The spec ID to get criteria status for
 * @param options.enabled - Whether to enable the query (default: true if specId provided)
 * @param options.refetchInterval - Polling interval in ms (default: disabled)
 */
export function useCriteriaStatus(
  specId: string | undefined,
  options?: {
    enabled?: boolean
    refetchInterval?: number | false
  }
) {
  return useQuery<CriteriaStatusResponse>({
    queryKey: specsKeys.criteriaStatus(specId!),
    queryFn: () => getCriteriaStatus(specId!),
    enabled: options?.enabled ?? !!specId,
    refetchInterval: options?.refetchInterval,
  })
}

// ============================================================================
// GitHub/PR Integration Hooks
// ============================================================================

/**
 * Hook to create a git branch for a spec.
 * Creates a branch in the project's GitHub repository for the spec's work.
 */
export function useCreateSpecBranch(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<CreateBranchResponse, Error, void>({
    mutationFn: () => createSpecBranch(specId),
    onSuccess: () => {
      // Invalidate spec detail to refresh branch_name
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to create a pull request for a completed spec.
 * Optionally force PR creation even if some tasks aren't completed.
 */
export function useCreateSpecPR(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<CreatePRResponse, Error, { force?: boolean } | undefined>({
    mutationFn: (options) => createSpecPR(specId, options?.force),
    onSuccess: () => {
      // Invalidate spec detail to refresh PR tracking fields
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

// ============================================================================
// Spec Launch Hook (Command Page Integration)
// ============================================================================

/**
 * Hook to launch a new spec directly from the command page.
 * This is the preferred entry point for spec-driven mode, bypassing ticket creation.
 * Creates a spec and optionally starts sandbox execution immediately.
 *
 * @returns Mutation with spec_id and sandbox_id for navigation
 */
export function useLaunchSpec() {
  const queryClient = useQueryClient()

  return useMutation<SpecLaunchResponse, Error, SpecLaunchRequest>({
    mutationFn: launchSpec,
    onSuccess: (data, variables) => {
      // Invalidate project specs list to show the new spec
      queryClient.invalidateQueries({ queryKey: specsKeys.project(variables.project_id) })
    },
  })
}

// ============================================================================
// Spec Events Hook (Real-time monitoring)
// ============================================================================

/**
 * Hook to get real-time events for a spec.
 * Returns sandbox events from all sandboxes associated with this spec,
 * ordered by creation time (newest first).
 *
 * Use refetchInterval for real-time updates during spec execution.
 * Recommended: 2000ms (2s) for active execution, false when idle.
 *
 * @param specId - The spec ID to get events for
 * @param options.enabled - Whether to enable the query (default: true if specId provided)
 * @param options.refetchInterval - Polling interval in ms for real-time updates (default: false)
 * @param options.limit - Max events to return (default: 100)
 * @param options.eventType - Filter by specific event type (optional)
 *
 * @example
 * // Poll every 2s when spec is executing
 * const { data: events } = useSpecEvents(specId, {
 *   enabled: spec?.status === "executing",
 *   refetchInterval: spec?.status === "executing" ? 2000 : false,
 * })
 */
export function useSpecEvents(
  specId: string | undefined,
  options?: {
    enabled?: boolean
    refetchInterval?: number | false
    limit?: number
    eventType?: string
  }
) {
  const params: GetSpecEventsParams = {}
  if (options?.limit) params.limit = options.limit
  if (options?.eventType) params.event_type = options.eventType

  return useQuery<SpecEventsResponse>({
    queryKey: [...specsKeys.events(specId!), params],
    queryFn: () => getSpecEvents(specId!, params),
    enabled: options?.enabled ?? !!specId,
    refetchInterval: options?.refetchInterval,
  })
}
