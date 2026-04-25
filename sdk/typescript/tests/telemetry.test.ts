/**
 * Unit tests for TypeScript telemetry callback (Wave 4 T9).
 */

import { describe, expect, it, vi, afterEach } from 'vitest';
import { OmoiOSClient, type TelemetryEvent } from '../src/client.js';

describe('Telemetry callback', () => {
  const originalFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('fires request + response events on a successful call', async () => {
    const events: TelemetryEvent[] = [];
    globalThis.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
    ) as typeof fetch;

    const client = new OmoiOSClient({
      baseUrl: 'http://localhost:18000',
      apiKey: 'secret-key',
      telemetry: (e) => events.push(e),
    });

    await client.connections.list();

    const kinds = events.map((e) => e.kind);
    expect(kinds).toContain('request');
    expect(kinds).toContain('response');

    const responseEvent = events.find((e) => e.kind === 'response');
    expect(responseEvent?.status).toBe(200);
    expect(responseEvent?.durationMs).toBeGreaterThanOrEqual(0);
    expect(responseEvent?.path).toBe('/api/v1/connections');
  });

  it('fires error event on network failure', async () => {
    const events: TelemetryEvent[] = [];
    globalThis.fetch = vi.fn(async () => {
      throw new Error('boom');
    }) as typeof fetch;

    const client = new OmoiOSClient({
      baseUrl: 'http://localhost:18000',
      apiKey: 'k',
      telemetry: (e) => events.push(e),
    });

    await expect(client.connections.list()).rejects.toThrow('boom');
    expect(events.some((e) => e.kind === 'error')).toBe(true);
  });

  it('does not break request when callback throws', async () => {
    globalThis.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
    ) as typeof fetch;

    const client = new OmoiOSClient({
      baseUrl: 'http://localhost:18000',
      apiKey: 'k',
      telemetry: () => {
        throw new Error('callback boom');
      },
    });

    // Should NOT propagate the callback exception.
    const rows = await client.connections.list();
    expect(rows).toEqual([]);
  });

  it('does not leak api key or Authorization header into events', async () => {
    const events: TelemetryEvent[] = [];
    globalThis.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
    ) as typeof fetch;

    const client = new OmoiOSClient({
      baseUrl: 'http://localhost:18000',
      apiKey: 'very-secret-key',
      telemetry: (e) => events.push(e),
    });

    await client.connections.list();

    const serialized = JSON.stringify(events);
    expect(serialized).not.toContain('very-secret-key');
    expect(serialized).not.toContain('Authorization');
  });

  it('is a no-op when telemetry option is omitted', async () => {
    globalThis.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
    ) as typeof fetch;

    const client = new OmoiOSClient({
      baseUrl: 'http://localhost:18000',
      apiKey: 'k',
    });

    // Should not throw or otherwise misbehave.
    await expect(client.connections.list()).resolves.toEqual([]);
  });
});
