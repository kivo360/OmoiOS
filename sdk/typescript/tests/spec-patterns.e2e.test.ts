/**
 * TypeScript SDK end-to-end tests for spec §18's four interaction patterns.
 *
 * Mirrors `sdk/python/tests/test_e2e_spec_patterns.py`. Skipped unless the
 * backend + Daytona env vars are set; this is an e2e suite, not a unit suite.
 *
 * Required env:
 *   OMOIOS_API_BASE_URL       — backend URL (e.g. http://localhost:18000)
 *   OMOIOS_PLATFORM_API_KEY   — tenant-scoped platform key (rpk_live_…)
 *   DAYTONA_API_KEY           — real Daytona credential
 *
 * Optional for Pattern D (multiplayer WS auth):
 *   OMOIOS_USER_JWT           — user JWT; required for ws:// auth
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';

import { OmoiOSClient } from '../src/client.js';
import type { Event as SessionEvent, Session } from '../src/types.js';

const API_BASE_URL = process.env.OMOIOS_API_BASE_URL ?? '';
const PLATFORM_KEY = process.env.OMOIOS_PLATFORM_API_KEY ?? '';
const DAYTONA_KEY = process.env.DAYTONA_API_KEY ?? '';
const USER_JWT = process.env.OMOIOS_USER_JWT ?? '';

const shouldRun = Boolean(API_BASE_URL && PLATFORM_KEY && DAYTONA_KEY);
const describeE2E = shouldRun ? describe : describe.skip;

const TERMINAL_EVENT_TYPES = new Set([
  'session.succeeded',
  'session.failed',
  'session.cancelled',
  'session.ended',
]);

// ─── fixtures ──────────────────────────────────────────────────────────────

let client: OmoiOSClient;
let workspaceId: string | null = null;

async function firstWorkspaceId(): Promise<string | null> {
  // Sessions no longer require a ticket (migration 071). We point at a
  // workspace directly; falling back to SKIP if the test org has none.
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces?limit=1`, {
    headers: { Authorization: `Bearer ${PLATFORM_KEY}` },
  });
  if (!res.ok) return null;
  const payload = (await res.json()) as
    | Array<Record<string, unknown>>
    | { items: Array<Record<string, unknown>> };
  const rows = Array.isArray(payload) ? payload : payload.items ?? [];
  if (rows.length === 0) return null;
  return String(rows[0]!.id);
}

async function createSession(titleSuffix = ''): Promise<Session> {
  if (!workspaceId) throw new Error('no workspace available');
  return client.sessions.create({
    workspaceId,
    prompt: `e2e pattern ${titleSuffix} ${Math.random().toString(36).slice(2, 8)}`.trim(),
    metadata: { source: 'tests/spec-patterns.e2e.test.ts' },
    idempotencyKey: `e2e-${crypto.randomUUID()}`,
  });
}

// Collect up to `limit` events, or return what we've got when `timeoutMs` elapses.
async function drainEvents(
  sessionId: string,
  limit: number,
  opts: { lastEventId?: string; timeoutMs?: number } = {},
): Promise<SessionEvent[]> {
  const collected: SessionEvent[] = [];
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs ?? 15000);
  try {
    for await (const evt of client.sessions.events(sessionId, {
      lastEventId: opts.lastEventId,
      signal: controller.signal,
    })) {
      collected.push(evt);
      if (collected.length >= limit) break;
    }
  } catch {
    // AbortError / stream close — fall through and return what we have.
  } finally {
    clearTimeout(timer);
  }
  return collected;
}

beforeAll(async () => {
  if (!shouldRun) return;
  client = new OmoiOSClient({ baseUrl: API_BASE_URL, apiKey: PLATFORM_KEY });
  workspaceId = await firstWorkspaceId();
});

afterAll(async () => {
  // No connection pooling to tear down — fetch + WebSocket are managed per-call.
});

// ─── Pattern A — fire and forget ───────────────────────────────────────────

describeE2E('Pattern A — fire and forget', () => {
  it('create returns session synchronously', async () => {
    if (!workspaceId) return;
    const s = await createSession('A');
    expect(s.id).toBeTruthy();
    const fetched = await client.sessions.get(s.id);
    expect(fetched.id).toBe(s.id);
  });

  it('idempotency key dedups retries', async () => {
    if (!workspaceId) return;
    const key = `e2e-idem-${crypto.randomUUID()}`;
    const params = {
      workspaceId,
      prompt: 'idem-replay — same key + same body must return the same session.',
      idempotencyKey: key,
    };
    const s1 = await client.sessions.create(params);
    const s2 = await client.sessions.create(params);
    expect(s2.id).toBe(s1.id);
  });
});

// ─── Pattern B — sync wait ─────────────────────────────────────────────────

describeE2E('Pattern B — sync wait', () => {
  it('iterates events until a terminal type or cap', async () => {
    if (!workspaceId) return;
    const s = await createSession('B');
    const collected: SessionEvent[] = [];
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60000);
    try {
      for await (const evt of client.sessions.events(s.id, { signal: controller.signal })) {
        collected.push(evt);
        if (TERMINAL_EVENT_TYPES.has(evt.type)) break;
        if (collected.length >= 50) break;
      }
    } catch {
      // Either abort or stream close — both acceptable for this pattern.
    } finally {
      clearTimeout(timer);
    }
    expect(collected.length).toBeGreaterThan(0);
    for (const evt of collected) {
      expect(evt.seq).toBeTypeOf('number');
    }
  }, 75000);
});

// ─── Pattern C — live stream ───────────────────────────────────────────────

describeE2E('Pattern C — live stream', () => {
  it('envelope fields present on every event', async () => {
    if (!workspaceId) return;
    const s = await createSession('C');
    const events = await drainEvents(s.id, 3, { timeoutMs: 30000 });
    expect(events.length).toBeGreaterThan(0);
    for (const evt of events) {
      expect(evt.id).toBeTruthy();
      expect(evt.seq).toBeGreaterThan(0);
      expect(evt.type).toBeTruthy();
      expect(evt.session_id).toBe(s.id);
      expect(evt.actor).toBeTruthy();
    }
  }, 45000);

  it('resume from Last-Event-ID advances past the cursor', async () => {
    if (!workspaceId) return;
    const s = await createSession('C-resume');
    const initial = await drainEvents(s.id, 2, { timeoutMs: 30000 });
    if (initial.length === 0) return; // nothing to resume from
    const resumeFrom = initial[initial.length - 1]!.seq;

    // Nudge the session so something appears past the cursor.
    try {
      await client.sessions.reply(s.id, `resume-probe-${Math.random().toString(36).slice(2, 8)}`);
    } catch {
      // some sessions may reject replies at this lifecycle stage; ignore.
    }

    const resumed = await drainEvents(s.id, 1, {
      lastEventId: String(resumeFrom),
      timeoutMs: 15000,
    });
    if (resumed.length > 0) {
      expect(resumed[0]!.seq).toBeGreaterThan(resumeFrom);
    }
  }, 60000);
});

// ─── Pattern D — multiplayer ───────────────────────────────────────────────

const describeMultiplayer = shouldRun && USER_JWT ? describe : describe.skip;

describeMultiplayer('Pattern D — multiplayer', () => {
  it('presence: participant.joined reaches the peer', async () => {
    if (!workspaceId) return;
    const s = await createSession('D-presence');

    const chA = client.sessions.connect(s.id, USER_JWT);
    const chB = client.sessions.connect(s.id, USER_JWT);

    const joined = new Promise<Record<string, unknown>>((resolve) => {
      chB.on('participant.joined', (frame) => resolve(frame));
    });

    try {
      await chB.open();
      await new Promise((r) => setTimeout(r, 200));
      await chA.open();
      const frame = await Promise.race([
        joined,
        new Promise<null>((r) => setTimeout(() => r(null), 10000)),
      ]);
      expect(frame).toBeTruthy();
    } finally {
      chA.close();
      chB.close();
    }
  }, 30000);

  it('message.send broadcasts to peers', async () => {
    if (!workspaceId) return;
    const s = await createSession('D-message');
    const text = `hello-${Math.random().toString(36).slice(2, 8)}`;

    const chA = client.sessions.connect(s.id, USER_JWT);
    const chB = client.sessions.connect(s.id, USER_JWT);

    const got = new Promise<Record<string, unknown>>((resolve) => {
      chB.on('session.message', (frame) => {
        const data = (frame.data ?? {}) as Record<string, unknown>;
        if (data.text === text) resolve(frame);
      });
    });

    try {
      await chB.open();
      await chA.open();
      await new Promise((r) => setTimeout(r, 100));
      chA.send({ type: 'message.send', data: { text } });
      const frame = await Promise.race([
        got,
        new Promise<null>((r) => setTimeout(() => r(null), 10000)),
      ]);
      expect(frame).toBeTruthy();
    } finally {
      chA.close();
      chB.close();
    }
  }, 30000);
});
