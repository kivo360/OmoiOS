/**
 * React Query hooks for Commits API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getCommit,
  getTicketCommits,
  getAgentCommits,
  linkCommitToTicket,
  getCommitDiff,
} from "@/lib/api/commits";
import type {
  Commit,
  CommitListResponse,
  CommitDiffResponse,
  LinkCommitRequest,
} from "@/lib/api/types";

// Query keys
export const commitKeys = {
  all: ["commits"] as const,
  details: () => [...commitKeys.all, "detail"] as const,
  detail: (sha: string) => [...commitKeys.details(), sha] as const,
  diff: (sha: string) => [...commitKeys.detail(sha), "diff"] as const,
  byTicket: (ticketId: string) =>
    [...commitKeys.all, "ticket", ticketId] as const,
  byAgent: (agentId: string) => [...commitKeys.all, "agent", agentId] as const,
};

/**
 * Hook to fetch a single commit
 */
export function useCommit(commitSha: string | undefined) {
  return useQuery<Commit>({
    queryKey: commitKeys.detail(commitSha!),
    queryFn: () => getCommit(commitSha!),
    enabled: !!commitSha,
  });
}

/**
 * Hook to fetch commits for a ticket
 */
export function useTicketCommits(
  ticketId: string | undefined,
  params?: { limit?: number; offset?: number },
) {
  return useQuery<CommitListResponse>({
    queryKey: commitKeys.byTicket(ticketId!),
    queryFn: () => getTicketCommits(ticketId!, params),
    enabled: !!ticketId,
  });
}

/**
 * Hook to fetch commits by an agent
 */
export function useAgentCommits(
  agentId: string | undefined,
  params?: { limit?: number; offset?: number },
) {
  return useQuery<CommitListResponse>({
    queryKey: commitKeys.byAgent(agentId!),
    queryFn: () => getAgentCommits(agentId!, params),
    enabled: !!agentId,
  });
}

/**
 * Hook to fetch commit diff
 */
export function useCommitDiff(
  commitSha: string | undefined,
  filePath?: string,
) {
  return useQuery<CommitDiffResponse>({
    queryKey: commitKeys.diff(commitSha!),
    queryFn: () => getCommitDiff(commitSha!, filePath),
    enabled: !!commitSha,
  });
}

/**
 * Hook to link a commit to a ticket
 */
export function useLinkCommit() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      ticketId,
      data,
    }: {
      ticketId: string;
      data: LinkCommitRequest;
    }) => linkCommitToTicket(ticketId, data),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({
        queryKey: commitKeys.byTicket(ticketId),
      });
    },
  });
}
