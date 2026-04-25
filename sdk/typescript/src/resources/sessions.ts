/**
 * Sessions resource — spec §03 primary SDK surface.
 *
 * Mirrors the Python SDK method-for-method. All four spec §18 interaction
 * patterns (fire-and-forget / sync wait / live stream / multiplayer) are
 * expressible via this one resource.
 */

import type { OmoiOSClient } from '../client.js';
import type {
  ChannelMessage,
  CreateSessionRequest,
  Event as SessionEvent,
  ForkRequest,
  Grant,
  Session,
  ShareRequest,
} from '../types.js';

// Node's UUID isn't in the global scope; use a tiny inline generator so we
// don't drag `uuid` into the SDK's production dependencies.
function randomIdempotencyKey(): string {
  // RFC4122-shaped random string; good enough for dedup keys.
  const bytes = new Uint8Array(16);
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export class SessionsResource {
  constructor(private readonly client: OmoiOSClient) {}

  // ─── core lifecycle ──────────────────────────────────────────────────────

  /**
   * Create a new session (spec §03). Returns in <200ms.
   *
   * Either `workspaceId` or `githubRepo` must be supplied along with
   * `prompt`. When only `githubRepo="owner/repo"` is given the backend
   * auto-binds a workspace in the caller's org (mirrors the ticket
   * auto-project pattern).
   *
   * Pass `idempotencyKey` to dedup retries across network failures; omit
   * for an auto-generated key.
   */
  async create(
    params: {
      prompt: string;
      workspaceId?: string;
      environmentId?: string;
      githubRepo?: string;
      shareWith?: string[];
      metadata?: Record<string, unknown>;
      idempotencyKey?: string;
      signal?: AbortSignal;
    },
  ): Promise<Session> {
    if (!params.workspaceId && !params.githubRepo) {
      throw new Error(
        'sessions.create: either `workspaceId` or `githubRepo` is required',
      );
    }

    const body: CreateSessionRequest = { prompt: params.prompt };
    if (params.workspaceId !== undefined) body.workspace_id = params.workspaceId;
    if (params.environmentId !== undefined)
      body.environment_id = params.environmentId;
    if (params.githubRepo !== undefined) body.github_repo = params.githubRepo;
    if (params.shareWith !== undefined) body.share_with = params.shareWith;
    if (params.metadata !== undefined) body.metadata = params.metadata;

    const response = await this.client._request('POST', '/api/v1/sessions', {
      body: JSON.stringify(body),
      headers: {
        'Idempotency-Key': params.idempotencyKey ?? randomIdempotencyKey(),
      },
      signal: params.signal,
    });
    return (await response.json()) as Session;
  }

  /** Fetch a session by id. */
  async get(
    sessionId: string,
    options: { signal?: AbortSignal } = {},
  ): Promise<Session> {
    const response = await this.client._request(
      'GET',
      `/api/v1/sessions/${sessionId}`,
      { signal: options.signal },
    );
    return (await response.json()) as Session;
  }

  /**
   * Auto-paginating list iterator (spec §09).
   *
   * Example:
   *
   *     for await (const s of client.sessions.list({ status: 'running' })) {
   *       console.log(s.id);
   *     }
   */
  async *list(
    params: {
      status?: string;
      phase_id?: string;
      ticket_id?: string;
      pageSize?: number;
      signal?: AbortSignal;
    } = {},
  ): AsyncIterable<Session> {
    const pageSize = params.pageSize ?? 100;
    let offset = 0;
    while (true) {
      const searchParams: Record<string, string> = {
        limit: String(pageSize),
        offset: String(offset),
      };
      if (params.status) searchParams.status = params.status;
      if (params.phase_id) searchParams.phase_id = params.phase_id;
      if (params.ticket_id) searchParams.ticket_id = params.ticket_id;

      const response = await this.client._request(
        'GET',
        '/api/v1/sessions',
        { searchParams, signal: params.signal },
      );
      const parsed = (await response.json()) as Session[] | { items: Session[] };
      const items = Array.isArray(parsed) ? parsed : parsed.items ?? [];

      for (const item of items) yield item;

      if (items.length < pageSize) return;
      offset += pageSize;
    }
  }

  /** Eager variant of `list()` — collects every page into an array. */
  async listAll(params: Parameters<SessionsResource['list']>[0] = {}): Promise<Session[]> {
    const out: Session[] = [];
    for await (const s of this.list(params)) out.push(s);
    return out;
  }

  /** Cancel a running session. Idempotent. */
  async cancel(
    sessionId: string,
    options: { signal?: AbortSignal } = {},
  ): Promise<Record<string, unknown>> {
    const response = await this.client._request(
      'DELETE',
      `/api/v1/sessions/${sessionId}`,
      { signal: options.signal },
    );
    return (await response.json()) as Record<string, unknown>;
  }

  // ─── spec §03 lifecycle actions ──────────────────────────────────────────

  /** Send a follow-up prompt mid-session. Non-blocking. */
  async reply(
    sessionId: string,
    text: string,
    options: { signal?: AbortSignal } = {},
  ): Promise<void> {
    await this.client._request(
      'POST',
      `/api/v1/sessions/${sessionId}/messages`,
      { body: JSON.stringify({ text }), signal: options.signal },
    );
  }

  /** Branch a session at event `fromSeq` with a new prompt. */
  async fork(
    sessionId: string,
    fromSeq: number,
    prompt: string,
    options: { signal?: AbortSignal } = {},
  ): Promise<Session> {
    const body: ForkRequest = { from_seq: fromSeq, prompt };
    const response = await this.client._request(
      'POST',
      `/api/v1/sessions/${sessionId}/fork`,
      { body: JSON.stringify(body), signal: options.signal },
    );
    return (await response.json()) as Session;
  }

  /** Grant ACL roles on a session (spec §07). */
  async share(
    sessionId: string,
    grants: Grant[],
    options: { signal?: AbortSignal } = {},
  ): Promise<Record<string, unknown>> {
    const body: ShareRequest = { grants };
    const response = await this.client._request(
      'POST',
      `/api/v1/sessions/${sessionId}/share`,
      { body: JSON.stringify(body), signal: options.signal },
    );
    return (await response.json()) as Record<string, unknown>;
  }

  /** List artifacts produced by this session. */
  async artifacts(
    sessionId: string,
    options: { signal?: AbortSignal } = {},
  ): Promise<Array<Record<string, unknown>>> {
    const response = await this.client._request(
      'GET',
      `/api/v1/sessions/${sessionId}/artifacts`,
      { signal: options.signal },
    );
    return (await response.json()) as Array<Record<string, unknown>>;
  }

  // ─── spec §03 streaming ──────────────────────────────────────────────────

  /**
   * SSE event iterator with `Last-Event-ID` resume (spec §09).
   *
   * Uses the platform `fetch` + `ReadableStream` — no extra deps.
   *
   * Example (Pattern B — sync wait):
   *
   *     for await (const e of client.sessions.events(id)) {
   *       if (e.type === 'session.succeeded') break;
   *     }
   */
  async *events(
    sessionId: string,
    options: { lastEventId?: string; signal?: AbortSignal } = {},
  ): AsyncIterable<SessionEvent> {
    // @ts-expect-error — `_headers` is private on the runtime class but we
    // need it to add auth headers for streaming. Same trick the spec §09
    // example uses.
    const authHeaders: Record<string, string> = this.client._headers?.() ?? {};
    const headers: Record<string, string> = {
      ...authHeaders,
      Accept: 'text/event-stream',
    };
    if (options.lastEventId) headers['Last-Event-ID'] = options.lastEventId;

    const url = new URL(
      `/api/v1/sessions/${sessionId}/events`,
      this.client.baseUrl,
    );

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers,
      signal: options.signal,
    });

    if (!response.ok || !response.body) {
      throw new Error(
        `Event stream failed: ${response.status} ${response.statusText}`,
      );
    }

    const reader = response.body
      .pipeThrough(new TextDecoderStream())
      .getReader();

    let buf = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) return;
      buf += value;
      // Frames are separated by "\n\n". Split-and-loop handles partial reads.
      let idx: number;
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const dataLine = frame
          .split('\n')
          .find((l) => l.startsWith('data: '));
        if (!dataLine) continue;
        const payload = dataLine.slice(6).trim();
        if (!payload) continue;
        try {
          yield JSON.parse(payload) as SessionEvent;
        } catch {
          // Skip malformed frames instead of killing the iterator.
        }
      }
    }
  }

  /** Open a multiplayer WebSocket channel (spec §07). */
  connect(sessionId: string, userToken?: string): SessionChannel {
    const token =
      userToken ?? this.client.jwtToken ?? this.client.apiKey ?? '';
    return new SessionChannel(this.client, sessionId, token);
  }
}

// ─── multiplayer channel ─────────────────────────────────────────────────────

type Handler = (frame: Record<string, unknown>) => void;

export class SessionChannel {
  private ws: WebSocket | null = null;
  private readonly handlers: Map<string, Handler[]> = new Map();
  private readonly starHandlers: Handler[] = [];

  constructor(
    private readonly client: OmoiOSClient,
    private readonly sessionId: string,
    private readonly token: string,
  ) {}

  // ── event subscriptions ────────────────────────────────────────────────

  /** Register a handler for a message type. Use `'*'` to catch all. */
  on(eventType: string, fn: Handler): void {
    if (eventType === '*') {
      this.starHandlers.push(fn);
      return;
    }
    const bucket = this.handlers.get(eventType) ?? [];
    bucket.push(fn);
    this.handlers.set(eventType, bucket);
  }

  // ── lifecycle ──────────────────────────────────────────────────────────

  /** Connect and start listening. Resolves when the socket is open. */
  async open(): Promise<this> {
    const base = this.client.baseUrl;
    const wsScheme = base.startsWith('https') ? 'wss' : 'ws';
    const host = base.split('://', 2)[1];
    const url =
      `${wsScheme}://${host}/api/v1/sessions/${this.sessionId}/ws` +
      `?token=${encodeURIComponent(this.token)}`;

    // Node 18+ exposes global WebSocket via undici; browsers always have it.
    const WSCtor: typeof WebSocket =
      (globalThis as unknown as { WebSocket?: typeof WebSocket }).WebSocket!;
    if (!WSCtor) {
      throw new Error(
        'WebSocket is not available in this runtime. ' +
          'Install `ws` and polyfill globalThis.WebSocket, or use Node 18+.',
      );
    }

    const ws = new WSCtor(url);
    this.ws = ws;

    await new Promise<void>((resolve, reject) => {
      const onOpen = () => {
        ws.removeEventListener('error', onError);
        resolve();
      };
      const onError = (ev: globalThis.Event) => {
        ws.removeEventListener('open', onOpen);
        reject(new Error(`WebSocket connect failed: ${String(ev)}`));
      };
      ws.addEventListener('open', onOpen, { once: true });
      ws.addEventListener('error', onError, { once: true });
    });

    ws.addEventListener('message', (ev) => {
      let frame: Record<string, unknown>;
      try {
        frame =
          typeof ev.data === 'string'
            ? (JSON.parse(ev.data) as Record<string, unknown>)
            : {};
      } catch {
        return;
      }
      for (const h of this.starHandlers) h(frame);
      const msgType = typeof frame.type === 'string' ? frame.type : undefined;
      if (msgType) {
        for (const h of this.handlers.get(msgType) ?? []) h(frame);
      }
    });

    return this;
  }

  /** Send one message frame (spec §07: `message.send`, `cursor.moved`, …). */
  send(message: ChannelMessage): void {
    if (!this.ws) {
      throw new Error('Channel is not open; call .open() first');
    }
    this.ws.send(JSON.stringify(message));
  }

  /** Close the WebSocket. */
  close(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
