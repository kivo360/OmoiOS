/**
 * TypeScript types for API responses
 * Matches backend Pydantic schemas in omoi_os/schemas/auth.py
 */

// ============================================================================
// User Types
// ============================================================================

export interface User {
  id: string
  email: string
  full_name: string | null
  department: string | null
  is_active: boolean
  is_verified: boolean
  is_super_admin: boolean
  avatar_url: string | null
  attributes: Record<string, unknown> | null
  created_at: string
  last_login_at: string | null
}

export interface UserCreate {
  email: string
  password: string
  full_name?: string
  department?: string
}

export interface UserUpdate {
  full_name?: string
  department?: string
  attributes?: Record<string, unknown>
}

// ============================================================================
// Auth Types
// ============================================================================

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface VerifyEmailRequest {
  token: string
}

export interface ForgotPasswordRequest {
  email: string
}

export interface ResetPasswordRequest {
  token: string
  new_password: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

// ============================================================================
// API Key Types
// ============================================================================

export interface APIKeyCreate {
  name: string
  scopes?: string[]
  expires_in_days?: number
  organization_id?: string
}

export interface APIKey {
  id: string
  name: string
  key_prefix: string
  scopes: string[]
  is_active: boolean
  last_used_at: string | null
  expires_at: string | null
  created_at: string
}

export interface APIKeyWithSecret extends APIKey {
  key: string
}

// ============================================================================
// API Error Types
// ============================================================================

export interface ValidationError {
  loc: (string | number)[]
  msg: string
  type: string
}

export interface APIError {
  detail: string | ValidationError[]
  code?: string
}

// ============================================================================
// Project Types
// ============================================================================

export interface Project {
  id: string
  name: string
  description: string | null
  github_owner: string | null
  github_repo: string | null
  github_connected: boolean
  default_phase_id: string
  status: "active" | "paused" | "archived" | "completed"
  settings: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  description?: string
  default_phase_id?: string
  github_owner?: string
  github_repo?: string
  settings?: Record<string, unknown>
}

export interface ProjectUpdate {
  name?: string
  description?: string
  default_phase_id?: string
  status?: "active" | "paused" | "archived" | "completed"
  github_owner?: string
  github_repo?: string
  github_connected?: boolean
  settings?: Record<string, unknown>
}

export interface ProjectListResponse {
  projects: Project[]
  total: number
}

export interface ProjectStats {
  project_id: string
  total_tickets: number
  tickets_by_status: Record<string, number>
  tickets_by_phase: Record<string, number>
  active_agents: number
  total_commits: number
}

// ============================================================================
// Agent Types
// ============================================================================

export interface Agent {
  agent_id: string
  agent_type: string
  phase_id: string | null
  status: string
  capabilities: string[]
  capacity: number
  health_status: string
  tags: string[]
  last_heartbeat: string | null
  created_at: string | null
  is_available?: boolean  // Computed from status
}

export interface AgentRegisterRequest {
  agent_type: string
  phase_id?: string
  capabilities: string[]
  capacity?: number
  status?: string
  tags?: string[]
}

export interface AgentUpdateRequest {
  capabilities?: string[]
  capacity?: number
  status?: string
  tags?: string[]
  health_status?: string
}

export interface AgentMatchResponse {
  agent: Agent
  match_score: number
  matched_capabilities: string[]
}

export interface AgentHealth {
  agent_id: string
  status: string
  health_status: string
  last_heartbeat: string | null
  seconds_since_heartbeat: number | null
  is_stale: boolean
}

export interface AgentStatistics {
  total_agents: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  by_health: Record<string, number>
  stale_count: number
}

// ============================================================================
// Organization Types
// ============================================================================

export interface Organization {
  id: string
  name: string
  slug: string
  description: string | null
  billing_email: string | null
  owner_id: string
  is_active: boolean
  max_concurrent_agents: number
  max_agent_runtime_hours: number
  created_at: string
  updated_at: string
}

export interface OrganizationSummary {
  id: string
  name: string
  slug: string
  role: string
}

export interface OrganizationCreate {
  name: string
  slug: string
  description?: string
  billing_email?: string
}

export interface OrganizationUpdate {
  name?: string
  description?: string
  billing_email?: string
  settings?: Record<string, unknown>
  max_concurrent_agents?: number
  max_agent_runtime_hours?: number
}

export interface Role {
  id: string
  name: string
  description: string | null
  permissions: string[]
  organization_id: string | null
  is_system: boolean
  inherits_from: string | null
  created_at: string
}

export interface RoleCreate {
  name: string
  description?: string
  permissions: string[]
  organization_id: string
  inherits_from?: string
}

export interface Membership {
  id: string
  user_id: string | null
  agent_id: string | null
  organization_id: string
  role_id: string
  role_name: string
  joined_at: string
}

export interface MembershipCreate {
  user_id?: string
  agent_id?: string
  role_id: string
}

// ============================================================================
// Ticket Types
// ============================================================================

export interface Ticket {
  id: string
  title: string
  description: string | null
  status: string
  priority: string
  phase_id: string
  approval_status: string | null
  created_at: string | null
  updated_at?: string | null
  project_id?: string
}

export interface TicketCreate {
  title: string
  description?: string
  phase_id?: string
  priority?: string
  project_id?: string
  // Deduplication options
  check_duplicates?: boolean
  similarity_threshold?: number
  force_create?: boolean
}

export interface TicketListParams {
  limit?: number
  offset?: number
  status?: string
  priority?: string
  phase_id?: string
  search?: string
}

export interface DuplicateCandidate {
  ticket_id: string
  title: string
  similarity_score: number
}

export interface DuplicateCheckResponse {
  is_duplicate: boolean
  message: string
  candidates: DuplicateCandidate[]
  highest_similarity: number
}

export interface TicketListResponse {
  tickets: Ticket[]
  total: number
}

export interface TicketTransitionRequest {
  to_status: string
  reason?: string
  force?: boolean
}

// ============================================================================
// Board Types
// ============================================================================

export interface BoardColumn {
  id: string
  name: string
  phase_mappings: string[]
  wip_limit: number | null
  order: number
  tickets: Ticket[]
}

export interface BoardViewResponse {
  columns: BoardColumn[]
}

export interface ColumnStats {
  column_id: string
  name: string
  ticket_count: number
  wip_limit: number | null
  utilization: number | null
  wip_exceeded: boolean
}

export interface WIPViolation {
  column_id: string
  column_name: string
  wip_limit: number
  current_count: number
  excess: number
}

export interface MoveTicketRequest {
  ticket_id: string
  target_column_id: string
  force?: boolean
}

// ============================================================================
// Task Types
// ============================================================================

export interface Task {
  id: string
  ticket_id: string
  phase_id: string
  task_type: string
  description: string
  priority: string
  status: string
  assigned_agent_id: string | null
  conversation_id: string | null
  result: Record<string, unknown> | null
  error_message: string | null
  dependencies: { depends_on?: string[] } | null
  timeout_seconds: number | null
  retry_count: number
  max_retries: number
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface TaskListItem {
  id: string
  ticket_id: string
  phase_id: string
  task_type: string
  description: string
  priority: string
  status: string
  assigned_agent_id: string | null
  created_at: string
}

export interface TaskDependencies {
  task_id: string
  depends_on: string[]
  dependencies_complete: boolean
  blocked_tasks: { id: string; description: string; status: string }[]
}

// ============================================================================
// Phase Gate Types
// ============================================================================

export interface GateValidationResult {
  gate_status: string
  requirements_met: boolean
  blocking_reasons: string[]
}

export interface PhaseArtifact {
  id: string
  artifact_type: string
  phase_id: string
  artifact_path: string | null
  artifact_content: Record<string, unknown> | null
}

export interface PhaseArtifactCreate {
  phase_id: string
  artifact_type: string
  artifact_path?: string
  artifact_content?: Record<string, unknown>
  collected_by?: string
}

// ============================================================================
// Monitor/Metrics Types
// ============================================================================

export interface MetricSample {
  metric_name: string
  value: number
  labels: Record<string, string>
  timestamp: string
}

export interface Anomaly {
  anomaly_id: string
  metric_name: string
  anomaly_type: string
  severity: string
  baseline_value: number
  observed_value: number
  deviation_percent: number
  description: string
  labels: Record<string, string> | null
  detected_at: string
  acknowledged_at: string | null
}

export interface DashboardSummary {
  total_tasks_pending: number
  total_tasks_completed: number
  active_agents: number
  stale_agents: number
  active_locks: number
  recent_anomalies: number
  critical_alerts: number
}

export interface MonitoringStatus {
  is_running: boolean
  last_check: string | null
  check_interval_seconds: number
  agents_monitored: number
  analyses_performed: number
}

export interface SystemHealth {
  overall_status: string
  component_health: Record<string, unknown>
  last_updated: string
}

// ============================================================================
// GitHub Integration Types
// ============================================================================

export interface ConnectRepositoryRequest {
  owner: string
  repo: string
  webhook_secret?: string
}

export interface ConnectRepositoryResponse {
  success: boolean
  message: string
  project_id: string
  webhook_url?: string
}

export interface RepositoryInfo {
  owner: string
  repo: string
  connected: boolean
  webhook_configured: boolean
}

export interface SyncRepositoryResponse {
  success: boolean
  message: string
}

// ============================================================================
// Commit Types
// ============================================================================

export interface Commit {
  id: string
  commit_sha: string
  commit_message: string
  commit_timestamp: string
  agent_id: string
  ticket_id: string
  files_changed: number | null
  insertions: number | null
  deletions: number | null
  files_list: Record<string, unknown> | null
  linked_at: string
  link_method: string | null
}

export interface CommitListResponse {
  commits: Commit[]
  total: number
}

export interface LinkCommitRequest {
  commit_sha: string
  agent_id: string
  commit_message?: string
  files_changed?: number
  insertions?: number
  deletions?: number
  files_list?: Record<string, unknown>
  link_method?: string
}

export interface FileDiff {
  path: string
  additions: number
  deletions: number
  changes: number
  status: string
  patch?: string
}

export interface CommitDiffResponse {
  commit_sha: string
  files: FileDiff[]
}

// ============================================================================
// Dependency Graph Types
// ============================================================================

export interface GraphNode {
  id: string
  type: "task" | "discovery" | "ticket"
  label: string
  status: string
  priority?: string
  phase_id?: string
  description?: string
  data?: Record<string, unknown>
}

export interface GraphEdge {
  source: string
  target: string
  type?: string
  label?: string
}

export interface GraphMetadata {
  total_nodes: number
  total_edges: number
  ticket_id?: string
  project_id?: string
}

export interface DependencyGraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  metadata: GraphMetadata
}

export interface BlockedTasksResponse {
  task_id: string
  blocked_tasks: Array<{
    id: string
    description: string
    status: string
    priority: string
    phase_id: string
  }>
  blocked_count: number
}

export interface BlockingTasksResponse {
  task_id: string
  blocking_tasks: Array<{
    id: string
    description: string
    status: string
    priority: string
    phase_id: string
    is_complete: boolean
  }>
  all_dependencies_complete: boolean
}

// ============================================================================
// Generic Response Types
// ============================================================================

export interface MessageResponse {
  message: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
