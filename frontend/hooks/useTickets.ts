/**
 * React Query hooks for Tickets API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  listTickets,
  getTicket,
  createTicket,
  checkDuplicates,
  transitionTicket,
  blockTicket,
  unblockTicket,
  progressTicket,
  approveTicket,
  rejectTicket,
  getPendingReviewCount,
  getTicketContext,
  spawnPhaseTasks,
  batchSpawnPhaseTasks,
} from "@/lib/api/tickets"
import type { SpawnPhaseTasksResponse } from "@/lib/api/tickets"
import type {
  Ticket,
  TicketCreate,
  TicketListParams,
  TicketListResponse,
  TicketTransitionRequest,
  DuplicateCheckResponse,
} from "@/lib/api/types"

// Query keys
export const ticketKeys = {
  all: ["tickets"] as const,
  lists: () => [...ticketKeys.all, "list"] as const,
  list: (params: TicketListParams) => [...ticketKeys.lists(), params] as const,
  details: () => [...ticketKeys.all, "detail"] as const,
  detail: (id: string) => [...ticketKeys.details(), id] as const,
  context: (id: string) => [...ticketKeys.detail(id), "context"] as const,
  pendingCount: () => [...ticketKeys.all, "pending-count"] as const,
}

/**
 * Hook to fetch list of tickets with filtering
 */
export function useTickets(params?: TicketListParams) {
  return useQuery<TicketListResponse>({
    queryKey: ticketKeys.list(params ?? {}),
    queryFn: () => listTickets(params),
  })
}

/**
 * Hook to check for duplicate tickets
 */
export function useCheckDuplicates() {
  return useMutation<
    DuplicateCheckResponse,
    Error,
    { title: string; description?: string; similarityThreshold?: number }
  >({
    mutationFn: ({ title, description, similarityThreshold }) =>
      checkDuplicates(title, description, similarityThreshold),
  })
}

/**
 * Hook to fetch a single ticket
 */
export function useTicket(ticketId: string | undefined) {
  return useQuery<Ticket>({
    queryKey: ticketKeys.detail(ticketId!),
    queryFn: () => getTicket(ticketId!),
    enabled: !!ticketId,
  })
}

/**
 * Hook to fetch ticket context
 */
export function useTicketContext(ticketId: string | undefined) {
  return useQuery({
    queryKey: ticketKeys.context(ticketId!),
    queryFn: () => getTicketContext(ticketId!),
    enabled: !!ticketId,
  })
}

/**
 * Hook to get pending review count
 */
export function usePendingReviewCount() {
  return useQuery({
    queryKey: ticketKeys.pendingCount(),
    queryFn: getPendingReviewCount,
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

/**
 * Hook to create a new ticket
 */
export function useCreateTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: TicketCreate) => createTicket(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ticketKeys.pendingCount() })
    },
  })
}

/**
 * Hook to transition ticket status
 */
export function useTransitionTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      ticketId,
      data,
    }: {
      ticketId: string
      data: TicketTransitionRequest
    }) => transitionTicket(ticketId, data),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook to block a ticket
 */
export function useBlockTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      ticketId,
      blockerType,
      suggestedRemediation,
    }: {
      ticketId: string
      blockerType: string
      suggestedRemediation?: string
    }) => blockTicket(ticketId, blockerType, suggestedRemediation),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook to unblock a ticket
 */
export function useUnblockTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ticketId: string) => unblockTicket(ticketId),
    onSuccess: (_, ticketId) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook to progress ticket to next phase
 */
export function useProgressTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ticketId: string) => progressTicket(ticketId),
    onSuccess: (_, ticketId) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook to approve a pending ticket
 */
export function useApproveTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ticketId: string) => approveTicket(ticketId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(result.ticket_id) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ticketKeys.pendingCount() })
    },
  })
}

/**
 * Hook to reject a pending ticket
 */
export function useRejectTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      ticketId,
      rejectionReason,
    }: {
      ticketId: string
      rejectionReason: string
    }) => rejectTicket(ticketId, rejectionReason),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(result.ticket_id) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ticketKeys.pendingCount() })
    },
  })
}

/**
 * Hook to spawn phase tasks for a ticket
 * This triggers the phase progression workflow
 */
export function useSpawnPhaseTasks() {
  const queryClient = useQueryClient()

  return useMutation<
    SpawnPhaseTasksResponse,
    Error,
    { ticketId: string; phaseId?: string }
  >({
    mutationFn: ({ ticketId, phaseId }) => spawnPhaseTasks(ticketId, phaseId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(result.ticket_id) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
      // Also invalidate board since tasks were spawned
      queryClient.invalidateQueries({ queryKey: ["board"] })
    },
  })
}

/**
 * Hook to batch spawn phase tasks for multiple tickets
 * Used for "Start Processing" button on board
 */
export function useBatchSpawnPhaseTasks() {
  const queryClient = useQueryClient()

  return useMutation<SpawnPhaseTasksResponse[], Error, string[]>({
    mutationFn: (ticketIds) => batchSpawnPhaseTasks(ticketIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ["board"] })
    },
  })
}
