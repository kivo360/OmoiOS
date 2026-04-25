/**
 * Connections — user-linked OAuth (spec §18 §2).
 *
 * V1 surfaces GitHub personal OAuth. LLM keys stay under `credentials`.
 */

import type { OmoiOSClient } from '../client.js';

export interface Connection {
  provider: string;
  connected_at?: string | null;
  scopes: string[];
}

export interface OAuthStart {
  oauth_start_url: string;
}

export class ConnectionsResource {
  constructor(private readonly client: OmoiOSClient) {}

  /** List providers the current user has connected. */
  async list(): Promise<Connection[]> {
    const res = await this.client._request('GET', '/api/v1/connections');
    return (await res.json()) as Connection[];
  }

  /** Revoke / wipe the stored token for a provider. */
  async remove(provider: string): Promise<void> {
    await this.client._request('DELETE', `/api/v1/connections/${provider}`);
  }

  /**
   * Get the URL the user should open to start the OAuth flow.
   *
   * The SDK does not handle the callback — the platform's existing
   * dashboard callback persists the token. Re-call `list()` after the
   * user completes the flow to observe the connection has landed.
   */
  async oauthUrl(provider: string): Promise<string> {
    const res = await this.client._request(
      'POST',
      `/api/v1/connections/${provider}/start`,
    );
    const body = (await res.json()) as OAuthStart;
    return body.oauth_start_url;
  }
}
