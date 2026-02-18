/**
 * React Query hooks for Agents API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listAgents,
  getAgent,
  registerAgent,
  updateAgent,
  toggleAgentAvailability,
  searchAgents,
  getAgentsHealth,
  getAgentStatistics,
  getAgentHealth,
  getStaleAgents,
  cleanupStaleAgents,
} from "@/lib/api/agents";
import type {
  Agent,
  AgentRegisterRequest,
  AgentUpdateRequest,
  AgentMatchResponse,
  AgentHealth,
  AgentStatistics,
} from "@/lib/api/types";

// Query keys
export const agentKeys = {
  all: ["agents"] as const,
  lists: () => [...agentKeys.all, "list"] as const,
  list: () => [...agentKeys.lists()] as const,
  details: () => [...agentKeys.all, "detail"] as const,
  detail: (id: string) => [...agentKeys.details(), id] as const,
  health: () => [...agentKeys.all, "health"] as const,
  healthAll: () => [...agentKeys.health(), "all"] as const,
  healthAgent: (id: string) => [...agentKeys.health(), id] as const,
  statistics: () => [...agentKeys.all, "statistics"] as const,
  stale: () => [...agentKeys.all, "stale"] as const,
  search: (params: object) => [...agentKeys.all, "search", params] as const,
};

/**
 * Hook to fetch list of all agents
 */
export function useAgents() {
  return useQuery<Agent[]>({
    queryKey: agentKeys.list(),
    queryFn: listAgents,
  });
}

/**
 * Hook to fetch a single agent
 */
export function useAgent(agentId: string | undefined) {
  return useQuery<Agent>({
    queryKey: agentKeys.detail(agentId!),
    queryFn: () => getAgent(agentId!),
    enabled: !!agentId,
  });
}

/**
 * Hook to register a new agent
 */
export function useRegisterAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AgentRegisterRequest) => registerAgent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: agentKeys.statistics() });
    },
  });
}

/**
 * Hook to update an agent
 */
export function useUpdateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      agentId,
      data,
    }: {
      agentId: string;
      data: AgentUpdateRequest;
    }) => updateAgent(agentId, data),
    onSuccess: (_, { agentId }) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
    },
  });
}

/**
 * Hook to toggle agent availability
 */
export function useToggleAgentAvailability() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      agentId,
      available,
    }: {
      agentId: string;
      available: boolean;
    }) => toggleAgentAvailability(agentId, available),
    onSuccess: (_, { agentId }) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
    },
  });
}

/**
 * Hook to search for agents
 */
export function useSearchAgents(params?: {
  capabilities?: string[];
  phase_id?: string;
  agent_type?: string;
  limit?: number;
}) {
  return useQuery<AgentMatchResponse[]>({
    queryKey: agentKeys.search(params ?? {}),
    queryFn: () => searchAgents(params),
    enabled:
      !!params?.capabilities?.length ||
      !!params?.phase_id ||
      !!params?.agent_type,
  });
}

/**
 * Hook to get health status for all agents
 */
export function useAgentsHealth(timeoutSeconds?: number) {
  return useQuery<AgentHealth[]>({
    queryKey: agentKeys.healthAll(),
    queryFn: () => getAgentsHealth(timeoutSeconds),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Hook to get agent statistics
 */
export function useAgentStatistics() {
  return useQuery<AgentStatistics>({
    queryKey: agentKeys.statistics(),
    queryFn: getAgentStatistics,
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Hook to get health for a specific agent
 */
export function useAgentHealth(
  agentId: string | undefined,
  timeoutSeconds?: number,
) {
  return useQuery<AgentHealth>({
    queryKey: agentKeys.healthAgent(agentId!),
    queryFn: () => getAgentHealth(agentId!, timeoutSeconds),
    enabled: !!agentId,
    refetchInterval: 15000, // Refresh every 15 seconds
  });
}

/**
 * Hook to get stale agents
 */
export function useStaleAgents(timeoutSeconds?: number) {
  return useQuery<Agent[]>({
    queryKey: agentKeys.stale(),
    queryFn: () => getStaleAgents(timeoutSeconds),
    refetchInterval: 60000, // Refresh every minute
  });
}

/**
 * Hook to cleanup stale agents
 */
export function useCleanupStaleAgents() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params?: { timeout_seconds?: number; mark_as?: string }) =>
      cleanupStaleAgents(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all });
    },
  });
}
