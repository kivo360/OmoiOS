/**
 * OmoiOS SDK - TypeScript client for the OmoiOS Agent Workspace Platform.
 */

// Types
export type {
  BindingKind,
  Credential,
  CreateCredentialRequest,
  VariableType,
  EnvironmentVariable,
  Environment,
  EnvironmentVersion,
  CreateEnvironmentRequest,
  CreateEnvironmentVersionRequest,
  Artifact,
  WebhookEvent,
  WebhookSubscription,
  WebhookDelivery,
  CreateWebhookRequest,
  WorkspaceSettings,
  UpdateWorkspaceSettingsRequest,
  GetEnvironmentResult,
  // Spec §03 session surface
  Session,
  SessionRole,
  Event,
  Grant,
  CreateSessionRequest,
  ForkRequest,
  ShareRequest,
  ChannelMessage,
} from './types.js';

// Client
export { OmoiOSClient } from './client.js';
export type { OmoiOSClientOptions } from './client.js';
export { MockOmoiOSClient } from './mockClient.js';

// Resources
export {
  ArtifactsResource,
  BaseResource,
  CredentialsResource,
  EnvironmentsResource,
  SessionsResource,
  SessionChannel,
  WebhooksResource,
  WorkspacesResource,
} from './resources/index.js';

// Errors
export {
  OmoiOSError,
  AuthError,
  NotFoundError,
  ValidationError,
  ServerError,
} from './errors.js';
