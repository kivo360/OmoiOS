/**
 * Sandbox API client for interacting with sandbox endpoints
 */

import { api } from "./client"
import type {
  SandboxEventResponse,
  SandboxEventsListResponse,
  SandboxMessage,
  MessageQueueResponse,
  TrajectorySummaryResponse,
  SandboxTask,
} from "./types"

// ============================================================================
// Sandbox Events API
// ============================================================================

/**
 * Get events for a specific sandbox
 */
export async function getSandboxEvents(
  sandboxId: string,
  options: {
    limit?: number
    offset?: number
    event_type?: string
  } = {}
): Promise<SandboxEventsListResponse> {
  const params = new URLSearchParams()
  if (options.limit) params.set("limit", options.limit.toString())
  if (options.offset) params.set("offset", options.offset.toString())
  if (options.event_type) params.set("event_type", options.event_type)

  const query = params.toString()
  return api.get<SandboxEventsListResponse>(
    `/api/v1/sandboxes/${sandboxId}/events${query ? `?${query}` : ""}`
  )
}

/**
 * Get trajectory summary for a sandbox (excludes heartbeats, provides summary)
 * Supports cursor-based pagination for infinite scroll
 */
export async function getSandboxTrajectory(
  sandboxId: string,
  options: {
    limit?: number
    cursor?: string | null
    direction?: "older" | "newer"
  } = {}
): Promise<TrajectorySummaryResponse> {
  const params = new URLSearchParams()
  if (options.limit) params.set("limit", options.limit.toString())
  if (options.cursor) params.set("cursor", options.cursor)
  if (options.direction) params.set("direction", options.direction)

  const query = params.toString()
  return api.get<TrajectorySummaryResponse>(
    `/api/v1/sandboxes/${sandboxId}/trajectory${query ? `?${query}` : ""}`
  )
}

// ============================================================================
// Sandbox Messages API
// ============================================================================

/**
 * Send a message to a sandbox (for user intervention/guidance)
 */
export async function sendSandboxMessage(
  sandboxId: string,
  message: SandboxMessage
): Promise<SandboxEventResponse> {
  return api.post<SandboxEventResponse>(
    `/api/v1/sandboxes/${sandboxId}/messages`,
    message
  )
}

/**
 * Get pending messages for a sandbox (typically used by workers, but useful for UI)
 */
export async function getSandboxMessages(
  sandboxId: string
): Promise<MessageQueueResponse> {
  return api.get<MessageQueueResponse>(
    `/api/v1/sandboxes/${sandboxId}/messages`
  )
}

// ============================================================================
// Sandbox Task API
// ============================================================================

/**
 * Get the task associated with a sandbox
 */
export async function getTaskBySandbox(sandboxId: string): Promise<SandboxTask> {
  return api.get<SandboxTask>(`/api/v1/sandboxes/${sandboxId}/task`)
}

// ============================================================================
// Sandbox Health API
// ============================================================================

/**
 * Check sandbox API health
 */
export async function checkSandboxHealth(): Promise<{ status: string }> {
  return api.get<{ status: string }>("/api/v1/sandboxes/health", false)
}

// ============================================================================
// Sandbox API Object (for convenience)
// ============================================================================

export const sandboxApi = {
  // Events
  getEvents: getSandboxEvents,
  getTrajectory: getSandboxTrajectory,

  // Messages
  sendMessage: sendSandboxMessage,
  getMessages: getSandboxMessages,

  // Task
  getTask: getTaskBySandbox,

  // Health
  checkHealth: checkSandboxHealth,
}

export default sandboxApi
