/**
 * Tickets API functions
 */

import { apiRequest } from "./client"
import type {
  Ticket,
  TicketCreate,
  TicketListResponse,
  TicketTransitionRequest,
} from "./types"

/**
 * List all tickets with pagination
 */
export async function listTickets(params?: {
  limit?: number
  offset?: number
}): Promise<TicketListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set("limit", String(params.limit))
  if (params?.offset) searchParams.set("offset", String(params.offset))

  const query = searchParams.toString()
  const url = query ? `/api/v1/tickets?${query}` : "/api/v1/tickets"

  return apiRequest<TicketListResponse>(url)
}

/**
 * Get a specific ticket by ID
 */
export async function getTicket(ticketId: string): Promise<Ticket> {
  return apiRequest<Ticket>(`/api/v1/tickets/${ticketId}`)
}

/**
 * Create a new ticket
 */
export async function createTicket(data: TicketCreate): Promise<Ticket> {
  return apiRequest<Ticket>("/api/v1/tickets", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

/**
 * Transition ticket to new status
 */
export async function transitionTicket(
  ticketId: string,
  data: TicketTransitionRequest
): Promise<Ticket> {
  return apiRequest<Ticket>(`/api/v1/tickets/${ticketId}/transition`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

/**
 * Block a ticket
 */
export async function blockTicket(
  ticketId: string,
  blockerType: string,
  suggestedRemediation?: string
): Promise<Ticket> {
  const params = new URLSearchParams()
  params.set("blocker_type", blockerType)
  if (suggestedRemediation) params.set("suggested_remediation", suggestedRemediation)

  return apiRequest<Ticket>(`/api/v1/tickets/${ticketId}/block?${params}`, {
    method: "POST",
  })
}

/**
 * Unblock a ticket
 */
export async function unblockTicket(ticketId: string): Promise<Ticket> {
  return apiRequest<Ticket>(`/api/v1/tickets/${ticketId}/unblock`, {
    method: "POST",
  })
}

/**
 * Progress ticket to next phase
 */
export async function progressTicket(
  ticketId: string
): Promise<Ticket | { status: string }> {
  return apiRequest<Ticket | { status: string }>(
    `/api/v1/tickets/${ticketId}/progress`,
    { method: "POST" }
  )
}

/**
 * Approve a pending ticket
 */
export async function approveTicket(
  ticketId: string
): Promise<{ ticket_id: string; status: string }> {
  return apiRequest<{ ticket_id: string; status: string }>(
    "/api/v1/tickets/approve",
    {
      method: "POST",
      body: JSON.stringify({ ticket_id: ticketId }),
    }
  )
}

/**
 * Reject a pending ticket
 */
export async function rejectTicket(
  ticketId: string,
  rejectionReason: string
): Promise<{ ticket_id: string; status: string }> {
  return apiRequest<{ ticket_id: string; status: string }>(
    "/api/v1/tickets/reject",
    {
      method: "POST",
      body: JSON.stringify({ ticket_id: ticketId, rejection_reason: rejectionReason }),
    }
  )
}

/**
 * Get count of pending review tickets
 */
export async function getPendingReviewCount(): Promise<{ pending_count: number }> {
  return apiRequest<{ pending_count: number }>("/api/v1/tickets/pending-review-count")
}

/**
 * Get ticket context
 */
export async function getTicketContext(ticketId: string): Promise<{
  ticket_id: string
  full_context: Record<string, unknown>
  summary: string | null
}> {
  return apiRequest<{
    ticket_id: string
    full_context: Record<string, unknown>
    summary: string | null
  }>(`/api/v1/tickets/${ticketId}/context`)
}
