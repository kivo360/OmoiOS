/**
 * Board API functions (Kanban board operations)
 */

import { apiRequest } from "./client"
import type {
  BoardViewResponse,
  ColumnStats,
  WIPViolation,
  MoveTicketRequest,
} from "./types"

/**
 * Get complete Kanban board view
 */
export async function getBoardView(projectId?: string): Promise<BoardViewResponse> {
  const url = projectId
    ? `/api/v1/board/view?project_id=${projectId}`
    : "/api/v1/board/view"
  return apiRequest<BoardViewResponse>(url)
}

/**
 * Move ticket to a different board column
 */
export async function moveTicket(
  data: MoveTicketRequest
): Promise<{
  ticket_id: string
  new_phase: string
  new_column: string
  status: string
}> {
  return apiRequest<{
    ticket_id: string
    new_phase: string
    new_column: string
    status: string
  }>("/api/v1/board/move", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

/**
 * Get statistics for all board columns
 */
export async function getColumnStats(projectId?: string): Promise<ColumnStats[]> {
  const url = projectId
    ? `/api/v1/board/stats?project_id=${projectId}`
    : "/api/v1/board/stats"
  return apiRequest<ColumnStats[]>(url)
}

/**
 * Check for WIP limit violations
 */
export async function checkWIPViolations(projectId?: string): Promise<WIPViolation[]> {
  const url = projectId
    ? `/api/v1/board/wip-violations?project_id=${projectId}`
    : "/api/v1/board/wip-violations"
  return apiRequest<WIPViolation[]>(url)
}

/**
 * Auto-transition ticket to next column
 */
export async function autoTransitionTicket(ticketId: string): Promise<{
  ticket_id: string
  new_phase?: string
  transitioned: boolean
  reason?: string
}> {
  return apiRequest<{
    ticket_id: string
    new_phase?: string
    transitioned: boolean
    reason?: string
  }>(`/api/v1/board/auto-transition/${ticketId}`, {
    method: "POST",
  })
}

/**
 * Get column for a specific phase
 */
export async function getColumnForPhase(
  phaseId: string
): Promise<{
  id: string
  name: string
  phase_mappings: string[]
  wip_limit: number | null
  order: number
}> {
  return apiRequest<{
    id: string
    name: string
    phase_mappings: string[]
    wip_limit: number | null
    order: number
  }>(`/api/v1/board/column/${phaseId}`)
}
