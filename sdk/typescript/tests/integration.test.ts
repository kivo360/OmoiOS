import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createServer, type Server, type IncomingMessage, type ServerResponse } from 'node:http';
import { OmoiOSClient } from '../src/client.js';
import {
  AuthError,
  NotFoundError,
  ServerError,
  ValidationError,
} from '../src/errors.js';

describe('OmoiOSClient integration', () => {
  let server: Server;
  let baseUrl: string;
  let requestLog: { method: string; url: string; headers: Record<string, string>; body: string }[] = [];
  let nextResponse: { status: number; body?: string } | null = null;

  function getPathname(reqUrl: string | undefined): string {
    if (!reqUrl) return '/';
    return new URL(reqUrl, baseUrl).pathname;
  }

  beforeAll(async () => {
    server = createServer((req: IncomingMessage, res: ServerResponse) => {
      let body = '';
      req.on('data', (chunk) => {
        body += chunk;
      });
      req.on('end', () => {
        requestLog.push({
          method: req.method ?? 'GET',
          url: req.url ?? '/',
          headers: Object.fromEntries(
            Object.entries(req.headers).map(([k, v]) => [k, String(v)])
          ),
          body,
        });

        if (nextResponse) {
          const { status, body: responseBody } = nextResponse;
          nextResponse = null;
          res.writeHead(status);
          res.end(responseBody ?? JSON.stringify({ detail: 'Overridden' }));
          return;
        }

        const pathname = getPathname(req.url);

        if (pathname.startsWith('/api/v1/credentials')) {
          handleCredentials(req, res, pathname);
        } else if (pathname.startsWith('/api/v1/environments')) {
          handleEnvironments(req, res, pathname);
        } else if (pathname.startsWith('/api/v1/artifacts')) {
          handleArtifacts(req, res, pathname);
        } else if (pathname.startsWith('/api/v1/webhooks/subscriptions')) {
          handleWebhooks(req, res, pathname);
        } else if (pathname.startsWith('/api/v1/workspaces')) {
          handleWorkspaces(req, res, pathname);
        } else {
          res.writeHead(404);
          res.end(JSON.stringify({ detail: 'Not found' }));
        }
      });
    });

    await new Promise<void>((resolve) => {
      server.listen(0, '127.0.0.1', () => {
        const addr = server.address();
        if (addr && typeof addr === 'object') {
          baseUrl = `http://127.0.0.1:${addr.port}`;
        }
        resolve();
      });
    });
  });

  afterAll(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  beforeEach(() => {
    requestLog = [];
    nextResponse = null;
  });

  function handleCredentials(req: IncomingMessage, res: ServerResponse, pathname: string): void {
    if (req.method === 'GET' && pathname === '/api/v1/credentials') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify([{ id: 'cred_1', workspace_id: 'ws_1', kind: 'bearer_secret', name: 'test', created_at: '2024-01-01T00:00:00Z' }]));
    } else if (req.method === 'GET' && pathname === '/api/v1/credentials/cred_1') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'cred_1', workspace_id: 'ws_1', kind: 'bearer_secret', name: 'test', created_at: '2024-01-01T00:00:00Z' }));
    } else if (req.method === 'POST' && pathname === '/api/v1/credentials') {
      res.writeHead(201, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'cred_new', workspace_id: 'ws_1', kind: 'bearer_secret', name: 'new', created_at: '2024-01-01T00:00:00Z' }));
    } else if (req.method === 'DELETE' && pathname === '/api/v1/credentials/cred_1') {
      res.writeHead(204);
      res.end();
    } else {
      res.writeHead(404);
      res.end(JSON.stringify({ detail: 'Not found' }));
    }
  }

  function handleEnvironments(req: IncomingMessage, res: ServerResponse, pathname: string): void {
    if (req.method === 'GET' && pathname === '/api/v1/environments') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify([{ id: 'env_1', org_id: 'org_1', name: 'staging', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }]));
    } else if (req.method === 'GET' && pathname === '/api/v1/environments/env_1') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        environment: { id: 'env_1', org_id: 'org_1', name: 'staging', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
        latest_version: { id: 'ver_1', environment_id: 'env_1', version_number: 1, variables: {}, created_at: '2024-01-01T00:00:00Z' },
      }));
    } else if (req.method === 'POST' && pathname === '/api/v1/environments') {
      res.writeHead(201, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'env_new', org_id: 'org_1', name: 'production', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }));
    } else if (req.method === 'POST' && pathname === '/api/v1/environments/env_1/versions') {
      res.writeHead(201, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'ver_new', environment_id: 'env_1', version_number: 2, variables: { VAR: { type: 'string', value: 'v' } }, created_at: '2024-01-01T00:00:00Z' }));
    } else {
      res.writeHead(404);
      res.end(JSON.stringify({ detail: 'Not found' }));
    }
  }

  function handleArtifacts(req: IncomingMessage, res: ServerResponse, pathname: string): void {
    if (req.method === 'GET' && pathname === '/api/v1/artifacts') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify([{ id: 'art_1', workspace_id: 'ws_1', name: 'file.txt', storage_backend: 'local', checksum: 'sha256:abc', size_bytes: 100, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }]));
    } else if (req.method === 'GET' && pathname === '/api/v1/artifacts/art_1') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'art_1', workspace_id: 'ws_1', name: 'file.txt', storage_backend: 'local', checksum: 'sha256:abc', size_bytes: 100, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }));
    } else if (req.method === 'GET' && pathname === '/api/v1/artifacts/art_1/download') {
      res.writeHead(200, { 'Content-Type': 'application/octet-stream' });
      res.end(Buffer.from('artifact content'));
    } else if (req.method === 'POST' && pathname === '/api/v1/artifacts/upload') {
      res.writeHead(201, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'art_new', workspace_id: 'ws_1', name: 'uploaded.bin', storage_backend: 'local', checksum: 'sha256:def', size_bytes: 1024, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }));
    } else if (req.method === 'DELETE' && pathname === '/api/v1/artifacts/art_1') {
      res.writeHead(204);
      res.end();
    } else {
      res.writeHead(404);
      res.end(JSON.stringify({ detail: 'Not found' }));
    }
  }

  function handleWebhooks(req: IncomingMessage, res: ServerResponse, pathname: string): void {
    if (req.method === 'GET' && pathname === '/api/v1/webhooks/subscriptions') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify([{ id: 'wh_1', org_id: 'org_1', url: 'https://example.com/hook', events: ['spec.created'], active: true, created_at: '2024-01-01T00:00:00Z' }]));
    } else if (req.method === 'GET' && pathname === '/api/v1/webhooks/subscriptions/wh_1') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'wh_1', org_id: 'org_1', url: 'https://example.com/hook', events: ['spec.created'], active: true, created_at: '2024-01-01T00:00:00Z' }));
    } else if (req.method === 'POST' && pathname === '/api/v1/webhooks/subscriptions') {
      res.writeHead(201, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'wh_new', org_id: 'org_1', url: 'https://new.com/hook', events: ['task.completed'], active: true, created_at: '2024-01-01T00:00:00Z' }));
    } else if (req.method === 'PATCH' && pathname === '/api/v1/webhooks/subscriptions/wh_1') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'wh_1', org_id: 'org_1', url: 'https://updated.com/hook', events: ['spec.created'], active: true, created_at: '2024-01-01T00:00:00Z' }));
    } else if (req.method === 'DELETE' && pathname === '/api/v1/webhooks/subscriptions/wh_1') {
      res.writeHead(204);
      res.end();
    } else if (req.method === 'GET' && pathname === '/api/v1/webhooks/subscriptions/wh_1/deliveries') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify([{ id: 'wd_1', subscription_id: 'wh_1', event: 'spec.created', payload: {}, status: 'delivered', attempts: 1, created_at: '2024-01-01T00:00:00Z' }]));
    } else if (req.method === 'POST' && pathname === '/api/v1/webhooks/subscriptions/wh_1/test') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ subscription_id: 'wh_1', event: 'spec.created', success: true }));
    } else {
      res.writeHead(404);
      res.end(JSON.stringify({ detail: 'Not found' }));
    }
  }

  function handleWorkspaces(req: IncomingMessage, res: ServerResponse, pathname: string): void {
    if (req.method === 'GET' && pathname === '/api/v1/workspaces/ws_1/settings') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'ws_settings_1', workspace_id: 'ws_1', egress_allowlist: ['api.github.com'], max_artifact_size_mb: 100, allowed_binding_kinds: ['bearer_secret'] }));
    } else if (req.method === 'PUT' && pathname === '/api/v1/workspaces/ws_1/settings') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 'ws_settings_1', workspace_id: 'ws_1', egress_allowlist: ['api.github.com', 'pypi.org'], max_artifact_size_mb: 200, allowed_binding_kinds: ['bearer_secret'] }));
    } else {
      res.writeHead(404);
      res.end(JSON.stringify({ detail: 'Not found' }));
    }
  }

  describe('initialization', () => {
    it('throws if no credential kind is provided', () => {
      expect(() => new OmoiOSClient({ baseUrl })).toThrow(
        'One of apiKey, jwtToken, or sessionToken must be provided'
      );
    });

    it('throws if multiple credential kinds are provided', () => {
      expect(
        () =>
          new OmoiOSClient({ baseUrl, apiKey: 'a', jwtToken: 'b' })
      ).toThrow('mutually exclusive');
    });

    it('accepts apiKey', () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test-key' });
      expect(client.apiKey).toBe('test-key');
      expect(client.jwtToken).toBeUndefined();
    });

    it('accepts jwtToken', () => {
      const client = new OmoiOSClient({ baseUrl, jwtToken: 'test-jwt' });
      expect(client.jwtToken).toBe('test-jwt');
      expect(client.apiKey).toBeUndefined();
    });

    it('accepts sessionToken', () => {
      const client = new OmoiOSClient({ baseUrl, sessionToken: 'sess_tok_abc' });
      expect(client.sessionToken).toBe('sess_tok_abc');
    });

    it('strips trailing slash from baseUrl', () => {
      const client = new OmoiOSClient({ baseUrl: baseUrl + '/', apiKey: 'test-key' });
      expect(client.baseUrl).toBe(baseUrl);
    });
  });

  describe('authentication headers', () => {
    it('sends Authorization Bearer + X-API-Key for platform keys (spec §01)', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'my-api-key' });
      await client.credentials.list('ws_1');

      // Spec §01 wants Bearer for all token kinds; we also keep X-API-Key as
      // a transitional echo so old backends still recognize the caller.
      expect(requestLog[0].headers['authorization']).toBe('Bearer my-api-key');
      expect(requestLog[0].headers['x-api-key']).toBe('my-api-key');
    });

    it('sends Authorization Bearer header for jwtToken auth', async () => {
      const client = new OmoiOSClient({ baseUrl, jwtToken: 'my-jwt-token' });
      await client.credentials.list('ws_1');

      expect(requestLog[0].headers['authorization']).toBe('Bearer my-jwt-token');
      expect(requestLog[0].headers['x-api-key']).toBeUndefined();
    });

    it('sends Authorization Bearer header for sessionToken auth', async () => {
      const client = new OmoiOSClient({ baseUrl, sessionToken: 'sess_tok_xyz' });
      await client.credentials.list('ws_1');

      expect(requestLog[0].headers['authorization']).toBe('Bearer sess_tok_xyz');
      expect(requestLog[0].headers['x-api-key']).toBeUndefined();
    });
  });

  describe('credentials resource', () => {
    it('list sends GET with workspace_id param', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const creds = await client.credentials.list('ws_1');

      expect(requestLog[0].method).toBe('GET');
      expect(requestLog[0].url).toBe('/api/v1/credentials?workspace_id=ws_1');
      expect(creds[0].id).toBe('cred_1');
    });

    it('get sends GET by id', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const cred = await client.credentials.get('cred_1');

      expect(requestLog[0].method).toBe('GET');
      expect(requestLog[0].url).toBe('/api/v1/credentials/cred_1');
      expect(cred.id).toBe('cred_1');
    });

    it('create sends POST with JSON body', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const cred = await client.credentials.create({
        workspace_id: 'ws_1',
        kind: 'bearer_secret',
        name: 'new',
        value: 'secret',
      });

      expect(requestLog[0].method).toBe('POST');
      expect(requestLog[0].headers['content-type']).toBe('application/json');
      expect(JSON.parse(requestLog[0].body)).toEqual({
        workspace_id: 'ws_1',
        kind: 'bearer_secret',
        name: 'new',
        value: 'secret',
      });
      expect(cred.id).toBe('cred_new');
    });

    it('delete sends DELETE', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      await client.credentials.delete('cred_1');

      expect(requestLog[0].method).toBe('DELETE');
      expect(requestLog[0].url).toBe('/api/v1/credentials/cred_1');
    });
  });

  describe('environments resource', () => {
    it('list sends GET with org_id param', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const envs = await client.environments.list('org_1');

      expect(requestLog[0].method).toBe('GET');
      expect(requestLog[0].url).toBe('/api/v1/environments?org_id=org_1');
      expect(envs[0].name).toBe('staging');
    });

    it('get returns environment and latest_version', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const result = await client.environments.get('env_1');

      expect(requestLog[0].method).toBe('GET');
      expect(result.environment.id).toBe('env_1');
      expect(result.latest_version).not.toBeNull();
    });

    it('create sends POST', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const env = await client.environments.create({ name: 'production', org_id: 'org_1' });

      expect(requestLog[0].method).toBe('POST');
      expect(env.name).toBe('production');
    });

    it('createVersion sends POST', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const version = await client.environments.createVersion('env_1', {
        variables: { VAR: { type: 'string', value: 'v' } },
      });

      expect(requestLog[0].method).toBe('POST');
      expect(version.environment_id).toBe('env_1');
    });
  });

  describe('artifacts resource', () => {
    it('list sends GET with workspace_id, limit, offset', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const artifacts = await client.artifacts.list('ws_1', 50, 10);

      expect(requestLog[0].method).toBe('GET');
      expect(requestLog[0].url).toBe('/api/v1/artifacts?workspace_id=ws_1&limit=50&offset=10');
      expect(artifacts[0].id).toBe('art_1');
    });

    it('get sends GET by id', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const artifact = await client.artifacts.get('art_1');

      expect(requestLog[0].method).toBe('GET');
      expect(artifact.id).toBe('art_1');
    });

    it('upload sends POST with FormData', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const content = Buffer.from('file content');
      const artifact = await client.artifacts.upload(content, 'ws_1', 'test.bin', 'text/plain', { source: 'test' });

      expect(requestLog[0].method).toBe('POST');
      expect(requestLog[0].url).toBe('/api/v1/artifacts/upload');
      expect(requestLog[0].headers['content-type']).toContain('multipart/form-data');
      expect(artifact.id).toBe('art_new');
    });

    it('download returns buffer', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const content = await client.artifacts.download('art_1');

      expect(requestLog[0].method).toBe('GET');
      expect(content.toString()).toBe('artifact content');
    });

    it('delete sends DELETE', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      await client.artifacts.delete('art_1');

      expect(requestLog[0].method).toBe('DELETE');
    });
  });

  describe('webhooks resource', () => {
    it('list sends GET with org_id, active_only, limit, offset', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const subs = await client.webhooks.list('org_1', true, 50, 10);

      expect(requestLog[0].method).toBe('GET');
      expect(requestLog[0].url).toBe('/api/v1/webhooks/subscriptions?org_id=org_1&active_only=true&limit=50&offset=10');
      expect(subs[0].url).toBe('https://example.com/hook');
    });

    it('get sends GET by id', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const sub = await client.webhooks.get('wh_1');

      expect(requestLog[0].method).toBe('GET');
      expect(sub.id).toBe('wh_1');
    });

    it('create sends POST with org_id query param', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const sub = await client.webhooks.create('org_1', { url: 'https://new.com/hook', events: ['task.completed'], secret: 'secret' });

      expect(requestLog[0].method).toBe('POST');
      expect(requestLog[0].url).toBe('/api/v1/webhooks/subscriptions?org_id=org_1');
      expect(sub.id).toBe('wh_new');
    });

    it('update sends PATCH', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const sub = await client.webhooks.update('wh_1', { url: 'https://updated.com/hook' });

      expect(requestLog[0].method).toBe('PATCH');
      expect(sub.url).toBe('https://updated.com/hook');
    });

    it('delete sends DELETE', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      await client.webhooks.delete('wh_1');

      expect(requestLog[0].method).toBe('DELETE');
    });

    it('listDeliveries sends GET', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const deliveries = await client.webhooks.listDeliveries('wh_1', 'delivered', 50, 10);

      expect(requestLog[0].method).toBe('GET');
      expect(requestLog[0].url).toBe('/api/v1/webhooks/subscriptions/wh_1/deliveries?limit=50&offset=10&status_filter=delivered');
      expect(deliveries[0].subscription_id).toBe('wh_1');
    });

    it('test sends POST', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const result = await client.webhooks.test('wh_1', 'spec.created', { data: 'value' });

      expect(requestLog[0].method).toBe('POST');
      expect(result.success).toBe(true);
    });
  });

  describe('workspaces resource', () => {
    it('getSettings sends GET', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const settings = await client.workspaces.getSettings('ws_1');

      expect(requestLog[0].method).toBe('GET');
      expect(settings.workspace_id).toBe('ws_1');
      expect(settings.max_artifact_size_mb).toBe(100);
    });

    it('updateSettings sends PUT with JSON body', async () => {
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      const settings = await client.workspaces.updateSettings('ws_1', { max_artifact_size_mb: 200 });

      expect(requestLog[0].method).toBe('PUT');
      expect(requestLog[0].headers['content-type']).toBe('application/json');
      expect(JSON.parse(requestLog[0].body)).toEqual({ max_artifact_size_mb: 200 });
      expect(settings.max_artifact_size_mb).toBe(200);
    });
  });

  describe('error handling', () => {
    it('throws AuthError on 401', async () => {
      nextResponse = { status: 401, body: JSON.stringify({ detail: 'Unauthorized' }) };
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      await expect(client.credentials.get('unauthorized')).rejects.toThrow(AuthError);
    });

    it('throws NotFoundError on 404', async () => {
      nextResponse = { status: 404, body: JSON.stringify({ detail: 'Not found' }) };
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      await expect(client.credentials.get('missing')).rejects.toThrow(NotFoundError);
    });

    it('throws ValidationError on 400', async () => {
      nextResponse = { status: 400, body: JSON.stringify({ detail: 'Bad request' }) };
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      await expect(client.credentials.get('bad')).rejects.toThrow(ValidationError);
    });

    it('throws ServerError on 500', async () => {
      nextResponse = { status: 500, body: JSON.stringify({ detail: 'Internal error' }) };
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      await expect(client.credentials.get('error')).rejects.toThrow(ServerError);
    });

    it('throws ValidationError on 422', async () => {
      nextResponse = { status: 422, body: JSON.stringify({ detail: 'Unprocessable' }) };
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test' });
      await expect(client.credentials.get('invalid')).rejects.toThrow(ValidationError);
    });
  });

  describe('timeout', () => {
    it('aborts request after timeout', async () => {
      nextResponse = null;
      const client = new OmoiOSClient({ baseUrl, apiKey: 'test', timeout: 100 });
      await expect(client.credentials.get('slow')).rejects.toThrow();
    });
  });
});
