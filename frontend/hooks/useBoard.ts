/**
 * React Query hooks for Board API (Kanban board)
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getBoardView,
  moveTicket,
  getColumnStats,
  checkWIPViolations,
  autoTransitionTicket,
} from "@/lib/api/board"
import type {
  BoardViewResponse,
  ColumnStats,
  WIPViolation,
  MoveTicketRequest,
} from "@/lib/api/types"
import { ticketKeys } from "./useTickets"

// Query keys
export const boardKeys = {
  all: ["board"] as const,
  view: (projectId?: string) => [...boardKeys.all, "view", projectId] as const,
  stats: (projectId?: string) => [...boardKeys.all, "stats", projectId] as const,
  violations: (projectId?: string) => [...boardKeys.all, "violations", projectId] as const,
}

/**
 * Hook to fetch Kanban board view
 */
export function useBoardView(projectId?: string) {
  return useQuery<BoardViewResponse>({
    queryKey: boardKeys.view(projectId),
    queryFn: () => getBoardView(projectId),
  })
}

/**
 * Hook to fetch column statistics
 */
export function useColumnStats(projectId?: string) {
  return useQuery<ColumnStats[]>({
    queryKey: boardKeys.stats(projectId),
    queryFn: () => getColumnStats(projectId),
  })
}

/**
 * Hook to check WIP limit violations
 */
export function useWIPViolations(projectId?: string) {
  return useQuery<WIPViolation[]>({
    queryKey: boardKeys.violations(projectId),
    queryFn: () => checkWIPViolations(projectId),
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

/**
 * Hook to move ticket between columns
 */
export function useMoveTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: MoveTicketRequest) => moveTicket(data),
    onSuccess: (result) => {
      // Invalidate board views
      queryClient.invalidateQueries({ queryKey: boardKeys.all })
      // Invalidate ticket data
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(result.ticket_id) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook to auto-transition ticket
 */
export function useAutoTransitionTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ticketId: string) => autoTransitionTicket(ticketId),
    onSuccess: (result) => {
      if (result.transitioned) {
        // Invalidate board views
        queryClient.invalidateQueries({ queryKey: boardKeys.all })
        // Invalidate ticket data
        queryClient.invalidateQueries({ queryKey: ticketKeys.detail(result.ticket_id) })
        queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
      }
    },
  })
}
