/**
 * TypeScript types for OmoiOS API.
 */

/** Credential binding kinds. */
export type BindingKind = 'bearer_secret' | 'user_oauth' | 'github_app';

/** Environment variable types. */
export type VariableType = 'string' | 'secret' | 'json';

/** Webhook event types. */
export type WebhookEvent =
  | 'spec.created'
  | 'task.started'
  | 'task.completed'
  | 'session.created'
  | 'artifact.uploaded';

/** Credential resource. */
export interface Credential {
  /** Unique identifier */
  id: string;
  /** Workspace ID */
  workspace_id: string;
  /** Credential binding kind */
  kind: BindingKind;
  /** User-friendly name */
  name: string;
  /** Additional configuration */
  config?: Record<string, unknown> | null;
  /** Credential version */
  version?: number;
  /** Creation timestamp (ISO 8601) */
  created_at: string;
  /** Last rotation timestamp (ISO 8601) */
  rotated_at?: string | null;
}

/** Request to create a credential. */
export interface CreateCredentialRequest {
  /** Workspace ID */
  workspace_id: string;
  /** Credential binding kind */
  kind: BindingKind;
  /** User-friendly name */
  name: string;
  /** Credential value (encrypted at rest) */
  value: string;
  /** Additional configuration (e.g., OAuth scopes) */
  config?: Record<string, unknown>;
}

/** Environment variable definition. */
export interface EnvironmentVariable {
  /** Variable type */
  type: VariableType;
  /** Variable value */
  value: string | Record<string, unknown>;
}

/** Environment resource. */
export interface Environment {
  /** Unique identifier */
  id: string;
  /** Organization ID */
  org_id: string;
  /** Environment name */
  name: string;
  /** Optional description */
  description?: string | null;
  /** Creation timestamp (ISO 8601) */
  created_at: string;
  /** Last update timestamp (ISO 8601) */
  updated_at: string;
}

/** Environment version (immutable snapshot). */
export interface EnvironmentVersion {
  /** Unique identifier */
  id: string;
  /** Parent environment ID */
  environment_id: string;
  /** Version number (1, 2, 3...) */
  version_number: number;
  /** Environment variables */
  variables: Record<string, EnvironmentVariable>;
  /** Creation timestamp (ISO 8601) */
  created_at: string;
}

/** Request to create an environment. */
export interface CreateEnvironmentRequest {
  /** Environment name */
  name: string;
  /** Optional description */
  description?: string;
  /** Organization ID */
  org_id: string;
}

/** Request to create an environment version. */
export interface CreateEnvironmentVersionRequest {
  /** Environment variables */
  variables: Record<string, EnvironmentVariable>;
}

/** Artifact resource. */
export interface Artifact {
  /** Unique identifier */
  id: string;
  /** Workspace ID */
  workspace_id: string;
  /** Artifact name */
  name: string;
  /** Storage backend (local, s3) */
  storage_backend: string;
  /** Storage path */
  storage_path?: string | null;
  /** SHA-256 checksum */
  checksum: string;
  /** File size in bytes */
  size_bytes: number;
  /** MIME content type */
  content_type?: string | null;
  /** Additional metadata */
  artifact_metadata?: Record<string, unknown> | null;
  /** Creation timestamp (ISO 8601) */
  created_at: string;
  /** Last update timestamp (ISO 8601) */
  updated_at: string;
}

/** Webhook subscription resource. */
export interface WebhookSubscription {
  /** Unique identifier */
  id: string;
  /** Organization ID */
  org_id: string;
  /** Webhook URL */
  url: string;
  /** Subscribed events */
  events: WebhookEvent[];
  /** Whether subscription is active */
  active: boolean;
  /** Creation timestamp (ISO 8601) */
  created_at: string;
  /** Last update timestamp (ISO 8601) */
  updated_at?: string;
}

/** Webhook delivery record. */
export interface WebhookDelivery {
  /** Unique identifier */
  id: string;
  /** Parent subscription ID */
  subscription_id: string;
  /** Event type */
  event: WebhookEvent;
  /** Event payload */
  payload: Record<string, unknown>;
  /** Delivery status */
  status: string;
  /** Number of delivery attempts */
  attempts: number;
  /** Next retry timestamp (ISO 8601) */
  next_retry_at?: string | null;
  /** Response HTTP status code */
  response_status?: number | null;
  /** Delivery timestamp (ISO 8601) */
  delivered_at?: string | null;
  /** Creation timestamp (ISO 8601) */
  created_at: string;
  /** Last update timestamp (ISO 8601) */
  updated_at?: string;
}

/** Request to create a webhook subscription. */
export interface CreateWebhookRequest {
  /** Webhook URL */
  url: string;
  /** Events to subscribe to */
  events: WebhookEvent[];
  /** Secret for signature verification */
  secret: string;
}

/** Workspace settings resource. */
export interface WorkspaceSettings {
  /** Unique identifier */
  id: string;
  /** Workspace ID */
  workspace_id: string;
  /** Allowed egress hostnames */
  egress_allowlist: string[];
  /** Maximum artifact size in MB */
  max_artifact_size_mb: number;
  /** Allowed credential binding kinds */
  allowed_binding_kinds: BindingKind[];
}

/** Request to update workspace settings. */
export interface UpdateWorkspaceSettingsRequest {
  /** Allowed egress hostnames */
  egress_allowlist?: string[];
  /** Maximum artifact size in MB */
  max_artifact_size_mb?: number;
  /** Allowed credential binding kinds */
  allowed_binding_kinds?: BindingKind[];
}

/** Result of getEnvironment call. */
export interface GetEnvironmentResult {
  /** Environment metadata */
  environment: Environment;
  /** Latest version (null if none exists) */
  latestVersion: EnvironmentVersion | null;
}

// ────────────────────────────────────────────────────────────────────────────
// Spec §03 session surface
// ────────────────────────────────────────────────────────────────────────────

/** ACL role on a session (spec §07). */
export type SessionRole = 'owner' | 'editor' | 'viewer';

/** A session — unit of agent execution (spec §02).
 *
 * `ticket_id` is nullable since the ticket decoupling (migration 071):
 * SDK-direct sessions have no ticket. Legacy ticket-driven rows created by
 * the dashboard still populate it.
 */
export interface Session {
  id: string;
  /** Legacy alias for `id`. */
  session_id?: string;
  ticket_id?: string | null;
  workspace_id?: string;
  environment_id?: string;
  environment_version?: number;
  environment_version_id?: string | null;
  github_repo?: string | null;
  status?: string;
  initial_prompt?: string;
  created_by?: string;
  created_at?: string;
  ended_at?: string;
  /**
   * One-time sandbox bearer returned on `create`. Null on reads. Never log
   * or persist this on the client side.
   */
  session_token?: string | null;
  [k: string]: unknown;
}

/** Spec §03 event envelope — every frame in the SSE/WS stream. */
export interface Event {
  id: string;
  seq: number;
  type: string;
  session_id: string;
  actor: string;
  timestamp?: string;
  data: Record<string, unknown>;
  [k: string]: unknown;
}

/** One ACL grant in a share request. */
export interface Grant {
  user_id: string;
  role: SessionRole;
}

/** Body for POST /api/v1/sessions (spec §03).
 *
 * Either `workspace_id` or `github_repo` must be supplied; `prompt` is
 * required. The backend auto-binds a workspace when only `github_repo` is
 * given (mirrors the ticket auto-project pattern).
 */
export interface CreateSessionRequest {
  prompt: string;
  workspace_id?: string;
  environment_id?: string;
  github_repo?: string;
  share_with?: string[];
  metadata?: Record<string, unknown>;
}

/** Body for POST /api/v1/sessions/{id}/fork. */
export interface ForkRequest {
  from_seq: number;
  prompt: string;
}

/** Body for POST /api/v1/sessions/{id}/share. */
export interface ShareRequest {
  grants: Grant[];
}

/** One inbound channel message shape (spec §07). */
export type ChannelMessage =
  | { type: 'message.send'; data: { text: string } }
  | { type: 'cursor.moved'; data: { file: string; line: number } }
  | { type: string; data: Record<string, unknown> };
