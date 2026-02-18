/**
 * Commits API functions
 */

import { apiRequest } from "./client";
import type {
  Commit,
  CommitListResponse,
  CommitDiffResponse,
  LinkCommitRequest,
} from "./types";

/**
 * Get commit details by SHA
 */
export async function getCommit(commitSha: string): Promise<Commit> {
  return apiRequest<Commit>(`/api/v1/commits/${commitSha}`);
}

/**
 * Get all commits linked to a ticket
 */
export async function getTicketCommits(
  ticketId: string,
  params?: { limit?: number; offset?: number },
): Promise<CommitListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));

  const query = searchParams.toString();
  const url = query
    ? `/api/v1/commits/ticket/${ticketId}?${query}`
    : `/api/v1/commits/ticket/${ticketId}`;

  return apiRequest<CommitListResponse>(url);
}

/**
 * Get all commits made by an agent
 */
export async function getAgentCommits(
  agentId: string,
  params?: { limit?: number; offset?: number },
): Promise<CommitListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));

  const query = searchParams.toString();
  const url = query
    ? `/api/v1/commits/agent/${agentId}?${query}`
    : `/api/v1/commits/agent/${agentId}`;

  return apiRequest<CommitListResponse>(url);
}

/**
 * Link a commit to a ticket
 */
export async function linkCommitToTicket(
  ticketId: string,
  data: LinkCommitRequest,
): Promise<Commit> {
  return apiRequest<Commit>(`/api/v1/commits/ticket/${ticketId}/link`, {
    method: "POST",
    body: data,
  });
}

/**
 * Get commit diff (file-by-file changes)
 */
export async function getCommitDiff(
  commitSha: string,
  filePath?: string,
): Promise<CommitDiffResponse> {
  const url = filePath
    ? `/api/v1/commits/${commitSha}/diff?file_path=${encodeURIComponent(filePath)}`
    : `/api/v1/commits/${commitSha}/diff`;
  return apiRequest<CommitDiffResponse>(url);
}
