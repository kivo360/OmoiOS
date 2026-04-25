/**
 * Usage — spec §18 §2 canonical SDK resource.
 *
 * Two methods:
 *   current()           → org-level summary for current billing period
 *   forSession(sid)     → per-session breakdown
 */

import type { OmoiOSClient } from '../client.js';

export interface UsageSummary {
  organization_id?: string;
  subscription_tier?: string;
  workflows_used: number;
  workflows_limit: number;
  free_workflows_remaining: number;
  credit_balance: number;
  can_execute: boolean;
  reason: string;
}

export interface SessionUsage {
  session_id: string;
  compute_seconds: number;
  tokens_input: number;
  tokens_output: number;
  total_cost: number;
}

export class UsageResource {
  constructor(private readonly client: OmoiOSClient) {}

  /** Return the current billing-period summary for an org. */
  async current(organizationId?: string): Promise<UsageSummary> {
    const searchParams = organizationId
      ? { organization_id: organizationId }
      : undefined;
    const res = await this.client._request('GET', '/api/v1/usage', {
      searchParams,
    });
    return (await res.json()) as UsageSummary;
  }

  /** Return compute_seconds + token totals for a single session. */
  async forSession(sessionId: string): Promise<SessionUsage> {
    const res = await this.client._request(
      'GET',
      `/api/v1/usage/sessions/${sessionId}`,
    );
    return (await res.json()) as SessionUsage;
  }
}
