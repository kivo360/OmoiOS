# OmoiOS TypeScript SDK

TypeScript SDK for the OmoiOS Agent Workspace Platform.

Resources: `sessions`, `environments`, `credentials`, `artifacts`,
`webhooks`, `workspaces`, `connections`, `usage` — spec §18 §2's canonical
seven plus workspace management.

## Spec §18 primitive patterns

```typescript
import { OmoiOSClient } from '@omoios/sdk';

const client = new OmoiOSClient({
  baseUrl: 'https://api.omoios.dev',
  apiKey: key,
  telemetry: (e) => console.log(e.kind, e.path, e.status, e.durationMs),
});

// Pattern A — fire and forget
const s = await client.sessions.create({
  workspaceId: ws,
  prompt: 'build an endpoint',
});

// Pattern B — sync wait
for await (const e of client.sessions.events(s.id)) {
  if (e.type === 'session.succeeded') break;
}

// Pattern C — live stream
for await (const e of client.sessions.events(s.id)) render(e);

// Pattern D — multiplayer
const ch = client.sessions.connect(s.id, jwt);
ch.on('cursor.moved', onCursor);
await ch.open();
```

## Cancellation

Every request method accepts an `AbortSignal` via `options.signal`. The
client merges it with its own timeout controller so whichever aborts
first wins:

```typescript
const controller = new AbortController();
setTimeout(() => controller.abort(), 5000);
await client.sessions.create({
  workspaceId: ws,
  prompt: '...',
  signal: controller.signal,
});
```

## Telemetry

The constructor's `telemetry` callback sees every HTTP lifecycle event
with a stable shape:

```typescript
type TelemetryEvent = {
  kind: 'request' | 'response' | 'stream_open' | 'stream_close' | 'error';
  method?: string;
  path: string;
  status?: number;
  durationMs?: number;
  framesReceived?: number;
  error?: string;
};
```

Auth headers are never included. Callback exceptions are swallowed —
telemetry cannot break a request path.

## Installation

```bash
pnpm add @omoios/sdk
```

Or with npm:

```bash
npm install @omoios/sdk
```

## Quick Start

```typescript
import { MockOmoiOSClient } from '@omoios/sdk';

// Use mock client for development
const client = new MockOmoiOSClient();

// List credentials
const credentials = client.listCredentials();
console.log(credentials);

// Create an environment
const env = client.createEnvironment({ name: 'staging', description: 'Staging environment' });
console.log(env);
```

## Development

```bash
cd sdk/typescript
pnpm install
pnpm test
```

## API Coverage

- Credentials (CRUD)
- Environments (versioned)
- Artifacts (upload/download)
- Webhooks (subscriptions & deliveries)
- Workspaces (settings)

## License

Apache License 2.0
