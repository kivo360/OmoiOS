/**
 * Tickets API functions
 */

import { apiRequest } from "./client";
import type {
  Ticket,
  TicketCreate,
  TicketListParams,
  TicketListResponse,
  TicketTransitionRequest,
  DuplicateCheckResponse,
} from "./types";

/**
 * List all tickets with pagination and filtering
 */
export async function listTickets(
  params?: TicketListParams,
): Promise<TicketListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.status) searchParams.set("status", params.status);
  if (params?.priority) searchParams.set("priority", params.priority);
  if (params?.phase_id) searchParams.set("phase_id", params.phase_id);
  if (params?.project_id) searchParams.set("project_id", params.project_id);
  if (params?.search) searchParams.set("search", params.search);

  const query = searchParams.toString();
  const url = query ? `/api/v1/tickets?${query}` : "/api/v1/tickets";

  return apiRequest<TicketListResponse>(url);
}

/**
 * Check for duplicate tickets before creating
 */
export async function checkDuplicates(
  title: string,
  description?: string,
  similarityThreshold?: number,
): Promise<DuplicateCheckResponse> {
  return apiRequest<DuplicateCheckResponse>(
    "/api/v1/tickets/check-duplicates",
    {
      method: "POST",
      body: {
        title,
        description,
        similarity_threshold: similarityThreshold,
      },
    },
  );
}

/**
 * Get a specific ticket by ID
 */
export async function getTicket(ticketId: string): Promise<Ticket> {
  return apiRequest<Ticket>(`/api/v1/tickets/${ticketId}`);
}

/**
 * Create a new ticket
 */
export async function createTicket(data: TicketCreate): Promise<Ticket> {
  return apiRequest<Ticket>("/api/v1/tickets", {
    method: "POST",
    body: data,
  });
}

/**
 * Transition ticket to new status
 */
export async function transitionTicket(
  ticketId: string,
  data: TicketTransitionRequest,
): Promise<Ticket> {
  return apiRequest<Ticket>(`/api/v1/tickets/${ticketId}/transition`, {
    method: "POST",
    body: data,
  });
}

/**
 * Block a ticket
 */
export async function blockTicket(
  ticketId: string,
  blockerType: string,
  suggestedRemediation?: string,
): Promise<Ticket> {
  const params = new URLSearchParams();
  params.set("blocker_type", blockerType);
  if (suggestedRemediation)
    params.set("suggested_remediation", suggestedRemediation);

  return apiRequest<Ticket>(`/api/v1/tickets/${ticketId}/block?${params}`, {
    method: "POST",
  });
}

/**
 * Unblock a ticket
 */
export async function unblockTicket(ticketId: string): Promise<Ticket> {
  return apiRequest<Ticket>(`/api/v1/tickets/${ticketId}/unblock`, {
    method: "POST",
  });
}

/**
 * Progress ticket to next phase
 */
export async function progressTicket(
  ticketId: string,
): Promise<Ticket | { status: string }> {
  return apiRequest<Ticket | { status: string }>(
    `/api/v1/tickets/${ticketId}/progress`,
    { method: "POST" },
  );
}

/**
 * Approve a pending ticket
 */
export async function approveTicket(
  ticketId: string,
): Promise<{ ticket_id: string; status: string }> {
  return apiRequest<{ ticket_id: string; status: string }>(
    "/api/v1/tickets/approve",
    {
      method: "POST",
      body: { ticket_id: ticketId },
    },
  );
}

/**
 * Reject a pending ticket
 */
export async function rejectTicket(
  ticketId: string,
  rejectionReason: string,
): Promise<{ ticket_id: string; status: string }> {
  return apiRequest<{ ticket_id: string; status: string }>(
    "/api/v1/tickets/reject",
    {
      method: "POST",
      body: { ticket_id: ticketId, rejection_reason: rejectionReason },
    },
  );
}

/**
 * Get count of pending review tickets
 */
export async function getPendingReviewCount(): Promise<{
  pending_count: number;
}> {
  return apiRequest<{ pending_count: number }>(
    "/api/v1/tickets/pending-review-count",
  );
}

/**
 * Get ticket context
 */
export async function getTicketContext(ticketId: string): Promise<{
  ticket_id: string;
  full_context: Record<string, unknown>;
  summary: string | null;
}> {
  return apiRequest<{
    ticket_id: string;
    full_context: Record<string, unknown>;
    summary: string | null;
  }>(`/api/v1/tickets/${ticketId}/context`);
}

/**
 * Spawn phase tasks response
 */
export interface SpawnPhaseTasksResponse {
  ticket_id: string;
  phase_id: string;
  tasks_spawned: number;
  task_ids: string[];
  error?: string;
}

/**
 * Spawn tasks for a ticket's current phase
 * This kicks off the phase progression workflow
 */
export async function spawnPhaseTasks(
  ticketId: string,
  phaseId?: string,
): Promise<SpawnPhaseTasksResponse> {
  const params = new URLSearchParams();
  if (phaseId) params.set("phase_id", phaseId);

  const query = params.toString();
  const url = query
    ? `/api/v1/tickets/${ticketId}/spawn-phase-tasks?${query}`
    : `/api/v1/tickets/${ticketId}/spawn-phase-tasks`;

  return apiRequest<SpawnPhaseTasksResponse>(url, { method: "POST" });
}

/**
 * Batch spawn phase tasks for multiple tickets
 * Returns results for each ticket
 */
export async function batchSpawnPhaseTasks(
  ticketIds: string[],
): Promise<SpawnPhaseTasksResponse[]> {
  const results = await Promise.allSettled(
    ticketIds.map((id) => spawnPhaseTasks(id)),
  );

  return results.map((result, index) => {
    if (result.status === "fulfilled") {
      return result.value;
    }
    return {
      ticket_id: ticketIds[index],
      phase_id: "",
      tasks_spawned: 0,
      task_ids: [],
      error: result.reason?.message || "Failed to spawn tasks",
    };
  });
}
