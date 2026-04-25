import {
  AuthError,
  NotFoundError,
  ServerError,
  ValidationError,
} from './errors.js';
import {
  ArtifactsResource,
  ConnectionsResource,
  CredentialsResource,
  EnvironmentsResource,
  SessionsResource,
  UsageResource,
  WebhooksResource,
  WorkspacesResource,
} from './resources/index.js';

/**
 * Options for the OmoiOS HTTP client.
 *
 * Spec §01 defines three token kinds. Exactly one must be provided:
 *
 *   - `apiKey`        — platform key (`rpk_live_…`) for server-side callers.
 *   - `jwtToken`      — user JWT (`eyJ…`) from the dashboard / OAuth flows.
 *   - `sessionToken`  — sandbox session bearer (`sess_tok_…`) for broker calls
 *                       made from inside a running sandbox.
 *
 * All three are sent as `Authorization: Bearer <token>`. `apiKey` is also
 * echoed as `X-API-Key` so backends that haven't migrated to Bearer yet
 * continue to recognize the caller.
 */
/**
 * Telemetry event shape (spec §18 §2 constructor option).
 *
 * Emitted synchronously from `_request`, `sessions.events()`, and
 * `SessionChannel.open/close`. Auth headers are never included.
 */
export interface TelemetryEvent {
  kind: 'request' | 'response' | 'stream_open' | 'stream_close' | 'error';
  method?: string;
  path: string;
  status?: number;
  durationMs?: number;
  framesReceived?: number;
  error?: string;
}

export interface OmoiOSClientOptions {
  /** API base URL (e.g., "https://api.omoios.dev") */
  baseUrl: string;
  /** Platform API key (`rpk_live_…`) */
  apiKey?: string;
  /** User JWT access token (`eyJ…`) */
  jwtToken?: string;
  /** Sandbox session bearer (`sess_tok_…`) */
  sessionToken?: string;
  /** HTTP request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /**
   * Optional telemetry callback — invoked with every HTTP lifecycle event.
   * Fire-and-forget; exceptions thrown by the callback are swallowed.
   */
  telemetry?: (event: TelemetryEvent) => void;
}

/**
 * HTTP client for the OmoiOS Agent Workspace Platform.
 *
 * Uses native fetch (Node.js 18+) for HTTP requests. Supports both API key
 * and JWT token authentication.
 *
 * @example
 * const client = new OmoiOSClient({
 *   baseUrl: 'https://api.omoios.dev',
 *   apiKey: 'your-api-key',
 * });
 * const creds = await client.credentials.list('ws-1');
 * console.log(creds[0].name);
 */
export class OmoiOSClient {
  /** API base URL */
  readonly baseUrl: string;
  /** Optional platform API key */
  readonly apiKey: string | undefined;
  /** Optional user JWT */
  readonly jwtToken: string | undefined;
  /** Optional sandbox session bearer */
  readonly sessionToken: string | undefined;
  /** Request timeout in milliseconds */
  readonly timeout: number;
  /** Optional telemetry callback (spec §18 §2) */
  private readonly _telemetry?: (event: TelemetryEvent) => void;

  /** Credentials resource */
  readonly credentials: CredentialsResource;
  /** Environments resource */
  readonly environments: EnvironmentsResource;
  /** Artifacts resource */
  readonly artifacts: ArtifactsResource;
  /** Webhooks resource */
  readonly webhooks: WebhooksResource;
  /** Workspaces resource */
  readonly workspaces: WorkspacesResource;
  /** Sessions resource (spec §03 primary surface) */
  readonly sessions: SessionsResource;
  /** Connections resource (user-linked OAuth — spec §18 §2) */
  readonly connections: ConnectionsResource;
  /** Usage resource (billing + per-session aggregates — spec §18 §2) */
  readonly usage: UsageResource;

  /**
   * Initialize the client.
   *
   * @param options - Client configuration options.
   * @throws {Error} If no credential is set, or if more than one is set.
   */
  constructor(options: OmoiOSClientOptions) {
    const provided = [options.apiKey, options.jwtToken, options.sessionToken]
      .filter(Boolean);
    if (provided.length === 0) {
      throw new Error(
        'One of apiKey, jwtToken, or sessionToken must be provided'
      );
    }
    if (provided.length > 1) {
      throw new Error(
        'apiKey, jwtToken, and sessionToken are mutually exclusive'
      );
    }

    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.jwtToken = options.jwtToken;
    this.sessionToken = options.sessionToken;
    this.timeout = options.timeout ?? 30000;
    this._telemetry = options.telemetry;

    this.credentials = new CredentialsResource(this);
    this.environments = new EnvironmentsResource(this);
    this.artifacts = new ArtifactsResource(this);
    this.webhooks = new WebhooksResource(this);
    this.workspaces = new WorkspacesResource(this);

    this.sessions = new SessionsResource(this);
    this.connections = new ConnectionsResource(this);
    this.usage = new UsageResource(this);
  }

  /**
   * Return the single active bearer token.
   */
  _authToken(): string | undefined {
    return this.apiKey ?? this.jwtToken ?? this.sessionToken;
  }

  /**
   * Build request headers with authentication.
   *
   * Spec §01 wants `Authorization: Bearer <token>` for all three token
   * kinds. Platform keys are also echoed as `X-API-Key` for transitional
   * compatibility with backends that haven't migrated to Bearer yet.
   */
  private _headers(): Record<string, string> {
    const headers: Record<string, string> = {};
    const token = this._authToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }
    return headers;
  }

  /**
   * Deliver a telemetry event to the caller callback. Internal — used by
   * `_request`, `sessions.events()`, and `SessionChannel`. Exceptions
   * thrown by the callback are swallowed so telemetry can never break a
   * request path.
   */
  _emitTelemetry(event: TelemetryEvent): void {
    const cb = this._telemetry;
    if (!cb) return;
    try {
      cb(event);
    } catch {
      // Telemetry is fire-and-forget.
    }
  }

  /**
   * Map HTTP error status codes to SDK exceptions.
   *
   * @param response - fetch Response object
   * @throws {AuthError} For 401 responses
   * @throws {NotFoundError} For 404 responses
   * @throws {ValidationError} For 400/422 responses
   * @throws {ServerError} For 5xx responses
   */
  private _handleErrors(response: Response): void {
    if (response.ok) {
      return;
    }

    if (response.status === 401) {
      throw new AuthError('Authentication failed');
    }
    if (response.status === 404) {
      throw new NotFoundError('Resource not found');
    }
    if (response.status === 400 || response.status === 422) {
      throw new ValidationError('Validation failed');
    }
    if (response.status >= 500) {
      throw new ServerError('Server error');
    }

    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  /**
   * Make an authenticated HTTP request.
   *
   * @param method - HTTP method (GET, POST, PUT, PATCH, DELETE)
   * @param path - API path (e.g., "/api/v1/credentials")
   * @param options - Request options
   * @returns fetch Response object
   * @throws {AuthError, NotFoundError, ValidationError, ServerError}
   */
  async _request(
    method: string,
    path: string,
    options: {
      searchParams?: Record<string, string>;
      body?: BodyInit;
      headers?: Record<string, string>;
      /**
       * Optional caller-provided AbortSignal. When the caller aborts, the
       * in-flight fetch is cancelled alongside the client's own timeout
       * signal — whichever aborts first wins.
       */
      signal?: AbortSignal;
    } = {}
  ): Promise<Response> {
    const url = new URL(path, this.baseUrl);
    if (options.searchParams) {
      for (const [key, value] of Object.entries(options.searchParams)) {
        url.searchParams.set(key, value);
      }
    }

    const headers: Record<string, string> = {
      ...this._headers(),
      ...options.headers,
    };

    if (options.body && typeof options.body === 'string') {
      headers['Content-Type'] = 'application/json';
    }

    // Two abort sources: (1) the client's timeout, (2) the caller's
    // AbortSignal if one was supplied. We merge by forwarding either
    // aborter to our controller — whichever fires first wins.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    if (options.signal) {
      if (options.signal.aborted) {
        controller.abort();
      } else {
        options.signal.addEventListener(
          'abort',
          () => controller.abort(),
          { once: true },
        );
      }
    }

    this._emitTelemetry({ kind: 'request', method, path });
    const startedAt = performance.now();
    try {
      const response = await fetch(url.toString(), {
        method,
        headers,
        body: options.body,
        signal: controller.signal,
      });

      this._emitTelemetry({
        kind: 'response',
        method,
        path,
        status: response.status,
        durationMs: performance.now() - startedAt,
      });
      this._handleErrors(response);
      return response;
    } catch (err) {
      this._emitTelemetry({
        kind: 'error',
        method,
        path,
        durationMs: performance.now() - startedAt,
        error: err instanceof Error ? err.message : String(err),
      });
      throw err;
    } finally {
      clearTimeout(timeoutId);
    }
  }
}
