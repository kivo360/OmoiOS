/**
 * Phases/Phase Gate API functions
 */

import { apiRequest } from "./client";
import type {
  GateValidationResult,
  PhaseArtifact,
  PhaseArtifactCreate,
} from "./types";

/**
 * Validate phase gate for a ticket
 */
export async function validateGate(
  ticketId: string,
  phaseId?: string,
): Promise<GateValidationResult> {
  const url = phaseId
    ? `/api/v1/tickets/${ticketId}/validate-gate?phase_id=${phaseId}`
    : `/api/v1/tickets/${ticketId}/validate-gate`;
  return apiRequest<GateValidationResult>(url, { method: "POST" });
}

/**
 * Get gate status for a ticket
 */
export async function getGateStatus(
  ticketId: string,
  phaseId?: string,
): Promise<Record<string, unknown>> {
  const url = phaseId
    ? `/api/v1/tickets/${ticketId}/gate-status?phase_id=${phaseId}`
    : `/api/v1/tickets/${ticketId}/gate-status`;
  return apiRequest<Record<string, unknown>>(url);
}

/**
 * Add artifact to a ticket's phase
 */
export async function addArtifact(
  ticketId: string,
  data: PhaseArtifactCreate,
): Promise<PhaseArtifact> {
  return apiRequest<PhaseArtifact>(`/api/v1/tickets/${ticketId}/artifacts`, {
    method: "POST",
    body: data,
  });
}
