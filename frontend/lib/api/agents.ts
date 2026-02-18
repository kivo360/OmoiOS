/**
 * Agents API functions
 */

import { apiRequest } from "./client";
import type {
  Agent,
  AgentRegisterRequest,
  AgentUpdateRequest,
  AgentMatchResponse,
  AgentHealth,
  AgentStatistics,
} from "./types";

/**
 * List all agents
 */
export async function listAgents(): Promise<Agent[]> {
  return apiRequest<Agent[]>("/api/v1/agents");
}

/**
 * Get a specific agent by ID
 */
export async function getAgent(agentId: string): Promise<Agent> {
  return apiRequest<Agent>(`/api/v1/agents/${agentId}`);
}

/**
 * Register a new agent
 */
export async function registerAgent(
  data: AgentRegisterRequest,
): Promise<Agent> {
  return apiRequest<Agent>("/api/v1/agents/register", {
    method: "POST",
    body: data,
  });
}

/**
 * Update an agent
 */
export async function updateAgent(
  agentId: string,
  data: AgentUpdateRequest,
): Promise<Agent> {
  return apiRequest<Agent>(`/api/v1/agents/${agentId}`, {
    method: "PATCH",
    body: data,
  });
}

/**
 * Toggle agent availability
 */
export async function toggleAgentAvailability(
  agentId: string,
  available: boolean,
): Promise<Agent> {
  return apiRequest<Agent>(`/api/v1/agents/${agentId}/availability`, {
    method: "POST",
    body: { available },
  });
}

/**
 * Search for agents by capabilities
 */
export async function searchAgents(params?: {
  capabilities?: string[];
  phase_id?: string;
  agent_type?: string;
  limit?: number;
}): Promise<AgentMatchResponse[]> {
  const searchParams = new URLSearchParams();
  if (params?.capabilities) {
    params.capabilities.forEach((c) => searchParams.append("capabilities", c));
  }
  if (params?.phase_id) searchParams.set("phase_id", params.phase_id);
  if (params?.agent_type) searchParams.set("agent_type", params.agent_type);
  if (params?.limit) searchParams.set("limit", String(params.limit));

  const query = searchParams.toString();
  const url = query
    ? `/api/v1/agents/search?${query}`
    : "/api/v1/agents/search";

  return apiRequest<AgentMatchResponse[]>(url);
}

/**
 * Get health status for all agents
 */
export async function getAgentsHealth(
  timeoutSeconds?: number,
): Promise<AgentHealth[]> {
  const url = timeoutSeconds
    ? `/api/v1/agents/health?timeout_seconds=${timeoutSeconds}`
    : "/api/v1/agents/health";
  return apiRequest<AgentHealth[]>(url);
}

/**
 * Get agent statistics
 */
export async function getAgentStatistics(): Promise<AgentStatistics> {
  return apiRequest<AgentStatistics>("/api/v1/agents/statistics");
}

/**
 * Get health for a specific agent
 */
export async function getAgentHealth(
  agentId: string,
  timeoutSeconds?: number,
): Promise<AgentHealth> {
  const url = timeoutSeconds
    ? `/api/v1/agents/${agentId}/health?timeout_seconds=${timeoutSeconds}`
    : `/api/v1/agents/${agentId}/health`;
  return apiRequest<AgentHealth>(url);
}

/**
 * Get stale agents
 */
export async function getStaleAgents(
  timeoutSeconds?: number,
): Promise<Agent[]> {
  const url = timeoutSeconds
    ? `/api/v1/agents/stale?timeout_seconds=${timeoutSeconds}`
    : "/api/v1/agents/stale";
  return apiRequest<Agent[]>(url);
}

/**
 * Cleanup stale agents
 */
export async function cleanupStaleAgents(params?: {
  timeout_seconds?: number;
  mark_as?: string;
}): Promise<{ success: boolean; marked_count: number; message: string }> {
  const searchParams = new URLSearchParams();
  if (params?.timeout_seconds)
    searchParams.set("timeout_seconds", String(params.timeout_seconds));
  if (params?.mark_as) searchParams.set("mark_as", params.mark_as);

  const query = searchParams.toString();
  const url = query
    ? `/api/v1/agents/cleanup-stale?${query}`
    : "/api/v1/agents/cleanup-stale";

  return apiRequest<{
    success: boolean;
    marked_count: number;
    message: string;
  }>(url, { method: "POST" });
}
