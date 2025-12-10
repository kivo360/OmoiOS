/**
 * React Query hooks for Phases/Phase Gate API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  validateGate,
  getGateStatus,
  addArtifact,
} from "@/lib/api/phases"
import type { GateValidationResult, PhaseArtifact, PhaseArtifactCreate } from "@/lib/api/types"
import { ticketKeys } from "./useTickets"

// Query keys
export const phaseKeys = {
  all: ["phases"] as const,
  gateStatus: (ticketId: string, phaseId?: string) =>
    [...phaseKeys.all, "gate-status", ticketId, phaseId] as const,
}

/**
 * Hook to fetch gate status for a ticket
 */
export function useGateStatus(ticketId: string | undefined, phaseId?: string) {
  return useQuery<Record<string, unknown>>({
    queryKey: phaseKeys.gateStatus(ticketId!, phaseId),
    queryFn: () => getGateStatus(ticketId!, phaseId),
    enabled: !!ticketId,
  })
}

/**
 * Hook to validate phase gate
 */
export function useValidateGate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ ticketId, phaseId }: { ticketId: string; phaseId?: string }) =>
      validateGate(ticketId, phaseId),
    onSuccess: (_, { ticketId, phaseId }) => {
      queryClient.invalidateQueries({ queryKey: phaseKeys.gateStatus(ticketId, phaseId) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) })
    },
  })
}

/**
 * Hook to add artifact
 */
export function useAddArtifact() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ ticketId, data }: { ticketId: string; data: PhaseArtifactCreate }) =>
      addArtifact(ticketId, data),
    onSuccess: (_, { ticketId, data }) => {
      queryClient.invalidateQueries({ queryKey: phaseKeys.gateStatus(ticketId, data.phase_id) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) })
    },
  })
}
