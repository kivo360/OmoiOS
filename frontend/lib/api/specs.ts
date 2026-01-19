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
  current_phase: string  // State machine phase: explore, requirements, design, tasks, sync, complete
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

  // GitHub/PR tracking fields
  branch_name: string | null
  pull_request_url: string | null
  pull_request_number: number | null
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

// ============================================================================
// GitHub/PR Integration
// ============================================================================

export interface CreateBranchResponse {
  success: boolean
  branch_name?: string
  error?: string
}

export interface CreatePRResponse {
  success: boolean
  pr_number?: number
  pr_url?: string
  error?: string
  already_exists?: boolean
  incomplete_tasks?: string[]
}

/**
 * Create a git branch for a spec.
 * This creates a branch in the project's GitHub repository for the spec's work.
 */
export async function createSpecBranch(specId: string): Promise<CreateBranchResponse> {
  return apiRequest<CreateBranchResponse>(`/api/v1/specs/${specId}/create-branch`, {
    method: "POST",
  })
}

/**
 * Create a pull request for a completed spec.
 * Optionally force PR creation even if some tasks aren't completed.
 */
export async function createSpecPR(
  specId: string,
  force?: boolean
): Promise<CreatePRResponse> {
  return apiRequest<CreatePRResponse>(`/api/v1/specs/${specId}/create-pr`, {
    method: "POST",
    body: { force: force || false },
  })
}

// ============================================================================
// Spec Launch (Direct spec creation from command page)
// ============================================================================

export interface SpecLaunchRequest {
  title: string
  description: string
  project_id: string
  working_directory?: string
  auto_execute?: boolean
}

export interface SpecLaunchResponse {
  spec_id: string
  sandbox_id: string | null
  status: string
  message: string
}

/**
 * Launch a new spec directly (bypassing ticket creation).
 * This is the preferred entry point from the command page for spec-driven mode.
 * Creates a spec and optionally starts sandbox execution immediately.
 */
export async function launchSpec(
  request: SpecLaunchRequest
): Promise<SpecLaunchResponse> {
  return apiRequest<SpecLaunchResponse>("/api/v1/specs/launch", {
    method: "POST",
    body: request,
  })
}

// ============================================================================
// Spec Events (Real-time monitoring)
// ============================================================================

export interface SpecEventItem {
  id: string
  sandbox_id: string
  spec_id: string | null
  event_type: string
  event_data: Record<string, unknown>
  source: string
  created_at: string
}

export interface SpecEventsResponse {
  spec_id: string
  events: SpecEventItem[]
  total_count: number
  has_more: boolean
}

export interface GetSpecEventsParams {
  limit?: number
  offset?: number
  event_type?: string
}

/**
 * Get sandbox events for a spec.
 * Returns events from all sandboxes associated with this spec,
 * ordered by creation time (newest first). Useful for real-time
 * monitoring of spec-driven development progress.
 */
export async function getSpecEvents(
  specId: string,
  params?: GetSpecEventsParams
): Promise<SpecEventsResponse> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set("limit", params.limit.toString())
  if (params?.offset) searchParams.set("offset", params.offset.toString())
  if (params?.event_type) searchParams.set("event_type", params.event_type)

  const query = searchParams.toString()
  return apiRequest<SpecEventsResponse>(
    `/api/v1/specs/${specId}/events${query ? `?${query}` : ""}`
  )
}

// ============================================================================
// Linked Tickets
// ============================================================================

export interface LinkedTicket {
  id: string
  title: string
  description: string | null
  status: string
  priority: string
  phase_id: string
  created_at: string | null
}

export interface LinkTicketsRequest {
  ticket_ids: string[]
}

export interface LinkTicketsResponse {
  spec_id: string
  linked_count: number
  already_linked_count: number
  ticket_ids: string[]
}

export interface LinkedTicketsResponse {
  spec_id: string
  tickets: LinkedTicket[]
  total: number
}

/**
 * Link tickets to a spec.
 * Associates one or more tickets with this specification.
 */
export async function linkTicketsToSpec(
  specId: string,
  ticketIds: string[]
): Promise<LinkTicketsResponse> {
  return apiRequest<LinkTicketsResponse>(`/api/v1/specs/${specId}/link-tickets`, {
    method: "POST",
    body: { ticket_ids: ticketIds },
  })
}

/**
 * Unlink tickets from a spec.
 * Removes the association between tickets and this specification.
 */
export async function unlinkTicketsFromSpec(
  specId: string,
  ticketIds: string[]
): Promise<{ spec_id: string; unlinked_count: number }> {
  return apiRequest<{ spec_id: string; unlinked_count: number }>(
    `/api/v1/specs/${specId}/unlink-tickets`,
    {
      method: "POST",
      body: { ticket_ids: ticketIds },
    }
  )
}

/**
 * Get tickets linked to a spec.
 * Returns all tickets that are associated with this specification.
 */
export async function getLinkedTickets(specId: string): Promise<LinkedTicketsResponse> {
  return apiRequest<LinkedTicketsResponse>(`/api/v1/specs/${specId}/linked-tickets`)
}

// ============================================================================
// Export
// ============================================================================

export type SpecExportFormat = "json" | "markdown"

/**
 * Export a spec in JSON or Markdown format.
 * Returns the spec data in the requested format.
 */
export async function exportSpec(
  specId: string,
  format: SpecExportFormat = "json"
): Promise<unknown> {
  // For markdown, we need to handle it differently since it returns text
  if (format === "markdown") {
    const response = await fetch(`/api/v1/specs/${specId}/export?format=markdown`, {
      credentials: "include",
    })
    if (!response.ok) {
      throw new Error(`Failed to export spec: ${response.statusText}`)
    }
    return response.text()
  }
  return apiRequest<unknown>(`/api/v1/specs/${specId}/export?format=${format}`)
}
