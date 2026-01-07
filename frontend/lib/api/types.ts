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
  waitlist_status: "pending" | "approved" | "none"
  created_at: string
  last_login_at: string | null
}

export interface UserCreate {
  email: string
  password: string
  full_name?: string
  department?: string
  referral_source?: string
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
// Waitlist Types
// ============================================================================

export interface WaitlistListResponse {
  users: User[]
  total: number
  limit: number
  offset: number
}

export interface WaitlistApproveResponse {
  message: string
  user: User
}

export interface WaitlistApproveAllResponse {
  message: string
  count: number
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
  organization_id: string  // Required - projects must belong to an organization
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
  // GitHub repo info for auto-project creation when project_id is not provided
  github_owner?: string
  github_repo?: string
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
  title: string | null
  description: string | null
  priority: string
  status: string
  sandbox_id: string | null
  assigned_agent_id: string | null
  conversation_id: string | null
  result: Record<string, unknown> | null
  error_message: string | null
  dependencies: { depends_on?: string[] } | null
  timeout_seconds: number | null
  retry_count: number
  max_retries: number
  created_at: string
  updated_at: string | null
  started_at: string | null
  completed_at: string | null
}

export interface TaskListItem {
  id: string
  ticket_id: string
  phase_id: string
  task_type: string
  title: string | null
  description: string | null
  priority: string
  status: string
  sandbox_id: string | null
  assigned_agent_id: string | null
  created_at: string
  updated_at: string | null
  started_at: string | null
}

export interface TaskDependencies {
  task_id: string
  depends_on: string[]
  dependencies_complete: boolean
  blocked_tasks: { id: string; description: string; status: string }[]
}

// Task associated with a sandbox (from GET /sandboxes/{id}/task)
export interface SandboxTask {
  id: string
  ticket_id: string
  phase_id: string
  task_type: string
  title: string | null
  description: string | null
  priority: string
  status: string
  sandbox_id: string
  assigned_agent_id: string | null
  created_at: string
  updated_at: string | null
  started_at: string | null
  completed_at: string | null
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
  ticket_id?: string
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
// OAuth Types
// ============================================================================

export interface OAuthProvider {
  name: string
  enabled: boolean
  manage_url?: string | null  // URL to manage the OAuth app (e.g., GitHub app settings)
}

export interface OAuthProvidersResponse {
  providers: OAuthProvider[]
}

export interface OAuthAuthUrlResponse {
  auth_url: string
  state: string
}

export interface ConnectedProvider {
  provider: string
  username: string | null
  connected: boolean
}

export interface ConnectedProvidersResponse {
  providers: ConnectedProvider[]
}

export interface DisconnectResponse {
  success: boolean
  message: string
}

// ============================================================================
// GitHub Repository Types (OAuth-based)
// ============================================================================

export interface GitHubRepo {
  id: number
  name: string
  full_name: string
  owner: string
  description: string | null
  private: boolean
  html_url: string
  clone_url: string
  default_branch: string
  language: string | null
  stargazers_count: number
  forks_count: number
}

export interface GitHubBranch {
  name: string
  sha: string
  protected: boolean
}

export interface GitHubFile {
  name: string
  path: string
  sha: string
  size: number
  type: string
  content: string | null
}

export interface GitHubCommitInfo {
  sha: string
  message: string
  author_name: string | null
  author_email: string | null
  date: string | null
  html_url: string | null
}

export interface GitHubPullRequest {
  number: number
  title: string
  state: string
  html_url: string
  head_branch: string
  base_branch: string
  body: string | null
  merged: boolean
  mergeable: boolean | null
  draft: boolean
}

export interface DirectoryItem {
  name: string
  path: string
  type: string
  size: number
  sha: string
}

export interface TreeItem {
  path: string
  type: string
  sha: string
  size: number | null
}

export interface FileOperationResult {
  success: boolean
  message: string
  commit_sha: string | null
  content_sha: string | null
  error: string | null
}

export interface BranchCreateResult {
  success: boolean
  ref: string | null
  sha: string | null
  error: string | null
}

export interface PullRequestCreateResult {
  success: boolean
  number: number | null
  html_url: string | null
  state: string | null
  error: string | null
}

export interface CreateFileRequest {
  content: string
  message: string
  branch?: string
}

export interface CreateBranchRequest {
  branch_name: string
  from_sha: string
}

export interface CreatePullRequestRequest {
  title: string
  head: string
  base: string
  body?: string
  draft?: boolean
}

// ============================================================================
// Sandbox Types
// ============================================================================

export interface SandboxEvent {
  id: string
  sandbox_id: string
  event_type: string
  event_data: Record<string, unknown>
  source: "agent" | "worker" | "system"
  created_at: string
}

export interface SandboxEventCreate {
  event_type: string
  event_data?: Record<string, unknown>
  source?: "agent" | "worker" | "system"
}

export interface SandboxEventResponse {
  status: string
  sandbox_id: string
  event_type: string
  event_id: string | null
  timestamp: string
}

export interface SandboxMessage {
  content: string
  message_type?: "user_message" | "interrupt" | "guardian_nudge" | "system"
}

export interface MessageItem {
  id: string
  content: string
  message_type: string
  created_at: string
}

export interface MessageQueueResponse {
  sandbox_id: string
  messages: MessageItem[]
  count: number
}

export interface HeartbeatSummary {
  count: number
  first_heartbeat: string | null
  last_heartbeat: string | null
}

export interface TrajectorySummaryResponse {
  sandbox_id: string
  events: SandboxEvent[]
  heartbeat_summary: HeartbeatSummary
  total_events: number
  trajectory_events: number
  // Cursor-based pagination
  next_cursor: string | null  // Cursor for loading older events
  prev_cursor: string | null  // Cursor for loading newer events
  has_more: boolean           // Whether there are more events to load
}

export interface SandboxEventsListResponse {
  sandbox_id: string
  events: SandboxEvent[]
  total: number
  limit: number
  offset: number
}

export interface SandboxInfo {
  sandbox_id: string
  task_id: string | null
  status: string
  created_at: string
  model: string | null
}

// File edit event data structure
export interface FileEditEventData {
  file_path: string
  change_type: "created" | "modified" | "deleted"
  lines_added: number
  lines_removed: number
  diff_preview?: string
  full_diff?: string
  full_diff_available?: boolean
  full_diff_size?: number
  turn?: number
  tool_use_id?: string
}

// Tool use event data structure
export interface ToolUseEventData {
  tool: string
  input: Record<string, unknown>
  tool_use_id: string
  turn?: number
}

// Tool result event data structure
export interface ToolResultEventData {
  tool_use_id: string
  content: string
  is_error?: boolean
  turn?: number
}

// Assistant message event data structure
export interface AssistantMessageEventData {
  content: string
  turn?: number
}

// Thinking event data structure
export interface ThinkingEventData {
  content: string
  turn?: number
}

// ============================================================================
// Billing Types
// ============================================================================

export interface BillingAccount {
  id: string
  organization_id: string
  stripe_customer_id: string | null
  has_payment_method: boolean
  status: string
  free_workflows_remaining: number
  free_workflows_reset_at: string | null
  credit_balance: number
  auto_billing_enabled: boolean
  billing_email: string | null
  tax_exempt: boolean
  total_workflows_completed: number
  total_amount_spent: number
  created_at: string | null
  updated_at: string | null
}

export interface Invoice {
  id: string
  invoice_number: string
  billing_account_id: string
  ticket_id: string | null
  stripe_invoice_id: string | null
  status: string
  period_start: string | null
  period_end: string | null
  subtotal: number
  tax_amount: number
  discount_amount: number
  total: number
  credits_applied: number
  amount_due: number
  amount_paid: number
  currency: string
  line_items: Record<string, unknown>[]
  description: string | null
  due_date: string | null
  finalized_at: string | null
  paid_at: string | null
  created_at: string | null
}

/**
 * Stripe invoice (fetched directly from Stripe API)
 */
export interface StripeInvoice {
  id: string  // Stripe invoice ID (e.g., "in_...")
  number: string | null  // Invoice number (e.g., "0001-0001")
  status: string  // draft, open, paid, uncollectible, void
  amount_due: number  // Amount in cents
  amount_paid: number  // Amount in cents
  amount_remaining: number  // Amount in cents
  subtotal: number  // Amount in cents
  total: number  // Amount in cents
  currency: string
  description: string | null
  customer_email: string | null
  hosted_invoice_url: string | null  // Link to view invoice on Stripe
  invoice_pdf: string | null  // Link to download PDF
  period_start: string | null
  period_end: string | null
  due_date: string | null
  created: string  // ISO date string
  paid_at: string | null
  lines: {
    id: string
    description: string | null
    amount: number
    currency: string
    quantity: number | null
  }[]
}

export interface Payment {
  id: string
  billing_account_id: string
  invoice_id: string | null
  stripe_payment_intent_id: string | null
  amount: number
  currency: string
  status: string
  payment_method_type: string | null
  payment_method_last4: string | null
  payment_method_brand: string | null
  failure_code: string | null
  failure_message: string | null
  refunded_amount: number
  description: string | null
  created_at: string | null
  succeeded_at: string | null
}

export interface UsageRecord {
  id: string
  billing_account_id: string
  ticket_id: string | null
  usage_type: string
  quantity: number
  unit_price: number
  total_price: number
  free_tier_used: boolean
  invoice_id: string | null
  billed: boolean
  usage_details: Record<string, unknown> | null
  recorded_at: string | null
  billed_at: string | null
}

export interface PaymentMethod {
  id: string
  type: string
  card_brand: string | null
  card_last4: string | null
  is_default: boolean
}

export interface StripeConfig {
  publishable_key: string | null
  is_configured: boolean
}

export interface CheckoutResponse {
  checkout_url: string
  session_id: string
}

export interface PortalResponse {
  portal_url: string
}

export interface CreditPurchaseRequest {
  amount_usd: number
  success_url?: string
  cancel_url?: string
}

export interface PaymentMethodRequest {
  payment_method_id: string
  set_as_default?: boolean
}

// ============================================================================
// Subscription Types
// ============================================================================

export type SubscriptionTier =
  | "free"
  | "pro"
  | "team"
  | "enterprise"
  | "lifetime"

export type SubscriptionStatus =
  | "active"
  | "trialing"
  | "past_due"
  | "canceled"
  | "paused"
  | "incomplete"

export interface Subscription {
  id: string
  organization_id: string
  billing_account_id: string
  stripe_subscription_id: string | null
  tier: SubscriptionTier
  status: SubscriptionStatus
  current_period_start: string | null
  current_period_end: string | null
  cancel_at_period_end: boolean
  canceled_at: string | null
  trial_start: string | null
  trial_end: string | null
  workflows_limit: number
  workflows_used: number
  workflows_remaining: number
  agents_limit: number
  storage_limit_gb: number
  storage_used_gb: number
  is_lifetime: boolean
  lifetime_purchase_date: string | null
  lifetime_purchase_amount: number | null
  is_byo: boolean
  byo_providers_configured: string[] | null
  created_at: string | null
  updated_at: string | null
}

export interface LifetimePurchaseRequest {
  success_url?: string
  cancel_url?: string
}

// Tier configuration for display purposes
export interface TierConfig {
  name: string
  displayName: string
  price: number
  priceLabel: string
  workflows: number
  workflowsLabel: string
  agents: number
  storageGb: number
  features: string[]
  highlighted?: boolean
  ctaLabel: string
}

export const TIER_CONFIGS: Record<SubscriptionTier, TierConfig> = {
  free: {
    name: "free",
    displayName: "Free",
    price: 0,
    priceLabel: "$0/month",
    workflows: 5,
    workflowsLabel: "5 workflows/month",
    agents: 1,
    storageGb: 2,
    features: [
      "5 workflows per month",
      "1 concurrent agent",
      "2GB storage",
      "Community support",
    ],
    ctaLabel: "Current Plan",
  },
  pro: {
    name: "pro",
    displayName: "Pro",
    price: 50,
    priceLabel: "$50/month",
    workflows: 100,
    workflowsLabel: "100 workflows/month",
    agents: 5,
    storageGb: 50,
    features: [
      "100 workflows per month",
      "5 concurrent agents",
      "50GB storage",
      "BYO API keys",
      "Priority support",
    ],
    highlighted: true,
    ctaLabel: "Upgrade to Pro",
  },
  team: {
    name: "team",
    displayName: "Team",
    price: 150,
    priceLabel: "$150/month",
    workflows: 500,
    workflowsLabel: "500 workflows/month",
    agents: 10,
    storageGb: 200,
    features: [
      "500 workflows per month",
      "10 concurrent agents",
      "200GB storage",
      "BYO API keys",
      "Team collaboration",
      "Priority support",
    ],
    ctaLabel: "Upgrade to Team",
  },
  enterprise: {
    name: "enterprise",
    displayName: "Enterprise",
    price: 0,
    priceLabel: "Custom",
    workflows: -1,
    workflowsLabel: "Unlimited",
    agents: -1,
    storageGb: -1,
    features: [
      "Unlimited workflows",
      "Unlimited agents",
      "Unlimited storage",
      "24/7 support",
      "Custom integrations",
      "SLA guarantee",
      "Data isolation",
    ],
    ctaLabel: "Contact Sales",
  },
  lifetime: {
    name: "lifetime",
    displayName: "Lifetime",
    price: 299,
    priceLabel: "$299 one-time",
    workflows: 50,
    workflowsLabel: "50 workflows/month",
    agents: 5,
    storageGb: 50,
    features: [
      "50 workflows per month",
      "5 concurrent agents",
      "50GB storage",
      "BYO API keys",
      "No recurring charges",
      "Founding member badge",
    ],
    ctaLabel: "Claim Lifetime Access",
  },
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
