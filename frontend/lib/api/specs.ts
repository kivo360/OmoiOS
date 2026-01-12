import { apiRequest } from "./client"

// Types
export interface AcceptanceCriterion {
  id: string
  text: string
  completed: boolean
}

export interface Requirement {
  id: string
  title: string
  condition: string
  action: string
  criteria: AcceptanceCriterion[]
  linked_design: string | null
  status: string
}

export interface ApiEndpoint {
  method: string
  endpoint: string
  description: string
}

export interface DesignArtifact {
  architecture: string | null
  data_model: string | null
  api_spec: ApiEndpoint[]
}

export interface SpecTask {
  id: string
  title: string
  description: string
  phase: string
  priority: string
  status: string
  assigned_agent: string | null
  dependencies: string[]
  estimated_hours: number | null
  actual_hours: number | null
}

export interface SpecExecution {
  overall_progress: number
  test_coverage: number
  tests_total: number
  tests_passing: number
  active_agents: number
  commits: number
  lines_added: number
  lines_removed: number
}

export interface Spec {
  id: string
  project_id: string
  title: string
  description: string | null
  status: string
  phase: string
  progress: number
  test_coverage: number
  active_agents: number
  linked_tickets: number
  requirements: Requirement[]
  design: DesignArtifact | null
  tasks: SpecTask[]
  execution: SpecExecution | null
  created_at: string
  updated_at: string
}

export interface SpecListResponse {
  specs: Spec[]
  total: number
}

export interface SpecCreate {
  title: string
  description?: string
  project_id: string
}

export interface SpecUpdate {
  title?: string
  description?: string
  status?: string
  phase?: string
}

export interface RequirementCreate {
  title: string
  condition: string
  action: string
}

export interface RequirementUpdate {
  title?: string
  condition?: string
  action?: string
  status?: string
}

export interface CriterionCreate {
  text: string
}

export interface CriterionUpdate {
  text?: string
  completed?: boolean
}

// API Functions

/**
 * List specs for a project
 */
export async function listProjectSpecs(
  projectId: string,
  params?: { status?: string }
): Promise<SpecListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.status) {
    searchParams.set("status", params.status)
  }
  const query = searchParams.toString()
  return apiRequest<SpecListResponse>(
    `/api/v1/specs/project/${projectId}${query ? `?${query}` : ""}`
  )
}

/**
 * Create a new spec
 */
export async function createSpec(data: SpecCreate): Promise<Spec> {
  return apiRequest<Spec>("/api/v1/specs", {
    method: "POST",
    body: data,
  })
}

/**
 * Get a spec by ID
 */
export async function getSpec(specId: string): Promise<Spec> {
  return apiRequest<Spec>(`/api/v1/specs/${specId}`)
}

/**
 * Update a spec
 */
export async function updateSpec(specId: string, data: SpecUpdate): Promise<Spec> {
  return apiRequest<Spec>(`/api/v1/specs/${specId}`, {
    method: "PATCH",
    body: data,
  })
}

/**
 * Delete a spec
 */
export async function deleteSpec(specId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/specs/${specId}`, {
    method: "DELETE",
  })
}

// Requirements

/**
 * Add a requirement to a spec
 */
export async function addRequirement(
  specId: string,
  data: RequirementCreate
): Promise<Requirement> {
  return apiRequest<Requirement>(`/api/v1/specs/${specId}/requirements`, {
    method: "POST",
    body: data,
  })
}

/**
 * Update a requirement
 */
export async function updateRequirement(
  specId: string,
  reqId: string,
  data: RequirementUpdate
): Promise<Requirement> {
  return apiRequest<Requirement>(`/api/v1/specs/${specId}/requirements/${reqId}`, {
    method: "PATCH",
    body: data,
  })
}

/**
 * Delete a requirement
 */
export async function deleteRequirement(
  specId: string,
  reqId: string
): Promise<void> {
  return apiRequest<void>(`/api/v1/specs/${specId}/requirements/${reqId}`, {
    method: "DELETE",
  })
}

// Acceptance Criteria

/**
 * Add a criterion to a requirement
 */
export async function addCriterion(
  specId: string,
  reqId: string,
  data: CriterionCreate
): Promise<AcceptanceCriterion> {
  return apiRequest<AcceptanceCriterion>(
    `/api/v1/specs/${specId}/requirements/${reqId}/criteria`,
    {
      method: "POST",
      body: data,
    }
  )
}

/**
 * Update a criterion
 */
export async function updateCriterion(
  specId: string,
  reqId: string,
  criterionId: string,
  data: CriterionUpdate
): Promise<AcceptanceCriterion> {
  return apiRequest<AcceptanceCriterion>(
    `/api/v1/specs/${specId}/requirements/${reqId}/criteria/${criterionId}`,
    {
      method: "PATCH",
      body: data,
    }
  )
}

// Design

/**
 * Update the design for a spec
 */
export async function updateDesign(
  specId: string,
  design: DesignArtifact
): Promise<DesignArtifact> {
  return apiRequest<DesignArtifact>(`/api/v1/specs/${specId}/design`, {
    method: "PUT",
    body: design,
  })
}

// Tasks

export interface TaskCreate {
  title: string
  description?: string
  phase?: string
  priority?: string
}

export interface TaskUpdate {
  title?: string
  description?: string
  phase?: string
  priority?: string
  status?: string
  assigned_agent?: string | null
}

/**
 * Add a task to a spec
 */
export async function addTask(
  specId: string,
  data: TaskCreate
): Promise<SpecTask> {
  return apiRequest<SpecTask>(`/api/v1/specs/${specId}/tasks`, {
    method: "POST",
    body: data,
  })
}

/**
 * Update a task
 */
export async function updateTask(
  specId: string,
  taskId: string,
  data: TaskUpdate
): Promise<SpecTask> {
  return apiRequest<SpecTask>(`/api/v1/specs/${specId}/tasks/${taskId}`, {
    method: "PATCH",
    body: data,
  })
}

/**
 * Delete a task
 */
export async function deleteTask(
  specId: string,
  taskId: string
): Promise<void> {
  return apiRequest<void>(`/api/v1/specs/${specId}/tasks/${taskId}`, {
    method: "DELETE",
  })
}

/**
 * Delete a criterion from a requirement
 */
export async function deleteCriterion(
  specId: string,
  reqId: string,
  criterionId: string
): Promise<void> {
  return apiRequest<void>(
    `/api/v1/specs/${specId}/requirements/${reqId}/criteria/${criterionId}`,
    {
      method: "DELETE",
    }
  )
}

// Approvals

/**
 * Approve requirements and move to design phase
 */
export async function approveRequirements(specId: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/api/v1/specs/${specId}/approve-requirements`, {
    method: "POST",
  })
}

/**
 * Approve design and move to execution phase
 */
export async function approveDesign(specId: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/api/v1/specs/${specId}/approve-design`, {
    method: "POST",
  })
}

// Version History

export interface SpecVersion {
  id: string
  spec_id: string
  version_number: number
  change_type: string
  change_summary: string
  change_details: Record<string, { old: unknown; new: unknown }> | null
  created_by: string | null
  snapshot: {
    title: string
    description: string | null
    status: string
    phase: string
    progress: number
    requirements_approved: boolean
    design_approved: boolean
  } | null
  created_at: string
}

export interface SpecVersionListResponse {
  versions: SpecVersion[]
  total: number
}

/**
 * List version history for a spec
 */
export async function listSpecVersions(
  specId: string,
  limit?: number
): Promise<SpecVersionListResponse> {
  const params = limit ? `?limit=${limit}` : ""
  return apiRequest<SpecVersionListResponse>(`/api/v1/specs/${specId}/versions${params}`)
}

// ============================================================================
// Task Execution
// ============================================================================

export interface ExecuteTasksRequest {
  task_ids?: string[]
}

export interface ExecuteTasksResponse {
  success: boolean
  message: string
  tasks_created: number
  tasks_skipped: number
  ticket_id: string | null
  errors: string[]
}

export interface ExecutionStatusResponse {
  spec_id: string
  total_tasks: number
  status_counts: Record<string, number>
  progress: number
  is_complete: boolean
}

export interface CriteriaStatusResponse {
  spec_id: string
  total_criteria: number
  completed_criteria: number
  completion_percentage: number
  all_complete: boolean
  by_requirement: Record<string, {
    requirement_title: string
    total: number
    completed: number
    criteria: Array<{
      id: string
      text: string
      completed: boolean
    }>
  }>
}

/**
 * Execute spec tasks via sandbox system.
 * Converts pending SpecTasks to executable Tasks and queues them for Daytona sandboxes.
 * Requires design_approved=true on the spec.
 */
export async function executeSpecTasks(
  specId: string,
  request?: ExecuteTasksRequest
): Promise<ExecuteTasksResponse> {
  return apiRequest<ExecuteTasksResponse>(`/api/v1/specs/${specId}/execute-tasks`, {
    method: "POST",
    body: request || {},
  })
}

/**
 * Get execution status for a spec's tasks.
 * Returns task counts by status and overall progress percentage.
 */
export async function getExecutionStatus(
  specId: string
): Promise<ExecutionStatusResponse> {
  return apiRequest<ExecutionStatusResponse>(`/api/v1/specs/${specId}/execution-status`)
}

/**
 * Get acceptance criteria status for a spec.
 * Returns completion status for all criteria organized by requirement.
 */
export async function getCriteriaStatus(
  specId: string
): Promise<CriteriaStatusResponse> {
  return apiRequest<CriteriaStatusResponse>(`/api/v1/specs/${specId}/criteria-status`)
}
